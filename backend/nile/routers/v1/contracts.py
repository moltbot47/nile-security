"""Contract CRUD endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.database import get_db
from nile.models.contract import Contract
from nile.models.nile_score import NileScore
from nile.models.vulnerability import Vulnerability
from nile.schemas.contract import ContractCreate, ContractResponse, NileScoreResponse

router = APIRouter()


@router.get("", response_model=list[ContractResponse])
async def list_contracts(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Contract).offset(skip).limit(limit))
    return result.scalars().all()


@router.post("", response_model=ContractResponse, status_code=201)
async def create_contract(data: ContractCreate, db: AsyncSession = Depends(get_db)):
    contract = Contract(
        address=data.address,
        name=data.name,
        source_url=data.source_url,
        chain=data.chain,
        compiler_version=data.compiler_version,
        is_verified=data.is_verified,
        metadata_=data.metadata,
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return contract


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(contract_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.get("/{contract_id}/nile-history", response_model=list[NileScoreResponse])
async def get_nile_history(
    contract_id: uuid.UUID, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(NileScore)
        .where(NileScore.contract_id == contract_id)
        .order_by(NileScore.computed_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{contract_id}/vulnerabilities")
async def get_contract_vulnerabilities(
    contract_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Vulnerability)
        .where(Vulnerability.contract_id == contract_id)
        .order_by(Vulnerability.detected_at.desc())
    )
    return result.scalars().all()
