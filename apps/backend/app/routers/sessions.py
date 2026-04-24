from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
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
        (monday.replace(hour=18, minute=18, second=0, microsecond=0), "mealtime", "Mealtime", "I want water", 0.78),
        ((monday + timedelta(days=1)).replace(hour=18, minute=42, second=0, microsecond=0), "mealtime", "Mealtime", "I want water", 0.76),
        ((monday + timedelta(days=2)).replace(hour=19, minute=5, second=0, microsecond=0), "homework", "Homework", "I need help", 0.72),
        ((monday + timedelta(days=3)).replace(hour=18, minute=31, second=0, microsecond=0), "mealtime", "Mealtime", "I want water", 0.81),
        ((monday + timedelta(days=4)).replace(hour=17, minute=58, second=0, microsecond=0), "transition", "Transition", "I need help", 0.69),
        (now.replace(hour=18, minute=22, second=0, microsecond=0), "mealtime", "Mealtime", "I want water", 0.8),
    ]

    logs = []
    for ts, ctx_name, ctx_label, label, confidence in demo_events:
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
            context={"name": ctx_name, "label": ctx_label},
            gesture_vector={"has_hand": True, "demo_mode": True, "landmarks": []},
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
                "routines": ["meals", "transitions", "homework"],
                "current_goal": "AAC support across school and home routines",
            },
            preferred_symbols=["Water", "Help", "More", "All Done"],
        )
        db.add(child)
        db.commit()
        db.refresh(child)
    else:
        child.age = 6
        child.behavior_profile = {
            "communication_profile": "Minimally verbal; uses gestures, pointing, and picture choices.",
            "routines": ["meals", "transitions", "homework"],
            "current_goal": "AAC support across school and home routines",
        }
        child.preferred_symbols = ["Water", "Help", "More", "All Done"]
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
