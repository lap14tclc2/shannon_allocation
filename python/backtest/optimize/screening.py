"""Cheap TRAIN-only symbol screening for large combinatorial searches.

The screen is intentionally growth-first: it keeps names with stronger historical
return/risk-adjusted momentum in the TRAIN slice while still requiring adequate
data and penalising pathological volatility/drawdown.  It is only a speed screen;
rolling OOS validation and MDD gates remain the real risk controls.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _max_drawdown(values: np.ndarray) -> float:
    peak = -np.inf
    worst = 0.0
    for v in values:
        peak = max(peak, v)
        if peak > 0:
            worst = min(worst, v / peak - 1.0)
    return float(worst)


def screen_universe(
    prices: pd.DataFrame,
    universe: list[str],
    train_window,
    top_k: int | None,
    annualization: int = 252,
    min_observations: int = 126,
) -> tuple[list[str], list[dict]]:
    """Return TRAIN-only screened symbols ranked strongest to weakest."""
    start, end = train_window
    frame = prices.loc[(prices.index >= start) & (prices.index <= end), universe]
    rows: list[dict] = []

    for symbol in universe:
        s = frame[symbol].dropna()
        if len(s) < min_observations:
            continue
        vals = s.to_numpy(dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.diff(np.log(vals))
        r = r[np.isfinite(r)]
        if len(r) < max(20, min_observations - 1):
            continue
        mean = float(np.mean(r))
        std = float(np.std(r, ddof=1)) if len(r) > 1 else 0.0
        ann_return = math.exp(mean * annualization) - 1.0
        ann_vol = std * math.sqrt(annualization)
        sharpe = mean / std * math.sqrt(annualization) if std > 1e-12 else -10.0
        mdd = _max_drawdown(vals)
        coverage = len(s) / max(1, len(frame))

        # Growth-first pre-screen. Return and Sharpe now dominate the ranking.
        # Drawdown/volatility remain mild penalties here because the expensive
        # portfolio-level rolling OOS stage already enforces the hard MDD gate.
        bounded_return = max(-1.0, min(2.0, ann_return))
        score = (
            1.35 * max(-3.0, min(3.0, sharpe))
            + 1.10 * bounded_return
            + 0.35 * mdd
            - 0.20 * max(0.0, ann_vol - 0.45)
            + 0.35 * coverage
        )
        rows.append(
            {
                "symbol": symbol,
                "screen_score": score,
                "observations": len(s),
                "coverage": coverage,
                "annualized_return": ann_return,
                "annualized_volatility": ann_vol,
                "sharpe": sharpe,
                "max_drawdown": mdd,
            }
        )

    rows.sort(key=lambda x: x["screen_score"], reverse=True)
    if not rows:
        return list(universe), []
    if not top_k or top_k >= len(rows):
        chosen = [r["symbol"] for r in rows]
    else:
        chosen = [r["symbol"] for r in rows[: max(1, int(top_k))]]
    return chosen, rows
