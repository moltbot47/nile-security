"""Task assignment API — agents claim and submit work."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.auth import get_current_agent
from nile.core.database import get_db
from nile.core.event_bus import publish_event
from nile.models.agent import Agent
from nile.models.scan_job import ScanJob
from nile.services.incentive_engine import award_contribution

router = APIRouter()


class TaskResponse(BaseModel):
    id: str
    contract_id: str
    mode: str
    status: str
    hint_level: str
    created_at: str


class TaskSubmitRequest(BaseModel):
    result: dict
    contribution_type: str = "detection"
    severity_found: str | None = None
    summary: str | None = None


class TaskSubmitResponse(BaseModel):
    scan_job_id: str
    status: str
    points_awarded: int


@router.get("/available", response_model=list[TaskResponse])
async def list_available_tasks(
    mode: str | None = None,
    limit: int = 20,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """List scan jobs that are queued and match agent capabilities."""
    query = select(ScanJob).where(ScanJob.status == "queued")
    if mode:
        query = query.where(ScanJob.mode == mode)
    query = query.order_by(ScanJob.created_at).limit(limit)

    result = await db.execute(query)
    jobs = result.scalars().all()

    # Filter by agent capabilities
    caps = current_agent.capabilities or []
    if caps:
        jobs = [j for j in jobs if j.mode in caps]

    return [
        TaskResponse(
            id=str(j.id),
            contract_id=str(j.contract_id),
            mode=j.mode,
            status=j.status,
            hint_level=j.hint_level,
            created_at=j.created_at.isoformat() if j.created_at else "",
        )
        for j in jobs
    ]


@router.post("/{task_id}/claim", response_model=TaskResponse)
async def claim_task(
    task_id: uuid.UUID,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Claim a queued scan job for this agent."""
    result = await db.execute(select(ScanJob).where(ScanJob.id == task_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Task not found")
    if job.status != "queued":
        raise HTTPException(status_code=409, detail=f"Task is already {job.status}")

    job.status = "running"
    job.agent = current_agent.name
    job.started_at = datetime.now(UTC)
    await db.flush()

    await publish_event(
        event_type="task.claimed",
        actor_id=str(current_agent.id),
        target_id=str(job.contract_id),
        metadata={"scan_job_id": str(job.id), "mode": job.mode},
        db=db,
    )

    await db.commit()

    return TaskResponse(
        id=str(job.id),
        contract_id=str(job.contract_id),
        mode=job.mode,
        status=job.status,
        hint_level=job.hint_level,
        created_at=job.created_at.isoformat() if job.created_at else "",
    )


@router.post("/{task_id}/submit", response_model=TaskSubmitResponse)
async def submit_task(
    task_id: uuid.UUID,
    req: TaskSubmitRequest,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Submit results for a claimed task."""
    result = await db.execute(select(ScanJob).where(ScanJob.id == task_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Task not found")
    if job.status != "running":
        raise HTTPException(status_code=409, detail=f"Task is {job.status}, not running")
    if job.agent != current_agent.name:
        raise HTTPException(status_code=403, detail="Task is claimed by a different agent")

    # Update scan job
    job.status = "succeeded"
    job.result = req.result
    job.finished_at = datetime.now(UTC)

    # Award contribution
    contribution = await award_contribution(
        db=db,
        agent_id=str(current_agent.id),
        contribution_type=req.contribution_type,
        severity_found=req.severity_found,
        contract_id=str(job.contract_id),
        scan_job_id=str(job.id),
        details=req.result,
        summary=req.summary,
    )

    await db.commit()

    return TaskSubmitResponse(
        scan_job_id=str(job.id),
        status="succeeded",
        points_awarded=contribution.points_awarded,
    )
