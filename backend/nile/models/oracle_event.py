"""OracleEvent model — real-world events affecting a person's NIL value."""

import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base, TimestampMixin, UUIDMixin


class OracleEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "oracle_events"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.id"), index=True
    )

    # Event details
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # social_viral, news_positive, sports_win, injury, scandal, etc.
    source: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # twitter, espn, reuters, etc.
    headline: Mapped[str] = mapped_column(Text, nullable=False)

    # Impact assessment
    impact_score: Mapped[int] = mapped_column(Integer, default=0)  # -100 to +100
    confidence: Mapped[float] = mapped_column(
        Numeric(5, 4), default=0
    )  # 0.0 to 1.0

    # Consensus tracking
    status: Mapped[str] = mapped_column(
        String(16), default="pending", index=True
    )  # pending, confirmed, rejected
    confirmations: Mapped[int] = mapped_column(Integer, default=0)
    rejections: Mapped[int] = mapped_column(Integer, default=0)
    required_confirmations: Mapped[int] = mapped_column(Integer, default=2)

    # On-chain reference
    on_chain_event_id: Mapped[str | None] = mapped_column(String(66))
    tx_hash: Mapped[str | None] = mapped_column(String(66))

    # Raw data and agent voting record
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    agent_votes: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # {agent_id: {vote: "confirm"|"reject", impact: int}}

    # Relationships
    person: Mapped["Person"] = relationship(  # noqa: F821
        "Person", back_populates="oracle_events"
    )
