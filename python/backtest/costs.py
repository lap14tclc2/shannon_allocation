"""Transaction cost model: buy fee, sell fee, sell-side tax, slippage.

All rates are in basis points (1 bps = 0.01%). Costs are applied to the trade
notional when an order is executed.
"""

from __future__ import annotations


def buy_cost(notional: float, params) -> float:
    """Total cost (VND) for a BUY of `notional`: fee + slippage."""
    fee = notional * params.fee_buy_bps / 10000.0
    slip = notional * params.slippage_bps / 10000.0
    return fee + slip


def sell_cost(notional: float, params) -> float:
    """Total cost (VND) for a SELL of `notional`: fee + tax + slippage."""
    fee = notional * params.fee_sell_bps / 10000.0
    tax = notional * params.tax_sell_bps / 10000.0
    slip = notional * params.slippage_bps / 10000.0
    return fee + tax + slip


def side_rate_bps(side: str, params) -> float:
    """Combined cost rate (bps) for a side, for reporting."""
    if side == "BUY":
        return params.fee_buy_bps + params.slippage_bps
    return params.fee_sell_bps + params.tax_sell_bps + params.slippage_bps