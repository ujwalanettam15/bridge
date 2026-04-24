from typing import Literal

from fastapi import APIRouter, Query

from app.integrations.ghost import get_ghost_status, pgmq_read

router = APIRouter(prefix="/ghost", tags=["ghost"])


@router.get("/status")
async def ghost_status():
    """Return Ghost space status for the sponsor audit panel."""
    return await get_ghost_status()


@router.get("/events")
async def ghost_events(
    limit: int = Query(20, ge=1, le=100),
    queue: Literal["bridge_agent_events", "bridge_care_actions"] = Query("bridge_agent_events"),
):
    """
    Read recent agent stage events from the Ghost-backed DB queue.
    Ghost serves as an active durable queue alongside Redis —
    judges can see both channels in the technical trace.
    """
    events = pgmq_read(queue, limit=limit)
    return {"source": "ghost_db_queue", "queue": queue, "events": events}
