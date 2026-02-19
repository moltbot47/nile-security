"""initial schema with agent ecosystem

Revision ID: 0765810ab271
Revises:
Create Date: 2026-02-19 04:22:33.877434

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0765810ab271"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- contracts ---
    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("address", sa.String(42), index=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("source_url", sa.Text),
        sa.Column("chain", sa.String(32), server_default="ethereum"),
        sa.Column("compiler_version", sa.String(32)),
        sa.Column("is_verified", sa.Boolean, server_default="false"),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- nile_scores ---
    op.create_table(
        "nile_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contract_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contracts.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("total_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("name_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("image_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("likeness_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("essence_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("score_details", postgresql.JSONB, server_default="{}"),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("trigger_id", postgresql.UUID(as_uuid=True)),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- scan_jobs ---
    op.create_table(
        "scan_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contract_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contracts.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(16), server_default="queued", index=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("agent", sa.String(32), nullable=False),
        sa.Column("config", postgresql.JSONB, server_default="{}"),
        sa.Column("hint_level", sa.String(8), server_default="none"),
        sa.Column("result", postgresql.JSONB),
        sa.Column("result_error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("tokens_used", sa.Integer, server_default="0"),
        sa.Column("api_cost_usd", sa.Numeric(10, 4), server_default="0"),
    )

    # --- vulnerabilities ---
    op.create_table(
        "vulnerabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contract_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contracts.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "scan_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scan_jobs.id")
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, index=True),
        sa.Column("category", sa.String(64), nullable=False, index=True),
        sa.Column("description", sa.Text),
        sa.Column("impact", sa.Text),
        sa.Column("proof_of_concept", sa.Text),
        sa.Column("remediation", sa.Text),
        sa.Column("file_path", sa.Text),
        sa.Column("line_start", sa.Integer),
        sa.Column("line_end", sa.Integer),
        sa.Column("confidence", sa.Numeric(3, 2)),
        sa.Column("exploitability_score", sa.Numeric(5, 2)),
        sa.Column("evmbench_vuln_id", sa.String(32)),
        sa.Column("evmbench_audit_id", sa.String(64)),
        sa.Column("status", sa.String(16), server_default="open"),
        sa.Column("patched_at", sa.DateTime(timezone=True)),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
    )

    # --- benchmark_runs ---
    op.create_table(
        "benchmark_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("split", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("agent", sa.String(32), nullable=False),
        sa.Column("total_score", sa.Numeric(8, 2), server_default="0"),
        sa.Column("max_score", sa.Numeric(8, 2), server_default="0"),
        sa.Column("score_pct", sa.Numeric(5, 2), server_default="0"),
        sa.Column("audit_results", postgresql.JSONB, server_default="[]"),
        sa.Column("baseline_agent", sa.String(32)),
        sa.Column("baseline_score_pct", sa.Numeric(5, 2)),
        sa.Column("status", sa.String(16), server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
    )

    # --- kpi_metrics ---
    op.create_table(
        "kpi_metrics",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("metric_name", sa.String(128), nullable=False, index=True),
        sa.Column("metric_type", sa.String(16), nullable=False),
        sa.Column("dimension", sa.String(16), nullable=False, index=True),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id")),
        sa.Column("category", sa.String(64)),
        sa.Column("agent", sa.String(32)),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True
        ),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
    )

    # --- agents ---
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("version", sa.String(32), server_default="0.1.0"),
        sa.Column("owner_id", sa.String(128), nullable=False, index=True),
        sa.Column("capabilities", postgresql.JSONB, server_default="[]"),
        sa.Column("config_schema", postgresql.JSONB, server_default="{}"),
        sa.Column("status", sa.String(16), server_default="pending_review", index=True),
        sa.Column("api_key_hash", sa.String(128)),
        sa.Column("api_endpoint", sa.Text),
        sa.Column("docker_image", sa.String(256)),
        sa.Column("nile_score_total", sa.Numeric(5, 2), server_default="0"),
        sa.Column("nile_score_name", sa.Numeric(5, 2), server_default="0"),
        sa.Column("nile_score_image", sa.Numeric(5, 2), server_default="0"),
        sa.Column("nile_score_likeness", sa.Numeric(5, 2), server_default="0"),
        sa.Column("nile_score_essence", sa.Numeric(5, 2), server_default="0"),
        sa.Column("total_points", sa.Integer, server_default="0"),
        sa.Column("total_contributions", sa.Integer, server_default="0"),
        sa.Column("is_online", sa.Boolean, server_default="false"),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- agent_contributions ---
    op.create_table(
        "agent_contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("contribution_type", sa.String(16), nullable=False, index=True),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id")),
        sa.Column("scan_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scan_jobs.id")),
        sa.Column("severity_found", sa.String(16)),
        sa.Column("verified", sa.Boolean, server_default="false"),
        sa.Column("points_awarded", sa.Integer, server_default="0"),
        sa.Column("details", postgresql.JSONB, server_default="{}"),
        sa.Column("summary", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- agent_messages ---
    op.create_table(
        "agent_messages",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "sender_agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "recipient_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id")
        ),
        sa.Column("channel", sa.String(32), nullable=False, index=True),
        sa.Column("message_type", sa.String(16), nullable=False),
        sa.Column("payload", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- ecosystem_events ---
    op.create_table(
        "ecosystem_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True
        ),
    )


def downgrade() -> None:
    op.drop_table("ecosystem_events")
    op.drop_table("agent_messages")
    op.drop_table("agent_contributions")
    op.drop_table("agents")
    op.drop_table("kpi_metrics")
    op.drop_table("benchmark_runs")
    op.drop_table("vulnerabilities")
    op.drop_table("scan_jobs")
    op.drop_table("nile_scores")
    op.drop_table("contracts")
