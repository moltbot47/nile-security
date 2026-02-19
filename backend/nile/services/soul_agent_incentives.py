"""Soul Agent incentive extensions — points for oracle, valuation, risk, governance."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.models.agent import Agent

logger = logging.getLogger(__name__)

# Soul Agent points table
SOUL_POINTS = {
    # Oracle agents
    "oracle_report_confirmed": 50,
    "oracle_report_rejected": -10,
    "oracle_vote_correct": 10,
    "oracle_vote_incorrect": -5,
    # Valuation agents
    "valuation_compute": 25,
    "valuation_snapshot_created": 15,
    # Market maker agents
    "liquidity_provision": 40,
    "market_making_hourly": 20,
    "spread_maintenance": 10,
    # Risk agents
    "risk_detection_critical": 100,
    "risk_detection_warning": 30,
    "risk_false_alarm": -15,
    "circuit_breaker_triggered": 50,
    # Governance agents
    "governance_vote": 10,
    "parameter_update_proposed": 20,
    "parameter_update_accepted": 30,
}

# Soul agent capability strings (register alongside existing detect/patch/exploit)
SOUL_CAPABILITIES = [
    "oracle",
    "valuation",
    "market_maker",
    "risk",
    "governance",
]


async def award_soul_points(
    db: AsyncSession,
    *,
    agent_id: str,
    action: str,
    metadata: dict | None = None,
) -> int:
    """Award points to a soul agent for an action.

    Returns the points awarded (negative for penalties).
    """
    points = SOUL_POINTS.get(action, 0)
    if points == 0:
        logger.warning("Unknown soul action: %s", action)
        return 0

    query = select(Agent).where(Agent.id == agent_id)
    result = await db.execute(query)
    agent = result.scalar_one_or_none()
    if not agent:
        logger.warning("Agent %s not found for soul points", agent_id)
        return 0

    agent.total_points = (agent.total_points or 0) + points
    agent.total_contributions = (agent.total_contributions or 0) + (1 if points > 0 else 0)

    await db.flush()

    logger.info(
        "Soul points: agent=%s, action=%s, points=%+d, total=%d",
        agent.name,
        action,
        points,
        agent.total_points,
    )
    return points


async def get_soul_agent_rankings(
    db: AsyncSession,
    capability: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Get soul agent rankings, optionally filtered by capability."""
    query = select(Agent).order_by(Agent.total_points.desc()).limit(limit)

    if capability:
        query = query.where(Agent.capabilities.contains([capability]))

    result = await db.execute(query)
    agents = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "name": a.name,
            "capabilities": a.capabilities,
            "total_points": a.total_points,
            "total_contributions": a.total_contributions,
            "nile_score_total": float(a.nile_score_total or 0),
            "is_online": a.is_online,
        }
        for a in agents
    ]
