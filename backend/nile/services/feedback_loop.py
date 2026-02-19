"""Self-improving feedback loops — track accuracy and evolve agent performance."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.event_bus import publish_event
from nile.models.agent_contribution import AgentContribution

logger = logging.getLogger(__name__)


async def get_agent_accuracy(db: AsyncSession, agent_id: str) -> dict:
    """Compute precision and recall metrics for an agent."""
    total = await db.scalar(
        select(func.count(AgentContribution.id)).where(
            AgentContribution.agent_id == agent_id,
            AgentContribution.contribution_type == "detection",
        )
    )

    verified = await db.scalar(
        select(func.count(AgentContribution.id)).where(
            AgentContribution.agent_id == agent_id,
            AgentContribution.contribution_type == "detection",
            AgentContribution.verified.is_(True),
        )
    )

    false_positives = await db.scalar(
        select(func.count(AgentContribution.id)).where(
            AgentContribution.agent_id == agent_id,
            AgentContribution.contribution_type == "detection",
            AgentContribution.points_awarded < 0,
        )
    )

    total = total or 0
    verified = verified or 0
    false_positives = false_positives or 0

    precision = verified / total if total > 0 else 0.0
    fp_rate = false_positives / total if total > 0 else 0.0

    return {
        "total_detections": total,
        "verified_detections": verified,
        "false_positives": false_positives,
        "precision": round(precision, 4),
        "false_positive_rate": round(fp_rate, 4),
    }


async def verify_contribution(
    db: AsyncSession,
    contribution_id: str,
    verifier_agent_id: str,
    is_valid: bool,
) -> None:
    """Cross-verify a contribution by another agent."""
    result = await db.execute(
        select(AgentContribution).where(AgentContribution.id == contribution_id)
    )
    contribution = result.scalar_one_or_none()
    if not contribution:
        return

    contribution.verified = is_valid

    event_type = "contribution.verified" if is_valid else "contribution.rejected"

    await publish_event(
        event_type=event_type,
        actor_id=verifier_agent_id,
        target_id=str(contribution.agent_id),
        metadata={
            "contribution_id": str(contribution_id),
            "is_valid": is_valid,
        },
        db=db,
    )

    if not is_valid:
        # Apply false positive penalty via incentive engine
        from nile.services.incentive_engine import penalize_false_positive

        await penalize_false_positive(db, str(contribution_id))

    await db.flush()
    logger.info(
        "Contribution %s %s by agent %s",
        contribution_id,
        "verified" if is_valid else "rejected",
        verifier_agent_id,
    )
