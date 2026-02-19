"""Scan worker — processes queued scan jobs and computes NILE scores."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.database import async_session
from nile.core.event_bus import publish_event
from nile.models.contract import Contract
from nile.models.nile_score import NileScore
from nile.models.scan_job import ScanJob
from nile.services.nile_scorer import (
    EssenceInputs,
    ImageInputs,
    LikenessInputs,
    NameInputs,
    compute_nile_score,
)

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 5


async def process_scan_job(db: AsyncSession, job: ScanJob) -> None:
    """Process a single scan job — run scoring and persist results."""
    job.status = "running"
    job.started_at = datetime.now(UTC)
    await db.flush()

    try:
        # Load the contract
        result = await db.execute(select(Contract).where(Contract.id == job.contract_id))
        contract = result.scalar_one_or_none()
        if not contract:
            raise ValueError(f"Contract {job.contract_id} not found")

        # Build scoring inputs from contract metadata and existing data
        meta = contract.metadata_ or {}

        name_inputs = NameInputs(
            is_verified=contract.is_verified,
            audit_count=meta.get("audit_count", 0),
            age_days=meta.get("age_days", 0),
            team_identified=meta.get("team_identified", False),
            ecosystem_score=meta.get("ecosystem_score", 0.0),
        )

        image_inputs = ImageInputs(
            open_critical=meta.get("open_critical", 0),
            open_high=meta.get("open_high", 0),
            open_medium=meta.get("open_medium", 0),
            avg_patch_time_days=meta.get("avg_patch_time_days"),
            trend=meta.get("trend", 0.0),
        )

        likeness_inputs = LikenessInputs(
            slither_findings=meta.get("slither_findings", []),
            evmbench_pattern_matches=meta.get("evmbench_pattern_matches", []),
        )

        essence_inputs = EssenceInputs(
            test_coverage_pct=meta.get("test_coverage_pct", 0.0),
            avg_cyclomatic_complexity=meta.get("avg_cyclomatic_complexity", 5.0),
            has_proxy_pattern=meta.get("has_proxy_pattern", False),
            has_admin_keys=meta.get("has_admin_keys", False),
            has_timelock=meta.get("has_timelock", True),
            external_call_count=meta.get("external_call_count", 0),
        )

        # Compute NILE score
        score_result = compute_nile_score(
            name_inputs, image_inputs, likeness_inputs, essence_inputs
        )

        # Persist score
        nile_score = NileScore(
            contract_id=contract.id,
            total_score=score_result.total_score,
            name_score=score_result.name_score,
            image_score=score_result.image_score,
            likeness_score=score_result.likeness_score,
            essence_score=score_result.essence_score,
            score_details=score_result.details,
            trigger_type="scan",
            trigger_id=job.id,
        )
        db.add(nile_score)

        # Update job
        job.status = "succeeded"
        job.result = {
            "nile_score": score_result.total_score,
            "grade": score_result.grade,
            "sub_scores": {
                "name": score_result.name_score,
                "image": score_result.image_score,
                "likeness": score_result.likeness_score,
                "essence": score_result.essence_score,
            },
        }
        job.finished_at = datetime.now(UTC)
        await db.flush()

        await publish_event(
            event_type="scan.completed",
            target_id=str(contract.id),
            metadata={
                "scan_job_id": str(job.id),
                "nile_score": score_result.total_score,
                "grade": score_result.grade,
            },
            db=db,
        )

        logger.info(
            "Scan job %s completed: score=%.2f grade=%s",
            job.id, score_result.total_score, score_result.grade,
        )

    except Exception as e:
        job.status = "failed"
        job.result_error = str(e)
        job.finished_at = datetime.now(UTC)
        await db.flush()
        logger.exception("Scan job %s failed: %s", job.id, e)


async def poll_and_process() -> None:
    """Poll for queued scan jobs and process them."""
    async with async_session() as db:
        result = await db.execute(
            select(ScanJob)
            .where(ScanJob.status == "queued")
            .order_by(ScanJob.created_at)
            .limit(5)
        )
        jobs = list(result.scalars().all())

        for job in jobs:
            await process_scan_job(db, job)

        await db.commit()


async def run_worker() -> None:
    """Main worker loop — polls for jobs continuously."""
    logger.info("NILE scan worker starting...")
    while True:
        try:
            await poll_and_process()
        except Exception:
            logger.exception("Worker poll cycle failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
