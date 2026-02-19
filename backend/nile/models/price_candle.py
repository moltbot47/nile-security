"""PriceCandle model — OHLCV data for soul token price charts."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base


class PriceCandle(Base):
    __tablename__ = "price_candles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    soul_token_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("soul_tokens.id"), index=True
    )

    interval: Mapped[str] = mapped_column(
        String(4), nullable=False, index=True
    )  # 1m, 5m, 1h, 1d
    open_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    close_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    open: Mapped[float] = mapped_column(Numeric(20, 10))
    high: Mapped[float] = mapped_column(Numeric(20, 10))
    low: Mapped[float] = mapped_column(Numeric(20, 10))
    close: Mapped[float] = mapped_column(Numeric(20, 10))
    volume_eth: Mapped[float] = mapped_column(Numeric(20, 10), default=0)
    volume_usd: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    trade_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint(
            "soul_token_id", "interval", "open_time",
            name="uq_candle_token_interval_time",
        ),
    )

    soul_token: Mapped["SoulToken"] = relationship(  # noqa: F821
        "SoulToken", back_populates="candles"
    )
