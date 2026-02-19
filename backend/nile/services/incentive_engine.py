"""Incentive engine — awards points for agent contributions."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.event_bus import publish_event
from nile.models.agent import Agent
from nile.models.agent_contribution import AgentContribution

# Points table
POINTS_TABLE: dict[tuple[str, str | None], int] = {
    ("detection", "critical"): 100,
    ("detection", "high"): 50,
    ("detection", "medium"): 25,
    ("detection", "low"): 10,
    ("patch", None): 75,
    ("exploit", None): 60,
    ("verification", None): 15,
}

FALSE_POSITIVE_PENALTY = -20


def calculate_points(contribution_type: str, severity: str | None = None) -> int:
    """Calculate points for a contribution based on type and severity."""
    # Exact match first
    points = POINTS_TABLE.get((contribution_type, severity))
    if points is not None:
        return points
    # Fall back to type-only match
    points = POINTS_TABLE.get((contribution_type, None))
    if points is not None:
        return points
    return 0


async def award_contribution(
    db: AsyncSession,
    agent_id: str,
    contribution_type: str,
    severity_found: str | None = None,
    contract_id: str | None = None,
    scan_job_id: str | None = None,
    details: dict | None = None,
    summary: str | None = None,
) -> AgentContribution:
    """Create a contribution record and award points."""
    points = calculate_points(contribution_type, severity_found)

    contribution = AgentContribution(
        agent_id=agent_id,
        contribution_type=contribution_type,
        contract_id=contract_id,
        scan_job_id=scan_job_id,
        severity_found=severity_found,
        points_awarded=points,
        details=details or {},
        summary=summary,
    )
    db.add(contribution)

    # Update agent cumulative stats
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent:
        agent.total_points += points
        agent.total_contributions += 1

    await db.flush()

    # Emit ecosystem event
    await publish_event(
        event_type=f"contribution.{contribution_type}",
        actor_id=str(agent_id),
        target_id=str(contract_id) if contract_id else None,
        metadata={
            "contribution_id": str(contribution.id),
            "points": points,
            "severity": severity_found,
        },
        db=db,
    )

    return contribution


async def penalize_false_positive(
    db: AsyncSession,
    contribution_id: str,
) -> None:
    """Mark a contribution as a false positive and deduct points."""
    result = await db.execute(
        select(AgentContribution).where(AgentContribution.id == contribution_id)
    )
    contribution = result.scalar_one_or_none()
    if not contribution:
        return

    # Reverse original points and apply penalty
    original_points = contribution.points_awarded
    contribution.points_awarded = FALSE_POSITIVE_PENALTY
    contribution.verified = False

    # Update agent
    result = await db.execute(select(Agent).where(Agent.id == contribution.agent_id))
    agent = result.scalar_one_or_none()
    if agent:
        agent.total_points -= original_points
        agent.total_points += FALSE_POSITIVE_PENALTY

    await db.flush()

    await publish_event(
        event_type="contribution.false_positive",
        actor_id=str(contribution.agent_id),
        metadata={
            "contribution_id": str(contribution_id),
            "penalty": FALSE_POSITIVE_PENALTY,
        },
        db=db,
    )
