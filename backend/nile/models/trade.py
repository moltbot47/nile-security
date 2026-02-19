"""Trade model — records every buy/sell of a soul token."""

import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base, TimestampMixin, UUIDMixin


class Trade(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "trades"

    soul_token_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("soul_tokens.id"), index=True
    )

    # Trade details
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # buy or sell
    token_amount: Mapped[float] = mapped_column(Numeric(28, 18), nullable=False)
    eth_amount: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    price_eth: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    price_usd: Mapped[float] = mapped_column(Numeric(16, 4), nullable=False)

    # Fee breakdown
    fee_total_eth: Mapped[float] = mapped_column(Numeric(20, 10), default=0)
    fee_creator_eth: Mapped[float] = mapped_column(Numeric(20, 10), default=0)
    fee_protocol_eth: Mapped[float] = mapped_column(Numeric(20, 10), default=0)
    fee_staker_eth: Mapped[float] = mapped_column(Numeric(20, 10), default=0)

    # Blockchain reference
    tx_hash: Mapped[str | None] = mapped_column(String(66), unique=True, index=True)
    block_number: Mapped[int | None] = mapped_column(Integer)
    trader_address: Mapped[str] = mapped_column(String(42), index=True)

    # Phase when trade occurred
    phase: Mapped[str] = mapped_column(String(16), default="bonding")

    # Source: "chain" (indexed from on-chain) or "backend" (off-chain matching)
    source: Mapped[str] = mapped_column(String(16), default="chain")

    # Relationships
    soul_token: Mapped["SoulToken"] = relationship(  # noqa: F821
        "SoulToken", back_populates="trades"
    )
