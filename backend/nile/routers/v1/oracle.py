"""Oracle API endpoints — report submission, voting, consensus."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.database import get_db
from nile.models.oracle_event import OracleEvent
from nile.schemas.person import OracleEventResponse

router = APIRouter()


class OracleReportRequest(BaseModel):
    person_id: uuid.UUID
    event_type: str = Field(..., min_length=1, max_length=64)
    source: str = Field(..., min_length=1, max_length=64)
    headline: str = Field(..., min_length=1, max_length=500)
    impact_score: int = Field(..., ge=-100, le=100)
    confidence: float = Field(default=0.5, ge=0, le=1)
    agent_id: str | None = None


class OracleVoteRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    approve: bool
    impact_score: int | None = None


@router.post("/reports", response_model=OracleEventResponse, status_code=201)
async def submit_report(
    req: OracleReportRequest,
    db: AsyncSession = Depends(get_db),
) -> OracleEventResponse:
    """Submit a new oracle report about a person."""
    event = OracleEvent(
        person_id=req.person_id,
        event_type=req.event_type,
        source=req.source,
        headline=req.headline,
        impact_score=req.impact_score,
        confidence=req.confidence,
        status="pending",
        confirmations=1,  # submitter auto-confirms
        rejections=0,
        required_confirmations=2,
        agent_votes={req.agent_id: {"approve": True, "impact": req.impact_score}}
        if req.agent_id
        else {},
    )
    db.add(event)
    await db.flush()
    await db.commit()
    await db.refresh(event)

    return OracleEventResponse.model_validate(event)


@router.post("/reports/{report_id}/vote", response_model=OracleEventResponse)
async def vote_on_report(
    report_id: uuid.UUID,
    req: OracleVoteRequest,
    db: AsyncSession = Depends(get_db),
) -> OracleEventResponse:
    """Vote on a pending oracle report."""
    query = select(OracleEvent).where(OracleEvent.id == report_id)
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Report not found")
    if event.status != "pending":
        raise HTTPException(409, f"Report already {event.status}")

    # Check if agent already voted
    votes = event.agent_votes or {}
    if req.agent_id in votes:
        raise HTTPException(409, "Agent already voted on this report")

    # Record vote
    votes[req.agent_id] = {
        "approve": req.approve,
        "impact": req.impact_score or event.impact_score,
    }
    event.agent_votes = votes

    if req.approve:
        event.confirmations += 1
    else:
        event.rejections += 1

    # Check consensus
    required = event.required_confirmations or 2
    if event.confirmations >= required:
        event.status = "confirmed"
    elif event.rejections > 3 - required:  # impossible to reach quorum
        event.status = "rejected"

    await db.flush()
    await db.commit()
    await db.refresh(event)

    return OracleEventResponse.model_validate(event)


@router.get("/reports", response_model=list[OracleEventResponse])
async def list_reports(
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[OracleEventResponse]:
    """List oracle reports, optionally filtered by status."""
    query = select(OracleEvent).order_by(OracleEvent.created_at.desc()).limit(limit)
    if status:
        query = query.where(OracleEvent.status == status)

    result = await db.execute(query)
    return [OracleEventResponse.model_validate(e) for e in result.scalars().all()]
