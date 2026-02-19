"""Risk engine — wash trade detection, pump/dump detection, circuit breakers."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.models.soul_token import SoulToken
from nile.models.trade import Trade
from nile.services.soul_collaboration import risk_to_circuit_breaker

logger = logging.getLogger(__name__)

# Circuit breaker duration (minutes)
CIRCUIT_BREAKER_DURATION = 15

# Thresholds
WASH_TRADE_WINDOW_SECONDS = 300  # 5 min
WASH_TRADE_MIN_RATIO = 0.8  # buy-back ≥80% of sold amount
PUMP_DUMP_WINDOW_MINUTES = 60  # 1 hour
PUMP_DUMP_PRICE_THRESHOLD = 0.5  # 50% increase
PUMP_DUMP_CONCENTRATION = 0.7  # 70% of volume from ≤3 wallets

# In-memory breaker state (per token_id → expiry datetime)
_active_breakers: dict[str, datetime] = {}


def is_circuit_breaker_active(token_id: str) -> bool:
    """Check if trading is paused for a token."""
    expiry = _active_breakers.get(token_id)
    if expiry is None:
        return False
    if datetime.now(UTC) >= expiry:
        del _active_breakers[token_id]
        return False
    return True


def activate_circuit_breaker(token_id: str, minutes: int = CIRCUIT_BREAKER_DURATION) -> datetime:
    """Activate circuit breaker for a token. Returns expiry time."""
    expiry = datetime.now(UTC) + timedelta(minutes=minutes)
    _active_breakers[token_id] = expiry
    logger.warning("Circuit breaker ACTIVATED for token %s until %s", token_id, expiry)
    return expiry


def get_active_breakers() -> dict[str, str]:
    """Return all active circuit breakers with their expiry times."""
    now = datetime.now(UTC)
    active = {}
    expired = []
    for token_id, expiry in _active_breakers.items():
        if now < expiry:
            active[token_id] = expiry.isoformat()
        else:
            expired.append(token_id)
    for token_id in expired:
        del _active_breakers[token_id]
    return active


async def check_wash_trading(
    db: AsyncSession,
    *,
    soul_token_id: str,
    trader_address: str,
) -> dict | None:
    """Detect wash trading: same wallet buy then sell (or reverse) within window.

    Returns risk alert dict if detected, None otherwise.
    """
    cutoff = datetime.now(UTC) - timedelta(seconds=WASH_TRADE_WINDOW_SECONDS)

    query = (
        select(Trade)
        .where(
            Trade.soul_token_id == soul_token_id,
            Trade.trader_address == trader_address,
            Trade.created_at >= cutoff,
        )
        .order_by(Trade.created_at.desc())
    )
    result = await db.execute(query)
    recent_trades = result.scalars().all()

    if len(recent_trades) < 2:
        return None

    buys = [t for t in recent_trades if t.side == "buy"]
    sells = [t for t in recent_trades if t.side == "sell"]

    if not buys or not sells:
        return None

    total_buy = sum(float(t.token_amount) for t in buys)
    total_sell = sum(float(t.token_amount) for t in sells)

    # Check if buy-back ratio is suspiciously high
    max_vol = max(total_buy, total_sell)
    ratio = min(total_buy, total_sell) / max_vol if max_vol > 0 else 0

    if ratio >= WASH_TRADE_MIN_RATIO:
        alert = {
            "risk_type": "wash_trading",
            "severity": "warning",
            "trader_address": trader_address,
            "soul_token_id": soul_token_id,
            "buy_amount": total_buy,
            "sell_amount": total_sell,
            "ratio": round(ratio, 3),
            "trade_count": len(recent_trades),
            "window_seconds": WASH_TRADE_WINDOW_SECONDS,
        }
        logger.warning("Wash trading detected: %s", alert)
        return alert

    return None


async def check_pump_and_dump(
    db: AsyncSession,
    *,
    soul_token_id: str,
) -> dict | None:
    """Detect pump & dump: >50% price rise in <1hr with concentrated buying.

    Returns risk alert dict if detected, None otherwise.
    """
    cutoff = datetime.now(UTC) - timedelta(minutes=PUMP_DUMP_WINDOW_MINUTES)

    # Get trades in the window
    query = (
        select(Trade)
        .where(
            Trade.soul_token_id == soul_token_id,
            Trade.created_at >= cutoff,
        )
        .order_by(Trade.created_at.asc())
    )
    result = await db.execute(query)
    trades = result.scalars().all()

    if len(trades) < 3:
        return None

    # Check price change
    first_price = float(trades[0].price_eth)
    last_price = float(trades[-1].price_eth)

    if first_price <= 0:
        return None

    price_change = (last_price - first_price) / first_price

    if price_change < PUMP_DUMP_PRICE_THRESHOLD:
        return None

    # Check concentration: what % of buy volume comes from top 3 wallets?
    buy_trades = [t for t in trades if t.side == "buy"]
    if not buy_trades:
        return None

    wallet_volumes: dict[str, float] = {}
    for t in buy_trades:
        addr = t.trader_address
        wallet_volumes[addr] = wallet_volumes.get(addr, 0) + float(t.eth_amount)

    total_buy_vol = sum(wallet_volumes.values())
    if total_buy_vol <= 0:
        return None

    # Top 3 wallets by volume
    sorted_wallets = sorted(wallet_volumes.items(), key=lambda x: x[1], reverse=True)
    top3_vol = sum(v for _, v in sorted_wallets[:3])
    concentration = top3_vol / total_buy_vol

    if concentration >= PUMP_DUMP_CONCENTRATION:
        alert = {
            "risk_type": "pump_and_dump",
            "severity": "critical",
            "soul_token_id": soul_token_id,
            "price_change_pct": round(price_change * 100, 2),
            "concentration_pct": round(concentration * 100, 2),
            "top_wallets": [addr for addr, _ in sorted_wallets[:3]],
            "trade_count": len(trades),
            "window_minutes": PUMP_DUMP_WINDOW_MINUTES,
        }
        logger.warning("Pump & dump detected: %s", alert)
        return alert

    return None


async def check_cliff_event(
    db: AsyncSession,
    *,
    soul_token_id: str,
) -> dict | None:
    """Detect cliff event: sudden >30% price drop in <10 minutes."""
    cutoff = datetime.now(UTC) - timedelta(minutes=10)

    query = (
        select(Trade)
        .where(
            Trade.soul_token_id == soul_token_id,
            Trade.created_at >= cutoff,
        )
        .order_by(Trade.created_at.asc())
    )
    result = await db.execute(query)
    trades = result.scalars().all()

    if len(trades) < 2:
        return None

    first_price = float(trades[0].price_eth)
    last_price = float(trades[-1].price_eth)

    if first_price <= 0:
        return None

    price_change = (last_price - first_price) / first_price

    if price_change < -0.3:  # >30% drop
        sell_trades = [t for t in trades if t.side == "sell"]
        total_sell_eth = sum(float(t.eth_amount) for t in sell_trades)

        alert = {
            "risk_type": "cliff_event",
            "severity": "critical",
            "soul_token_id": soul_token_id,
            "price_drop_pct": round(abs(price_change) * 100, 2),
            "sell_volume_eth": round(total_sell_eth, 4),
            "trade_count": len(trades),
            "window_minutes": 10,
        }
        logger.warning("Cliff event detected: %s", alert)
        return alert

    return None


async def run_risk_checks(
    db: AsyncSession,
    *,
    soul_token_id: str,
    trader_address: str,
) -> list[dict]:
    """Run all risk checks after a trade. Returns list of risk alerts.

    If critical severity found, activates circuit breaker and publishes event.
    """
    alerts: list[dict] = []

    # 1. Wash trading check
    wash = await check_wash_trading(
        db, soul_token_id=soul_token_id, trader_address=trader_address
    )
    if wash:
        alerts.append(wash)

    # 2. Pump & dump check
    pump = await check_pump_and_dump(db, soul_token_id=soul_token_id)
    if pump:
        alerts.append(pump)

    # 3. Cliff event check
    cliff = await check_cliff_event(db, soul_token_id=soul_token_id)
    if cliff:
        alerts.append(cliff)

    # If any critical alert, activate circuit breaker
    critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
    if critical_alerts:
        activate_circuit_breaker(str(soul_token_id))

        # Get token info for event publishing
        query = select(SoulToken).where(SoulToken.id == soul_token_id)
        result = await db.execute(query)
        token = result.scalar_one_or_none()

        if token:
            for alert in critical_alerts:
                await risk_to_circuit_breaker(
                    person_id=str(token.person_id),
                    token_id=str(token.id),
                    risk_type=alert["risk_type"],
                    severity=alert["severity"],
                    details=alert,
                )

    return alerts


async def get_token_risk_summary(
    db: AsyncSession,
    soul_token_id: str,
) -> dict:
    """Get a risk summary for a token: recent trade stats + breaker status."""
    now = datetime.now(UTC)
    hour_ago = now - timedelta(hours=1)

    # Recent trade stats
    stats_query = (
        select(
            func.count(Trade.id).label("trade_count"),
            func.count(func.distinct(Trade.trader_address)).label("unique_traders"),
            func.sum(Trade.eth_amount).label("total_volume_eth"),
        )
        .where(
            and_(
                Trade.soul_token_id == soul_token_id,
                Trade.created_at >= hour_ago,
            )
        )
    )
    result = await db.execute(stats_query)
    row = result.one()

    breaker_active = is_circuit_breaker_active(str(soul_token_id))
    breaker_expiry = _active_breakers.get(str(soul_token_id))

    return {
        "soul_token_id": soul_token_id,
        "circuit_breaker_active": breaker_active,
        "circuit_breaker_expiry": breaker_expiry.isoformat() if breaker_expiry else None,
        "last_hour": {
            "trade_count": row.trade_count or 0,
            "unique_traders": row.unique_traders or 0,
            "total_volume_eth": float(row.total_volume_eth or 0),
        },
    }
