"""Agent NILE Identity scorer — applies the same 4-dimension framework to agents."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.models.agent import Agent
from nile.models.agent_contribution import AgentContribution


@dataclass
class AgentNileResult:
    total_score: float
    name_score: float
    image_score: float
    likeness_score: float
    essence_score: float
    grade: str
    details: dict


def _grade(score: float) -> str:
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"


async def compute_agent_nile_score(db: AsyncSession, agent_id: str) -> AgentNileResult:
    """Compute NILE identity score for an agent based on their track record."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one()

    # --- Name (25%): Registration completeness, version history, owner reputation ---
    name_score = 0.0
    if agent.name:
        name_score += 20
    if agent.description:
        name_score += 20
    if agent.version and agent.version != "0.1.0":
        name_score += 20  # Has been updated
    if agent.owner_id:
        name_score += 20
    if agent.capabilities:
        name_score += 20
    name_score = min(name_score, 100.0)

    # --- Image (25%): False positive rate (inverse), accuracy, uptime ---
    contributions_result = await db.execute(
        select(AgentContribution).where(AgentContribution.agent_id == agent_id)
    )
    contributions = list(contributions_result.scalars().all())

    total_contribs = len(contributions)
    verified_count = sum(1 for c in contributions if c.verified)
    false_positive_count = sum(1 for c in contributions if c.points_awarded < 0)

    image_score = 50.0  # Base score
    if total_contribs > 0:
        accuracy_rate = verified_count / total_contribs
        fp_rate = false_positive_count / total_contribs
        image_score = (accuracy_rate * 70) + ((1 - fp_rate) * 30)
    if agent.is_online:
        image_score = min(image_score + 10, 100.0)

    # --- Likeness (25%): Specialization depth, pattern coverage ---
    likeness_score = 0.0
    if total_contribs >= 1:
        likeness_score += 20
    if total_contribs >= 5:
        likeness_score += 20
    if total_contribs >= 20:
        likeness_score += 20
    # Capability breadth
    cap_count = len(agent.capabilities) if agent.capabilities else 0
    likeness_score += min(cap_count * 15, 40)
    likeness_score = min(likeness_score, 100.0)

    # --- Essence (25%): Points efficiency, contribution rate ---
    essence_score = 0.0
    if agent.total_points > 0:
        avg_points = agent.total_points / max(total_contribs, 1)
        # Scale: 0-10 pts avg = 0-50, 10-50 = 50-80, 50+ = 80-100
        if avg_points >= 50:
            essence_score = 80 + min((avg_points - 50) / 5, 20)
        elif avg_points >= 10:
            essence_score = 50 + (avg_points - 10) / 40 * 30
        else:
            essence_score = avg_points * 5
    essence_score = min(essence_score, 100.0)

    total_score = (name_score + image_score + likeness_score + essence_score) / 4
    grade = _grade(total_score)

    return AgentNileResult(
        total_score=round(total_score, 2),
        name_score=round(name_score, 2),
        image_score=round(image_score, 2),
        likeness_score=round(likeness_score, 2),
        essence_score=round(essence_score, 2),
        grade=grade,
        details={
            "total_contributions": total_contribs,
            "verified_contributions": verified_count,
            "false_positives": false_positive_count,
            "total_points": agent.total_points,
        },
    )


async def update_agent_nile_scores(db: AsyncSession, agent_id: str) -> None:
    """Recompute and persist agent NILE scores."""
    scores = await compute_agent_nile_score(db, agent_id)
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one()

    agent.nile_score_total = scores.total_score
    agent.nile_score_name = scores.name_score
    agent.nile_score_image = scores.image_score
    agent.nile_score_likeness = scores.likeness_score
    agent.nile_score_essence = scores.essence_score

    await db.flush()
