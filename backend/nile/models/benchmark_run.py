"""Benchmark run model — EVMbench evaluation results."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from nile.models.base import Base, UUIDMixin


class BenchmarkRun(UUIDMixin, Base):
    __tablename__ = "benchmark_runs"

    split: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    agent: Mapped[str] = mapped_column(String(32), nullable=False)

    # Aggregate results
    total_score: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    max_score: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    score_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    # Per-audit breakdown
    audit_results: Mapped[list] = mapped_column(JSONB, default=list)

    # Baseline comparison
    baseline_agent: Mapped[str | None] = mapped_column(String(32))
    baseline_score_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))

    status: Mapped[str] = mapped_column(String(16), default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
