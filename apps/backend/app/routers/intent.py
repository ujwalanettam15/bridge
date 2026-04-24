from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from datetime import datetime
import json

from app.ml import mediapipe_processor, audio_processor, intent_reasoner
from app.models import Child, IntentLog
from app.core.database import get_db
from app.core.redis_client import redis

router = APIRouter()


class InferRequest(BaseModel):
    child_id: str
    frame_b64: str
    audio_b64: str = ""
    context: dict = {}


@router.post("/infer")
async def infer_intent(payload: InferRequest, db=Depends(get_db)):
    gesture = await mediapipe_processor.extract_gesture_vector(payload.frame_b64)

    audio = {"transcript": "", "confidence": 0}
    if payload.audio_b64:
        audio = await audio_processor.transcribe_audio(payload.audio_b64)

    child = db.query(Child).filter(Child.id == payload.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    result = await intent_reasoner.classify_intent(gesture, audio, child, payload.context)

    log = IntentLog(
        child_id=payload.child_id,
        timestamp=datetime.utcnow(),
        context=payload.context,
        gesture_vector=gesture,
        audio_transcript=audio["transcript"],
        ranked_intents=result["intents"],
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    response = {**result, "intent_log_id": log.id}

    try:
        await redis.publish(f"intent:{payload.child_id}", json.dumps(response))
    except Exception:
        response["redis_status"] = "unavailable"

    return response


@router.websocket("/ws/intent/{child_id}")
async def intent_websocket(websocket: WebSocket, child_id: str):
    await websocket.accept()
    try:
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"intent:{child_id}")
    except Exception:
        await websocket.send_text(json.dumps({"error": "Redis unavailable"}))
        await websocket.close()
        return
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"].decode())
    except WebSocketDisconnect:
        await pubsub.unsubscribe(f"intent:{child_id}")
