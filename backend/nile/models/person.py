"""Person model — represents a human whose NIL value is tokenized."""

from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base, TimestampMixin, UUIDMixin


class Person(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "persons"

    # Identity
    display_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    banner_url: Mapped[str | None] = mapped_column(Text)

    # Verification
    verification_level: Mapped[str] = mapped_column(
        String(16), default="unverified", index=True
    )  # unverified, verified, premium
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Category and tags
    category: Mapped[str] = mapped_column(
        String(64), default="general", index=True
    )  # athlete, creator, musician, entrepreneur, etc.
    tags: Mapped[list] = mapped_column(JSONB, default=list)

    # Social links
    social_links: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # {"twitter": "...", "instagram": "...", etc.}

    # NILE Valuation Scores (human NIL context, 0-100 each)
    nile_name_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    nile_image_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    nile_likeness_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    nile_essence_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    nile_total_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    # Relationships
    soul_token: Mapped["SoulToken | None"] = relationship(  # noqa: F821
        "SoulToken", back_populates="person", uselist=False
    )
    valuation_snapshots: Mapped[list["ValuationSnapshot"]] = relationship(  # noqa: F821
        "ValuationSnapshot", back_populates="person", lazy="dynamic"
    )
    oracle_events: Mapped[list["OracleEvent"]] = relationship(  # noqa: F821
        "OracleEvent", back_populates="person", lazy="dynamic"
    )
