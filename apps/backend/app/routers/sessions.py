from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
import os
import uuid

from app.models import Child, IntentLog, Session
from app.core.database import get_db

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    child_id: str


@router.post("/")
def create_session(payload: SessionCreate, db=Depends(get_db)):
    session = Session(
        id=str(uuid.uuid4()),
        child_id=payload.child_id,
        started_at=datetime.utcnow(),
        intent_log=[],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}")
def get_session(session_id: str, db=Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/child/{child_id}")
def get_child_sessions(child_id: str, db=Depends(get_db)):
    return db.query(Session).filter(Session.child_id == child_id).all()


@router.get("/child/{child_id}/logs")
def get_child_intent_logs(child_id: str, db=Depends(get_db)):
    return (
        db.query(IntentLog)
        .filter(IntentLog.child_id == child_id)
        .order_by(IntentLog.timestamp.desc())
        .limit(100)
        .all()
    )


@router.post("/child/{child_id}/seed-demo")
def seed_demo_logs(child_id: str, db=Depends(get_db)):
    from datetime import timedelta

    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    db.query(IntentLog).filter(IntentLog.child_id == child_id).delete()

    now = datetime.utcnow()
    monday = now - timedelta(days=now.weekday())
    demo_events = [
        (
            (monday - timedelta(days=7)).replace(hour=7, minute=35, second=0, microsecond=0),
            "school_dropoff",
            "School drop-off",
            "I need my hat",
            0.81,
            "Calmer when hat was available before entering class.",
        ),
        (
            (monday - timedelta(days=6)).replace(hour=12, minute=10, second=0, microsecond=0),
            "school_lunch",
            "School lunch",
            "Too loud",
            0.68,
            "Moved to quieter table and used visual choice to rejoin lunch.",
        ),
        (
            (monday - timedelta(days=5)).replace(hour=15, minute=24, second=0, microsecond=0),
            "therapy",
            "Therapy",
            "I need help",
            0.74,
            "Reached for picture card after modeled help request.",
        ),
        (
            (monday - timedelta(days=4)).replace(hour=18, minute=12, second=0, microsecond=0),
            "mealtime",
            "Meal",
            "I want more",
            0.77,
            "Continued meal after more was modeled on the board.",
        ),
        (
            (monday - timedelta(days=3)).replace(hour=19, minute=2, second=0, microsecond=0),
            "bathroom",
            "Bathroom",
            "Bathroom",
            0.7,
            "Transitioned with less distress after bathroom card was offered.",
        ),
        (
            (monday - timedelta(days=2)).replace(hour=17, minute=46, second=0, microsecond=0),
            "transition",
            "Transition",
            "Stop",
            0.69,
            "Paused activity and used timer before changing rooms.",
        ),
        (
            (monday - timedelta(days=1)).replace(hour=20, minute=14, second=0, microsecond=0),
            "bedtime",
            "Bedtime",
            "All done",
            0.73,
            "Ended story routine calmly after all-done choice.",
        ),
        (
            monday.replace(hour=18, minute=18, second=0, microsecond=0),
            "mealtime",
            "Meal",
            "I want water",
            0.78,
            "Resolved after water and picture choice.",
        ),
        (
            (monday + timedelta(days=1)).replace(hour=7, minute=40, second=0, microsecond=0),
            "school_dropoff",
            "School drop-off",
            "I need my hat",
            0.82,
            "Hat used as comfort item during transition.",
        ),
        (
            (monday + timedelta(days=2)).replace(hour=19, minute=5, second=0, microsecond=0),
            "homework",
            "Homework",
            "I need help",
            0.72,
            "Task resumed after modeled help request.",
        ),
        (
            (monday + timedelta(days=3)).replace(hour=18, minute=31, second=0, microsecond=0),
            "mealtime",
            "Meal",
            "I want more",
            0.76,
            "Used picture choice to continue meal.",
        ),
        (
            (monday + timedelta(days=4)).replace(hour=17, minute=58, second=0, microsecond=0),
            "transition",
            "Transition",
            "I need a break",
            0.74,
            "Calmer after short pause and visual timer.",
        ),
        (
            now.replace(hour=18, minute=22, second=0, microsecond=0),
            "mealtime",
            "Meal",
            "I want my hat",
            0.86,
            "Comfort-item request before mealtime transition.",
        ),
        (
            now.replace(hour=18, minute=28, second=0, microsecond=0),
            "mealtime",
            "Meal",
            "I want water",
            0.8,
            "Independent request after visual choice was available.",
        ),
        (
            now.replace(hour=18, minute=34, second=0, microsecond=0),
            "mealtime",
            "Meal",
            "Too loud",
            0.71,
            "Covered ears near kitchen noise; calmer after moving to quieter seat.",
        ),
    ]

    logs = []
    for ts, ctx_name, ctx_label, label, confidence, support_note in demo_events:
        secondary = "I need help" if label == "I want water" else "I want water"
        ranked = [
            {"label": label, "confidence": confidence},
            {"label": secondary, "confidence": 0.16},
            {"label": "I need a break", "confidence": 0.1},
        ]

        log = IntentLog(
            id=str(uuid.uuid4()),
            child_id=child_id,
            timestamp=ts,
            context={"name": ctx_name, "label": ctx_label, "support_note": support_note},
            gesture_vector={"has_hand": True, "source": "seeded_maya_evidence", "landmarks": []},
            audio_transcript="",
            ranked_intents=ranked,
            confirmed_label=label,
            confirmed_at=ts,
            spoken_phrase=label,
        )
        logs.append(log)

    for log in logs:
        db.add(log)
    db.commit()

    return {"seeded": len(logs), "message": "Demo data seeded"}


@router.post("/seed-maya-demo")
def seed_maya_demo(db=Depends(get_db)):
    child = db.query(Child).filter(Child.name == "Maya").first()
    if not child:
        child = Child(
            id=str(uuid.uuid4()),
            name="Maya",
            age=6,
            behavior_profile={
                "communication_profile": "Minimally verbal; uses gestures, pointing, and picture choices.",
                "routines": ["meals", "school drop-off", "transitions", "homework"],
                "current_goal": "AAC support across school and home routines",
                "comfort_item": "Hat often supports calmer transitions when offered proactively.",
                "teacher_contact": {
                    "name": "Ms. Rivera",
                    "role": "1st grade teacher",
                    "phone": os.getenv("VAPI_CUSTOMER_NUMBER", ""),
                },
            },
            preferred_symbols=["Water", "Hat", "Help", "Break", "More", "All Done"],
        )
        db.add(child)
        db.commit()
        db.refresh(child)
    else:
        child.age = 6
        child.behavior_profile = {
            "communication_profile": "Minimally verbal; uses gestures, pointing, and picture choices.",
            "routines": ["meals", "school drop-off", "transitions", "homework"],
            "current_goal": "AAC support across school and home routines",
            "comfort_item": "Hat often supports calmer transitions when offered proactively.",
            "teacher_contact": {
                "name": "Ms. Rivera",
                "role": "1st grade teacher",
                "phone": os.getenv("VAPI_CUSTOMER_NUMBER", ""),
            },
        }
        child.preferred_symbols = ["Water", "Hat", "Help", "Break", "More", "All Done"]
        db.add(child)
        db.commit()
    result = seed_demo_logs(child.id, db)
    db.refresh(child)
    return {"child": {
        "id": child.id,
        "name": child.name,
        "age": child.age,
        "behavior_profile": child.behavior_profile or {},
        "preferred_symbols": child.preferred_symbols or [],
    }, **result}
