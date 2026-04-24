from datetime import datetime
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm.attributes import flag_modified

from app.agents.teacher_update_agent import persist_teacher_evidence, teacher_report_from_messages
from app.core.agent_events import publish_agent_event
from app.core.database import get_db
from app.integrations.ghost import pgmq_send
from app.models import AgentRun, Child

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _message_from_payload(payload: dict) -> dict:
    return payload.get("message") if isinstance(payload.get("message"), dict) else payload


def _call_id(message: dict) -> str | None:
    call = message.get("call") or {}
    return (
        message.get("callId")
        or message.get("call_id")
        or call.get("id")
        or (message.get("metadata") or {}).get("bridge_call_id")
    )


def _agent_run_id(message: dict) -> str | None:
    metadata = message.get("metadata") or (message.get("call") or {}).get("metadata") or {}
    return (
        metadata.get("bridge_agent_run_id")
        or (message.get("assistantOverrides") or {}).get("variableValues", {}).get("agent_run_id")
    )


def _find_teacher_run(db, message: dict) -> AgentRun | None:
    run_id = _agent_run_id(message)
    if run_id:
        run = db.query(AgentRun).filter(AgentRun.id == run_id, AgentRun.action_type == "teacher_daily_update").first()
        if run:
            return run
    call_id = _call_id(message)
    if not call_id:
        return None
    runs = (
        db.query(AgentRun)
        .filter(AgentRun.action_type == "teacher_daily_update")
        .order_by(AgentRun.created_at.desc())
        .limit(50)
        .all()
    )
    for run in runs:
        draft = run.draft or {}
        status = run.sponsor_statuses or {}
        teacher_status = status.get("vapi_teacher") or {}
        if call_id and call_id in {draft.get("vapi_call_id"), teacher_status.get("call_id"), (teacher_status.get("vapi_response") or {}).get("id")}:
            return run
    return None


def _transcript_message(message: dict) -> dict | None:
    text = message.get("transcript") or message.get("text")
    if not text:
        return None
    return {
        "role": message.get("role") or message.get("speaker") or "teacher",
        "text": text,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _messages_from_end_report(message: dict) -> list[dict]:
    artifact = message.get("artifact") or {}
    messages = artifact.get("messages") or message.get("messages") or []
    parsed = []
    for item in messages:
        text = item.get("message") or item.get("text") or item.get("content")
        if isinstance(text, list):
            text = " ".join(str(part.get("text", part)) for part in text)
        if not text:
            continue
        parsed.append({
            "role": item.get("role") or "teacher",
            "text": str(text),
            "timestamp": datetime.utcnow().isoformat(),
        })
    if parsed:
        return parsed
    transcript = artifact.get("transcript") or message.get("transcript")
    if transcript:
        return [{"role": "teacher", "text": transcript, "timestamp": datetime.utcnow().isoformat()}]
    return []


@router.post("/vapi")
async def vapi_webhook(payload: dict, db=Depends(get_db)):
    message = _message_from_payload(payload)
    message_type = message.get("type") or message.get("messageType") or "unknown"
    run = _find_teacher_run(db, message)
    if not run:
        return {"status": "ignored", "reason": "No matching teacher update AgentRun"}
    child = db.query(Child).filter(Child.id == run.child_id).first()
    if not child:
        return {"status": "ignored", "reason": "Child not found"}

    draft = dict(run.draft or {})
    webhook_events = draft.get("webhook_events") or []
    webhook_events.append({
        "type": message_type,
        "received_at": datetime.utcnow().isoformat(),
        "call_id": _call_id(message),
    })
    draft["webhook_events"] = webhook_events

    if message_type == "status-update":
        draft["call_status"] = message.get("status") or draft.get("call_status") or "status-update"
        await publish_agent_event(child.id, "teacher_call_status", f"Vapi teacher call status: {draft['call_status']}.", {"agent_run_id": run.id})

    transcript_item = _transcript_message(message)
    if transcript_item:
        messages = draft.get("transcript_messages") or []
        messages.append(transcript_item)
        draft["transcript_messages"] = messages
        await publish_agent_event(child.id, "teacher_transcript_received", "Teacher transcript snippet received from Vapi.", {"agent_run_id": run.id, "snippet": transcript_item["text"][:140]})

    if message_type == "end-of-call-report":
        messages = _messages_from_end_report(message) or draft.get("transcript_messages") or []
        if messages:
            draft["transcript_messages"] = messages
        contact = draft.get("teacher_contact") or {"name": "Ms. Rivera", "role": "1st grade teacher"}
        report = teacher_report_from_messages(child, contact, draft.get("transcript_messages") or [], call_status="webhook_received")
        evidence_count = persist_teacher_evidence(child.id, report, db, run.id)
        draft["mini_report"] = report
        draft["evidence_entries_added"] = evidence_count
        draft["call_status"] = "complete"
        run.status = "report_ready"
        await publish_agent_event(child.id, "teacher_report_generated", "Teacher mini-report generated from Vapi end-of-call report.", {"agent_run_id": run.id, "evidence_entries_added": evidence_count})

    run.draft = draft
    run.updated_at = datetime.utcnow()
    flag_modified(run, "draft")
    db.add(run)
    db.commit()
    pgmq_send("bridge_agent_events", {
        "event": f"vapi_{message_type}",
        "agent_run_id": run.id,
        "child_id": child.id,
        "call_id": _call_id(message),
        "ts": time.time(),
    })
    return {"status": "received", "message_type": message_type, "agent_run_id": run.id}
