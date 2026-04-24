from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime

from app.integrations import vapi, tinyfish, nexla
from app.models import Child, Session, IntentLog
from app.core.database import get_db
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


class TherapistSyncRequest(BaseModel):
    therapist_webhook: str = ""


class TherapistSearchRequest(BaseModel):
    child_id: str
    zip_code: str
    insurance_provider: str = ""


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


@router.post("/confirm-intent")
def confirm_intent(payload: ConfirmIntentRequest, db=Depends(get_db)):
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
    return {
        "status": "profile updated",
        "confirmed_label": payload.confirmed_label,
        "behavior_profile": child.behavior_profile or {},
    }
