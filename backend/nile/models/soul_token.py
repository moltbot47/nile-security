"""SoulToken model — ERC-20 token representing a person's tradeable NIL value."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base, TimestampMixin, UUIDMixin


class SoulToken(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "soul_tokens"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.id"), unique=True, index=True
    )

    # On-chain addresses
    token_address: Mapped[str | None] = mapped_column(
        String(42), unique=True, index=True
    )
    curve_address: Mapped[str | None] = mapped_column(String(42))
    pool_address: Mapped[str | None] = mapped_column(String(42))

    # Token identity
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)

    # Market phase
    phase: Mapped[str] = mapped_column(
        String(16), default="bonding", index=True
    )  # bonding, amm, orderbook
    chain: Mapped[str] = mapped_column(String(16), default="base")

    # Cached market data (updated by market data worker)
    current_price_eth: Mapped[float] = mapped_column(Numeric(20, 10), default=0)
    current_price_usd: Mapped[float] = mapped_column(Numeric(16, 4), default=0)
    market_cap_usd: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    total_supply: Mapped[float] = mapped_column(Numeric(28, 18), default=0)
    reserve_balance_eth: Mapped[float] = mapped_column(Numeric(20, 10), default=0)
    volume_24h_usd: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    price_change_24h_pct: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    holder_count: Mapped[int] = mapped_column(Integer, default=0)

    # NILE valuation total for this person's token
    nile_valuation_total: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    # Graduation
    graduation_threshold_eth: Mapped[float] = mapped_column(
        Numeric(20, 10), default=20
    )  # ~$50K
    graduated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Creator info
    creator_address: Mapped[str | None] = mapped_column(String(42))
    creator_royalty_bps: Mapped[int] = mapped_column(Integer, default=50)  # 0.5%

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    person: Mapped["Person"] = relationship(  # noqa: F821
        "Person", back_populates="soul_token"
    )
    trades: Mapped[list["Trade"]] = relationship(  # noqa: F821
        "Trade", back_populates="soul_token", lazy="dynamic"
    )
    candles: Mapped[list["PriceCandle"]] = relationship(  # noqa: F821
        "PriceCandle", back_populates="soul_token", lazy="dynamic"
    )
