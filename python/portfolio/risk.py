from __future__ import annotations

import math

import numpy as np
import pandas as pd


def concentration_metrics(position_rows: list[dict]) -> dict:
    weights = [max(0.0, float(p.get("weight") or 0)) for p in position_rows]
    return {
        "hhi": sum(w * w for w in weights) if weights else 0.0,
        "max_position_weight": max(weights) if weights else 0.0,
        "n_positions": len(weights),
    }


def _returns_frame(histories: dict[str, list[dict]]) -> pd.DataFrame:
    series = {}
    for symbol, rows in histories.items():
        if not rows:
            continue
        s = pd.Series(
            {r["trading_date"]: float(r["close"]) for r in rows if r.get("close") is not None},
            dtype=float,
        ).sort_index()
        if len(s) < 3:
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            ret = np.log(s / s.shift(1))
        series[symbol] = ret.replace([np.inf, -np.inf], np.nan)
    return pd.DataFrame(series).sort_index() if series else pd.DataFrame()


def _pairwise_covariance(returns: pd.DataFrame, min_periods: int = 40) -> tuple[np.ndarray | None, list[str], dict]:
    if returns.empty:
        return None, [], {"reason": "no_return_history"}
    eligible = [c for c in returns.columns if returns[c].count() >= min_periods]
    if not eligible:
        return None, [], {"reason": "insufficient_history"}
    frame = returns[eligible]
    cov_df = frame.cov(min_periods=min_periods) * 252.0
    # Pairwise history prevents a newly listed symbol from erasing all covariance
    # observations. Unknown cross-covariances are conservatively treated as zero;
    # the quality block reports how many pairs were unavailable.
    missing_pairs = int(cov_df.isna().sum().sum())
    cov = cov_df.fillna(0.0).to_numpy(dtype=float)
    diag = np.diag(np.diag(cov))
    cov = 0.90 * cov + 0.10 * diag  # light diagonal shrinkage for stability
    return cov, eligible, {
        "eligible_symbols": len(eligible),
        "missing_covariance_cells": missing_pairs,
        "min_periods": min_periods,
    }


def _vol_for_window(returns: pd.DataFrame, symbols: list[str], weights: np.ndarray, days: int) -> float | None:
    if not symbols:
        return None
    window = returns[symbols].tail(days)
    cov, eligible, _ = _pairwise_covariance(window, min_periods=max(20, min(40, days // 2)))
    if cov is None or eligible != symbols:
        return None
    variance = float(weights @ cov @ weights)
    return math.sqrt(max(0.0, variance))


def _solve_erc(cov: np.ndarray) -> np.ndarray | None:
    n = cov.shape[0]
    if n == 0:
        return None
    target = 1.0 / n
    weights = np.full(n, target, dtype=float)
    for _ in range(1000):
        marginal = cov @ weights
        variance = float(weights @ marginal)
        if variance <= 1e-16:
            return None
        rc = (weights * marginal) / variance
        if np.max(np.abs(rc - target)) < 1e-7:
            return weights / weights.sum()
        # Multiplicative risk-budget update. Clip the denominator to avoid an
        # unstable sign flip from noisy pairwise covariance estimates.
        safe = np.maximum(np.abs(rc), 1e-12)
        weights = weights * np.power(target / safe, 0.35)
        weights = np.maximum(weights, 1e-10)
        weights /= weights.sum()
    marginal = cov @ weights
    variance = float(weights @ marginal)
    if variance <= 0:
        return None
    rc = (weights * marginal) / variance
    return weights if np.max(np.abs(rc - target)) < 1e-4 else None


def portfolio_risk(position_rows: list[dict], histories: dict[str, list[dict]]) -> dict:
    """Informational portfolio risk; never produces or executes a trade."""
    concentration = concentration_metrics(position_rows)
    if not position_rows:
        return {
            **concentration,
            "status": "NO_POSITIONS",
            "volatility_63": None,
            "volatility_252": None,
            "risk_contributions": {},
            "erc_reference_weights": {},
            "quality": {"reason": "no_positions"},
        }

    value_by_symbol = {
        p["symbol"]: max(0.0, float(p.get("market_value") or 0))
        for p in position_rows
    }
    total = sum(value_by_symbol.values())
    if total <= 0:
        return {
            **concentration,
            "status": "UNAVAILABLE",
            "volatility_63": None,
            "volatility_252": None,
            "risk_contributions": {},
            "erc_reference_weights": {},
            "quality": {"reason": "zero_equity_value"},
        }

    returns = _returns_frame(histories)
    cov, eligible, quality = _pairwise_covariance(returns, min_periods=40)
    requested = [p["symbol"] for p in position_rows]
    missing = sorted(set(requested) - set(eligible))
    if cov is None:
        return {
            **concentration,
            "status": "UNAVAILABLE",
            "volatility_63": None,
            "volatility_252": None,
            "risk_contributions": {},
            "erc_reference_weights": {},
            "quality": {**quality, "missing_symbols": missing},
        }

    eligible_values = np.array([value_by_symbol[s] for s in eligible], dtype=float)
    eligible_total = float(eligible_values.sum())
    weights = eligible_values / eligible_total if eligible_total > 0 else np.full(len(eligible), 1 / len(eligible))
    marginal = cov @ weights
    variance = float(weights @ marginal)
    vol252 = math.sqrt(max(0.0, variance)) if variance >= 0 else None
    rc = (weights * marginal) / variance if variance > 1e-16 else np.zeros(len(weights))

    vol63 = _vol_for_window(returns, eligible, weights, 63)
    erc = _solve_erc(cov)
    risk_contrib = {s: float(v) for s, v in zip(eligible, rc)}
    erc_weights = {s: float(v) for s, v in zip(eligible, erc)} if erc is not None else {}

    status = "VALID" if not missing else "PARTIAL"
    return {
        **concentration,
        "status": status,
        "volatility_63": vol63,
        "volatility_252": vol252,
        "risk_contributions": risk_contrib,
        "erc_reference_weights": erc_weights,
        "quality": {
            **quality,
            "requested_symbols": len(requested),
            "missing_symbols": missing,
            "coverage_weight": eligible_total / total if total > 0 else 0.0,
        },
    }
