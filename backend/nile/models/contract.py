"""Contract model — the 'Name' identity of each smart contract."""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base, TimestampMixin, UUIDMixin


class Contract(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "contracts"

    address: Mapped[str | None] = mapped_column(String(42), index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    chain: Mapped[str] = mapped_column(String(32), default="ethereum")
    compiler_version: Mapped[str | None] = mapped_column(String(32))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    nile_scores = relationship("NileScore", back_populates="contract", lazy="selectin")
    vulnerabilities = relationship("Vulnerability", back_populates="contract", lazy="selectin")
    scan_jobs = relationship("ScanJob", back_populates="contract", lazy="selectin")
