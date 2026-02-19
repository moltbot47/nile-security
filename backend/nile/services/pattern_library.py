"""Pattern library — shared knowledge base of verified vulnerability signatures."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.event_bus import publish_event
from nile.models.ecosystem_event import EcosystemEvent


async def store_pattern(
    db: AsyncSession,
    category: str,
    severity: str,
    pattern_data: dict,
    discovered_by_agent_id: str,
) -> EcosystemEvent:
    """Store a verified vulnerability pattern in the knowledge base."""
    event = EcosystemEvent(
        event_type="knowledge.pattern_added",
        actor_id=discovered_by_agent_id,
        metadata_={
            "category": category,
            "severity": severity,
            "pattern": pattern_data,
        },
    )
    db.add(event)
    await db.flush()

    await publish_event(
        event_type="knowledge.pattern_added",
        actor_id=discovered_by_agent_id,
        metadata={
            "category": category,
            "severity": severity,
            "event_id": event.id,
        },
        db=db,
    )

    return event


async def query_patterns(
    db: AsyncSession,
    category: str | None = None,
    severity: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Query the pattern library for known vulnerability signatures."""
    query = (
        select(EcosystemEvent)
        .where(EcosystemEvent.event_type == "knowledge.pattern_added")
        .order_by(EcosystemEvent.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    events = result.scalars().all()

    patterns = []
    for e in events:
        meta = e.metadata_ or {}
        if category and meta.get("category") != category:
            continue
        if severity and meta.get("severity") != severity:
            continue
        patterns.append({
            "id": e.id,
            "category": meta.get("category"),
            "severity": meta.get("severity"),
            "pattern": meta.get("pattern", {}),
            "discovered_by": str(e.actor_id) if e.actor_id else None,
            "created_at": e.created_at.isoformat() if e.created_at else "",
        })

    return patterns
