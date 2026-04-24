from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
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

    result = await intent_reasoner.classify_intent(gesture, audio, child, payload.context)

    await redis.publish(f"intent:{payload.child_id}", json.dumps(result))

    log = IntentLog(
        child_id=payload.child_id,
        timestamp=datetime.utcnow(),
        gesture_vector=gesture,
        audio_transcript=audio["transcript"],
        ranked_intents=result["intents"],
    )
    db.add(log)
    db.commit()

    return result


@router.websocket("/ws/intent/{child_id}")
async def intent_websocket(websocket: WebSocket, child_id: str):
    await websocket.accept()
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"intent:{child_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"].decode())
    except WebSocketDisconnect:
        await pubsub.unsubscribe(f"intent:{child_id}")
