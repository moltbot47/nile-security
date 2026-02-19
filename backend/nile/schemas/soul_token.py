"""Pydantic schemas for Soul Token and Trading endpoints."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# --- Soul Token Schemas ---


class SoulTokenResponse(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID
    token_address: str | None = None
    curve_address: str | None = None
    pool_address: str | None = None
    name: str
    symbol: str
    phase: str
    chain: str
    current_price_eth: float
    current_price_usd: float
    market_cap_usd: float
    total_supply: float
    reserve_balance_eth: float
    volume_24h_usd: float
    price_change_24h_pct: float
    holder_count: int
    nile_valuation_total: float
    graduation_threshold_eth: float
    graduated_at: datetime | None = None
    creator_address: str | None = None
    created_at: datetime

    # Person info
    person_name: str | None = None
    person_slug: str | None = None
    person_category: str | None = None

    model_config = {"from_attributes": True}


class SoulTokenListItem(BaseModel):
    id: uuid.UUID
    name: str
    symbol: str
    phase: str
    current_price_usd: float
    market_cap_usd: float
    volume_24h_usd: float
    price_change_24h_pct: float
    holder_count: int
    person_name: str | None = None
    person_slug: str | None = None

    model_config = {"from_attributes": True}


class MarketOverview(BaseModel):
    total_tokens: int
    total_market_cap_usd: float
    total_volume_24h_usd: float
    graduating_soon_count: int


# --- Trade Schemas ---


class TradeResponse(BaseModel):
    id: uuid.UUID
    soul_token_id: uuid.UUID
    side: str
    token_amount: float
    eth_amount: float
    price_eth: float
    price_usd: float
    fee_total_eth: float
    tx_hash: str | None = None
    trader_address: str | None = None
    phase: str
    created_at: datetime

    model_config = {"from_attributes": True}


class QuoteRequest(BaseModel):
    person_id: uuid.UUID
    side: str = Field(..., pattern=r"^(buy|sell)$")
    amount: Decimal = Field(..., gt=0)


class QuoteResponse(BaseModel):
    person_id: uuid.UUID
    side: str
    input_amount: float
    output_amount: float
    fee: float
    price_impact_pct: float
    estimated_price: float


class TradeRequest(BaseModel):
    person_id: uuid.UUID
    side: str = Field(..., pattern=r"^(buy|sell)$")
    amount: Decimal = Field(..., gt=0)
    max_slippage_pct: float = Field(default=1.0, ge=0, le=50)
    trader_address: str = Field(..., min_length=42, max_length=42)


# --- Price Candle Schemas ---


class PriceCandleResponse(BaseModel):
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume_eth: float
    volume_usd: float
    trade_count: int

    model_config = {"from_attributes": True}


# --- Portfolio Schemas ---


class PortfolioItem(BaseModel):
    id: uuid.UUID
    soul_token_id: uuid.UUID
    token_symbol: str | None = None
    person_name: str | None = None
    balance: float
    avg_buy_price_eth: float
    total_invested_eth: float
    realized_pnl_eth: float
    current_price_eth: float | None = None
    unrealized_pnl_eth: float | None = None

    model_config = {"from_attributes": True}
