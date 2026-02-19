"""add_soul_token_market_tables

Revision ID: be8251cf9f1a
Revises: 0765810ab271
Create Date: 2026-02-19 06:12:17.813450

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "be8251cf9f1a"
down_revision: Union[str, Sequence[str], None] = "0765810ab271"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Soul Token market tables."""

    # 1. persons
    op.create_table(
        "persons",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("display_name", sa.String(256), nullable=False, index=True),
        sa.Column("slug", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("bio", sa.Text()),
        sa.Column("avatar_url", sa.Text()),
        sa.Column("banner_url", sa.Text()),
        sa.Column("verification_level", sa.String(16), server_default="unverified", index=True),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("category", sa.String(64), server_default="general", index=True),
        sa.Column("tags", postgresql.JSONB(), server_default="[]"),
        sa.Column("social_links", postgresql.JSONB(), server_default="{}"),
        sa.Column("nile_name_score", sa.Numeric(5, 2), server_default="0"),
        sa.Column("nile_image_score", sa.Numeric(5, 2), server_default="0"),
        sa.Column("nile_likeness_score", sa.Numeric(5, 2), server_default="0"),
        sa.Column("nile_essence_score", sa.Numeric(5, 2), server_default="0"),
        sa.Column("nile_total_score", sa.Numeric(5, 2), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 2. soul_tokens
    op.create_table(
        "soul_tokens",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("person_id", sa.UUID(), sa.ForeignKey("persons.id"), unique=True, index=True),
        sa.Column("token_address", sa.String(42), unique=True, index=True),
        sa.Column("curve_address", sa.String(42)),
        sa.Column("pool_address", sa.String(42)),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("phase", sa.String(16), server_default="bonding", index=True),
        sa.Column("chain", sa.String(16), server_default="base"),
        sa.Column("current_price_eth", sa.Numeric(20, 10), server_default="0"),
        sa.Column("current_price_usd", sa.Numeric(16, 4), server_default="0"),
        sa.Column("market_cap_usd", sa.Numeric(16, 2), server_default="0"),
        sa.Column("total_supply", sa.Numeric(28, 18), server_default="0"),
        sa.Column("reserve_balance_eth", sa.Numeric(20, 10), server_default="0"),
        sa.Column("volume_24h_usd", sa.Numeric(16, 2), server_default="0"),
        sa.Column("price_change_24h_pct", sa.Numeric(8, 4), server_default="0"),
        sa.Column("holder_count", sa.Integer(), server_default="0"),
        sa.Column("nile_valuation_total", sa.Numeric(5, 2), server_default="0"),
        sa.Column("graduation_threshold_eth", sa.Numeric(20, 10), server_default="20"),
        sa.Column("graduated_at", sa.DateTime(timezone=True)),
        sa.Column("creator_address", sa.String(42)),
        sa.Column("creator_royalty_bps", sa.Integer(), server_default="50"),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 3. trades
    op.create_table(
        "trades",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "soul_token_id", sa.UUID(), sa.ForeignKey("soul_tokens.id"), index=True
        ),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("token_amount", sa.Numeric(28, 18), nullable=False),
        sa.Column("eth_amount", sa.Numeric(20, 10), nullable=False),
        sa.Column("price_eth", sa.Numeric(20, 10), nullable=False),
        sa.Column("price_usd", sa.Numeric(16, 4), nullable=False),
        sa.Column("fee_total_eth", sa.Numeric(20, 10), server_default="0"),
        sa.Column("fee_creator_eth", sa.Numeric(20, 10), server_default="0"),
        sa.Column("fee_protocol_eth", sa.Numeric(20, 10), server_default="0"),
        sa.Column("fee_staker_eth", sa.Numeric(20, 10), server_default="0"),
        sa.Column("tx_hash", sa.String(66), unique=True, index=True),
        sa.Column("block_number", sa.Integer()),
        sa.Column("trader_address", sa.String(42), index=True),
        sa.Column("phase", sa.String(16), server_default="bonding"),
        sa.Column("source", sa.String(16), server_default="chain"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 4. price_candles
    op.create_table(
        "price_candles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "soul_token_id", sa.UUID(), sa.ForeignKey("soul_tokens.id"), index=True
        ),
        sa.Column("interval", sa.String(4), nullable=False, index=True),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(20, 10)),
        sa.Column("high", sa.Numeric(20, 10)),
        sa.Column("low", sa.Numeric(20, 10)),
        sa.Column("close", sa.Numeric(20, 10)),
        sa.Column("volume_eth", sa.Numeric(20, 10), server_default="0"),
        sa.Column("volume_usd", sa.Numeric(16, 2), server_default="0"),
        sa.Column("trade_count", sa.Integer(), server_default="0"),
        sa.UniqueConstraint(
            "soul_token_id", "interval", "open_time",
            name="uq_candle_token_interval_time",
        ),
    )

    # 5. oracle_events
    op.create_table(
        "oracle_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("person_id", sa.UUID(), sa.ForeignKey("persons.id"), index=True),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("impact_score", sa.Integer(), server_default="0"),
        sa.Column("confidence", sa.Numeric(5, 4), server_default="0"),
        sa.Column("status", sa.String(16), server_default="pending", index=True),
        sa.Column("confirmations", sa.Integer(), server_default="0"),
        sa.Column("rejections", sa.Integer(), server_default="0"),
        sa.Column("required_confirmations", sa.Integer(), server_default="2"),
        sa.Column("on_chain_event_id", sa.String(66)),
        sa.Column("tx_hash", sa.String(66)),
        sa.Column("raw_data", postgresql.JSONB(), server_default="{}"),
        sa.Column("agent_votes", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 6. valuation_snapshots
    op.create_table(
        "valuation_snapshots",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("person_id", sa.UUID(), sa.ForeignKey("persons.id"), index=True),
        sa.Column("name_score", sa.Numeric(5, 2)),
        sa.Column("image_score", sa.Numeric(5, 2)),
        sa.Column("likeness_score", sa.Numeric(5, 2)),
        sa.Column("essence_score", sa.Numeric(5, 2)),
        sa.Column("total_score", sa.Numeric(5, 2)),
        sa.Column("fair_value_usd", sa.Numeric(16, 4), server_default="0"),
        sa.Column("trigger_type", sa.String(32)),
        sa.Column("trigger_id", sa.UUID()),
        sa.Column("score_details", postgresql.JSONB(), server_default="{}"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # 7. portfolios
    op.create_table(
        "portfolios",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("wallet_address", sa.String(42), nullable=False, index=True),
        sa.Column(
            "soul_token_id", sa.UUID(), sa.ForeignKey("soul_tokens.id"), index=True
        ),
        sa.Column("balance", sa.Numeric(28, 18), server_default="0"),
        sa.Column("avg_buy_price_eth", sa.Numeric(20, 10), server_default="0"),
        sa.Column("total_invested_eth", sa.Numeric(20, 10), server_default="0"),
        sa.Column("realized_pnl_eth", sa.Numeric(20, 10), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "wallet_address", "soul_token_id",
            name="uq_portfolio_wallet_token",
        ),
    )


def downgrade() -> None:
    """Drop Soul Token market tables."""
    op.drop_table("portfolios")
    op.drop_table("valuation_snapshots")
    op.drop_table("oracle_events")
    op.drop_table("price_candles")
    op.drop_table("trades")
    op.drop_table("soul_tokens")
    op.drop_table("persons")
