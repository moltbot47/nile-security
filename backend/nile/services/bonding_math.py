"""Bancor continuous token bonding curve math — Python implementation.

Mirrors the Solidity BondingCurve.sol logic so off-chain simulations produce
prices that match what the on-chain contracts would return.

Key parameters (matching BondingCurve.sol):
  - RESERVE_RATIO = 333_333 / 1_000_000  (≈ 33.3%)
  - FEE_BPS       = 100  (1%)
  - INITIAL_RESERVE = 10 ETH (in wei: 10e18)
  - INITIAL_SUPPLY  = 100_000 tokens (in wei: 100_000e18)

Formulas (continuous token model):
  Buy:  tokensOut = supply * ((1 + ethIn / reserve) ^ (ratio) - 1)
  Sell: ethOut    = reserve * (1 - (1 - tokensIn / supply) ^ (1 / ratio))

For gas efficiency the Solidity uses piecewise linear+quadratic approximation.
We replicate that same approximation here so results match exactly.
"""

from __future__ import annotations

from decimal import Decimal, getcontext

# High precision for financial calculations
getcontext().prec = 50

# ---------------------------------------------------------------------------
# Constants — must match BondingCurve.sol
# ---------------------------------------------------------------------------
RESERVE_RATIO: int = 333_333          # PPM
PPM: int = 1_000_000
FEE_BPS: int = 100                    # 1%
FEE_CREATOR_BPS: int = 50             # 0.5%
FEE_PROTOCOL_BPS: int = 30            # 0.3%
FEE_STAKER_BPS: int = 20              # 0.2%

INITIAL_RESERVE_ETH: float = 10.0     # 10 ETH virtual reserve
INITIAL_SUPPLY: float = 100_000.0     # 100k virtual token supply

# Ratio as a float for quick math
RATIO_F: float = RESERVE_RATIO / PPM  # ≈ 0.333333
INV_RATIO_F: float = PPM / RESERVE_RATIO  # ≈ 3.000003


def _calculate_buy_approx(supply: float, reserve: float, eth_in: float) -> float:
    """Bancor buy with the same linear/quadratic approximation as BondingCurve.sol.

    tokensOut = supply * ((1 + ethIn/reserve)^ratio - 1)
    Approximated as:
      - Linear  (x < 0.1): supply * n * x
      - Quadratic (x >= 0.1): supply * (n*x + n*(n-1)*x^2 / 2)
    where x = ethIn / reserve, n = RESERVE_RATIO / PPM
    """
    if reserve <= 0 or supply <= 0 or eth_in <= 0:
        return 0.0

    x = eth_in / reserve
    n = RATIO_F  # ≈ 0.333333

    if x < 0.1:
        # Linear approximation
        result = supply * n * x
    else:
        # Quadratic approximation
        nx = n * x
        n_minus_1 = max(n - 1.0, 0.0)
        x2 = x * x
        quad_term = (n * n_minus_1 * x2) / 2.0
        result = supply * (nx + quad_term)

    return result


def _calculate_sell_approx(supply: float, reserve: float, tokens_in: float) -> float:
    """Bancor sell with the same linear/quadratic approximation as BondingCurve.sol.

    ethOut = reserve * (1 - (1 - tokensIn/supply)^(1/ratio))
    Approximated as:
      - Linear  (x < 0.1): reserve * n * x
      - Quadratic (x >= 0.1): reserve * (n*x - n*(n-1)*x^2 / 2)
    where x = tokensIn / supply, n = PPM / RESERVE_RATIO (≈ 3.0)
    """
    if supply <= 0 or reserve <= 0 or tokens_in <= 0:
        return 0.0

    if tokens_in >= supply:
        return reserve  # Selling everything returns all reserve

    x = tokens_in / supply
    n = INV_RATIO_F  # ≈ 3.0

    if x < 0.1:
        # Linear approximation
        result = reserve * n * x
    else:
        # Quadratic approximation
        nx = n * x
        n_minus_1 = max(n - 1.0, 0.0)
        x2 = x * x
        quad_term = (n * n_minus_1 * x2) / 2.0
        result = reserve * (nx - quad_term)

    # Never return more than total reserve
    return min(result, reserve)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate_purchase_return(
    supply: float,
    reserve_balance: float,
    reserve_ratio: int,
    eth_amount: float,
) -> float:
    """Calculate how many tokens are minted for a given ETH deposit.

    Args:
        supply: Current effective token supply (circulating + INITIAL_SUPPLY).
        reserve_balance: Current ETH reserve in the curve.
        reserve_ratio: Reserve ratio in PPM (use RESERVE_RATIO = 333333).
        eth_amount: ETH amount being deposited (before fees).

    Returns:
        Number of tokens minted.
    """
    # Deduct fee first (matching contract behavior)
    fee = eth_amount * FEE_BPS / 10_000
    eth_after_fee = eth_amount - fee

    tokens_out = _calculate_buy_approx(supply, reserve_balance, eth_after_fee)
    return tokens_out


def calculate_sale_return(
    supply: float,
    reserve_balance: float,
    reserve_ratio: int,
    token_amount: float,
) -> float:
    """Calculate how much ETH is returned for burning tokens.

    Args:
        supply: Current effective token supply (circulating + INITIAL_SUPPLY).
        reserve_balance: Current ETH reserve in the curve.
        reserve_ratio: Reserve ratio in PPM (use RESERVE_RATIO = 333333).
        token_amount: Number of tokens being sold/burned.

    Returns:
        ETH returned after fees.
    """
    gross_eth = _calculate_sell_approx(supply, reserve_balance, token_amount)
    fee = gross_eth * FEE_BPS / 10_000
    eth_after_fee = gross_eth - fee
    return eth_after_fee


def get_fee_breakdown(gross_amount: float) -> dict[str, float]:
    """Calculate the fee breakdown matching BondingCurve.sol distribution.

    Args:
        gross_amount: The gross ETH amount (either deposit for buy, or gross_eth for sell).

    Returns:
        Dict with fee_total, fee_creator, fee_protocol, fee_staker.
    """
    fee_total = gross_amount * FEE_BPS / 10_000
    fee_creator = fee_total * FEE_CREATOR_BPS / FEE_BPS
    fee_protocol = fee_total * FEE_PROTOCOL_BPS / FEE_BPS
    fee_staker = fee_total - fee_creator - fee_protocol
    return {
        "fee_total": fee_total,
        "fee_creator": fee_creator,
        "fee_protocol": fee_protocol,
        "fee_staker": fee_staker,
    }


def get_current_price(
    supply: float,
    reserve_balance: float,
    reserve_ratio: int,
) -> float:
    """Calculate the current instantaneous price per token in ETH.

    Matches BondingCurve.sol _currentPrice():
      price = (reserve * PPM) / (supply * RESERVE_RATIO / 1e18)
    But in Python we use floating point, so simplified:
      price = reserve / (supply * ratio)

    Args:
        supply: Current effective token supply.
        reserve_balance: Current ETH reserve.
        reserve_ratio: Reserve ratio in PPM.

    Returns:
        Price per token in ETH.
    """
    if supply <= 0:
        return 0.0
    ratio = reserve_ratio / PPM
    return reserve_balance / (supply * ratio)


def get_effective_supply(circulating_supply: float) -> float:
    """Calculate effective supply = circulating + virtual initial supply.

    The bonding curve uses a virtual initial supply (100k tokens) and
    virtual initial reserve (10 ETH) to avoid division-by-zero and
    to provide initial liquidity depth.
    """
    return circulating_supply + INITIAL_SUPPLY


def get_effective_reserve(actual_reserve: float) -> float:
    """Calculate effective reserve = actual + virtual initial reserve."""
    return actual_reserve + INITIAL_RESERVE_ETH


def simulate_buy(
    circulating_supply: float,
    actual_reserve_eth: float,
    eth_amount: float,
) -> dict:
    """Full buy simulation returning all trade details.

    This is the main function used by trading.py for off-chain simulation.

    Args:
        circulating_supply: Tokens in circulation (excludes virtual supply).
        actual_reserve_eth: Actual ETH in reserve (excludes virtual reserve).
        eth_amount: ETH being spent by buyer.

    Returns:
        Dict with tokens_out, eth_after_fee, fees, new_supply, new_reserve, new_price.
    """
    effective_supply = get_effective_supply(circulating_supply)
    effective_reserve = get_effective_reserve(actual_reserve_eth)

    fees = get_fee_breakdown(eth_amount)
    eth_after_fee = eth_amount - fees["fee_total"]

    tokens_out = _calculate_buy_approx(effective_supply, effective_reserve, eth_after_fee)

    # State after trade
    new_reserve = actual_reserve_eth + eth_after_fee
    new_supply = circulating_supply + tokens_out
    new_effective_supply = get_effective_supply(new_supply)
    new_effective_reserve = get_effective_reserve(new_reserve)
    new_price = get_current_price(new_effective_supply, new_effective_reserve, RESERVE_RATIO)

    return {
        "tokens_out": tokens_out,
        "eth_spent": eth_amount,
        "eth_after_fee": eth_after_fee,
        "fee_total": fees["fee_total"],
        "fee_creator": fees["fee_creator"],
        "fee_protocol": fees["fee_protocol"],
        "fee_staker": fees["fee_staker"],
        "new_supply": new_supply,
        "new_reserve": new_reserve,
        "new_price_eth": new_price,
    }


def simulate_sell(
    circulating_supply: float,
    actual_reserve_eth: float,
    token_amount: float,
) -> dict:
    """Full sell simulation returning all trade details.

    Args:
        circulating_supply: Tokens in circulation (excludes virtual supply).
        actual_reserve_eth: Actual ETH in reserve (excludes virtual reserve).
        token_amount: Tokens being sold by seller.

    Returns:
        Dict with eth_out, fees, new_supply, new_reserve, new_price.
    """
    effective_supply = get_effective_supply(circulating_supply)
    effective_reserve = get_effective_reserve(actual_reserve_eth)

    gross_eth = _calculate_sell_approx(effective_supply, effective_reserve, token_amount)
    fees = get_fee_breakdown(gross_eth)
    eth_after_fee = gross_eth - fees["fee_total"]

    # State after trade
    new_reserve = actual_reserve_eth - gross_eth
    # Guard against floating point drift making reserve negative
    new_reserve = max(new_reserve, 0.0)
    new_supply = circulating_supply - token_amount
    new_supply = max(new_supply, 0.0)

    new_effective_supply = get_effective_supply(new_supply)
    new_effective_reserve = get_effective_reserve(new_reserve)
    new_price = get_current_price(new_effective_supply, new_effective_reserve, RESERVE_RATIO)

    return {
        "eth_out": eth_after_fee,
        "gross_eth": gross_eth,
        "tokens_sold": token_amount,
        "fee_total": fees["fee_total"],
        "fee_creator": fees["fee_creator"],
        "fee_protocol": fees["fee_protocol"],
        "fee_staker": fees["fee_staker"],
        "new_supply": new_supply,
        "new_reserve": new_reserve,
        "new_price_eth": new_price,
    }


def quote_buy(
    circulating_supply: float,
    actual_reserve_eth: float,
    eth_amount: float,
) -> dict:
    """Quick quote for a buy — same as simulate_buy but lighter return."""
    sim = simulate_buy(circulating_supply, actual_reserve_eth, eth_amount)
    return {
        "tokens_out": sim["tokens_out"],
        "fee": sim["fee_total"],
        "price_impact_pct": _price_impact_pct(
            actual_reserve_eth, circulating_supply, eth_amount, is_buy=True
        ),
        "estimated_price": sim["new_price_eth"],
    }


def quote_sell(
    circulating_supply: float,
    actual_reserve_eth: float,
    token_amount: float,
) -> dict:
    """Quick quote for a sell."""
    sim = simulate_sell(circulating_supply, actual_reserve_eth, token_amount)
    return {
        "eth_out": sim["eth_out"],
        "fee": sim["fee_total"],
        "price_impact_pct": _price_impact_pct(
            actual_reserve_eth, circulating_supply, token_amount, is_buy=False
        ),
        "estimated_price": sim["new_price_eth"],
    }


def _price_impact_pct(
    reserve: float, supply: float, amount: float, *, is_buy: bool
) -> float:
    """Estimate price impact as a percentage."""
    eff_reserve = get_effective_reserve(reserve)
    eff_supply = get_effective_supply(supply)
    if eff_reserve <= 0 or eff_supply <= 0:
        return 0.0

    price_before = get_current_price(eff_supply, eff_reserve, RESERVE_RATIO)
    if price_before <= 0:
        return 0.0

    if is_buy:
        sim = simulate_buy(supply, reserve, amount)
        price_after = sim["new_price_eth"]
    else:
        sim = simulate_sell(supply, reserve, amount)
        price_after = sim["new_price_eth"]

    impact = abs(price_after - price_before) / price_before * 100
    return min(impact, 100.0)
