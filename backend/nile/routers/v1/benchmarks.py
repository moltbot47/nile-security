"""Benchmark run endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.database import get_db
from nile.models.benchmark_run import BenchmarkRun
from nile.schemas.benchmark import BenchmarkBaseline, BenchmarkCreate, BenchmarkResponse

router = APIRouter()

# Published EVMbench baselines (Feb 2026)
PUBLISHED_BASELINES = [
    BenchmarkBaseline(
        agent="gpt-5.3-codex", mode="exploit", score_pct=72.2, source="evmbench_published"
    ),
    BenchmarkBaseline(
        agent="gpt-5", mode="exploit", score_pct=31.9, source="evmbench_published"
    ),
]


@router.get("", response_model=list[BenchmarkResponse])
async def list_benchmarks(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BenchmarkRun).order_by(BenchmarkRun.started_at.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/run", response_model=BenchmarkResponse, status_code=201)
async def create_benchmark(data: BenchmarkCreate, db: AsyncSession = Depends(get_db)):
    run = BenchmarkRun(
        split=data.split,
        mode=data.mode,
        agent=data.agent,
        baseline_agent=data.baseline_agent,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    # TODO: enqueue benchmark worker
    return run


@router.get("/baselines", response_model=list[BenchmarkBaseline])
async def get_baselines():
    return PUBLISHED_BASELINES


@router.get("/{run_id}", response_model=BenchmarkResponse)
async def get_benchmark(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BenchmarkRun).where(BenchmarkRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Benchmark run not found")
    return run
