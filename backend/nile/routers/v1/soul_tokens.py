"""Soul Token API endpoints — token listings, market data, candles."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from nile.core.database import get_db
from nile.models.price_candle import PriceCandle
from nile.models.soul_token import SoulToken
from nile.models.trade import Trade
from nile.schemas.soul_token import (
    MarketOverview,
    PriceCandleResponse,
    SoulTokenListItem,
    SoulTokenResponse,
    TradeResponse,
)

router = APIRouter()


@router.get("", response_model=list[SoulTokenListItem])
async def list_soul_tokens(
    sort: str = "market_cap",
    phase: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[SoulTokenListItem]:
    """List soul tokens with market data."""
    query = select(SoulToken).options(selectinload(SoulToken.person))

    if phase:
        query = query.where(SoulToken.phase == phase)

    if sort == "market_cap":
        query = query.order_by(SoulToken.market_cap_usd.desc())
    elif sort == "volume":
        query = query.order_by(SoulToken.volume_24h_usd.desc())
    elif sort == "new":
        query = query.order_by(SoulToken.created_at.desc())
    elif sort == "price":
        query = query.order_by(SoulToken.current_price_usd.desc())

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    tokens = result.scalars().all()

    return [
        SoulTokenListItem(
            id=t.id,
            name=t.name,
            symbol=t.symbol,
            phase=t.phase,
            current_price_usd=float(t.current_price_usd or 0),
            market_cap_usd=float(t.market_cap_usd or 0),
            volume_24h_usd=float(t.volume_24h_usd or 0),
            price_change_24h_pct=float(t.price_change_24h_pct or 0),
            holder_count=t.holder_count or 0,
            person_name=t.person.display_name if t.person else None,
            person_slug=t.person.slug if t.person else None,
        )
        for t in tokens
    ]


@router.get("/market-overview", response_model=MarketOverview)
async def market_overview(
    db: AsyncSession = Depends(get_db),
) -> MarketOverview:
    """Global market statistics."""
    total = await db.execute(select(func.count(SoulToken.id)))
    mcap = await db.execute(select(func.sum(SoulToken.market_cap_usd)))
    vol = await db.execute(select(func.sum(SoulToken.volume_24h_usd)))
    graduating = await db.execute(
        select(func.count(SoulToken.id)).where(
            SoulToken.phase == "bonding",
            SoulToken.reserve_balance_eth >= SoulToken.graduation_threshold_eth * 0.8,
        )
    )

    return MarketOverview(
        total_tokens=total.scalar() or 0,
        total_market_cap_usd=float(mcap.scalar() or 0),
        total_volume_24h_usd=float(vol.scalar() or 0),
        graduating_soon_count=graduating.scalar() or 0,
    )


@router.get("/graduating-soon", response_model=list[SoulTokenListItem])
async def graduating_soon(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> list[SoulTokenListItem]:
    """Tokens approaching graduation threshold."""
    query = (
        select(SoulToken)
        .options(selectinload(SoulToken.person))
        .where(SoulToken.phase == "bonding")
        .order_by(
            (SoulToken.reserve_balance_eth / SoulToken.graduation_threshold_eth).desc()
        )
        .limit(limit)
    )
    result = await db.execute(query)
    tokens = result.scalars().all()

    return [
        SoulTokenListItem(
            id=t.id,
            name=t.name,
            symbol=t.symbol,
            phase=t.phase,
            current_price_usd=float(t.current_price_usd or 0),
            market_cap_usd=float(t.market_cap_usd or 0),
            volume_24h_usd=float(t.volume_24h_usd or 0),
            price_change_24h_pct=float(t.price_change_24h_pct or 0),
            holder_count=t.holder_count or 0,
            person_name=t.person.display_name if t.person else None,
            person_slug=t.person.slug if t.person else None,
        )
        for t in tokens
    ]


@router.get("/{token_id}", response_model=SoulTokenResponse)
async def get_soul_token(
    token_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SoulTokenResponse:
    """Get soul token details with market data."""
    query = (
        select(SoulToken)
        .where(SoulToken.id == token_id)
        .options(selectinload(SoulToken.person))
    )
    result = await db.execute(query)
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(404, "Soul token not found")

    return SoulTokenResponse(
        id=token.id,
        person_id=token.person_id,
        token_address=token.token_address,
        curve_address=token.curve_address,
        pool_address=token.pool_address,
        name=token.name,
        symbol=token.symbol,
        phase=token.phase,
        chain=token.chain,
        current_price_eth=float(token.current_price_eth or 0),
        current_price_usd=float(token.current_price_usd or 0),
        market_cap_usd=float(token.market_cap_usd or 0),
        total_supply=float(token.total_supply or 0),
        reserve_balance_eth=float(token.reserve_balance_eth or 0),
        volume_24h_usd=float(token.volume_24h_usd or 0),
        price_change_24h_pct=float(token.price_change_24h_pct or 0),
        holder_count=token.holder_count or 0,
        nile_valuation_total=float(token.nile_valuation_total or 0),
        graduation_threshold_eth=float(token.graduation_threshold_eth or 0),
        graduated_at=token.graduated_at,
        creator_address=token.creator_address,
        created_at=token.created_at,
        person_name=token.person.display_name if token.person else None,
        person_slug=token.person.slug if token.person else None,
        person_category=token.person.category if token.person else None,
    )


@router.get("/{token_id}/trades", response_model=list[TradeResponse])
async def list_trades(
    token_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[TradeResponse]:
    """Get trade history for a soul token."""
    query = (
        select(Trade)
        .where(Trade.soul_token_id == token_id)
        .order_by(Trade.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    return [TradeResponse.model_validate(t) for t in result.scalars().all()]


@router.get("/{token_id}/candles", response_model=list[PriceCandleResponse])
async def get_candles(
    token_id: uuid.UUID,
    interval: str = "1h",
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[PriceCandleResponse]:
    """Get OHLCV candles for a soul token."""
    query = (
        select(PriceCandle)
        .where(PriceCandle.soul_token_id == token_id, PriceCandle.interval == interval)
        .order_by(PriceCandle.open_time.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return [PriceCandleResponse.model_validate(c) for c in result.scalars().all()]
