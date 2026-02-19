"""Trading API endpoints — quotes, buy/sell, portfolio."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from nile.core.database import get_db
from nile.core.rate_limit import quote_limiter, trading_limiter
from nile.models.portfolio import Portfolio
from nile.models.soul_token import SoulToken
from nile.models.trade import Trade
from nile.schemas.soul_token import (
    PortfolioItem,
    QuoteRequest,
    QuoteResponse,
    TradeRequest,
    TradeResponse,
)
from nile.services.risk_engine import is_circuit_breaker_active, run_risk_checks

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/quote", response_model=QuoteResponse)
async def get_quote(
    request: Request,
    req: QuoteRequest,
    db: AsyncSession = Depends(get_db),
) -> QuoteResponse:
    """Get a price quote for a buy or sell."""
    quote_limiter.check(request)
    # Look up soul token by person_id
    query = select(SoulToken).where(SoulToken.person_id == req.person_id)
    result = await db.execute(query)
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(404, "No soul token found for this person")

    # For now return simulated quote based on cached market data
    price = float(token.current_price_usd or 0)
    amount = float(req.amount)

    if req.side == "buy":
        # ETH amount in → tokens out
        fee = amount * 0.01
        net_amount = amount - fee
        tokens_out = net_amount / price if price > 0 else 0
        return QuoteResponse(
            person_id=req.person_id,
            side="buy",
            input_amount=amount,
            output_amount=tokens_out,
            fee=fee,
            price_impact_pct=min(amount / max(float(token.market_cap_usd or 1), 1) * 100, 50),
            estimated_price=price,
        )
    else:
        # Token amount in → ETH out
        eth_out = amount * price
        fee = eth_out * 0.01
        return QuoteResponse(
            person_id=req.person_id,
            side="sell",
            input_amount=amount,
            output_amount=eth_out - fee,
            fee=fee,
            price_impact_pct=min(amount / max(float(token.total_supply or 1), 1) * 100, 50),
            estimated_price=price,
        )


@router.post("/buy", response_model=TradeResponse, status_code=201)
async def execute_buy(
    request: Request,
    req: TradeRequest,
    db: AsyncSession = Depends(get_db),
) -> TradeResponse:
    """Execute a buy trade (off-chain record, on-chain tx async)."""
    trading_limiter.check(request)
    query = select(SoulToken).where(SoulToken.person_id == req.person_id)
    result = await db.execute(query)
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(404, "No soul token found for this person")

    # Circuit breaker check
    if is_circuit_breaker_active(str(token.id)):
        raise HTTPException(
            423, "Trading paused — circuit breaker active for this token"
        )

    amount = float(req.amount)
    price = float(token.current_price_usd or 0)
    price_eth = float(token.current_price_eth or 0)
    fee = amount * 0.01
    tokens_out = (amount - fee) / price if price > 0 else 0

    trade = Trade(
        soul_token_id=token.id,
        side="buy",
        token_amount=tokens_out,
        eth_amount=amount,
        price_eth=price_eth,
        price_usd=price,
        fee_total_eth=fee,
        fee_creator_eth=fee * 0.5,
        fee_protocol_eth=fee * 0.3,
        fee_staker_eth=fee * 0.2,
        trader_address=req.trader_address,
        phase=token.phase,
        source="api",
    )
    db.add(trade)
    await db.flush()
    await db.commit()
    await db.refresh(trade)

    # Post-trade risk checks (async, non-blocking for response)
    try:
        alerts = await run_risk_checks(
            db, soul_token_id=str(token.id), trader_address=req.trader_address
        )
        if alerts:
            logger.warning("Risk alerts after buy: %s", alerts)
    except Exception:
        logger.exception("Risk check failed after buy")

    return TradeResponse.model_validate(trade)


@router.post("/sell", response_model=TradeResponse, status_code=201)
async def execute_sell(
    request: Request,
    req: TradeRequest,
    db: AsyncSession = Depends(get_db),
) -> TradeResponse:
    """Execute a sell trade (off-chain record, on-chain tx async)."""
    trading_limiter.check(request)
    query = select(SoulToken).where(SoulToken.person_id == req.person_id)
    result = await db.execute(query)
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(404, "No soul token found for this person")

    # Circuit breaker check
    if is_circuit_breaker_active(str(token.id)):
        raise HTTPException(
            423, "Trading paused — circuit breaker active for this token"
        )

    amount = float(req.amount)
    price = float(token.current_price_usd or 0)
    price_eth = float(token.current_price_eth or 0)
    eth_out = amount * price_eth
    fee = eth_out * 0.01

    trade = Trade(
        soul_token_id=token.id,
        side="sell",
        token_amount=amount,
        eth_amount=eth_out - fee,
        price_eth=price_eth,
        price_usd=price,
        fee_total_eth=fee,
        fee_creator_eth=fee * 0.5,
        fee_protocol_eth=fee * 0.3,
        fee_staker_eth=fee * 0.2,
        trader_address=req.trader_address,
        phase=token.phase,
        source="api",
    )
    db.add(trade)
    await db.flush()
    await db.commit()
    await db.refresh(trade)

    # Post-trade risk checks
    try:
        alerts = await run_risk_checks(
            db, soul_token_id=str(token.id), trader_address=req.trader_address
        )
        if alerts:
            logger.warning("Risk alerts after sell: %s", alerts)
    except Exception:
        logger.exception("Risk check failed after sell")

    return TradeResponse.model_validate(trade)


@router.get("/history", response_model=list[TradeResponse])
async def trade_history(
    trader_address: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[TradeResponse]:
    """Get trade history, optionally filtered by trader."""
    query = select(Trade).order_by(Trade.created_at.desc()).limit(limit)
    if trader_address:
        query = query.where(Trade.trader_address == trader_address)

    result = await db.execute(query)
    return [TradeResponse.model_validate(t) for t in result.scalars().all()]


@router.get("/portfolio", response_model=list[PortfolioItem])
async def get_portfolio(
    wallet_address: str,
    db: AsyncSession = Depends(get_db),
) -> list[PortfolioItem]:
    """Get portfolio holdings for a wallet."""
    query = (
        select(Portfolio)
        .where(Portfolio.wallet_address == wallet_address)
        .options(selectinload(Portfolio.soul_token))
    )
    result = await db.execute(query)
    holdings = result.scalars().all()

    items = []
    for h in holdings:
        token = h.soul_token
        current_price = float(token.current_price_eth or 0) if token else 0
        balance = float(h.balance or 0)
        avg_price = float(h.avg_buy_price_eth or 0)
        unrealized = (current_price - avg_price) * balance if current_price and avg_price else None

        items.append(
            PortfolioItem(
                id=h.id,
                soul_token_id=h.soul_token_id,
                token_symbol=token.symbol if token else None,
                person_name=None,
                balance=balance,
                avg_buy_price_eth=avg_price,
                total_invested_eth=float(h.total_invested_eth or 0),
                realized_pnl_eth=float(h.realized_pnl_eth or 0),
                current_price_eth=current_price,
                unrealized_pnl_eth=unrealized,
            )
        )
    return items
