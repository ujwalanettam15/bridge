"""
Updates a child's behavior_profile from confirmed intents.
Called when a parent confirms what their child was communicating,
building a personalized signal→intent map over time.
"""
from app.models import Child, IntentLog
from datetime import datetime, timedelta
from sqlalchemy.orm.attributes import flag_modified


def update_profile_from_confirmed_intent(
    child: Child,
    intent_label: str,
    gesture_vector: dict,
    audio_transcript: str,
    db,
) -> None:
    profile = dict(child.behavior_profile or {})

    # Track how many times each intent has been confirmed
    confirmed = profile.setdefault("confirmed_intents", {})
    confirmed[intent_label] = confirmed.get(intent_label, 0) + 1

    # Store distinctive audio patterns for this intent (up to 10)
    if audio_transcript:
        sounds = profile.setdefault("intent_sounds", {})
        history = sounds.setdefault(intent_label, [])
        if audio_transcript not in history:
            history.append(audio_transcript)
        sounds[intent_label] = history[-10:]

    # Track whether hands were present for this intent
    hand_signals = profile.setdefault("hand_signals", {})
    hand_signals[intent_label] = gesture_vector.get("has_hand", False)

    child.behavior_profile = profile
    flag_modified(child, "behavior_profile")
    db.add(child)
    db.commit()


def get_recent_intents(child_id: str, minutes: int, db) -> list:
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    logs = (
        db.query(IntentLog)
        .filter(IntentLog.child_id == child_id, IntentLog.timestamp >= cutoff)
        .order_by(IntentLog.timestamp.desc())
        .all()
    )
    return [
        {
            "label": i["label"],
            "confidence": i.get("confidence", i.get("probability", 0)),
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
        if log.ranked_intents
        for i in log.ranked_intents[:1]  # top intent per log entry
    ]
