from datetime import datetime, timedelta
import uuid

from app.models import IntentLog


TEACHER_UPDATE_QUESTIONS = [
    "What communication moments did Maya show today?",
    "Which supports helped at school or during caregiving routines?",
    "Were there any friction points Bridge should document for the parent?",
    "What home follow-up would make tomorrow easier?",
]


def default_teacher_contact(child) -> dict:
    profile = child.behavior_profile or {}
    contact = profile.get("teacher_contact") or {}
    return {
        "name": contact.get("name") or "Ms. Rivera",
        "role": contact.get("role") or "1st grade teacher",
        "phone": contact.get("phone") or "",
    }


def merge_teacher_contact(child, requested: dict | None = None) -> dict:
    base = default_teacher_contact(child)
    requested = requested or {}
    return {
        "name": requested.get("name") or base["name"],
        "role": requested.get("role") or base["role"],
        "phone": requested.get("phone") or base["phone"],
    }


def seeded_teacher_messages(teacher_name: str = "Ms. Rivera") -> list[dict]:
    return [
        {
            "role": "assistant",
            "text": f"Hi {teacher_name}, this is Bridge calling with parent approval to collect Maya's school update.",
        },
        {
            "role": "teacher",
            "text": "At drop-off Maya reached for her black hat and settled once she had it.",
        },
        {
            "role": "teacher",
            "text": "Lunch was loud today. She covered her ears and used the Too loud symbol after staff pointed to it.",
        },
        {
            "role": "teacher",
            "text": "During a worksheet she used Help after staff modeled the symbol, then finished the first row.",
        },
        {
            "role": "teacher",
            "text": "Cleanup was easier with a visual timer. She needed a short break before lining up.",
        },
    ]


def teacher_report_from_messages(child, contact: dict, messages: list[dict], call_status: str = "replayed") -> dict:
    teacher_lines = [
        message.get("text", "")
        for message in messages
        if (message.get("role") or "").lower() in {"teacher", "user", "customer"}
    ]
    transcript_excerpt = " ".join(teacher_lines) or "Teacher update transcript is waiting."
    evidence_entries = [
        {
            "context": "School drop-off",
            "confirmed_moment": "I need my hat",
            "support_note": "Teacher reported Maya settled when her hat was available during drop-off.",
            "source": "teacher_daily_update",
        },
        {
            "context": "School lunch",
            "confirmed_moment": "Too loud",
            "support_note": "Lunch noise led Maya to cover her ears; staff supported her with the Too loud symbol.",
            "source": "teacher_daily_update",
        },
        {
            "context": "Classwork",
            "confirmed_moment": "I need help",
            "support_note": "Maya used Help after staff modeled the symbol and then resumed worksheet work.",
            "source": "teacher_daily_update",
        },
        {
            "context": "Cleanup transition",
            "confirmed_moment": "I need a break",
            "support_note": "Visual timer and a short break helped Maya move through cleanup more calmly.",
            "source": "teacher_daily_update",
        },
    ]
    return {
        "title": f"School / caregiver daily update for {child.name}",
        "teacher": {
            "name": contact.get("name") or "Ms. Rivera",
            "role": contact.get("role") or "1st grade teacher",
        },
        "call_status": call_status,
        "transcript_excerpt": transcript_excerpt,
        "observed_communication_moments": [
            "Requested black hat during drop-off as a comfort-item transition support.",
            "Used Too loud during lunch after staff modeled the symbol.",
            "Used Help during worksheet work after staff modeling.",
            "Needed a break during cleanup before lining up.",
        ],
        "supports_used_at_school": [
            "Comfort item available before high-demand transitions.",
            "Staff modeling on the communication board.",
            "Visual timer before cleanup and line-up transitions.",
            "Quieter lunch seating after noise sensitivity signs.",
        ],
        "concerns_or_friction_points": [
            "Noisy lunch environment may make communication access harder.",
            "Drop-off and cleanup transitions need proactive visual supports.",
        ],
        "recommended_home_follow_up": [
            "Offer hat access before transitions and track whether the routine stays calmer.",
            "Keep Too loud, Help, Break, and Hat visible on the home board after school.",
            "Share this pattern with the IEP/AAC team as home-school evidence.",
        ],
        "evidence_entries_added": evidence_entries,
        "parent_review_notice": "Parent review is required before this update is delivered to the school or care-team destination.",
    }


def persist_teacher_evidence(child_id: str, report: dict, db, agent_run_id: str | None = None) -> int:
    entries = report.get("evidence_entries_added") or []
    if not entries:
        return 0

    existing = (
        db.query(IntentLog)
        .filter(IntentLog.child_id == child_id)
        .all()
    )
    existing_keys = {
        (
            (log.context or {}).get("source"),
            (log.context or {}).get("agent_run_id"),
            log.confirmed_label,
            (log.context or {}).get("label"),
        )
        for log in existing
    }

    now = datetime.utcnow()
    created = 0
    for index, entry in enumerate(entries):
        key = (entry.get("source"), agent_run_id, entry.get("confirmed_moment"), entry.get("context"))
        if key in existing_keys:
            continue
        label = entry.get("confirmed_moment") or "School communication moment"
        context_label = entry.get("context") or "School"
        ts = now + timedelta(seconds=index)
        log = IntentLog(
            id=str(uuid.uuid4()),
            child_id=child_id,
            timestamp=ts,
            context={
                "name": context_label.lower().replace(" ", "_"),
                "label": context_label,
                "support_note": entry.get("support_note"),
                "source": entry.get("source") or "teacher_daily_update",
                "agent_run_id": agent_run_id,
            },
            gesture_vector={"source": "teacher_daily_update", "agent_run_id": agent_run_id, "landmarks": []},
            audio_transcript="",
            ranked_intents=[
                {"label": label, "confidence": 0.82},
                {"label": "I need help", "confidence": 0.12},
                {"label": "I need a break", "confidence": 0.06},
            ],
            confirmed_label=label,
            confirmed_at=ts,
            spoken_phrase=label,
        )
        db.add(log)
        created += 1
    if created:
        db.commit()
    return created
