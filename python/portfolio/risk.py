from __future__ import annotations

import math

import numpy as np
import pandas as pd


def concentration_metrics(position_rows: list[dict]) -> dict:
    nav_weights = [max(0.0, float(p.get("weight") or 0)) for p in position_rows]
    equity_total = sum(nav_weights)
    equity_weights = [w / equity_total for w in nav_weights] if equity_total > 1e-12 else []
    hhi = sum(w * w for w in equity_weights) if equity_weights else 0.0
    effective = (1.0 / hhi) if hhi > 1e-12 else 0.0
    n = len(equity_weights)
    largest_index = int(np.argmax(equity_weights)) if equity_weights else None
    largest_symbol = (
        str(position_rows[largest_index].get("symbol") or "").upper()
        if largest_index is not None
        else None
    )
    return {
        "hhi": hhi,
        "equity_hhi": hhi,
        "effective_positions": effective,
        "effective_position_ratio": (effective / n) if n else 0.0,
        "max_position_weight": max(nav_weights) if nav_weights else 0.0,
        "max_equity_weight": max(equity_weights) if equity_weights else 0.0,
        "largest_position_symbol": largest_symbol or None,
        "equity_weight_sum": equity_total,
        "n_positions": n,
    }


def _returns_frame(histories: dict[str, list[dict]]) -> pd.DataFrame:
    series = {}
    for symbol, rows in histories.items():
        if not rows:
            continue
        indexed = {
            r["trading_date"]: {
                "close": float(r["close"]),
                "cash": float(r.get("analytics_cash_distribution") or 0),
                "factor": float(r.get("analytics_share_factor") or 1),
            }
            for r in rows if r.get("close") is not None
        }
        s = pd.Series({day: values["close"] for day, values in indexed.items()}, dtype=float).sort_index()
        if len(s) < 3:
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            ret = np.log(s / s.shift(1))
        for day, values in indexed.items():
            if day not in ret.index or values["cash"] == 0 and values["factor"] == 1:
                continue
            previous = s.shift(1).get(day)
            adjusted_value = values["close"] * values["factor"] + values["cash"]
            if previous is not None and pd.notna(previous) and previous > 0 and adjusted_value > 0:
                ret.loc[day] = np.log(adjusted_value / previous)
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
    missing_pairs = int(cov_df.isna().sum().sum())
    cov = cov_df.fillna(0.0).to_numpy(dtype=float)
    diag = np.diag(np.diag(cov))
    cov = 0.90 * cov + 0.10 * diag
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


def _series_volatility(series: pd.Series, days: int, min_periods: int) -> float | None:
    values = series.dropna().tail(days)
    if len(values) < min_periods:
        return None
    return float(values.std(ddof=1) * math.sqrt(252.0))


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


def _correlation_metrics(returns: pd.DataFrame, symbols: list[str]) -> dict:
    if len(symbols) < 2:
        return {
            "average_correlation": None,
            "max_correlation": None,
            "correlation_symbols": list(symbols),
            "correlation_matrix": ({symbols[0]: {symbols[0]: 1.0}} if symbols else {}),
        }
    corr = returns[symbols].tail(252).corr(min_periods=40)
    values = []
    matrix = {}
    for row_symbol in symbols:
        matrix[row_symbol] = {}
        for column_symbol in symbols:
            value = corr.loc[row_symbol, column_symbol]
            matrix[row_symbol][column_symbol] = float(value) if pd.notna(value) else None
    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            value = corr.iloc[i, j]
            if pd.notna(value):
                values.append(float(value))
    return {
        "average_correlation": float(np.mean(values)) if values else None,
        "max_correlation": max(values) if values else None,
        "correlation_symbols": list(symbols),
        "correlation_matrix": matrix,
    }


def _portfolio_return_metrics(returns: pd.DataFrame, symbols: list[str], weights: np.ndarray) -> dict:
    if not symbols:
        return {}
    frame = returns[symbols].tail(252).dropna(how="any")
    if len(frame) < 20:
        return {
            "daily_var_95": None,
            "daily_cvar_95": None,
            "max_daily_loss": None,
            "max_daily_loss_date": None,
            "downside_volatility": None,
            "positive_day_ratio": None,
            "return_observations": int(len(frame)),
        }
    p = frame.to_numpy(dtype=float) @ weights
    var95 = float(np.quantile(p, 0.05))
    tail = p[p <= var95]
    downside = p[p < 0]
    worst_index = int(np.argmin(p))
    downside_vol = float(np.std(downside, ddof=1) * math.sqrt(252)) if len(downside) >= 2 else None
    return {
        "daily_var_95": var95,
        "daily_cvar_95": float(np.mean(tail)) if len(tail) else var95,
        "max_daily_loss": float(p[worst_index]),
        "max_daily_loss_date": str(frame.index[worst_index]),
        "downside_volatility": downside_vol,
        "positive_day_ratio": float(np.mean(p > 0)),
        "return_observations": int(len(p)),
    }


def _symbol_metrics(
    position_rows: list[dict],
    returns: pd.DataFrame,
    eligible: list[str],
    risk_contrib: dict[str, float],
) -> dict[str, dict]:
    total_value = sum(max(0.0, float(p.get("market_value") or 0)) for p in position_rows)
    corr = (
        returns[eligible].tail(252).corr(min_periods=40)
        if len(eligible) >= 2
        else pd.DataFrame()
    )
    metrics: dict[str, dict] = {}

    for row in position_rows:
        symbol = str(row.get("symbol") or "").upper()
        value = max(0.0, float(row.get("market_value") or 0))
        series = returns[symbol] if symbol in returns.columns else pd.Series(dtype=float)
        vol63 = _series_volatility(series, 63, 20)
        vol252 = _series_volatility(series, 252, 40)
        ratio = (vol63 / vol252) if vol63 is not None and vol252 and vol252 > 0 else None

        avg_corr = None
        max_corr = None
        if symbol in corr.columns:
            peers = [
                float(corr.loc[symbol, peer])
                for peer in corr.columns
                if peer != symbol and pd.notna(corr.loc[symbol, peer])
            ]
            if peers:
                avg_corr = float(np.mean(peers))
                max_corr = max(peers)

        recent = series.dropna().tail(252)
        worst_return = None
        worst_date = None
        if len(recent):
            worst_date = str(recent.idxmin())
            worst_return = float(recent.min())

        price_val = float(row.get("price") or 0) if row.get("price") else None
        metrics[symbol] = {
            "current_price": price_val,
            "equity_weight": (value / total_value) if total_value > 0 else None,
            "risk_contribution": risk_contrib.get(symbol),
            "volatility_63": vol63,
            "volatility_252": vol252,
            "volatility_ratio": ratio,
            "average_correlation_to_others": avg_corr,
            "max_correlation_to_others": max_corr,
            "worst_daily_return": worst_return,
            "worst_daily_return_date": worst_date,
            "return_observations": int(series.count()) if symbol in returns.columns else 0,
        }

    return metrics


def portfolio_risk(position_rows: list[dict], histories: dict[str, list[dict]]) -> dict:
    """Informational portfolio risk; never produces or executes a trade."""
    concentration = concentration_metrics(position_rows)
    empty_payload = {
        **concentration,
        "volatility_63": None,
        "volatility_252": None,
        "volatility_ratio": None,
        "risk_contributions": {},
        "symbol_metrics": {},
        "risk_contribution_hhi": None,
        "largest_risk_symbol": None,
        "largest_risk_contribution": None,
        "equal_risk_contribution": None,
        "risk_concentration_ratio": None,
        "erc_reference_weights": {},
        "average_correlation": None,
        "max_correlation": None,
        "correlation_symbols": [],
        "correlation_matrix": {},
        "diversification_ratio": None,
        "daily_var_95": None,
        "daily_cvar_95": None,
        "max_daily_loss": None,
        "max_daily_loss_date": None,
        "downside_volatility": None,
        "positive_day_ratio": None,
        "return_observations": 0,
    }
    if not position_rows:
        return {**empty_payload, "status": "NO_POSITIONS", "quality": {"reason": "no_positions"}}

    value_by_symbol = {
        p["symbol"]: max(0.0, float(p.get("market_value") or 0))
        for p in position_rows
    }
    total = sum(value_by_symbol.values())
    if total <= 0:
        return {**empty_payload, "status": "UNAVAILABLE", "quality": {"reason": "zero_equity_value"}}

    returns = _returns_frame(histories)
    cov, eligible, quality = _pairwise_covariance(returns, min_periods=40)
    requested = [p["symbol"] for p in position_rows]
    missing = sorted(set(requested) - set(eligible))
    if cov is None:
        symbol_metrics = _symbol_metrics(position_rows, returns, [], {})
        return {
            **empty_payload,
            "symbol_metrics": symbol_metrics,
            "status": "UNAVAILABLE",
            "quality": {
                **quality,
                "requested_symbols": len(requested),
                "missing_symbols": missing,
                "coverage_weight": 0.0,
            },
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
    largest_risk_symbol = max(risk_contrib, key=risk_contrib.get) if risk_contrib else None
    largest_risk_contribution = risk_contrib.get(largest_risk_symbol) if largest_risk_symbol else None
    equal_risk = 1.0 / len(eligible) if eligible else None
    risk_concentration_ratio = (
        largest_risk_contribution / equal_risk
        if largest_risk_contribution is not None and equal_risk and equal_risk > 0
        else None
    )
    rc_hhi = float(sum(float(v) ** 2 for v in rc)) if len(rc) else None

    indiv_vol = np.sqrt(np.maximum(0.0, np.diag(cov)))
    weighted_indiv_vol = float(weights @ indiv_vol)
    diversification_ratio = weighted_indiv_vol / vol252 if vol252 and vol252 > 1e-12 else None

    corr_metrics = _correlation_metrics(returns, eligible)
    return_metrics = _portfolio_return_metrics(returns, eligible, weights)
    symbol_metrics = _symbol_metrics(position_rows, returns, eligible, risk_contrib)

    status = "VALID" if not missing else "PARTIAL"
    return {
        **concentration,
        **corr_metrics,
        **return_metrics,
        "status": status,
        "volatility_63": vol63,
        "volatility_252": vol252,
        "volatility_ratio": (vol63 / vol252) if vol63 is not None and vol252 and vol252 > 0 else None,
        "risk_contributions": risk_contrib,
        "symbol_metrics": symbol_metrics,
        "risk_contribution_hhi": rc_hhi,
        "largest_risk_symbol": largest_risk_symbol,
        "largest_risk_contribution": largest_risk_contribution,
        "equal_risk_contribution": equal_risk,
        "risk_concentration_ratio": risk_concentration_ratio,
        "erc_reference_weights": erc_weights,
        "diversification_ratio": diversification_ratio,
        "quality": {
            **quality,
            "requested_symbols": len(requested),
            "missing_symbols": missing,
            "coverage_weight": eligible_total / total if total > 0 else 0.0,
        },
    }
