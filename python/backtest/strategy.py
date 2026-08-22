"""Shannon-style rebalancing with sell-to-buy + cash funding.

Signal computation is separated from execution so the simulation can compute a
signal at close[t] and execute at close[t+1] (no look-ahead), applying
transaction costs at execution time.

Funding model (mirrors the reference portfolio_allocation):
- NORMAL band (target * (1 +/- normal_band)) -> HOLD, no trade
- outside NORMAL: drift < 0 -> BUY, drift >= 0 -> SELL
- target trade amount = |target_value - current_value|
- available funding = totalSell + cashReserve
- funded buy total = min(totalBuy, available funding), pro-rata buy scaling
"""

from __future__ import annotations

import math

from .config import BacktestParams


def classify_band(weight: float, target: float, params: BacktestParams) -> str:
    normal_low = target * (1 - params.normal_band)
    normal_high = target * (1 + params.normal_band)
    if normal_low <= weight <= normal_high:
        return "NORMAL"

    soft_low = target * (1 - params.soft_band)
    soft_high = target * (1 + params.soft_band)
    if soft_low <= weight <= soft_high:
        return "SOFT"
    return "HARD"


def compute_recommendations(
    shares: dict[str, float],
    cash: float,
    prices: dict[str, float],
    targets: dict[str, float],
    params: BacktestParams,
):
    """Compute the rebalance signal at current prices. Does NOT mutate anything.

    Returns (recs, funding) where each rec carries target/funded trade amounts in
    VND (signal-price based) and `funding` summarises the funding math.
    """
    values = {s: shares.get(s, 0.0) * prices[s] for s in shares}
    equity = sum(values.values())
    total_nav = equity + cash

    buys: list[tuple[str, float]] = []  # (symbol, target_trade_amount)
    sells: list[tuple[str, float]] = []  # (symbol, target_trade_amount)
    recs: list[dict] = []

    if total_nav <= 0:
        return recs, {}

    for s in shares:
        weight = values[s] / total_nav
        target = targets.get(s, 0.0)
        band = classify_band(weight, target, params)
        drift = weight - target
        rec = {
            "symbol": s,
            "signal_weight": round(weight, 6),
            "current_weight": round(weight, 6),
            "target_weight": round(target, 6),
            "band": band,
            "drift": round(drift, 6),
            "recommendation": "HOLD",
            "target_trade_amount": 0.0,
            "funded_trade_amount": 0.0,
            "shares_to_trade": 0.0,
            "execution_price": None,
        }
        if band == "NORMAL" or target <= 0:
            recs.append(rec)
            continue
        trade = abs(target * total_nav - values[s])
        rec["target_trade_amount"] = round(trade, 2)
        if trade <= 0:
            recs.append(rec)
            continue
        if drift < 0:
            rec["recommendation"] = "BUY"
            buys.append((s, trade))
        else:
            rec["recommendation"] = "SELL"
            sells.append((s, trade))
        recs.append(rec)

    total_sell = sum(t for _, t in sells)
    total_buy = sum(t for _, t in buys)
    available_funding = total_sell + cash
    funded_buy_total = min(total_buy, available_funding)
    buy_scale = (funded_buy_total / total_buy) if total_buy > 0 else 0.0

    for rec in recs:
        if rec["recommendation"] == "SELL":
            rec["funded_trade_amount"] = rec["target_trade_amount"]
        elif rec["recommendation"] == "BUY":
            rec["funded_trade_amount"] = round(rec["target_trade_amount"] * buy_scale, 2)

    funding = {
        "total_sell": total_sell,
        "total_buy": total_buy,
        "available_funding": available_funding,
        "funded_buy_total": funded_buy_total,
        "buy_scale": buy_scale,
    }
    return recs, funding


def snapshot_holdings(shares: dict[str, float], prices: dict[str, float], total_nav: float) -> list[dict]:
    """Snapshot current holdings with value and weight per symbol."""
    holdings = []
    for s in sorted(shares):
        value = shares.get(s, 0.0) * prices.get(s, 0.0)
        holdings.append(
            {
                "symbol": s,
                "shares": round(shares.get(s, 0.0), 4),
                "price": round(prices.get(s, 0.0), 2),
                "value": round(value, 2),
                "weight": round(value / total_nav, 6) if total_nav > 0 else 0.0,
            }
        )
    return holdings


def total_nav(shares: dict[str, float], cash: float, prices: dict[str, float]) -> float:
    return sum(shares.get(s, 0.0) * prices[s] for s in shares) + cash


def _floor_shares(shares: float) -> float:
    return math.floor(shares + 1e-9)