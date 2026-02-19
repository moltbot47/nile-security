"""Soul agent collaboration pipelines — event-driven workflows between agent types."""

import json
import logging

import redis.asyncio as aioredis

from nile.config import settings

logger = logging.getLogger(__name__)


async def _publish(event_type: str, metadata: dict) -> None:
    """Publish event to Redis for cross-service consumption."""
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        payload = json.dumps({"event_type": event_type, "metadata": metadata})
        await r.publish("nile:events", payload)
        await r.close()
    except Exception:
        logger.exception("Failed to publish event %s", event_type)


async def oracle_to_valuation(
    person_id: str,
    event_id: str,
    impact_score: int,
    event_type: str,
) -> None:
    """Confirmed oracle event → trigger valuation re-compute.

    Called after an oracle report reaches consensus. Notifies valuation
    agents to re-score the affected person.
    """
    await _publish(
        "soul.oracle_confirmed",
        {
            "person_id": person_id,
            "event_id": event_id,
            "impact_score": impact_score,
            "event_type": event_type,
            "action": "revalue",
        },
    )
    logger.info("Oracle→Valuation pipeline: person=%s, impact=%s", person_id, impact_score)


async def valuation_to_market_maker(
    person_id: str,
    old_score: float,
    new_score: float,
    fair_value_usd: float,
) -> None:
    """Significant score change → alert market makers to adjust spreads.

    Triggered when NILE total score changes by >5% after revaluation.
    """
    change_pct = abs(new_score - old_score) / max(old_score, 1) * 100
    if change_pct < 5:
        return  # Not significant enough

    await _publish(
        "soul.valuation_changed",
        {
            "person_id": person_id,
            "old_score": old_score,
            "new_score": new_score,
            "change_pct": round(change_pct, 2),
            "fair_value_usd": fair_value_usd,
            "action": "adjust_spread",
        },
    )
    logger.info(
        "Valuation→MarketMaker: person=%s, change=%.1f%%, fair_value=$%.2f",
        person_id,
        change_pct,
        fair_value_usd,
    )


async def risk_to_circuit_breaker(
    person_id: str,
    token_id: str,
    risk_type: str,
    severity: str,
    details: dict,
) -> None:
    """Critical risk anomaly → pause trading + alert all agents.

    Triggered by risk agents detecting wash trading, pump/dump, or cliff events.
    Circuit breaker pauses trading for 15 minutes.
    """
    await _publish(
        "soul.risk_alert",
        {
            "person_id": person_id,
            "token_id": token_id,
            "risk_type": risk_type,
            "severity": severity,
            "details": details,
            "action": "circuit_breaker",
            "pause_minutes": 15,
        },
    )
    logger.warning(
        "Risk→CircuitBreaker: token=%s, type=%s, severity=%s",
        token_id,
        risk_type,
        severity,
    )


async def oracle_consensus_broadcast(
    event_id: str,
    person_id: str,
    headline: str,
    source: str,
) -> None:
    """New oracle report → broadcast to all oracle agents for cross-verification.

    Sent when a new report is submitted. Other oracle agents should verify
    the claim and vote approve/reject.
    """
    await _publish(
        "soul.oracle_report_pending",
        {
            "event_id": event_id,
            "person_id": person_id,
            "headline": headline,
            "source": source,
            "action": "cross_verify",
        },
    )
    logger.info("Oracle broadcast: event=%s, headline=%s", event_id, headline[:80])


async def graduation_notification(
    person_id: str,
    token_id: str,
    token_symbol: str,
    reserve_eth: float,
) -> None:
    """Token graduated from bonding curve → notify all agents + Discord."""
    await _publish(
        "soul.token_graduated",
        {
            "person_id": person_id,
            "token_id": token_id,
            "token_symbol": token_symbol,
            "reserve_eth": reserve_eth,
            "action": "graduation",
        },
    )
    logger.info("Graduation: $%s graduated with %.2f ETH reserve", token_symbol, reserve_eth)
