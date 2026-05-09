"""Trading API endpoints — quotes, buy/sell, portfolio.

Supports two modes controlled by settings.use_chain (NILE_USE_CHAIN env var):

  USE_CHAIN=False (default):
    Off-chain simulation using the Bancor bonding curve math from
    bonding_math.py.  Prices match what the on-chain contracts would
    return, but no transactions are broadcast.

  USE_CHAIN=True:
    Reads quotes from the deployed NileRouter contract via chain_service.
    Trade records include tx_hash and block_number after on-chain execution.

In both modes, every trade updates:
  - The Trade table (trade record)
  - The Portfolio table (wallet holdings, avg buy price, PnL)
  - The SoulToken table (current_price_eth, current_price_usd, reserve_balance_eth, total_supply)
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from nile.config import settings
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
from nile.services.bonding_math import (
    RESERVE_RATIO,
    get_current_price,
    get_effective_reserve,
    get_effective_supply,
    quote_buy as bancor_quote_buy,
    quote_sell as bancor_quote_sell,
    simulate_buy,
    simulate_sell,
)
from nile.services.risk_engine import is_circuit_breaker_active, run_risk_checks

logger = logging.getLogger(__name__)

router = APIRouter()

# Flag: flip to True when contracts are deployed on Base
USE_CHAIN: bool = settings.use_chain


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_token_by_person(db: AsyncSession, person_id: uuid.UUID) -> SoulToken:
    """Look up a SoulToken by person_id or raise 404."""
    query = select(SoulToken).where(SoulToken.person_id == person_id)
    result = await db.execute(query)
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(404, "No soul token found for this person")
    return token


def _token_supply(token: SoulToken) -> float:
    """Get the circulating supply from the SoulToken record."""
    return float(token.total_supply or 0)


def _token_reserve(token: SoulToken) -> float:
    """Get the actual (non-virtual) reserve from the SoulToken record."""
    return float(token.reserve_balance_eth or 0)


async def _update_portfolio_buy(
    db: AsyncSession,
    wallet_address: str,
    soul_token_id: uuid.UUID,
    tokens_bought: float,
    eth_spent: float,
    current_price_eth: float,
) -> None:
    """Create or update a Portfolio record after a buy trade.

    - Increases token_balance
    - Increases total_invested_eth
    - Recalculates avg_buy_price
    - Updates current_value_eth and unrealized_pnl_eth
    """
    query = select(Portfolio).where(
        Portfolio.wallet_address == wallet_address,
        Portfolio.soul_token_id == soul_token_id,
    )
    result = await db.execute(query)
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        portfolio = Portfolio(
            wallet_address=wallet_address,
            soul_token_id=soul_token_id,
            balance=tokens_bought,
            avg_buy_price_eth=current_price_eth,
            total_invested_eth=eth_spent,
            total_sold_eth=0.0,
            realized_pnl_eth=0.0,
            current_value_eth=tokens_bought * current_price_eth,
            unrealized_pnl_eth=0.0,
        )
        db.add(portfolio)
    else:
        old_balance = float(portfolio.balance or 0)
        old_invested = float(portfolio.total_invested_eth or 0)
        old_avg = float(portfolio.avg_buy_price_eth or 0)

        new_balance = old_balance + tokens_bought
        new_invested = old_invested + eth_spent

        # Weighted average buy price
        if new_balance > 0:
            new_avg = (old_avg * old_balance + current_price_eth * tokens_bought) / new_balance
        else:
            new_avg = current_price_eth

        new_value = new_balance * current_price_eth
        unrealized = new_value - (new_balance * new_avg)

        portfolio.balance = new_balance
        portfolio.total_invested_eth = new_invested
        portfolio.avg_buy_price_eth = new_avg
        portfolio.current_value_eth = new_value
        portfolio.unrealized_pnl_eth = unrealized


async def _update_portfolio_sell(
    db: AsyncSession,
    wallet_address: str,
    soul_token_id: uuid.UUID,
    tokens_sold: float,
    eth_received: float,
    current_price_eth: float,
) -> None:
    """Update a Portfolio record after a sell trade.

    - Decreases token_balance
    - Increases total_sold_eth
    - Calculates realized_pnl for this sale
    - Updates current_value_eth and unrealized_pnl_eth
    """
    query = select(Portfolio).where(
        Portfolio.wallet_address == wallet_address,
        Portfolio.soul_token_id == soul_token_id,
    )
    result = await db.execute(query)
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        logger.warning(
            "Sell with no portfolio record: wallet=%s token=%s",
            wallet_address,
            soul_token_id,
        )
        portfolio = Portfolio(
            wallet_address=wallet_address,
            soul_token_id=soul_token_id,
            balance=0.0,
            avg_buy_price_eth=0.0,
            total_invested_eth=0.0,
            total_sold_eth=eth_received,
            realized_pnl_eth=0.0,
            current_value_eth=0.0,
            unrealized_pnl_eth=0.0,
        )
        db.add(portfolio)
        return

    old_balance = float(portfolio.balance or 0)
    old_avg = float(portfolio.avg_buy_price_eth or 0)
    old_realized = float(portfolio.realized_pnl_eth or 0)
    old_sold = float(portfolio.total_sold_eth or 0)

    # Realized PnL: difference between sale proceeds and cost basis
    cost_basis = tokens_sold * old_avg
    realized_this_trade = eth_received - cost_basis

    new_balance = max(old_balance - tokens_sold, 0.0)
    new_sold = old_sold + eth_received
    new_realized = old_realized + realized_this_trade

    new_value = new_balance * current_price_eth
    unrealized = new_value - (new_balance * old_avg) if new_balance > 0 else 0.0

    portfolio.balance = new_balance
    portfolio.total_sold_eth = new_sold
    portfolio.realized_pnl_eth = new_realized
    portfolio.current_value_eth = new_value
    portfolio.unrealized_pnl_eth = unrealized


async def _update_token_price(
    db: AsyncSession,
    token: SoulToken,
    new_price_eth: float,
    new_reserve: float | None = None,
    new_supply: float | None = None,
    eth_usd_price: float | None = None,
) -> None:
    """Update the SoulToken cached market data after a trade."""
    token.current_price_eth = new_price_eth

    if eth_usd_price is not None and eth_usd_price > 0:
        token.current_price_usd = new_price_eth * eth_usd_price
        if new_supply is not None:
            token.market_cap_usd = new_supply * new_price_eth * eth_usd_price
    else:
        old_eth = float(token.current_price_eth or 0)
        old_usd = float(token.current_price_usd or 0)
        if old_eth > 0:
            ratio = old_usd / old_eth
        else:
            ratio = 2500.0
        token.current_price_usd = new_price_eth * ratio
        if new_supply is not None:
            token.market_cap_usd = new_supply * new_price_eth * ratio

    if new_reserve is not None:
        token.reserve_balance_eth = new_reserve
    if new_supply is not None:
        token.total_supply = new_supply


async def _get_eth_usd_price() -> float | None:
    """Try to get ETH/USD price from chain service (best-effort)."""
    if USE_CHAIN:
        try:
            from nile.services.chain_service import chain_service
            return await chain_service.get_eth_price_usd()
        except Exception:
            logger.debug("Could not fetch ETH/USD price from chain")
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/quote", response_model=QuoteResponse)
async def get_quote(
    request: Request,
    req: QuoteRequest,
    db: AsyncSession = Depends(get_db),
) -> QuoteResponse:
    """Get a price quote for a buy or sell."""
    quote_limiter.check(request)
    token = await _get_token_by_person(db, req.person_id)

    amount = float(req.amount)
    supply = _token_supply(token)
    reserve = _token_reserve(token)

    if USE_CHAIN:
        # ---- On-chain quote via NileRouter ----
        from nile.services.chain_service import chain_service

        person_bytes = token.person_id.bytes
        if req.side == "buy":
            eth_wei = int(amount * 1e18)
            result = await chain_service.get_quote_buy(person_bytes, eth_wei)
            if result is None:
                raise HTTPException(503, "Chain quote unavailable")
            tokens_out_wei, fee_wei = result
            tokens_out = tokens_out_wei / 1e18
            fee = fee_wei / 1e18
            eff_supply = get_effective_supply(supply)
            eff_reserve = get_effective_reserve(reserve)
            est_price = get_current_price(eff_supply, eff_reserve + amount, RESERVE_RATIO)
            return QuoteResponse(
                person_id=req.person_id,
                side="buy",
                input_amount=amount,
                output_amount=tokens_out,
                fee=fee,
                price_impact_pct=min(amount / max(eff_reserve, 0.01) * 100, 50),
                estimated_price=est_price,
            )
        else:
            token_wei = int(amount * 1e18)
            result = await chain_service.get_quote_sell(person_bytes, token_wei)
            if result is None:
                raise HTTPException(503, "Chain quote unavailable")
            eth_out_wei, fee_wei = result
            eth_out = eth_out_wei / 1e18
            fee = fee_wei / 1e18
            eff_supply = get_effective_supply(supply)
            eff_reserve = get_effective_reserve(reserve)
            est_price = get_current_price(
                max(eff_supply - amount, 1),
                max(eff_reserve - eth_out, 0.01),
                RESERVE_RATIO,
            )
            return QuoteResponse(
                person_id=req.person_id,
                side="sell",
                input_amount=amount,
                output_amount=eth_out,
                fee=fee,
                price_impact_pct=min(amount / max(eff_supply, 1) * 100, 50),
                estimated_price=est_price,
            )

    else:
        # ---- Off-chain Bancor simulation ----
        if req.side == "buy":
            q = bancor_quote_buy(supply, reserve, amount)
            return QuoteResponse(
                person_id=req.person_id,
                side="buy",
                input_amount=amount,
                output_amount=q["tokens_out"],
                fee=q["fee"],
                price_impact_pct=q["price_impact_pct"],
                estimated_price=q["estimated_price"],
            )
        else:
            q = bancor_quote_sell(supply, reserve, amount)
            return QuoteResponse(
                person_id=req.person_id,
                side="sell",
                input_amount=amount,
                output_amount=q["eth_out"],
                fee=q["fee"],
                price_impact_pct=q["price_impact_pct"],
                estimated_price=q["estimated_price"],
            )


@router.post("/buy", response_model=TradeResponse, status_code=201)
async def execute_buy(
    request: Request,
    req: TradeRequest,
    db: AsyncSession = Depends(get_db),
) -> TradeResponse:
    """Execute a buy trade.

    Off-chain: records trade with Bancor-accurate pricing.
    On-chain: reads quote from NileRouter and records the result.
    """
    trading_limiter.check(request)
    token = await _get_token_by_person(db, req.person_id)

    if is_circuit_breaker_active(str(token.id)):
        raise HTTPException(
            423, "Trading paused -- circuit breaker active for this token"
        )

    amount = float(req.amount)
    supply = _token_supply(token)
    reserve = _token_reserve(token)

    tx_hash: str | None = None
    block_number: int | None = None
    source = "api"

    if USE_CHAIN:
        from nile.services.chain_service import chain_service

        person_bytes = token.person_id.bytes
        eth_wei = int(amount * 1e18)

        quote_result = await chain_service.get_quote_buy(person_bytes, eth_wei)
        if quote_result is None:
            raise HTTPException(503, "Chain unavailable for trading")
        tokens_out_wei, fee_wei = quote_result
        tokens_out = tokens_out_wei / 1e18
        fee_total = fee_wei / 1e18

        sim = simulate_buy(supply, reserve, amount)
        new_price_eth = sim["new_price_eth"]
        new_supply = sim["new_supply"]
        new_reserve = sim["new_reserve"]
        source = "chain"
    else:
        sim = simulate_buy(supply, reserve, amount)
        tokens_out = sim["tokens_out"]
        fee_total = sim["fee_total"]
        new_price_eth = sim["new_price_eth"]
        new_supply = sim["new_supply"]
        new_reserve = sim["new_reserve"]

    fee_creator = fee_total * 0.5
    fee_protocol = fee_total * 0.3
    fee_staker = fee_total * 0.2

    price_eth = new_price_eth
    eth_usd = await _get_eth_usd_price()
    price_usd = price_eth * (eth_usd if eth_usd else 2500.0)

    trade = Trade(
        soul_token_id=token.id,
        side="buy",
        token_amount=tokens_out,
        eth_amount=amount,
        price_eth=price_eth,
        price_usd=price_usd,
        fee_total_eth=fee_total,
        fee_creator_eth=fee_creator,
        fee_protocol_eth=fee_protocol,
        fee_staker_eth=fee_staker,
        trader_address=req.trader_address,
        tx_hash=tx_hash,
        block_number=block_number,
        phase=token.phase,
        source=source,
    )
    db.add(trade)

    await _update_token_price(
        db, token,
        new_price_eth=new_price_eth,
        new_reserve=new_reserve,
        new_supply=new_supply,
        eth_usd_price=eth_usd,
    )

    await _update_portfolio_buy(
        db,
        wallet_address=req.trader_address,
        soul_token_id=token.id,
        tokens_bought=tokens_out,
        eth_spent=amount,
        current_price_eth=new_price_eth,
    )

    await db.flush()
    await db.commit()
    await db.refresh(trade)

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
    """Execute a sell trade.

    Off-chain: records trade with Bancor-accurate pricing.
    On-chain: reads quote from NileRouter and records the result.
    """
    trading_limiter.check(request)
    token = await _get_token_by_person(db, req.person_id)

    if is_circuit_breaker_active(str(token.id)):
        raise HTTPException(
            423, "Trading paused -- circuit breaker active for this token"
        )

    amount = float(req.amount)
    supply = _token_supply(token)
    reserve = _token_reserve(token)

    tx_hash: str | None = None
    block_number: int | None = None
    source = "api"

    if USE_CHAIN:
        from nile.services.chain_service import chain_service

        person_bytes = token.person_id.bytes
        token_wei = int(amount * 1e18)

        quote_result = await chain_service.get_quote_sell(person_bytes, token_wei)
        if quote_result is None:
            raise HTTPException(503, "Chain unavailable for trading")
        eth_out_wei, fee_wei = quote_result
        eth_out = eth_out_wei / 1e18
        fee_total = fee_wei / 1e18

        sim = simulate_sell(supply, reserve, amount)
        new_price_eth = sim["new_price_eth"]
        new_supply = sim["new_supply"]
        new_reserve = sim["new_reserve"]
        source = "chain"
    else:
        sim = simulate_sell(supply, reserve, amount)
        eth_out = sim["eth_out"]
        fee_total = sim["fee_total"]
        new_price_eth = sim["new_price_eth"]
        new_supply = sim["new_supply"]
        new_reserve = sim["new_reserve"]

    fee_creator = fee_total * 0.5
    fee_protocol = fee_total * 0.3
    fee_staker = fee_total * 0.2

    price_eth = new_price_eth
    eth_usd = await _get_eth_usd_price()
    price_usd = price_eth * (eth_usd if eth_usd else 2500.0)

    trade = Trade(
        soul_token_id=token.id,
        side="sell",
        token_amount=amount,
        eth_amount=eth_out,
        price_eth=price_eth,
        price_usd=price_usd,
        fee_total_eth=fee_total,
        fee_creator_eth=fee_creator,
        fee_protocol_eth=fee_protocol,
        fee_staker_eth=fee_staker,
        trader_address=req.trader_address,
        tx_hash=tx_hash,
        block_number=block_number,
        phase=token.phase,
        source=source,
    )
    db.add(trade)

    await _update_token_price(
        db, token,
        new_price_eth=new_price_eth,
        new_reserve=new_reserve,
        new_supply=new_supply,
        eth_usd_price=eth_usd,
    )

    await _update_portfolio_sell(
        db,
        wallet_address=req.trader_address,
        soul_token_id=token.id,
        tokens_sold=amount,
        eth_received=eth_out,
        current_price_eth=new_price_eth,
    )

    await db.flush()
    await db.commit()
    await db.refresh(trade)

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
        current_value = balance * current_price
        unrealized = current_value - (balance * avg_price) if balance > 0 and avg_price > 0 else 0.0

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
