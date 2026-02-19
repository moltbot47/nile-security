"""KPI metric model — time-series dashboard metrics."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from nile.models.base import Base


class KPIMetric(Base):
    __tablename__ = "kpi_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(16), nullable=False)
    dimension: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)

    # Optional dimensional breakdowns
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id")
    )
    category: Mapped[str | None] = mapped_column(String(64))
    agent: Mapped[str | None] = mapped_column(String(32))

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        index=True,
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
