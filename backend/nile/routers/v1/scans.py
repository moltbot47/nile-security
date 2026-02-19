"""Scan job endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.database import get_db
from nile.models.scan_job import ScanJob
from nile.schemas.scan import ScanCreate, ScanResponse

router = APIRouter()


@router.get("", response_model=list[ScanResponse])
async def list_scans(
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ScanJob).order_by(ScanJob.created_at.desc())
    if status:
        query = query.where(ScanJob.status == status)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("", response_model=ScanResponse, status_code=201)
async def create_scan(data: ScanCreate, db: AsyncSession = Depends(get_db)):
    scan = ScanJob(
        contract_id=data.contract_id,
        mode=data.mode,
        agent=data.agent,
        config=data.config,
        hint_level=data.hint_level,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    # TODO: enqueue scan worker job
    return scan


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScanJob).where(ScanJob.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan
