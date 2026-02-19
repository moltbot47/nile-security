"""Redis-backed event bus for the NILE ecosystem."""

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from nile.config import settings
from nile.models.ecosystem_event import EcosystemEvent

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def publish_event(
    event_type: str,
    actor_id: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    db: AsyncSession | None = None,
) -> dict:
    """Publish an ecosystem event to Redis and optionally persist to DB."""
    event_data = {
        "event_type": event_type,
        "actor_id": actor_id,
        "target_id": target_id,
        "metadata": metadata or {},
        "created_at": datetime.now(UTC).isoformat(),
    }

    # Persist to database if session provided
    if db is not None:
        db_event = EcosystemEvent(
            event_type=event_type,
            actor_id=actor_id,
            target_id=target_id,
            metadata_=metadata or {},
        )
        db.add(db_event)
        await db.flush()
        event_data["id"] = db_event.id

    # Publish to Redis
    r = await get_redis()
    await r.publish("nile:events", json.dumps(event_data, default=str))

    # Also publish to type-specific channel
    channel = f"nile:event:{event_type.split('.')[0]}"
    await r.publish(channel, json.dumps(event_data, default=str))

    return event_data


async def event_stream() -> AsyncGenerator[str, None]:
    """SSE event generator — yields ecosystem events as they arrive."""
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe("nile:events")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield f"data: {message['data']}\n\n"
    finally:
        await pubsub.unsubscribe("nile:events")
        await pubsub.close()
