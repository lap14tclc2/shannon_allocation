from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .permanent_loss_risk import assess_portfolio_permanent_loss_risk
from .risk_warnings import generate_risk_warnings


def concentration_metrics(position_rows: list[dict]) -> dict:
    nav_weights = [max(0.0, float(p.get("weight") or 0)) for p in position_rows if str(p.get("symbol") or "").upper() != "CASH"]
    total_nav_weight = sum(max(0.0, float(p.get("weight") or 0)) for p in position_rows)
    equity_total_val = sum(max(0.0, float(p.get("market_value") or 0)) for p in position_rows if str(p.get("symbol") or "").upper() != "CASH")

    equity_weights = [
        (max(0.0, float(p.get("market_value") or 0)) / equity_total_val)
        for p in position_rows
        if str(p.get("symbol") or "").upper() != "CASH"
    ] if equity_total_val > 1e-12 else []

    hhi = sum(w * w for w in equity_weights) if equity_weights else 0.0
    effective = (1.0 / hhi) if hhi > 1e-12 else 0.0
    n = len(equity_weights)
    equity_position_rows = [p for p in position_rows if str(p.get("symbol") or "").upper() != "CASH"]
    largest_index = int(np.argmax(equity_weights)) if equity_weights else None
    largest_symbol = (
        str(equity_position_rows[largest_index].get("symbol") or "").upper()
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
        "equity_weight_sum": sum(equity_weights),
        "total_nav_weight": total_nav_weight,
        "n_positions": n,
    }


def _returns_frame(histories: dict[str, list[dict]]) -> pd.DataFrame:
    series = {}
    for symbol, rows in histories.items():
        if not rows or symbol.upper() == "CASH":
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
        series[symbol.upper()] = ret.replace([np.inf, -np.inf], np.nan)
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


def _correlation_metrics(returns: pd.DataFrame, all_requested_symbols: list[str]) -> dict:
    """Calculates pairwise correlations for ALL requested equity symbols.

    Returns None for missing / insufficient pairs. Zero synthetic default fallbacks (0 or 0.35)!
    """
    symbols = [s.upper() for s in all_requested_symbols if s.upper() != "CASH"]
    if not symbols:
        return {
            "average_correlation": None,
            "max_correlation": None,
            "correlation_symbols": [],
            "correlation_matrix": {},
        }
    if len(symbols) < 2:
        return {
            "average_correlation": None,
            "max_correlation": None,
            "correlation_symbols": list(symbols),
            "correlation_matrix": {symbols[0]: {symbols[0]: 1.0}},
        }

    valid_cols = [s for s in symbols if s in returns.columns]
    corr_frame = returns[valid_cols].tail(252).corr(min_periods=40) if len(valid_cols) >= 2 else pd.DataFrame()

    values = []
    matrix = {}
    for s1 in symbols:
        matrix[s1] = {}
        for s2 in symbols:
            if s1 == s2:
                matrix[s1][s2] = 1.0
            elif s1 in corr_frame.columns and s2 in corr_frame.columns:
                val = corr_frame.loc[s1, s2]
                matrix[s1][s2] = float(val) if pd.notna(val) else None
            else:
                matrix[s1][s2] = None

    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            v = matrix[symbols[i]][symbols[j]]
            if v is not None:
                values.append(v)

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


MIN_PORTFOLIO_RISK_NAV_COVERAGE_COMPLETE = 0.80
MIN_PORTFOLIO_RISK_NAV_COVERAGE_PARTIAL = 0.50
MIN_PORTFOLIO_RISK_SYMBOLS = 2


def _symbol_metrics(
    position_rows: list[dict],
    returns: pd.DataFrame,
    eligible: list[str],
    risk_contrib: dict[str, float],
    coverage_status: str = "COMPLETE",
) -> dict[str, dict]:
    equity_total_value = sum(max(0.0, float(p.get("market_value") or 0)) for p in position_rows if str(p.get("symbol") or "").upper() != "CASH")
    corr = (
        returns[eligible].tail(252).corr(min_periods=40)
        if len(eligible) >= 2
        else pd.DataFrame()
    )
    metrics: dict[str, dict] = {}

    contrib_scope = "FULL_PORTFOLIO" if coverage_status == "COMPLETE" else ("ELIGIBLE_UNIVERSE_ONLY" if eligible else "UNAVAILABLE")

    for row in position_rows:
        symbol = str(row.get("symbol") or "").upper()
        if symbol == "CASH":
            continue
        value = max(0.0, float(row.get("market_value") or 0))
        nav_wt = float(row.get("weight") or 0.0)
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

        is_eligible = symbol in eligible
        rc_val = float(risk_contrib[symbol]) if is_eligible and symbol in risk_contrib else None

        sym_var_95 = None
        sym_cvar_95 = None
        clean_series = series.dropna()
        if len(clean_series) >= 40:
            arr = clean_series.to_numpy()
            q5 = float(np.percentile(arr, 5))
            sym_var_95 = float(-q5) if q5 < 0 else 0.0
            tail = arr[arr <= q5]
            sym_cvar_95 = float(-np.mean(tail)) if len(tail) > 0 and np.mean(tail) < 0 else sym_var_95

        if not is_eligible or rc_val is None:
            rc_text = "Chưa tính được"
        elif contrib_scope == "FULL_PORTFOLIO":
            rc_text = f"{rc_val * 100:.2f}% tổng biến động danh mục"
        else:
            rc_text = f"{rc_val * 100:.0f}% trong phần đo lường được"

        price_val = float(row.get("price") or 0) if row.get("price") else None
        metrics[symbol] = {
            "current_price": price_val,
            "weight": nav_wt,
            "nav_weight": nav_wt,
            "equity_weight": (value / equity_total_value) if equity_total_value > 0 else None,
            "risk_contribution": rc_val,
            "risk_contribution_text": rc_text,
            "risk_contribution_status": "AVAILABLE" if is_eligible else "UNAVAILABLE",
            "risk_contribution_scope": contrib_scope if is_eligible else "UNAVAILABLE",
            "risk_contribution_reason": None if is_eligible else "INSUFFICIENT_PRICE_HISTORY",
            "volatility_63": vol63,
            "volatility_252": vol252,
            "annualized_volatility": vol252,
            "volatility_ratio": ratio,
            "daily_var_95": sym_var_95,
            "daily_cvar_95": sym_cvar_95,
            "average_correlation_to_others": avg_corr,
            "max_correlation_to_others": max_corr,
            "worst_daily_return": worst_return,
            "worst_daily_return_date": worst_date,
            "return_observations": int(series.count()) if symbol in returns.columns else 0,
        }

    return metrics


def portfolio_risk(
    position_rows: list[dict],
    histories: dict[str, list[dict]],
    valuation_signals: dict[str, dict] | None = None,
) -> dict:
    """Informational portfolio risk; strictly separates Market Risk from Permanent Capital Loss Risk.

    Enforces risk coverage tracking and zero synthetic fallbacks.
    """
    concentration = concentration_metrics(position_rows)

    requested_symbols = [str(p.get("symbol") or "").upper() for p in position_rows if str(p.get("symbol") or "").upper() != "CASH"]
    total_equity_symbols = len(requested_symbols)

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
        "correlation_symbols": requested_symbols,
        "correlation_matrix": {s1: {s2: (1.0 if s1 == s2 else None) for s2 in requested_symbols} for s1 in requested_symbols},
        "diversification_ratio": None,
        "daily_var_95": None,
        "daily_cvar_95": None,
        "max_daily_loss": None,
        "max_daily_loss_date": None,
        "downside_volatility": None,
        "positive_day_ratio": None,
        "return_observations": 0,
        "risk_eligible_symbols": [],
        "risk_total_symbols": total_equity_symbols,
        "risk_eligible_count": 0,
        "risk_eligible_nav_weight": 0.0,
        "risk_coverage_status": "INSUFFICIENT",
        "risk_contribution_scope": "UNAVAILABLE",
    }

    perm_loss_data = assess_portfolio_permanent_loss_risk(position_rows, valuation_signals)

    if not position_rows or sum(max(0.0, float(p.get("market_value") or 0)) for p in position_rows) <= 0:
        status_code = "NO_POSITIONS" if not position_rows else "UNAVAILABLE"
        payload = {**empty_payload, "status": status_code, "quality": {"reason": status_code.lower()}}
        warn_data = generate_risk_warnings(payload, position_rows)

        market_risk = {
            "status": "INSUFFICIENT_DATA",
            "risk_coverage_status": "INSUFFICIENT",
            "overall_severity": "INSUFFICIENT_DATA",
            "overall_severity_text": "Chưa đủ dữ liệu",
            "headline": "Chưa đủ dữ liệu để ước tính đáng tin cậy biến động toàn danh mục",
            "warnings": warn_data["warnings"],
        }
        permanent_loss_risk_summary = {
            "overall_severity": perm_loss_data["overall_severity"],
            "overall_severity_text": perm_loss_data["overall_severity_text"],
            "headline": perm_loss_data["headline"],
            "high_risk_count": perm_loss_data["high_risk_count"],
            "elevated_count": perm_loss_data["elevated_count"],
            "top_concerns": perm_loss_data["top_concerns"],
        }
        risk_summary = {
            "market_risk": market_risk,
            "permanent_loss_risk": permanent_loss_risk_summary,
            "overall_severity": "INSUFFICIENT_DATA",
            "overall_severity_text": "Chưa đủ dữ liệu",
            "headline": "Chưa đủ dữ liệu để ước tính đáng tin cậy biến động toàn danh mục",
            "total_warning_count": warn_data["summary"]["total_warning_count"],
            "high_risk_count": warn_data["summary"]["high_risk_count"],
            "warning_count": warn_data["summary"]["warning_count"],
            "top_concerns": warn_data["summary"]["top_concerns"],
        }
        return {
            **payload,
            "market_risk": market_risk,
            "permanent_loss_risk": permanent_loss_risk_summary,
            "symbol_risk": {},
            "risk_summary": risk_summary,
            "warnings": warn_data["warnings"],
        }

    returns = _returns_frame(histories)
    cov, eligible, quality = _pairwise_covariance(returns, min_periods=40)
    missing = sorted(set(requested_symbols) - set(eligible))

    value_by_symbol = {
        str(p["symbol"]).upper(): max(0.0, float(p.get("market_value") or 0))
        for p in position_rows if str(p.get("symbol") or "").upper() != "CASH"
    }
    total = sum(value_by_symbol.values())

    eligible_count = len(eligible)
    eligible_nav_weight = sum(float(p.get("weight") or 0.0) for p in position_rows if str(p.get("symbol") or "").upper() in eligible)

    if eligible_count == total_equity_symbols and total_equity_symbols >= 1 and eligible_nav_weight >= MIN_PORTFOLIO_RISK_NAV_COVERAGE_COMPLETE:
        coverage_status = "COMPLETE"
    elif eligible_nav_weight >= MIN_PORTFOLIO_RISK_NAV_COVERAGE_PARTIAL and eligible_count >= 1:
        coverage_status = "PARTIAL"
    else:
        coverage_status = "INSUFFICIENT"

    if coverage_status == "COMPLETE":
        contrib_scope = "FULL_PORTFOLIO"
    elif eligible_count > 0:
        contrib_scope = "ELIGIBLE_UNIVERSE_ONLY"
    else:
        contrib_scope = "UNAVAILABLE"

    corr_metrics = _correlation_metrics(returns, requested_symbols)

    if cov is None:
        symbol_metrics = _symbol_metrics(position_rows, returns, [], {}, coverage_status)
        payload = {
            **empty_payload,
            **corr_metrics,
            "symbol_metrics": symbol_metrics,
            "status": "UNAVAILABLE",
            "risk_eligible_symbols": [],
            "risk_total_symbols": total_equity_symbols,
            "risk_eligible_count": 0,
            "risk_eligible_nav_weight": 0.0,
            "risk_coverage_status": "INSUFFICIENT",
            "risk_contribution_scope": "UNAVAILABLE",
            "quality": {
                **quality,
                "requested_symbols": len(requested_symbols),
                "missing_symbols": missing,
                "coverage_weight": 0.0,
            },
        }
        warn_data = generate_risk_warnings(payload, position_rows)
        market_risk = {
            "status": "INSUFFICIENT_DATA",
            "risk_coverage_status": "INSUFFICIENT",
            "overall_severity": "INSUFFICIENT_DATA",
            "overall_severity_text": "Chưa đủ dữ liệu",
            "headline": "Chưa đủ dữ liệu để ước tính đáng tin cậy biến động toàn danh mục",
            "warnings": warn_data["warnings"],
        }
        permanent_loss_risk_summary = {
            "overall_severity": perm_loss_data["overall_severity"],
            "overall_severity_text": perm_loss_data["overall_severity_text"],
            "headline": perm_loss_data["headline"],
            "high_risk_count": perm_loss_data["high_risk_count"],
            "elevated_count": perm_loss_data["elevated_count"],
            "top_concerns": perm_loss_data["top_concerns"],
        }
        risk_summary = {
            "market_risk": market_risk,
            "permanent_loss_risk": permanent_loss_risk_summary,
            "overall_severity": "INSUFFICIENT_DATA",
            "overall_severity_text": "Chưa đủ dữ liệu",
            "headline": "Chưa đủ dữ liệu để ước tính đáng tin cậy biến động toàn danh mục",
            "total_warning_count": warn_data["summary"]["total_warning_count"],
            "high_risk_count": warn_data["summary"]["high_risk_count"],
            "warning_count": warn_data["summary"]["warning_count"],
            "top_concerns": warn_data["summary"]["top_concerns"],
        }
        return {
            **payload,
            "market_risk": market_risk,
            "permanent_loss_risk": permanent_loss_risk_summary,
            "symbol_risk": {},
            "risk_summary": risk_summary,
            "warnings": warn_data["warnings"],
        }

    eligible_values = np.array([value_by_symbol[s] for s in eligible], dtype=float)
    eligible_total = float(eligible_values.sum())
    weights = eligible_values / eligible_total if eligible_total > 0 else np.full(len(eligible), 1 / len(eligible))
    marginal = cov @ weights
    variance = float(weights @ marginal)
    vol252_measured = math.sqrt(max(0.0, variance)) if variance >= 0 else None
    rc = (weights * marginal) / variance if variance > 1e-16 else np.zeros(len(weights))

    vol63_measured = _vol_for_window(returns, eligible, weights, 63)
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
    diversification_ratio = weighted_indiv_vol / vol252_measured if vol252_measured and vol252_measured > 1e-12 else None

    return_metrics = _portfolio_return_metrics(returns, eligible, weights)
    symbol_metrics = _symbol_metrics(position_rows, returns, eligible, risk_contrib, coverage_status)

    vol252_portfolio = vol252_measured if coverage_status == "COMPLETE" else None
    vol63_portfolio = vol63_measured if coverage_status == "COMPLETE" else None

    if coverage_status != "COMPLETE":
        return_metrics["daily_var_95"] = None
        return_metrics["daily_cvar_95"] = None
        return_metrics["downside_volatility"] = None
        return_metrics["max_daily_loss"] = None
        return_metrics["max_daily_loss_date"] = None

    status = "VALID" if not missing else "PARTIAL"
    payload = {
        **concentration,
        **corr_metrics,
        **return_metrics,
        "status": status,
        "volatility_63": vol63_portfolio,
        "volatility_252": vol252_portfolio,
        "measured_volatility_63": vol63_measured,
        "measured_volatility_252": vol252_measured,
        "volatility_ratio": (vol63_measured / vol252_measured) if vol63_measured is not None and vol252_measured and vol252_measured > 0 else None,
        "risk_contributions": risk_contrib,
        "symbol_metrics": symbol_metrics,
        "risk_contribution_hhi": rc_hhi,
        "largest_risk_symbol": largest_risk_symbol,
        "largest_risk_contribution": largest_risk_contribution,
        "equal_risk_contribution": equal_risk,
        "risk_concentration_ratio": risk_concentration_ratio,
        "erc_reference_weights": erc_weights,
        "diversification_ratio": diversification_ratio,
        "risk_eligible_symbols": eligible,
        "risk_total_symbols": total_equity_symbols,
        "risk_eligible_count": eligible_count,
        "risk_eligible_nav_weight": eligible_nav_weight,
        "risk_coverage_status": coverage_status,
        "risk_contribution_scope": contrib_scope,
        "quality": {
            **quality,
            "requested_symbols": total_equity_symbols,
            "missing_symbols": missing,
            "coverage_weight": eligible_total / total if total > 0 else 0.0,
        },
    }
    warn_data = generate_risk_warnings(payload, position_rows)

    symbol_risk = {}
    for p in position_rows:
        sym = str(p.get("symbol") or "").upper()
        if not sym or sym == "CASH":
            continue
        sm = symbol_metrics.get(sym, {})
        perm_assess = perm_loss_data["symbol_assessments"].get(sym, {})

        rc_val = sm.get("risk_contribution")
        w = float(p.get("weight") or 0.0)

        if coverage_status != "COMPLETE" and rc_val is not None:
            explanation = (
                f"{sym} chiếm {w * 100:.1f}% NAV và đóng góp {rc_val * 100:.1f}% biến động trong phần danh mục có đủ dữ liệu ({eligible_nav_weight * 100:.1f}% NAV). "
                f"Con số này không đại diện cho 100% rủi ro toàn danh mục."
            )
        elif rc_val is not None:
            explanation = f"{sym} chiếm {w * 100:.1f}% NAV và đóng góp {rc_val * 100:.1f}% vào tổng biến động danh mục."
        else:
            explanation = f"{sym} chưa có đủ dữ liệu lịch sử giá để tính đóng góp rủi ro (Chưa tính được)."

        symbol_risk[sym] = {
            "market_risk": {
                "weight": w,
                "nav_weight": w,
                "equity_weight": sm.get("equity_weight"),
                "risk_contribution": rc_val,
                "risk_contribution_status": sm.get("risk_contribution_status"),
                "risk_contribution_scope": sm.get("risk_contribution_scope"),
                "risk_contribution_reason": sm.get("risk_contribution_reason"),
                "volatility_63": sm.get("volatility_63"),
                "volatility_252": sm.get("volatility_252"),
                "volatility_ratio": sm.get("volatility_ratio"),
                "average_correlation": sm.get("average_correlation_to_others"),
                "explanation": explanation,
            },
            "permanent_loss_risk": perm_assess,
        }

    headline = warn_data["summary"]["headline"]
    market_risk_status = status
    overall_severity = warn_data["summary"]["overall_severity"]
    overall_severity_text = warn_data["summary"]["overall_severity_text"]

    if coverage_status == "INSUFFICIENT":
        market_risk_status = "INSUFFICIENT_DATA"
        overall_severity = "INSUFFICIENT_DATA"
        overall_severity_text = "Chưa đủ dữ liệu"
        headline = "Chưa đủ dữ liệu để ước tính đáng tin cậy biến động toàn danh mục"

    market_risk_actionable = bool(
        coverage_status == "COMPLETE"
        or (eligible_nav_weight >= MIN_PORTFOLIO_RISK_NAV_COVERAGE_COMPLETE and eligible_count >= MIN_PORTFOLIO_RISK_SYMBOLS)
    )

    risk_context = {
        "data_status": coverage_status,
        "market_risk_data_status": "VALID" if coverage_status == "COMPLETE" else ("PARTIAL" if coverage_status == "PARTIAL" else "INSUFFICIENT"),
        "actionable": market_risk_actionable,
        "market_risk_actionable": market_risk_actionable,
        "eligible_nav_weight": eligible_nav_weight,
        "eligible_symbol_count": eligible_count,
        "total_symbol_count": total_equity_symbols,
        "eligible_symbols": eligible,
        "missing_symbols": missing,
        "risk_contribution_scope": contrib_scope,
    }

    market_risk = {
        "status": market_risk_status,
        "status_text": overall_severity_text,
        "market_risk_data_status": "VALID" if coverage_status == "COMPLETE" else ("PARTIAL" if coverage_status == "PARTIAL" else "INSUFFICIENT"),
        "market_risk_actionable": market_risk_actionable,
        "actionable": market_risk_actionable,
        "risk_coverage_status": coverage_status,
        "risk_contribution_scope": contrib_scope,
        "risk_eligible_symbols": eligible,
        "risk_total_symbols": total_equity_symbols,
        "risk_eligible_count": eligible_count,
        "risk_eligible_nav_weight": eligible_nav_weight,
        "overall_severity": overall_severity,
        "overall_severity_text": overall_severity_text,
        "headline": headline,
        "volatility_63": vol63_portfolio,
        "volatility_252": vol252_portfolio,
        "measured_volatility_252": vol252_measured,
        "volatility_ratio": (vol63_measured / vol252_measured) if vol63_measured is not None and vol252_measured and vol252_measured > 0 else None,
        "largest_risk_symbol": largest_risk_symbol,
        "largest_risk_contribution": largest_risk_contribution,
        "max_position_weight": concentration.get("max_position_weight"),
        "hhi": concentration.get("hhi"),
        "effective_positions": concentration.get("effective_positions"),
        "average_correlation": corr_metrics.get("average_correlation"),
        "max_correlation": corr_metrics.get("max_correlation"),
        "diversification_ratio": diversification_ratio,
        "daily_var_95": return_metrics.get("daily_var_95"),
        "daily_cvar_95": return_metrics.get("daily_cvar_95"),
        "warnings": warn_data["warnings"],
    }

    permanent_loss_risk_summary = {
        "overall_severity": perm_loss_data["overall_severity"],
        "overall_severity_text": perm_loss_data["overall_severity_text"],
        "headline": perm_loss_data["headline"],
        "high_risk_count": perm_loss_data["high_risk_count"],
        "elevated_count": perm_loss_data["elevated_count"],
        "moderate_count": perm_loss_data["moderate_count"],
        "low_count": perm_loss_data["low_count"],
        "unknown_count": perm_loss_data["unknown_count"],
        "top_concerns": perm_loss_data["top_concerns"],
    }

    risk_summary = {
        "market_risk": market_risk,
        "permanent_loss_risk": permanent_loss_risk_summary,
        "market_risk_actionable": market_risk_actionable,
        "overall_severity": overall_severity,
        "overall_severity_text": overall_severity_text,
        "headline": headline,
        "total_warning_count": warn_data["summary"]["total_warning_count"],
        "high_risk_count": warn_data["summary"]["high_risk_count"],
        "warning_count": warn_data["summary"]["warning_count"],
        "top_concerns": warn_data["summary"]["top_concerns"],
    }

    return {
        **payload,
        "market_risk_actionable": market_risk_actionable,
        "risk_context": risk_context,
        "overall_severity": overall_severity,
        "overall_severity_text": overall_severity_text,
        "portfolio_daily_var_95": return_metrics.get("daily_var_95"),
        "portfolio_daily_cvar_95": return_metrics.get("daily_cvar_95"),
        "portfolio_downside_volatility": return_metrics.get("downside_volatility"),
        "market_risk": market_risk,
        "permanent_loss_risk": permanent_loss_risk_summary,
        "symbol_risk": symbol_risk,
        "risk_summary": risk_summary,
        "warnings": warn_data["warnings"],
    }
