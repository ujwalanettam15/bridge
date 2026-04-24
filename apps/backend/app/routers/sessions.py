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
