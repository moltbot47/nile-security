"""Scan job model — audit job tracking."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base, UUIDMixin


class ScanJob(UUIDMixin, Base):
    __tablename__ = "scan_jobs"

    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # detect, patch, exploit
    agent: Mapped[str] = mapped_column(String(32), nullable=False)

    # Configuration
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    hint_level: Mapped[str] = mapped_column(String(8), default="none")

    # Results
    result: Mapped[dict | None] = mapped_column(JSONB)
    result_error: Mapped[str | None] = mapped_column(Text)

    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Cost tracking
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    api_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), default=0)

    # Relationships
    contract = relationship("Contract", back_populates="scan_jobs")
    vulnerabilities = relationship("Vulnerability", back_populates="scan_job")
