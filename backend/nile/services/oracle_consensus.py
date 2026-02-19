"""Oracle consensus service — manages event submission, voting, and valuation triggers."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.models.oracle_event import OracleEvent
from nile.models.person import Person
from nile.models.valuation_snapshot import ValuationSnapshot
from nile.services.soul_valuation import (
    PersonEssenceInputs,
    PersonImageInputs,
    PersonLikenessInputs,
    PersonNameInputs,
    compute_person_valuation,
)

logger = logging.getLogger(__name__)

# Required confirmations for consensus
DEFAULT_REQUIRED = 2


async def submit_oracle_report(
    db: AsyncSession,
    *,
    agent_id: str,
    person_id: uuid.UUID,
    event_type: str,
    source: str,
    headline: str,
    impact_score: int,
    confidence: float = 0.5,
) -> OracleEvent:
    """Submit a new oracle report from an agent."""
    event = OracleEvent(
        person_id=person_id,
        event_type=event_type,
        source=source,
        headline=headline,
        impact_score=impact_score,
        confidence=confidence,
        status="pending",
        confirmations=1,
        rejections=0,
        required_confirmations=DEFAULT_REQUIRED,
        agent_votes={agent_id: {"approve": True, "impact": impact_score}},
    )
    db.add(event)
    await db.flush()
    logger.info("Oracle report submitted: %s by agent %s", event.id, agent_id)
    return event


async def vote_on_report(
    db: AsyncSession,
    *,
    agent_id: str,
    event_id: uuid.UUID,
    approve: bool,
    impact_score: int | None = None,
) -> OracleEvent:
    """Cast a vote on a pending oracle report. Returns updated event."""
    query = select(OracleEvent).where(OracleEvent.id == event_id)
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    if not event:
        raise ValueError(f"Oracle event {event_id} not found")
    if event.status != "pending":
        raise ValueError(f"Event already {event.status}")

    votes = event.agent_votes or {}
    if agent_id in votes:
        raise ValueError(f"Agent {agent_id} already voted")

    votes[agent_id] = {
        "approve": approve,
        "impact": impact_score if impact_score is not None else event.impact_score,
    }
    event.agent_votes = votes

    if approve:
        event.confirmations += 1
    else:
        event.rejections += 1

    # Check consensus
    await check_consensus(db, event)
    await db.flush()
    return event


async def check_consensus(db: AsyncSession, event: OracleEvent) -> bool:
    """Check if an oracle event has reached consensus. Triggers revaluation if confirmed."""
    required = event.required_confirmations or DEFAULT_REQUIRED

    if event.confirmations >= required:
        event.status = "confirmed"
        logger.info("Oracle event %s CONFIRMED (impact=%s)", event.id, event.impact_score)
        # Trigger revaluation
        await _trigger_revaluation(db, event)
        return True

    # Check if rejection is inevitable
    total_possible = event.confirmations + event.rejections
    remaining_votes = max(0, 3 - total_possible)  # assume max 3 oracle agents
    if event.confirmations + remaining_votes < required:
        event.status = "rejected"
        logger.info("Oracle event %s REJECTED", event.id)
        return True

    return False


async def _trigger_revaluation(db: AsyncSession, event: OracleEvent) -> None:
    """Re-compute NILE scores for a person after a confirmed oracle event."""
    query = select(Person).where(Person.id == event.person_id)
    result = await db.execute(query)
    person = result.scalar_one_or_none()
    if not person:
        logger.warning("Person %s not found for revaluation", event.person_id)
        return

    # Gather confirmed events for this person
    events_query = select(OracleEvent).where(
        OracleEvent.person_id == person.id,
        OracleEvent.status == "confirmed",
    )
    events_result = await db.execute(events_query)
    confirmed_events = events_result.scalars().all()

    positive = sum(1 for e in confirmed_events if e.impact_score > 0)
    negative = sum(1 for e in confirmed_events if e.impact_score < 0)
    neutral = sum(1 for e in confirmed_events if e.impact_score == 0)

    # Build inputs from person state + oracle data
    name_inputs = PersonNameInputs(
        verification_level=person.verification_level or "unverified",
    )
    image_inputs = PersonImageInputs(
        positive_events=positive,
        negative_events=negative,
        neutral_events=neutral,
        avg_sentiment=0.5 + (positive - negative) / max(len(confirmed_events), 1) * 0.3,
    )
    likeness_inputs = PersonLikenessInputs(
        category=person.category or "general",
    )
    essence_inputs = PersonEssenceInputs()

    valuation = compute_person_valuation(
        name_inputs, image_inputs, likeness_inputs, essence_inputs
    )

    # Update person scores
    person.nile_name_score = valuation.name_score
    person.nile_image_score = valuation.image_score
    person.nile_likeness_score = valuation.likeness_score
    person.nile_essence_score = valuation.essence_score
    person.nile_total_score = valuation.total_score

    # Create valuation snapshot
    snapshot = ValuationSnapshot(
        person_id=person.id,
        name_score=valuation.name_score,
        image_score=valuation.image_score,
        likeness_score=valuation.likeness_score,
        essence_score=valuation.essence_score,
        total_score=valuation.total_score,
        fair_value_usd=valuation.fair_value_usd,
        trigger_type="oracle_event",
        trigger_id=event.id,
        score_details=valuation.details,
    )
    db.add(snapshot)

    logger.info(
        "Revaluation complete for %s: total=%.2f, grade=%s, fair_value=$%.2f",
        person.display_name,
        valuation.total_score,
        valuation.grade,
        valuation.fair_value_usd,
    )
