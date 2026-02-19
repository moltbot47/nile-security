"""Collaboration pipelines — orchestrate agent-to-agent workflows."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.event_bus import publish_event
from nile.models.agent_message import AgentMessage
from nile.models.scan_job import ScanJob

logger = logging.getLogger(__name__)


async def create_followup_task(
    db: AsyncSession,
    contract_id: str,
    mode: str,
    triggered_by_agent_id: str,
    config: dict | None = None,
) -> ScanJob:
    """Create a follow-up scan job (e.g., detect triggers patch task)."""
    job = ScanJob(
        contract_id=contract_id,
        status="queued",
        mode=mode,
        agent="unassigned",
        config=config or {},
        hint_level="none",
    )
    db.add(job)
    await db.flush()

    await publish_event(
        event_type=f"task.created.{mode}",
        actor_id=triggered_by_agent_id,
        target_id=contract_id,
        metadata={"scan_job_id": str(job.id), "mode": mode},
        db=db,
    )

    return job


async def detect_to_patch_pipeline(
    db: AsyncSession,
    contract_id: str,
    detection_agent_id: str,
    vulnerability_details: dict,
) -> ScanJob:
    """When a vulnerability is detected, create a patch task."""
    logger.info("Detect→Patch pipeline: creating patch task for contract %s", contract_id)

    job = await create_followup_task(
        db=db,
        contract_id=contract_id,
        mode="patch",
        triggered_by_agent_id=detection_agent_id,
        config={"vulnerability": vulnerability_details},
    )

    # Broadcast to patch-capable agents
    message = AgentMessage(
        sender_agent_id=detection_agent_id,
        recipient_agent_id=None,  # broadcast
        channel="patch",
        message_type="request",
        payload={
            "action": "patch_needed",
            "contract_id": contract_id,
            "scan_job_id": str(job.id),
            "vulnerability": vulnerability_details,
        },
    )
    db.add(message)
    await db.flush()

    return job


async def detect_to_exploit_pipeline(
    db: AsyncSession,
    contract_id: str,
    detection_agent_id: str,
    vulnerability_details: dict,
) -> ScanJob:
    """When a vulnerability is detected, create an exploit verification task."""
    logger.info("Detect→Exploit pipeline: creating exploit task for contract %s", contract_id)

    job = await create_followup_task(
        db=db,
        contract_id=contract_id,
        mode="exploit",
        triggered_by_agent_id=detection_agent_id,
        config={"vulnerability": vulnerability_details, "verify_only": True},
    )

    message = AgentMessage(
        sender_agent_id=detection_agent_id,
        recipient_agent_id=None,
        channel="exploit",
        message_type="request",
        payload={
            "action": "exploit_verify",
            "contract_id": contract_id,
            "scan_job_id": str(job.id),
            "vulnerability": vulnerability_details,
        },
    )
    db.add(message)
    await db.flush()

    return job


async def patch_verify_pipeline(
    db: AsyncSession,
    contract_id: str,
    patch_agent_id: str,
    patch_details: dict,
) -> ScanJob:
    """After a patch, create a re-scan to verify the fix."""
    logger.info("Patch→Verify pipeline: creating verify scan for contract %s", contract_id)

    job = await create_followup_task(
        db=db,
        contract_id=contract_id,
        mode="detect",
        triggered_by_agent_id=patch_agent_id,
        config={"verify_patch": True, "patch_details": patch_details},
    )

    message = AgentMessage(
        sender_agent_id=patch_agent_id,
        recipient_agent_id=None,
        channel="detection",
        message_type="request",
        payload={
            "action": "verify_patch",
            "contract_id": contract_id,
            "scan_job_id": str(job.id),
            "patch_details": patch_details,
        },
    )
    db.add(message)
    await db.flush()

    return job


async def send_agent_message(
    db: AsyncSession,
    sender_id: str,
    channel: str,
    message_type: str,
    payload: dict,
    recipient_id: str | None = None,
) -> AgentMessage:
    """Send a message between agents."""
    message = AgentMessage(
        sender_agent_id=sender_id,
        recipient_agent_id=recipient_id,
        channel=channel,
        message_type=message_type,
        payload=payload,
    )
    db.add(message)
    await db.flush()

    await publish_event(
        event_type="agent.message",
        actor_id=sender_id,
        target_id=recipient_id,
        metadata={
            "channel": channel,
            "message_type": message_type,
        },
        db=db,
    )

    return message
