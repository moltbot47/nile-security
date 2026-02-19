"""Agent model — registered AI agents in the NILE ecosystem."""


from sqlalchemy import Boolean, DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base, TimestampMixin, UUIDMixin


class Agent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(32), default="0.1.0")

    # Owner identity
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Capabilities: ["detect", "patch", "exploit"]
    capabilities: Mapped[list] = mapped_column(JSONB, default=list)
    config_schema: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Status
    status: Mapped[str] = mapped_column(String(16), default="pending_review", index=True)

    # Authentication
    api_key_hash: Mapped[str | None] = mapped_column(String(128))

    # Execution mode
    api_endpoint: Mapped[str | None] = mapped_column(Text)
    docker_image: Mapped[str | None] = mapped_column(String(256))

    # Agent NILE identity scores (0-100)
    nile_score_total: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    nile_score_name: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    nile_score_image: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    nile_score_likeness: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    nile_score_essence: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    # Cumulative stats
    total_points: Mapped[int] = mapped_column(default=0)
    total_contributions: Mapped[int] = mapped_column(default=0)

    # Liveness
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    last_heartbeat: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    contributions = relationship("AgentContribution", back_populates="agent", lazy="selectin")
    sent_messages = relationship(
        "AgentMessage", foreign_keys="AgentMessage.sender_agent_id", back_populates="sender"
    )
