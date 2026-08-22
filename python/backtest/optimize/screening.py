"""Cheap train-only symbol screening for large combinatorial searches.

The optimizer still performs full portfolio backtests for candidates.  Screening
only narrows a very large input universe (for example ~90 names) before NSGA-II
using information from the TRAIN window only, so validation/test remain untouched.

Because current price files expose close prices only, the screen focuses on data
coverage, individual Sharpe, drawdown and volatility.  Liquidity/sector filters
can be layered in later when point-in-time metadata is available.
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
    """Return (screened_symbols, diagnostics), ranked from strongest to weakest.

    ``train_window`` is a (start, end) pair of timestamps.  No data after end is
    inspected.  If top_k is None/0 or >= universe size, the original universe is
    returned after data-quality filtering.
    """
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

        # Deliberately simple and bounded.  This is a speed screen, not the final
        # portfolio objective.  Low drawdown/data quality matter more than raw return.
        score = (
            max(-3.0, min(3.0, sharpe))
            + 1.25 * mdd
            - 0.35 * max(0.0, ann_vol - 0.35)
            + 0.50 * coverage
            + 0.15 * max(-1.0, min(1.0, ann_return))
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
