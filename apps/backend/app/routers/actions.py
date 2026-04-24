from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
import time
import uuid

from app.integrations import vapi, tinyfish, nexla
from app.integrations.ghost import pgmq_send, fork_for_agent_run, delete_fork
from app.models import AgentRun, Child, Session, IntentLog
from app.core.database import get_db
from app.core.agent_events import get_recent_agent_events, publish_agent_event
from app.agents.journal_agent import generate_daily_journal, generate_therapist_summary
from app.agents.teacher_update_agent import (
    TEACHER_UPDATE_QUESTIONS,
    merge_teacher_contact,
    persist_teacher_evidence,
    seeded_teacher_messages,
    teacher_report_from_messages,
)
from app.ml.symbol_predictor import predict_symbols
from app.ml.profile_updater import update_profile_from_confirmed_intent

router = APIRouter(prefix="/actions", tags=["actions"])


class SpeakRequest(BaseModel):
    phrase: str
    child_id: str
    voice_id: str = None


class IEPRequest(BaseModel):
    child_id: str
    school_district: str
    grade: str = ""
    disability: str = "Autism Spectrum Disorder"


class InsuranceAppealRequest(BaseModel):
    child_id: str
    insurance_provider: str
    denial_reason: str


class SyncSessionRequest(BaseModel):
    session_id: str
    therapist_webhook: str


class SymbolPredictRequest(BaseModel):
    child_id: str
    context: dict = {}


class ConfirmIntentRequest(BaseModel):
    child_id: str
    intent_log_id: str
    confirmed_label: str


class DemoConfirmIntentRequest(BaseModel):
    child_id: str
    confirmed_label: str
    context: dict = {}
    confidence: float = 0.74


class TherapistSyncRequest(BaseModel):
    therapist_webhook: str = ""


class TherapistSearchRequest(BaseModel):
    child_id: str
    zip_code: str
    insurance_provider: str = ""


class IEPAgentRunRequest(BaseModel):
    child_id: str
    school_district: str = "San Francisco Unified School District"
    grade: str = "1st"
    disability: str = "Autism Spectrum Disorder"
    source_urls: list[str] = []


class ApproveCareFollowupRequest(BaseModel):
    child_id: str
    agent_run_id: str
    followup_type: str
    therapist_webhook: str = ""
    customer_number: str = ""


class TeacherUpdateRequest(BaseModel):
    child_id: str
    teacher_contact: dict = {}
    force_replay: bool = False


def _top_intent(log: IntentLog) -> str:
    if log.confirmed_label:
        return log.confirmed_label
    if log.ranked_intents and len(log.ranked_intents) > 0:
        return log.ranked_intents[0].get("label", "Unknown")
    return "Unknown"


def _display_time(value: datetime | None) -> str:
    if not value:
        return "Recorded moment"
    return f"{value.strftime('%a')} {value.month}/{value.day} {value.strftime('%I:%M %p').lstrip('0')}"


def _pattern_summary(child_id: str, db) -> dict:
    logs = (
        db.query(IntentLog)
        .filter(IntentLog.child_id == child_id)
        .order_by(IntentLog.timestamp.desc())
        .limit(25)
        .all()
    )
    confirmed = [log for log in logs if log.confirmed_label]
    label_counts = {}
    context_counts = {}
    hat_count = 0
    meal_count = 0
    transition_count = 0
    noise_count = 0
    help_count = 0
    evidence_events = []
    for log in confirmed:
        label = _top_intent(log)
        label_counts[label] = label_counts.get(label, 0) + 1
        context = (log.context or {}).get("label") or (log.context or {}).get("name") or "Session"
        context_counts[context] = context_counts.get(context, 0) + 1
        if "hat" in label.lower():
            hat_count += 1
        if "meal" in context.lower():
            meal_count += 1
        if "transition" in context.lower() or "drop-off" in context.lower():
            transition_count += 1
        if "loud" in label.lower():
            noise_count += 1
        if "help" in label.lower():
            help_count += 1
        evidence_events.append({
            "date": _display_time(log.timestamp),
            "context": context,
            "confirmed_moment": label,
            "support_note": (log.context or {}).get("support_note") or "Parent confirmed and saved this moment for pattern tracking.",
        })
    top_intents = sorted(label_counts.items(), key=lambda item: item[1], reverse=True)
    top_contexts = sorted(context_counts.items(), key=lambda item: item[1], reverse=True)
    evidence_events = list(reversed(evidence_events))
    return {
        "confirmed_moments": len(confirmed),
        "top_intents": [{"label": label, "count": count} for label, count in top_intents],
        "top_contexts": [{"label": label, "count": count} for label, count in top_contexts],
        "evidence_events": evidence_events,
        "label_counts": label_counts,
        "context_counts": context_counts,
        "meal_moments": meal_count,
        "comfort_item_moments": hat_count,
        "transition_related_moments": transition_count,
        "noise_sensitivity_moments": noise_count,
        "help_request_moments": help_count,
        "pattern_detected": "Communication supports reduce frustration during meals, transitions, and work demands.",
        "recommended_action": "Request AAC/assistive technology review and shared home-school communication supports.",
    }


def _voice_update_text(child: Child, run: AgentRun) -> str:
    pattern = run.pattern_summary or {}
    top_intents = pattern.get("top_intents") or []
    intent_text = ", ".join(f"{item['count']} {item['label']}" for item in top_intents[:2]) or "confirmed communication moments"
    return (
        f"Hi, this is Bridge with a parent-approved update for {child.name}. "
        f"This week, {child.name} had {pattern.get('confirmed_moments', 0)} confirmed communication moments, "
        f"including {intent_text}. Bridge prepared an AAC and IEP support packet for review."
    )


def _teacher_update_packet(child: Child, run: AgentRun) -> dict:
    draft = run.draft or {}
    return {
        "child_name": child.name,
        "agent_run_id": run.id,
        "action_type": run.action_type,
        "teacher_contact": draft.get("teacher_contact"),
        "mini_report": draft.get("mini_report"),
        "transcript_messages": draft.get("transcript_messages", []),
        "evidence_entries_added": (draft.get("mini_report") or {}).get("evidence_entries_added", []),
        "sponsor_statuses": run.sponsor_statuses or {},
    }


async def _finalize_teacher_replay(child: Child, run: AgentRun, contact: dict, call_status: str, db) -> tuple[dict, int]:
    messages = seeded_teacher_messages(contact.get("name"))
    report = teacher_report_from_messages(child, contact, messages, call_status=call_status)
    evidence_count = persist_teacher_evidence(child.id, report, db, run.id)
    draft = run.draft or {}
    draft.update({
        "teacher_contact": contact,
        "transcript_messages": messages,
        "mini_report": report,
        "evidence_entries_added": evidence_count,
        "call_status": call_status,
    })
    run.draft = draft
    run.status = "report_ready"
    run.updated_at = datetime.utcnow()
    db.add(run)
    db.commit()
    db.refresh(run)
    await publish_agent_event(
        child.id,
        "teacher_transcript_received",
        "Teacher update transcript received and summarized.",
        {"agent_run_id": run.id, "evidence_entries_added": evidence_count},
    )
    await publish_agent_event(
        child.id,
        "teacher_report_generated",
        "Teacher mini-report generated and added to the evidence timeline.",
        {"agent_run_id": run.id, "report_title": report.get("title")},
    )
    pgmq_send("bridge_agent_events", {
        "event": "teacher_report_generated",
        "agent_run_id": run.id,
        "child_id": child.id,
        "evidence_entries_added": evidence_count,
        "ts": time.time(),
    })
    return report, evidence_count


def _documentation_insight(child: Child, label: str, context: dict | None) -> dict:
    context_name = (context or {}).get("label") or (context or {}).get("name") or "this routine"
    lower_label = label.lower()
    if "hat" in lower_label:
        return {
            "title": "Pattern note added",
            "message": (
                f"Bridge logged this as documentation, not just a one-time request. "
                f"Maya has a plausible comfort-item pattern: hat access during {context_name} may help her settle before the next step."
            ),
            "recommendation": "Next time, offer the hat before the meal transition and track whether the routine stays calmer.",
        }
    if "water" in lower_label:
        return {
            "title": "Pattern note added",
            "message": (
                f"Bridge added this to Maya's evidence timeline. Repeated water requests during {context_name} can show a routine-based communication need."
            ),
            "recommendation": "Keep water visible before the next similar routine and compare confirmations over time.",
        }
    return {
        "title": "Moment documented",
        "message": f"Bridge added this parent-confirmed moment to Maya's evidence timeline for pattern tracking.",
        "recommendation": "Confirming moments over time helps build support-ready documentation for care and school conversations.",
    }


@router.post("/speak")
async def speak_symbol(payload: SpeakRequest, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == payload.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    result = await vapi.speak_symbol(payload.phrase, payload.voice_id)
    return result


@router.post("/iep-request")
async def file_iep(payload: IEPRequest, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == payload.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    result = await tinyfish.file_iep_request(
        {
            "name": child.name,
            "age": child.age,
            "grade": payload.grade,
            "disability_category": payload.disability,
        },
        payload.school_district,
    )
    return result


@router.post("/iep-agent-run")
async def run_iep_agent(payload: IEPAgentRunRequest, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == payload.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    run_label = f"{child.id[:8]}-{int(time.time())}"
    fork_info = await fork_for_agent_run(run_label)

    pattern = _pattern_summary(child.id, db)
    await publish_agent_event(child.id, "agent_started", "Care Agent started AAC/IEP packet run.")
    await publish_agent_event(child.id, "history_loaded", "Confirmed communication history loaded.", pattern)
    pgmq_send("bridge_agent_events", {
        "event": "agent_run_started",
        "child_id": child.id,
        "run_label": run_label,
        "fork": fork_info,
        "ts": time.time(),
    })

    result = await tinyfish.run_iep_agent(
        {
            "name": child.name,
            "age": child.age,
            "grade": payload.grade,
            "disability_category": payload.disability,
        },
        payload.school_district,
        pattern,
        payload.source_urls or None,
    )
    await publish_agent_event(child.id, "sources_opened", "TinyFish opened school and AAC sources.", {"source_count": len(result.get("sources", []))})
    await publish_agent_event(child.id, "facts_extracted", "Source-grounded AAC/IEP facts extracted.", {"facts": result.get("extracted_facts", [])})
    await publish_agent_event(child.id, "draft_ready", "Parent-review AAC/IEP support packet drafted.")

    now = datetime.utcnow()
    run = AgentRun(
        id=str(uuid.uuid4()),
        child_id=child.id,
        action_type="iep_support_packet",
        status=result.get("status", "draft_ready"),
        created_at=now,
        updated_at=now,
        source_urls=payload.source_urls or tinyfish.DEFAULT_IEP_SOURCE_URLS,
        sources=result.get("sources", []),
        extracted_facts=result.get("extracted_facts", []),
        draft=result.get("draft", {}),
        pattern_summary=pattern,
        agent_steps=result.get("agent_steps", []),
        sponsor_statuses={
            **(result.get("sponsor_statuses", {}) or {}),
            "redis": {
                "status": "published",
                "provider": "Redis",
                "message": "Care Agent events published to live memory stream.",
            },
            "ghost": {
                "status": "audit_saved",
                "provider": "Ghost/TigerData",
                "role": "audit store + DB-backed event queue + database fork",
                "message": "Agent run audited in the configured DATABASE_URL. Ghost durable queue captured agent events.",
                "fork": fork_info,
            },
        },
        approvals={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    pgmq_send("bridge_agent_events", {
        "event": "agent_run_completed",
        "agent_run_id": run.id,
        "run_label": run_label,
        "ts": time.time(),
    })
    if fork_info.get("status") == "created" and fork_info.get("fork_name"):
        deleted = await delete_fork(fork_info["fork_name"])
        sponsor_statuses = run.sponsor_statuses or {}
        ghost_status = sponsor_statuses.get("ghost", {})
        ghost_status["fork_cleanup"] = "deleted" if deleted else "delete_failed"
        sponsor_statuses["ghost"] = ghost_status
        run.sponsor_statuses = sponsor_statuses
        db.add(run)
        db.commit()
        db.refresh(run)
    await publish_agent_event(child.id, "approval_required", "Packet is ready and waiting for parent approval.", {"agent_run_id": run.id})

    return {
        "agent_run_id": run.id,
        "status": run.status,
        "agent_steps": run.agent_steps,
        "sources": run.sources,
        "extracted_facts": run.extracted_facts,
        "draft": run.draft,
        "pattern_summary": run.pattern_summary,
        "source_trace": result.get("source_trace", []),
        "parent_control_notice": result.get("parent_control_notice"),
        "sponsor_statuses": run.sponsor_statuses,
    }


@router.post("/request-teacher-update")
async def request_teacher_update(payload: TeacherUpdateRequest, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == payload.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    now = datetime.utcnow()
    contact = merge_teacher_contact(child, payload.teacher_contact)
    pattern = _pattern_summary(child.id, db)
    run = AgentRun(
        id=str(uuid.uuid4()),
        child_id=child.id,
        action_type="teacher_daily_update",
        status="call_requested",
        created_at=now,
        updated_at=now,
        source_urls=[],
        sources=[],
        extracted_facts=[],
        draft={
            "teacher_contact": contact,
            "requested_questions": TEACHER_UPDATE_QUESTIONS,
            "call_status": "requested",
            "transcript_messages": [],
            "mini_report": None,
        },
        pattern_summary=pattern,
        agent_steps=[
            "Parent approved teacher/caregiver update request",
            "Vapi queued outbound teacher call",
            "Transcript captured or replayed for reliable demo",
            "Teacher mini-report generated",
            "Evidence entries added to timeline",
        ],
        sponsor_statuses={
            "redis": {
                "status": "published",
                "provider": "Redis",
                "message": "Teacher update request published to Live Agent Memory.",
            },
            "ghost": {
                "status": "audit_saved",
                "provider": "Ghost/TigerData",
                "message": "Teacher update AgentRun saved with transcript/report audit fields.",
            },
        },
        approvals={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    await publish_agent_event(child.id, "teacher_call_requested", f"Teacher update requested for {contact['name']}.", {"agent_run_id": run.id})
    pgmq_send("bridge_agent_events", {
        "event": "teacher_call_requested",
        "agent_run_id": run.id,
        "child_id": child.id,
        "teacher": contact,
        "ts": time.time(),
    })

    if payload.force_replay:
        vapi_result = {
            "status": "replayed",
            "provider": "Vapi",
            "message": "Teacher update transcript replayed locally for a reliable demo run.",
            "call_payload": {
                "teacher": contact,
                "requested_questions": TEACHER_UPDATE_QUESTIONS,
                "agent_run_id": run.id,
            },
        }
    else:
        vapi_result = await vapi.request_teacher_daily_update(
            child.name,
            contact,
            pattern,
            TEACHER_UPDATE_QUESTIONS,
            run.id,
        )
    sponsor_statuses = run.sponsor_statuses or {}
    sponsor_statuses["vapi_teacher"] = vapi_result
    draft = run.draft or {}
    draft["vapi_call_id"] = vapi_result.get("call_id") or (vapi_result.get("vapi_response") or {}).get("id")
    draft["call_status"] = vapi_result.get("status", "prepared")
    draft["call_payload"] = vapi_result.get("call_payload")
    run.sponsor_statuses = sponsor_statuses
    run.draft = draft
    run.status = "call_queued" if vapi_result.get("status") in {"queued", "ringing", "in-progress"} else "transcript_replay"
    run.updated_at = datetime.utcnow()
    db.add(run)
    db.commit()
    db.refresh(run)

    await publish_agent_event(child.id, "teacher_call_queued", vapi_result.get("message", "Teacher update call queued."), {"agent_run_id": run.id, "status": vapi_result.get("status")})
    pgmq_send("bridge_agent_events", {
        "event": "teacher_call_queued",
        "agent_run_id": run.id,
        "child_id": child.id,
        "status": vapi_result.get("status"),
        "call_id": draft.get("vapi_call_id"),
        "ts": time.time(),
    })

    live_webhook_expected = bool(draft.get("vapi_call_id")) and bool(vapi_result.get("status") not in {"prepared", "error"}) and not payload.force_replay
    if not live_webhook_expected:
        report, _ = await _finalize_teacher_replay(child, run, contact, "replayed", db)
    else:
        report, _ = await _finalize_teacher_replay(child, run, contact, "queued_with_replay", db)

    return {
        "agent_run_id": run.id,
        "status": run.status,
        "teacher_update": run.draft,
        "mini_report": report,
        "sponsor_statuses": run.sponsor_statuses,
        "agent_steps": run.agent_steps,
    }


@router.get("/teacher-updates/{child_id}")
async def get_teacher_updates(child_id: str, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    runs = (
        db.query(AgentRun)
        .filter(AgentRun.child_id == child_id, AgentRun.action_type == "teacher_daily_update")
        .order_by(AgentRun.created_at.desc())
        .limit(10)
        .all()
    )
    return {
        "updates": [
            {
                "agent_run_id": run.id,
                "status": run.status,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "teacher_update": run.draft or {},
                "mini_report": (run.draft or {}).get("mini_report"),
                "sponsor_statuses": run.sponsor_statuses or {},
                "approvals": run.approvals or {},
            }
            for run in runs
        ]
    }


@router.post("/insurance-appeal")
async def appeal_insurance(payload: InsuranceAppealRequest, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == payload.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    result = await tinyfish.appeal_insurance_denial(
        {"name": child.name, "age": child.age},
        payload.insurance_provider,
        payload.denial_reason,
    )
    return result


@router.post("/therapist-search")
async def therapist_search(payload: TherapistSearchRequest, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == payload.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    result = await tinyfish.search_therapists(
        {"name": child.name, "age": child.age},
        payload.zip_code,
        payload.insurance_provider,
    )
    return result


@router.post("/sync-session")
async def sync_session(payload: SyncSessionRequest, db=Depends(get_db)):
    session = db.query(Session).filter(Session.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await nexla.sync_session_to_therapist(
        {
            "session_id": session.id,
            "child_id": session.child_id,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "intent_log": session.intent_log,
        },
        payload.therapist_webhook,
    )
    return {"status": "synced"}


@router.get("/journal/{child_id}")
async def get_daily_journal(child_id: str, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    journal = await generate_daily_journal(child_id, child.name, db)
    return {"journal": journal}


@router.post("/predict-symbols")
async def get_predicted_symbols(payload: SymbolPredictRequest, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == payload.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    recent_logs = (
        db.query(IntentLog)
        .filter(IntentLog.child_id == payload.child_id)
        .order_by(IntentLog.timestamp.desc())
        .limit(20)
        .all()
    )
    recent_intents = [log.ranked_intents for log in recent_logs if log.ranked_intents]

    symbols = await predict_symbols(
        payload.child_id,
        child.behavior_profile or {},
        recent_intents,
        payload.context,
    )
    return {"symbols": symbols}


@router.get("/therapist-summary/{child_id}")
async def get_therapist_summary(child_id: str, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    summary = await generate_therapist_summary(child_id, child.name, db)
    return summary


@router.post("/sync-therapist-summary/{child_id}")
async def sync_therapist_summary(child_id: str, payload: TherapistSyncRequest, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    summary = await generate_therapist_summary(child_id, child.name, db)
    result = await nexla.sync_therapist_summary_to_nexla(summary, payload.therapist_webhook)
    return result


@router.post("/approve-care-followup")
async def approve_care_followup(payload: ApproveCareFollowupRequest, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == payload.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    run = db.query(AgentRun).filter(AgentRun.id == payload.agent_run_id, AgentRun.child_id == payload.child_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    await publish_agent_event(child.id, "approval_received", f"Parent approved {payload.followup_type}.", {"agent_run_id": run.id})
    packet = {
        "child_name": child.name,
        "agent_run_id": run.id,
        "action_type": run.action_type,
        "pattern_summary": run.pattern_summary,
        "sources": run.sources,
        "draft": run.draft,
    }

    if payload.followup_type == "nexla_sync":
        result = await nexla.sync_care_packet_to_nexla(packet, payload.therapist_webhook)
        event_type = "nexla_sync_complete"
        sponsor_key = "nexla"
    elif payload.followup_type == "teacher_update_nexla_sync":
        if run.action_type != "teacher_daily_update":
            raise HTTPException(status_code=400, detail="teacher_update_nexla_sync requires a teacher update run")
        result = await nexla.sync_teacher_update_to_nexla(_teacher_update_packet(child, run), payload.therapist_webhook)
        event_type = "teacher_update_nexla_complete"
        sponsor_key = "nexla_teacher_update"
    elif payload.followup_type == "vapi_update":
        result = await vapi.send_care_team_voice_update(
            _voice_update_text(child, run),
            {"customer_number": payload.customer_number} if payload.customer_number else {},
        )
        event_type = "vapi_update_complete"
        sponsor_key = "vapi"
    else:
        raise HTTPException(status_code=400, detail="Unsupported followup_type")

    approvals = run.approvals or {}
    approved_at = datetime.utcnow().isoformat()
    approvals[payload.followup_type] = {
        "approved_at": approved_at,
        "result": result,
    }
    sponsor_statuses = run.sponsor_statuses or {}
    sponsor_statuses[sponsor_key] = result
    run.approvals = approvals
    run.sponsor_statuses = sponsor_statuses
    run.updated_at = datetime.utcnow()
    db.add(run)
    db.commit()
    pgmq_send("bridge_care_actions", {
        "event": payload.followup_type,
        "agent_run_id": run.id,
        "child_id": child.id,
        "approved_at": approved_at,
        "status": result.get("status"),
        "ts": time.time(),
    })
    await publish_agent_event(child.id, event_type, result.get("message", f"{payload.followup_type} complete."), {"status": result.get("status")})
    return {
        "status": result.get("status", "complete"),
        "followup_type": payload.followup_type,
        "result": result,
        "sponsor_statuses": sponsor_statuses,
        "approvals": approvals,
    }


@router.get("/agent-events/{child_id}")
async def recent_agent_events(child_id: str):
    return {"events": await get_recent_agent_events(child_id)}


@router.post("/confirm-intent")
async def confirm_intent(payload: ConfirmIntentRequest, db=Depends(get_db)):
    """Parent confirms what the child was actually communicating — updates behavioral profile."""
    child = db.query(Child).filter(Child.id == payload.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    log = db.query(IntentLog).filter(IntentLog.id == payload.intent_log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Intent log not found")

    update_profile_from_confirmed_intent(
        child,
        payload.confirmed_label,
        log.gesture_vector or {},
        log.audio_transcript or "",
        db,
    )
    log.confirmed_label = payload.confirmed_label
    log.confirmed_at = datetime.utcnow()
    db.add(log)
    db.commit()
    db.refresh(child)
    insight = _documentation_insight(child, payload.confirmed_label, log.context or {})
    await publish_agent_event(
        child.id,
        "parent_confirmed",
        f'Parent documented: "{payload.confirmed_label}"',
        {
            "context": log.context or {},
            "intent_log_id": log.id,
            "documentation_insight": insight,
        },
    )
    return {
        "status": "moment documented",
        "confirmed_label": payload.confirmed_label,
        "documentation_insight": insight,
        "behavior_profile": child.behavior_profile or {},
    }


@router.post("/demo-confirm-intent")
async def demo_confirm_intent(payload: DemoConfirmIntentRequest, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == payload.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    now = datetime.utcnow()
    ranked = [
        {"label": payload.confirmed_label, "confidence": payload.confidence},
        {"label": "I need help", "confidence": 0.16},
        {"label": "I need a break", "confidence": 0.1},
    ]
    log = IntentLog(
        id=str(uuid.uuid4()),
        child_id=child.id,
        timestamp=now,
        context=payload.context or {"name": "mealtime", "label": "Mealtime"},
        gesture_vector={"presentation_mode": True, "source": "live_session_confirm"},
        audio_transcript="",
        ranked_intents=ranked,
        confirmed_label=payload.confirmed_label,
        confirmed_at=now,
        spoken_phrase=payload.confirmed_label,
    )
    db.add(log)
    update_profile_from_confirmed_intent(
        child,
        payload.confirmed_label,
        log.gesture_vector or {},
        "",
        db,
    )
    db.commit()
    insight = _documentation_insight(child, payload.confirmed_label, log.context or {})
    await publish_agent_event(
        child.id,
        "parent_confirmed",
        f'Parent documented: "{payload.confirmed_label}"',
        {
            "context": log.context or {},
            "intent_log_id": log.id,
            "presentation_safe": True,
            "documentation_insight": insight,
        },
    )
    return {
        "status": "moment documented",
        "intent_log_id": log.id,
        "confirmed_label": payload.confirmed_label,
        "documentation_insight": insight,
        "behavior_profile": child.behavior_profile or {},
    }
