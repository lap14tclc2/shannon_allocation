"""Strictly-past OHLC-close alpha ranking for dynamic portfolio membership.

This layer answers only *which symbols are active*. It never assigns portfolio
weights; ERC remains responsible for relative risk weights after selection.

The methodology is deliberately transparent and fixed (not optimizer genes):
- 3M / 6M / 12M momentum when enough history exists
- trend versus a long moving average (or 3M fallback early in history)
- downside-aware drawdown quality
- volatility penalty
- cross-sectional z-score normalization
- greedy correlation diversification with deterministic relaxation when needed

Every statistic uses rows strictly BEFORE ``pos``. The final holdout therefore
cannot influence a selection made inside TRAIN/validation/recent windows.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

from .config import BacktestParams


@dataclass(frozen=True)
class AlphaSelectionResult:
    symbols: tuple[str, ...]
    scores: dict[str, float]
    diagnostics: dict

    def as_dict(self) -> dict:
        return {
            "symbols": list(self.symbols),
            "scores": {k: round(float(v), 6) for k, v in self.scores.items()},
            "diagnostics": self.diagnostics,
        }


def _safe_return(values: np.ndarray, lookback: int) -> float | None:
    if len(values) < lookback + 1:
        return None
    a = float(values[-lookback - 1])
    b = float(values[-1])
    if not (math.isfinite(a) and math.isfinite(b)) or a <= 0 or b <= 0:
        return None
    return b / a - 1.0


def _zscore(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce")
    mean = clean.mean(skipna=True)
    std = clean.std(skipna=True, ddof=0)
    if not math.isfinite(float(mean)) if pd.notna(mean) else True:
        return pd.Series(0.0, index=series.index)
    if pd.isna(std) or float(std) <= 1e-12:
        return pd.Series(0.0, index=series.index)
    return ((clean - float(mean)) / float(std)).fillna(0.0)


def _symbol_features(history: pd.Series, params: BacktestParams) -> dict | None:
    x = history.dropna().astype(float)
    if len(x) < max(3, int(params.alpha_min_observations)):
        return None
    # Require a fresh observation immediately before the signal. Stale suspended
    # names are not eligible for a new allocation even though existing holdings
    # may still be valued using forward-filled prices elsewhere.
    if history.empty or pd.isna(history.iloc[-1]):
        return None

    values = x.to_numpy(dtype=float)
    if np.any(values <= 0) or not np.all(np.isfinite(values)):
        return None

    short = _safe_return(values, int(params.alpha_short_lookback))
    medium = _safe_return(values, int(params.alpha_medium_lookback))
    long = _safe_return(values, int(params.alpha_long_lookback))

    trend_len = min(len(values), int(params.alpha_long_lookback))
    if trend_len < 3:
        return None
    ma = float(np.mean(values[-trend_len:]))
    trend = values[-1] / ma - 1.0 if ma > 0 else None

    ret_window = values[-min(len(values), int(params.alpha_short_lookback) + 1):]
    with np.errstate(divide="ignore", invalid="ignore"):
        log_ret = np.diff(np.log(ret_window))
    log_ret = log_ret[np.isfinite(log_ret)]
    volatility = (
        float(np.std(log_ret, ddof=1) * math.sqrt(params.annualization_factor))
        if len(log_ret) >= 2
        else None
    )

    peak_window = values[-min(len(values), int(params.alpha_long_lookback)):]
    peak = float(np.max(peak_window)) if len(peak_window) else values[-1]
    drawdown = values[-1] / peak - 1.0 if peak > 0 else None

    return {
        "mom_short": short,
        "mom_medium": medium,
        "mom_long": long,
        "trend": trend,
        "volatility": volatility,
        "drawdown": drawdown,
        "observations": int(len(values)),
    }


def alpha_score_table(
    raw_prices: pd.DataFrame,
    universe: list[str],
    pos: int,
    params: BacktestParams,
) -> pd.DataFrame:
    """Return cross-sectional alpha features/scores using only rows ``< pos``."""
    if pos <= 1 or raw_prices.empty:
        return pd.DataFrame()
    available = [s for s in universe if s in raw_prices.columns]
    if not available:
        return pd.DataFrame()

    long_lb = max(
        int(params.alpha_long_lookback),
        int(params.alpha_medium_lookback),
        int(params.alpha_short_lookback),
        int(params.alpha_correlation_lookback),
        int(params.alpha_min_observations),
    )
    start = max(0, pos - long_lb - 2)
    history = raw_prices.iloc[start:pos]

    rows = {}
    for symbol in available:
        f = _symbol_features(history[symbol], params)
        if f is not None:
            rows[symbol] = f
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame.from_dict(rows, orient="index")
    # Missing longer-horizon momentum early in history is neutral (z=0), not an
    # automatic positive/negative signal. Available horizons carry the ranking.
    z_short = _zscore(df["mom_short"])
    z_medium = _zscore(df["mom_medium"])
    z_long = _zscore(df["mom_long"])
    z_trend = _zscore(df["trend"])
    z_vol = _zscore(df["volatility"])
    z_dd = _zscore(df["drawdown"])

    # Growth first, but quality matters. Higher drawdown value means closer to
    # zero (less damaged), so its z-score is rewarded. High volatility is penalized.
    df["alpha_score"] = (
        0.20 * z_short
        + 0.25 * z_medium
        + 0.30 * z_long
        + 0.15 * z_trend
        + 0.10 * z_dd
        - 0.10 * z_vol
    )
    return df.sort_values(["alpha_score"], ascending=False, kind="mergesort")


def _pair_corr(
    raw_prices: pd.DataFrame,
    a: str,
    b: str,
    pos: int,
    lookback: int,
) -> float | None:
    start = max(0, pos - max(3, int(lookback)) - 1)
    pair = raw_prices.iloc[start:pos][[a, b]].dropna()
    if len(pair) < 20:
        return None
    values = pair.to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        rets = np.log(values[1:] / values[:-1])
    rets = rets[np.all(np.isfinite(rets), axis=1)]
    if len(rets) < 10:
        return None
    corr = float(np.corrcoef(rets[:, 0], rets[:, 1])[0, 1])
    return corr if math.isfinite(corr) else None


def select_alpha_symbols(
    raw_prices: pd.DataFrame,
    universe: list[str],
    pos: int,
    params: BacktestParams,
    portfolio_size: int | None = None,
) -> AlphaSelectionResult:
    """Rank the market and greedily diversify the top alpha names."""
    n = int(portfolio_size or params.dynamic_alpha_portfolio_size)
    if n < 1:
        return AlphaSelectionResult((), {}, {"reason": "invalid_portfolio_size"})

    table = alpha_score_table(raw_prices, universe, pos, params)
    if table.empty or len(table) < n:
        return AlphaSelectionResult(
            (),
            {},
            {
                "reason": "insufficient_alpha_candidates",
                "eligible": int(len(table)),
                "required": n,
            },
        )

    ranked = list(table.index)
    scores = {s: float(table.loc[s, "alpha_score"]) for s in ranked}
    base_limit = float(params.alpha_max_pair_correlation)
    thresholds = []
    for x in (base_limit, max(base_limit, 0.85), max(base_limit, 0.92), 1.01):
        if x not in thresholds:
            thresholds.append(x)

    selected: list[str] = []
    accepted_at: dict[str, float] = {}
    pair_cache: dict[tuple[str, str], float | None] = {}

    def corr(a: str, b: str):
        key = tuple(sorted((a, b)))
        if key not in pair_cache:
            pair_cache[key] = _pair_corr(
                raw_prices,
                key[0],
                key[1],
                pos,
                int(params.alpha_correlation_lookback),
            )
        return pair_cache[key]

    for threshold in thresholds:
        for symbol in ranked:
            if symbol in selected:
                continue
            if not selected:
                selected.append(symbol)
                accepted_at[symbol] = threshold
            else:
                correlations = [corr(symbol, s) for s in selected]
                finite = [c for c in correlations if c is not None]
                # Missing correlation is conservative at the primary threshold:
                # defer the name to later passes rather than inventing diversity.
                if len(finite) != len(correlations) and threshold <= base_limit + 1e-12:
                    continue
                max_corr = max(finite) if finite else 0.0
                if max_corr <= threshold:
                    selected.append(symbol)
                    accepted_at[symbol] = threshold
            if len(selected) >= n:
                break
        if len(selected) >= n:
            break

    selected = selected[:n]
    selected_scores = {s: scores[s] for s in selected}
    selected_pairs = []
    max_selected_corr = None
    for i, a in enumerate(selected):
        for b in selected[i + 1:]:
            c = corr(a, b)
            if c is not None:
                selected_pairs.append({"a": a, "b": b, "correlation": round(c, 6)})
                max_selected_corr = c if max_selected_corr is None else max(max_selected_corr, c)

    diagnostics = {
        "eligible": int(len(table)),
        "required": n,
        "base_correlation_limit": base_limit,
        "max_selected_correlation": round(max_selected_corr, 6) if max_selected_corr is not None else None,
        "accepted_at_threshold": {s: accepted_at.get(s) for s in selected},
        "top_ranked": [
            {
                "symbol": s,
                "score": round(scores[s], 6),
                "observations": int(table.loc[s, "observations"]),
            }
            for s in ranked[: min(20, len(ranked))]
        ],
        "selected_pairs": selected_pairs,
    }
    return AlphaSelectionResult(tuple(selected), selected_scores, diagnostics)
