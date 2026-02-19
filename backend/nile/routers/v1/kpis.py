"""KPI dashboard endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.database import get_db
from nile.models.contract import Contract
from nile.models.kpi_metric import KPIMetric
from nile.models.nile_score import NileScore
from nile.models.scan_job import ScanJob
from nile.models.vulnerability import Vulnerability
from nile.schemas.kpi import (
    AssetHealthItem,
    AssetHealthResponse,
    AttackerKPIs,
    DefenderKPIs,
    KPITrendPoint,
    KPITrendsResponse,
)

router = APIRouter()


@router.get("/attacker", response_model=AttackerKPIs)
async def attacker_kpis(time_range: str = "30d", db: AsyncSession = Depends(get_db)):
    # Exploit success rate from scan jobs in exploit mode
    total_exploits = await db.execute(
        select(func.count()).select_from(ScanJob).where(ScanJob.mode == "exploit")
    )
    successful_exploits = await db.execute(
        select(func.count())
        .select_from(ScanJob)
        .where(ScanJob.mode == "exploit", ScanJob.status == "succeeded")
    )
    total = total_exploits.scalar() or 0
    success = successful_exploits.scalar() or 0

    # Vulnerability category distribution
    cat_result = await db.execute(
        select(Vulnerability.category, func.count())
        .group_by(Vulnerability.category)
        .order_by(func.count().desc())
    )
    categories = dict(cat_result.all())
    cat_total = sum(categories.values()) or 1
    distribution = {k: round(v / cat_total, 3) for k, v in categories.items()}

    return AttackerKPIs(
        exploit_success_rate=round(success / total, 3) if total > 0 else 0.0,
        attack_vector_distribution=distribution,
        time_range=time_range,
    )


@router.get("/defender", response_model=DefenderKPIs)
async def defender_kpis(time_range: str = "30d", db: AsyncSession = Depends(get_db)):
    # Detection recall from detect-mode scans
    total_detects = await db.execute(
        select(func.count()).select_from(ScanJob).where(ScanJob.mode == "detect")
    )
    successful_detects = await db.execute(
        select(func.count())
        .select_from(ScanJob)
        .where(ScanJob.mode == "detect", ScanJob.status == "succeeded")
    )
    total = total_detects.scalar() or 0
    success = successful_detects.scalar() or 0

    # Patch success rate
    total_patches = await db.execute(
        select(func.count()).select_from(ScanJob).where(ScanJob.mode == "patch")
    )
    successful_patches = await db.execute(
        select(func.count())
        .select_from(ScanJob)
        .where(ScanJob.mode == "patch", ScanJob.status == "succeeded")
    )
    patch_total = total_patches.scalar() or 0
    patch_success = successful_patches.scalar() or 0

    return DefenderKPIs(
        detection_recall=round(success / total, 3) if total > 0 else 0.0,
        patch_success_rate=round(patch_success / patch_total, 3) if patch_total > 0 else 0.0,
        time_range=time_range,
    )


@router.get("/asset-health", response_model=AssetHealthResponse)
async def asset_health(db: AsyncSession = Depends(get_db)):
    contracts_result = await db.execute(select(Contract))
    contracts = contracts_result.scalars().all()

    items = []
    total_score = 0.0
    for contract in contracts:
        # Get latest NILE score
        score_result = await db.execute(
            select(NileScore)
            .where(NileScore.contract_id == contract.id)
            .order_by(NileScore.computed_at.desc())
            .limit(1)
        )
        latest_score = score_result.scalar_one_or_none()

        # Count open vulnerabilities
        vuln_count = await db.execute(
            select(func.count())
            .select_from(Vulnerability)
            .where(Vulnerability.contract_id == contract.id, Vulnerability.status == "open")
        )
        open_vulns = vuln_count.scalar() or 0

        nile_score = float(latest_score.total_score) if latest_score else 0.0
        total_score += nile_score

        grade = "F"
        if nile_score >= 90:
            grade = "A+"
        elif nile_score >= 80:
            grade = "A"
        elif nile_score >= 70:
            grade = "B"
        elif nile_score >= 60:
            grade = "C"
        elif nile_score >= 50:
            grade = "D"

        items.append(
            AssetHealthItem(
                contract_id=str(contract.id),
                contract_name=contract.name,
                nile_score=nile_score,
                grade=grade,
                open_vulnerabilities=open_vulns,
            )
        )

    return AssetHealthResponse(
        items=items,
        total_contracts=len(contracts),
        avg_nile_score=round(total_score / len(contracts), 2) if contracts else 0.0,
    )


@router.get("/trends", response_model=KPITrendsResponse)
async def kpi_trends(
    metric_name: str = "defender.detection_recall",
    dimension: str = "defender",
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KPIMetric)
        .where(KPIMetric.metric_name == metric_name, KPIMetric.dimension == dimension)
        .order_by(KPIMetric.recorded_at.desc())
        .limit(limit)
    )
    metrics = result.scalars().all()

    data = [
        KPITrendPoint(timestamp=m.recorded_at.isoformat(), value=float(m.value))
        for m in reversed(metrics)
    ]
    return KPITrendsResponse(metric_name=metric_name, dimension=dimension, data=data)
