"""NILE score model — composite security scoring snapshots."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base, UUIDMixin


class NileScore(UUIDMixin, Base):
    __tablename__ = "nile_scores"

    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False, index=True
    )

    # Composite NILE score (0-100)
    total_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    # Sub-scores (each 0-100)
    name_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    image_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    likeness_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    essence_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    # Breakdown details
    score_details: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Trigger info
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    contract = relationship("Contract", back_populates="nile_scores")
