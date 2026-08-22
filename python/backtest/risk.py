"""Absolute portfolio-risk overlay for ERC targets.

ERC remains responsible for relative risk allocation. When enabled, this module
controls total equity exposure:

    live_weight_i = equity_exposure * bounded_erc_weight_i
    cash_target   = 1 - equity_exposure

Risk can be refreshed less frequently than Shannon drift checks. With the default
``risk_refresh_days=5``, daily calls inside a simulation reuse the same strictly-
past weekly risk snapshot, greatly reducing rolling covariance work during large
optimizer searches.

When disabled, ERC targets are returned unchanged (apart from numerical
normalisation) so old backtests remain a valid A/B baseline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import BacktestParams


@dataclass(frozen=True)
class RiskOverlayResult:
    targets: dict[str, float]
    relative_targets: dict[str, float]
    equity_exposure: float
    cash_target: float
    fast_volatility: float | None
    slow_volatility: float | None
    risk_volatility: float | None
    target_volatility: float
    observations_fast: int
    observations_slow: int

    def as_dict(self) -> dict:
        return {
            "enabled": True,
            "equity_exposure": round(self.equity_exposure, 6),
            "cash_target": round(self.cash_target, 6),
            "fast_volatility": round(self.fast_volatility, 6) if self.fast_volatility is not None else None,
            "slow_volatility": round(self.slow_volatility, 6) if self.slow_volatility is not None else None,
            "risk_volatility": round(self.risk_volatility, 6) if self.risk_volatility is not None else None,
            "target_volatility": round(self.target_volatility, 6),
            "observations_fast": self.observations_fast,
            "observations_slow": self.observations_slow,
            "relative_targets": {k: round(v, 6) for k, v in self.relative_targets.items()},
            "targets": {k: round(v, 6) for k, v in self.targets.items()},
        }


def _normalise(weights: dict[str, float]) -> dict[str, float]:
    clean = {k: max(0.0, float(v)) for k, v in weights.items()}
    total = sum(clean.values())
    if total <= 0:
        return {k: 0.0 for k in clean}
    return {k: v / total for k, v in clean.items()}


def apply_position_cap(weights: dict[str, float], max_weight: float | None) -> dict[str, float]:
    """Return long-only weights summing to one with an optional per-name cap."""
    w = _normalise(weights)
    if not w or max_weight is None or max_weight <= 0 or max_weight >= 1:
        return w

    n = len(w)
    cap = max(float(max_weight), 1.0 / n)
    remaining = set(w)
    out = {k: 0.0 for k in w}
    remaining_mass = 1.0

    while remaining:
        base_total = sum(w[k] for k in remaining)
        if base_total <= 0:
            equal = remaining_mass / len(remaining)
            for k in remaining:
                out[k] = equal
            break

        proposed = {k: remaining_mass * w[k] / base_total for k in remaining}
        capped = [k for k, v in proposed.items() if v > cap + 1e-12]
        if not capped:
            for k, v in proposed.items():
                out[k] = v
            break

        for k in capped:
            out[k] = cap
            remaining_mass -= cap
            remaining.remove(k)

    total = sum(out.values())
    if total > 0:
        out = {k: v / total for k, v in out.items()}
    return out


def _risk_snapshot_pos(pos: int, refresh_days: int) -> int:
    """Return a strictly non-future position shared by one refresh bucket."""
    refresh = max(1, int(refresh_days))
    if refresh == 1:
        return pos
    snap = pos - (pos % refresh)
    return snap if snap >= 3 else pos


def _portfolio_volatility(
    raw_prices: pd.DataFrame,
    symbols: list[str],
    pos: int,
    lookback: int,
    weights: dict[str, float],
    annualization_factor: int,
) -> tuple[float | None, int]:
    """Annualized volatility with covariance reuse.

    The expensive covariance matrix depends on symbols, snapshot position,
    lookback and annualization — not on the current ERC weights. Optimizer
    candidates frequently revisit the same symbol set/date with different timing
    genes or target weights, so cache the covariance once and only recompute the
    cheap ``w'Cov w`` multiplication for each call. This is mathematically
    identical to recomputing ``np.cov`` every time.
    """
    symbols_key = tuple(symbols)
    cache_key = (symbols_key, int(pos), int(lookback), int(annualization_factor))
    cache = raw_prices.attrs.setdefault("_risk_covariance_cache", {})
    cached = cache.get(cache_key)

    if cached is None:
        start = max(0, pos - max(2, int(lookback)))
        window = raw_prices.iloc[start:pos][symbols].dropna()
        observations = len(window)
        if observations < 3:
            cached = (None, observations)
            cache[cache_key] = cached
        else:
            values = window.to_numpy(dtype=float)
            with np.errstate(divide="ignore", invalid="ignore"):
                returns = np.log(values[1:] / values[:-1])
            returns = returns[np.all(np.isfinite(returns), axis=1)]
            if returns.shape[0] < 2:
                cached = (None, observations)
                cache[cache_key] = cached
            else:
                cov = np.cov(returns, rowvar=False, ddof=1)
                cov = np.atleast_2d(np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0))
                cov *= annualization_factor
                cached = (cov, observations)
                cache[cache_key] = cached

    cov, observations = cached
    if cov is None:
        return None, observations

    vec = np.asarray([weights[s] for s in symbols], dtype=float)
    variance = float(vec @ cov @ vec)
    return math.sqrt(max(variance, 0.0)), observations


def risk_adjusted_targets(
    raw_prices: pd.DataFrame,
    symbols: list[str],
    pos: int,
    erc_targets: dict[str, float],
    params: BacktestParams,
) -> tuple[dict[str, float], dict]:
    """Scale ERC weights by an absolute volatility target using only past data."""
    original = _normalise(erc_targets)

    if not params.risk_overlay_enabled:
        return original, {
            "enabled": False,
            "equity_exposure": 1.0,
            "cash_target": 0.0,
            "fast_volatility": None,
            "slow_volatility": None,
            "risk_volatility": None,
            "target_volatility": params.target_volatility,
            "risk_refresh_days": params.risk_refresh_days,
            "risk_snapshot_position": pos,
            "relative_targets": {k: round(v, 6) for k, v in original.items()},
            "targets": {k: round(v, 6) for k, v in original.items()},
        }

    bounded = apply_position_cap(original, params.max_position_weight)
    risk_pos = _risk_snapshot_pos(pos, params.risk_refresh_days)
    fast, n_fast = _portfolio_volatility(
        raw_prices,
        symbols,
        risk_pos,
        params.risk_fast_lookback,
        bounded,
        params.annualization_factor,
    )
    slow, n_slow = _portfolio_volatility(
        raw_prices,
        symbols,
        risk_pos,
        params.risk_slow_lookback,
        bounded,
        params.annualization_factor,
    )
    available = [
        v for v in (fast, slow)
        if v is not None and math.isfinite(v) and v > 1e-12
    ]
    risk_vol = max(available) if available else None

    if risk_vol is None:
        exposure = min(1.0, max(0.0, params.risk_missing_data_exposure))
    else:
        exposure = params.target_volatility / risk_vol if params.target_volatility > 0 else 0.0
        exposure = min(1.0, max(params.min_equity_exposure, exposure))

    targets = {s: bounded[s] * exposure for s in symbols}
    result = RiskOverlayResult(
        targets=targets,
        relative_targets=bounded,
        equity_exposure=exposure,
        cash_target=1.0 - exposure,
        fast_volatility=fast,
        slow_volatility=slow,
        risk_volatility=risk_vol,
        target_volatility=params.target_volatility,
        observations_fast=n_fast,
        observations_slow=n_slow,
    )
    info = result.as_dict()
    info["risk_refresh_days"] = max(1, int(params.risk_refresh_days))
    info["risk_snapshot_position"] = int(risk_pos)
    return targets, info