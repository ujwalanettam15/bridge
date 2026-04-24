from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.models import Session, IntentLog
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
    from app.models import Child
    import random
    from datetime import timedelta

    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    existing = db.query(IntentLog).filter(IntentLog.child_id == child_id).count()
    if existing > 0:
        return {"seeded": 0, "message": "Already has data"}

    demo_intents = [
        {"label": "I want water", "confidence": 0.78},
        {"label": "I need a break", "confidence": 0.65},
        {"label": "I want more", "confidence": 0.71},
        {"label": "I'm done", "confidence": 0.82},
        {"label": "I need help", "confidence": 0.69},
        {"label": "I want food", "confidence": 0.74},
    ]
    contexts = [
        {"name": "mealtime", "label": "Mealtime"},
        {"name": "therapy", "label": "Therapy"},
        {"name": "school", "label": "School"},
    ]

    now = datetime.utcnow()
    logs = []
    for _ in range(16):
        days_ago = random.randint(0, 6)
        hours_ago = random.randint(7, 19)
        ts = now - timedelta(days=days_ago, hours=hours_ago)

        primary = random.choice(demo_intents)
        others = random.sample([d for d in demo_intents if d != primary], 2)
        ranked = [
            {"label": primary["label"], "confidence": primary["confidence"]},
            {"label": others[0]["label"], "confidence": round((1 - primary["confidence"]) * 0.55, 2)},
            {"label": others[1]["label"], "confidence": round((1 - primary["confidence"]) * 0.35, 2)},
        ]
        ctx = random.choice(contexts)
        confirmed = primary["label"] if random.random() > 0.25 else None

        log = IntentLog(
            id=str(uuid.uuid4()),
            child_id=child_id,
            timestamp=ts,
            context=ctx,
            gesture_vector={"has_hand": True, "demo_mode": True, "landmarks": []},
            audio_transcript="",
            ranked_intents=ranked,
            confirmed_label=confirmed,
            confirmed_at=ts if confirmed else None,
            spoken_phrase=None,
        )
        logs.append(log)

    for log in logs:
        db.add(log)
    db.commit()

    return {"seeded": len(logs), "message": "Demo data seeded"}
