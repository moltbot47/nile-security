"""ValuationSnapshot model — point-in-time NILE valuation of a person."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base, UUIDMixin


class ValuationSnapshot(UUIDMixin, Base):
    __tablename__ = "valuation_snapshots"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.id"), index=True
    )

    # NILE sub-scores for human valuation (0-100)
    name_score: Mapped[float] = mapped_column(Numeric(5, 2))
    image_score: Mapped[float] = mapped_column(Numeric(5, 2))
    likeness_score: Mapped[float] = mapped_column(Numeric(5, 2))
    essence_score: Mapped[float] = mapped_column(Numeric(5, 2))
    total_score: Mapped[float] = mapped_column(Numeric(5, 2))

    # Fair value estimate in USD
    fair_value_usd: Mapped[float] = mapped_column(Numeric(16, 4), default=0)

    # What triggered this snapshot
    trigger_type: Mapped[str] = mapped_column(
        String(32)
    )  # scheduled, oracle_event, manual
    trigger_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Detailed breakdown
    score_details: Mapped[dict] = mapped_column(JSONB, default=dict)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    person: Mapped["Person"] = relationship(  # noqa: F821
        "Person", back_populates="valuation_snapshots"
    )
