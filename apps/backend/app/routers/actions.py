from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.integrations import vapi, tinyfish, nexla
from app.models import AgentRun, Child, Session, IntentLog
from app.core.database import get_db
from app.core.agent_events import get_recent_agent_events, publish_agent_event
from app.agents.journal_agent import generate_daily_journal, generate_therapist_summary
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


def _top_intent(log: IntentLog) -> str:
    if log.confirmed_label:
        return log.confirmed_label
    if log.ranked_intents and len(log.ranked_intents) > 0:
        return log.ranked_intents[0].get("label", "Unknown")
    return "Unknown"


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
    for log in confirmed:
        label = _top_intent(log)
        label_counts[label] = label_counts.get(label, 0) + 1
        context = (log.context or {}).get("label") or (log.context or {}).get("name") or "Session"
        context_counts[context] = context_counts.get(context, 0) + 1
    top_intents = sorted(label_counts.items(), key=lambda item: item[1], reverse=True)
    top_contexts = sorted(context_counts.items(), key=lambda item: item[1], reverse=True)
    return {
        "confirmed_moments": len(confirmed),
        "top_intents": [{"label": label, "count": count} for label, count in top_intents],
        "top_contexts": [{"label": label, "count": count} for label, count in top_contexts],
        "pattern_detected": "Repeated communication access needs during daily routines.",
        "recommended_action": "Draft AAC/IEP support packet",
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

    pattern = _pattern_summary(child.id, db)
    await publish_agent_event(child.id, "agent_started", "Care Agent started AAC/IEP packet run.")
    await publish_agent_event(child.id, "history_loaded", "Confirmed communication history loaded.", pattern)

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
                "provider": "Ghost/Postgres",
                "message": "Agent run saved to the configured DATABASE_URL audit table.",
            },
        },
        approvals={},
    )
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
        "parent_control_notice": result.get("parent_control_notice"),
        "sponsor_statuses": run.sponsor_statuses,
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
    approvals[payload.followup_type] = {
        "approved_at": datetime.utcnow().isoformat(),
        "result": result,
    }
    sponsor_statuses = run.sponsor_statuses or {}
    sponsor_statuses[sponsor_key] = result
    run.approvals = approvals
    run.sponsor_statuses = sponsor_statuses
    run.updated_at = datetime.utcnow()
    db.add(run)
    db.commit()
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
    await publish_agent_event(
        child.id,
        "parent_confirmed",
        f'Parent confirmed: "{payload.confirmed_label}"',
        {
            "context": log.context or {},
            "intent_log_id": log.id,
        },
    )
    return {
        "status": "profile updated",
        "confirmed_label": payload.confirmed_label,
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
        gesture_vector={"demo_mode": True, "source": "live_session_confirm"},
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
    await publish_agent_event(
        child.id,
        "parent_confirmed",
        f'Parent confirmed: "{payload.confirmed_label}"',
        {
            "context": log.context or {},
            "intent_log_id": log.id,
            "demo_safe": True,
        },
    )
    return {
        "status": "profile updated",
        "intent_log_id": log.id,
        "confirmed_label": payload.confirmed_label,
        "behavior_profile": child.behavior_profile or {},
    }
