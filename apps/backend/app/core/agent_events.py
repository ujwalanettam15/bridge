import json
from datetime import datetime

from app.core.redis_client import redis

_fallback_events: dict[str, list[dict]] = {}


async def publish_agent_event(child_id: str, event_type: str, message: str, payload: dict | None = None):
    event = {
        "type": event_type,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "payload": payload or {},
    }
    try:
        key = f"agent_events:{child_id}"
        await redis.lpush(key, json.dumps(event))
        await redis.ltrim(key, 0, 24)
        await redis.publish(f"agent:{child_id}", json.dumps(event))
        return event
    except Exception:
        fallback_event = {**event, "redis_status": "unavailable"}
        child_events = _fallback_events.setdefault(child_id, [])
        child_events.insert(0, fallback_event)
        del child_events[25:]
        return fallback_event


async def get_recent_agent_events(child_id: str, limit: int = 20):
    try:
        raw_events = await redis.lrange(f"agent_events:{child_id}", 0, limit - 1)
    except Exception:
        return _fallback_events.get(child_id, [])[:limit]
    events = []
    for raw in raw_events:
        try:
            if isinstance(raw, bytes):
                raw = raw.decode()
            events.append(json.loads(raw))
        except Exception:
            continue
    return events
