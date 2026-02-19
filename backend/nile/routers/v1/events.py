"""Events API — SSE stream and event history."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.database import get_db
from nile.core.event_bus import event_stream
from nile.models.ecosystem_event import EcosystemEvent

router = APIRouter()


class EventResponse(BaseModel):
    id: int
    event_type: str
    actor_id: str | None
    target_id: str | None
    metadata: dict
    created_at: str


@router.get("/stream")
async def sse_stream():
    """Server-Sent Events stream for real-time ecosystem updates."""
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", response_model=list[EventResponse])
async def event_history(
    event_type: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get recent ecosystem events."""
    query = select(EcosystemEvent).order_by(EcosystemEvent.created_at.desc()).limit(limit)
    if event_type:
        query = query.where(EcosystemEvent.event_type == event_type)

    result = await db.execute(query)
    events = result.scalars().all()

    return [
        EventResponse(
            id=e.id,
            event_type=e.event_type,
            actor_id=str(e.actor_id) if e.actor_id else None,
            target_id=str(e.target_id) if e.target_id else None,
            metadata=e.metadata_ or {},
            created_at=e.created_at.isoformat() if e.created_at else "",
        )
        for e in events
    ]
