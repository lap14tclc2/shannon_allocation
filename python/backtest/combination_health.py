"""Fast, research-only diagnostics for a user-owned stock combination.

This module deliberately does NOT choose a portfolio and does NOT optimize timing.
It answers whether a fixed combination is statistically healthy enough to justify
running the expensive allocation optimizer, and can offer optional diversification
suggestions that the user must explicitly apply.

Leakage rule: the last ``holdout_days`` sessions are never inspected. Health and
suggestions use only the research sample before that global holdout.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .config import BacktestParams
from .erc import ERCError, solve_erc


SHORT_CORR_DAYS = 63
LONG_CORR_DAYS = 252
HIGH_CORR = 0.75
VERY_HIGH_CORR = 0.85


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _max_drawdown_from_log_returns(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return 0.0
    wealth = np.exp(np.cumsum(returns))
    peaks = np.maximum.accumulate(wealth)
    dd = wealth / np.maximum(peaks, 1e-12) - 1.0
    return float(np.min(dd))


def _aligned_prices(frame: pd.DataFrame, symbols: list[str], lookback: int) -> pd.DataFrame:
    aligned = frame[symbols].dropna(how="any")
    if len(aligned) > lookback + 1:
        aligned = aligned.iloc[-(lookback + 1):]
    return aligned


def _returns(frame: pd.DataFrame, symbols: list[str], lookback: int) -> pd.DataFrame:
    aligned = _aligned_prices(frame, symbols, lookback)
    if len(aligned) < 3:
        return pd.DataFrame(columns=symbols)
    values = aligned.to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        arr = np.log(values[1:] / values[:-1])
    out = pd.DataFrame(arr, index=aligned.index[1:], columns=symbols)
    return out.replace([np.inf, -np.inf], np.nan).dropna(how="any")


def _pair_rows(short_corr: pd.DataFrame, long_corr: pd.DataFrame, symbols: list[str]) -> list[dict]:
    rows: list[dict] = []
    for i, a in enumerate(symbols):
        for b in symbols[i + 1:]:
            c63 = None
            c252 = None
            if a in short_corr.index and b in short_corr.columns:
                value = short_corr.loc[a, b]
                if pd.notna(value):
                    c63 = float(value)
            if a in long_corr.index and b in long_corr.columns:
                value = long_corr.loc[a, b]
                if pd.notna(value):
                    c252 = float(value)
            available = [v for v in (c63, c252) if v is not None and math.isfinite(v)]
            risk_corr = max(available) if available else None
            rows.append(
                {
                    "a": a,
                    "b": b,
                    "corr_63d": round(c63, 4) if c63 is not None else None,
                    "corr_252d": round(c252, 4) if c252 is not None else None,
                    "risk_corr": round(risk_corr, 4) if risk_corr is not None else None,
                }
            )
    return rows


def _components(symbols: list[str], pairs: list[dict], threshold: float = HIGH_CORR) -> list[list[str]]:
    graph = {s: set() for s in symbols}
    for row in pairs:
        corr = row.get("risk_corr")
        if corr is not None and corr >= threshold:
            graph[row["a"]].add(row["b"])
            graph[row["b"]].add(row["a"])
    seen: set[str] = set()
    groups: list[list[str]] = []
    for start in symbols:
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        group: list[str] = []
        while stack:
            node = stack.pop()
            group.append(node)
            for nxt in graph[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        groups.append(sorted(group))
    return sorted(groups, key=lambda g: (-len(g), g))


def _baseline_metrics(long_returns: pd.DataFrame) -> dict:
    if long_returns.empty:
        return {
            "equal_weight_return_pct": None,
            "equal_weight_volatility_pct": None,
            "equal_weight_sharpe": None,
            "equal_weight_mdd_pct": None,
            "diversification_ratio": None,
        }
    values = long_returns.to_numpy(dtype=float)
    n = values.shape[1]
    weights = np.full(n, 1.0 / n)
    portfolio = values @ weights
    mean = float(np.mean(portfolio))
    std = float(np.std(portfolio, ddof=1)) if len(portfolio) > 1 else 0.0
    ann_return = math.exp(mean * 252.0) - 1.0
    ann_vol = std * math.sqrt(252.0)
    sharpe = mean / std * math.sqrt(252.0) if std > 1e-12 else 0.0
    mdd = _max_drawdown_from_log_returns(portfolio)

    asset_vol = np.std(values, axis=0, ddof=1) * math.sqrt(252.0) if len(values) > 1 else np.zeros(n)
    cov = np.cov(values, rowvar=False, ddof=1) * 252.0 if len(values) > 1 else np.zeros((n, n))
    cov = np.atleast_2d(np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0))
    pvol = math.sqrt(max(float(weights @ cov @ weights), 0.0))
    weighted_asset_vol = float(weights @ asset_vol)
    div_ratio = weighted_asset_vol / pvol if pvol > 1e-12 else None

    return {
        "equal_weight_return_pct": round(ann_return * 100.0, 3),
        "equal_weight_volatility_pct": round(ann_vol * 100.0, 3),
        "equal_weight_sharpe": round(sharpe, 4),
        "equal_weight_mdd_pct": round(mdd * 100.0, 3),
        "diversification_ratio": round(float(div_ratio), 4) if div_ratio is not None else None,
    }


def _snapshot(
    research: pd.DataFrame,
    symbols: list[str],
    params: BacktestParams,
    solve_erc_flag: bool = True,
) -> dict:
    short_returns = _returns(research, symbols, SHORT_CORR_DAYS)
    long_returns = _returns(research, symbols, LONG_CORR_DAYS)
    short_corr = short_returns.corr() if not short_returns.empty else pd.DataFrame()
    long_corr = long_returns.corr() if not long_returns.empty else pd.DataFrame()
    pairs = _pair_rows(short_corr, long_corr, symbols)
    valid_corrs = [float(p["risk_corr"]) for p in pairs if p.get("risk_corr") is not None]
    high = [p for p in pairs if p.get("risk_corr") is not None and p["risk_corr"] >= HIGH_CORR]
    very_high = [p for p in pairs if p.get("risk_corr") is not None and p["risk_corr"] >= VERY_HIGH_CORR]
    groups = _components(symbols, pairs)
    baseline = _baseline_metrics(long_returns)

    erc_feasible = False
    erc_error = None
    erc_weights = None
    erc_portfolio_volatility_pct = None
    if solve_erc_flag and len(long_returns) >= params.minimum_observations:
        try:
            solved = solve_erc(long_returns.to_numpy(dtype=float), params)
            erc_feasible = True
            erc_weights = {s: round(float(w), 6) for s, w in zip(symbols, solved.weights.tolist())}
            erc_portfolio_volatility_pct = round(float(solved.portfolio_risk) * 100.0, 3)
        except ERCError as exc:
            erc_error = str(exc)

    return {
        "short_observations": int(len(short_returns)),
        "long_observations": int(len(long_returns)),
        "average_correlation": round(float(np.mean(valid_corrs)), 4) if valid_corrs else None,
        "max_correlation": round(float(np.max(valid_corrs)), 4) if valid_corrs else None,
        "high_correlation_pairs": sorted(high, key=lambda p: p["risk_corr"], reverse=True),
        "very_high_correlation_pairs": sorted(very_high, key=lambda p: p["risk_corr"], reverse=True),
        "high_pair_ratio": round(len(high) / max(1, len(pairs)), 4),
        "clusters": [g for g in groups if len(g) > 1],
        "largest_cluster_size": max((len(g) for g in groups), default=0),
        "erc_feasible": erc_feasible,
        "erc_error": erc_error,
        "erc_weights": erc_weights,
        "erc_portfolio_volatility_pct": erc_portfolio_volatility_pct,
        **baseline,
    }


def _data_quality(research: pd.DataFrame, symbols: list[str]) -> tuple[list[dict], float]:
    rows = []
    for symbol in symbols:
        series = research[symbol].dropna()
        recent = research[symbol].iloc[-LONG_CORR_DAYS:].notna().mean() if len(research) else 0.0
        rows.append(
            {
                "symbol": symbol,
                "observations": int(len(series)),
                "history_years": round(len(series) / 252.0, 2),
                "research_coverage": round(len(series) / max(1, len(research)), 4),
                "recent_252d_coverage": round(float(recent), 4),
                "first_date": str(series.index[0].date()) if len(series) else None,
                "last_date": str(series.index[-1].date()) if len(series) else None,
            }
        )
    min_recent = min((r["recent_252d_coverage"] for r in rows), default=0.0)
    return rows, min_recent


def _health_score(snapshot: dict, min_recent_coverage: float) -> dict:
    avg_corr = snapshot.get("average_correlation")
    high_ratio = snapshot.get("high_pair_ratio") or 0.0
    div = snapshot.get("diversification_ratio")
    long_obs = snapshot.get("long_observations") or 0

    data_score = _clip(100.0 * min(min_recent_coverage, long_obs / LONG_CORR_DAYS), 0.0, 100.0)
    if avg_corr is None:
        correlation_score = 0.0
    else:
        correlation_score = _clip(
            100.0 - max(0.0, avg_corr - 0.25) * 110.0 - high_ratio * 35.0,
            0.0,
            100.0,
        )
    diversification_score = 0.0 if div is None else _clip(50.0 + (div - 1.0) * 70.0, 0.0, 100.0)
    erc_score = 100.0 if snapshot.get("erc_feasible") else 0.0
    overall = 0.30 * data_score + 0.30 * correlation_score + 0.25 * diversification_score + 0.15 * erc_score
    return {
        "overall": round(overall, 1),
        "data_quality": round(data_score, 1),
        "correlation": round(correlation_score, 1),
        "diversification": round(diversification_score, 1),
        "erc_feasibility": round(erc_score, 1),
    }


def _status(snapshot: dict, data_rows: list[dict], params: BacktestParams) -> tuple[str, list[str]]:
    invalid: list[str] = []
    if snapshot.get("long_observations", 0) < params.minimum_observations:
        invalid.append(
            f"Only {snapshot.get('long_observations', 0)} common return observations; "
            f"ERC requires at least {params.minimum_observations}."
        )
    if any(r["recent_252d_coverage"] < 0.75 for r in data_rows):
        weak = [r["symbol"] for r in data_rows if r["recent_252d_coverage"] < 0.75]
        invalid.append("Insufficient recent data coverage: " + ", ".join(weak))
    if not snapshot.get("erc_feasible"):
        invalid.append("ERC feasibility check failed on the research-only 252D window.")
    if invalid:
        return "invalid", invalid

    warnings: list[str] = []
    avg = snapshot.get("average_correlation")
    if avg is not None and avg >= 0.60:
        warnings.append(f"Average conservative correlation is high ({avg:.2f}).")
    if (snapshot.get("high_pair_ratio") or 0.0) >= 0.25:
        warnings.append("At least 25% of symbol pairs have conservative correlation >= 0.75.")
    if snapshot.get("largest_cluster_size", 0) > max(2, len(data_rows) // 2):
        warnings.append("More than half of the portfolio sits in one high-correlation cluster.")
    div = snapshot.get("diversification_ratio")
    if div is not None and div < 1.20:
        warnings.append(f"Diversification ratio is weak ({div:.2f}).")
    if snapshot.get("long_observations", 0) < 126:
        warnings.append("Common aligned history is shorter than half a trading year.")
    return ("warning", warnings) if warnings else ("healthy", [])


def _candidate_quality_ok(current: dict, proposed: dict) -> bool:
    current_ret = current.get("equal_weight_return_pct")
    proposed_ret = proposed.get("equal_weight_return_pct")
    current_sharpe = current.get("equal_weight_sharpe")
    proposed_sharpe = proposed.get("equal_weight_sharpe")
    if current_ret is None or proposed_ret is None:
        return False
    if current_sharpe is None or proposed_sharpe is None:
        return proposed_ret >= current_ret - 5.0
    return not (proposed_ret < current_ret - 5.0 and proposed_sharpe < current_sharpe - 0.10)


def _suggestions(
    research: pd.DataFrame,
    symbols: list[str],
    available_symbols: list[str],
    params: BacktestParams,
    current: dict,
    limit: int,
) -> list[dict]:
    recent = research.iloc[-LONG_CORR_DAYS:]
    eligible = []
    selected = set(symbols)
    for symbol in available_symbols:
        if symbol in selected or symbol not in research.columns:
            continue
        coverage = float(recent[symbol].notna().mean()) if len(recent) else 0.0
        if coverage >= 0.95 and int(research[symbol].notna().sum()) >= params.minimum_observations + 1:
            eligible.append(symbol)

    scored: list[tuple[float, str, str, dict]] = []
    cur_avg = current.get("average_correlation")
    cur_div = current.get("diversification_ratio")
    cur_cluster = current.get("largest_cluster_size", 0)
    cur_sharpe = current.get("equal_weight_sharpe") or 0.0
    if cur_avg is None or cur_div is None:
        return []

    for remove in symbols:
        base = [s for s in symbols if s != remove]
        for add in eligible:
            proposed_symbols = sorted(base + [add])
            snap = _snapshot(research, proposed_symbols, params, solve_erc_flag=False)
            new_avg = snap.get("average_correlation")
            new_div = snap.get("diversification_ratio")
            if new_avg is None or new_div is None or snap.get("long_observations", 0) < params.minimum_observations:
                continue
            corr_gain = cur_avg - new_avg
            div_gain = new_div - cur_div
            cluster_gain = cur_cluster - snap.get("largest_cluster_size", 0)
            sharpe_gain = (snap.get("equal_weight_sharpe") or 0.0) - cur_sharpe
            if corr_gain < 0.02 and div_gain < 0.05 and cluster_gain <= 0:
                continue
            if not _candidate_quality_ok(current, snap):
                continue
            score = (
                corr_gain * 100.0
                + div_gain * 15.0
                + max(0, cluster_gain) * 4.0
                + _clip(sharpe_gain, -1.0, 1.0) * 2.0
            )
            scored.append((score, remove, add, snap))

    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for _score, remove, add, _cheap in scored:
        proposed_symbols = sorted([s for s in symbols if s != remove] + [add])
        deep = _snapshot(research, proposed_symbols, params, solve_erc_flag=True)
        if not deep.get("erc_feasible"):
            continue
        reasons = []
        corr_gain = cur_avg - float(deep.get("average_correlation") or cur_avg)
        div_gain = float(deep.get("diversification_ratio") or cur_div) - cur_div
        cluster_gain = cur_cluster - deep.get("largest_cluster_size", cur_cluster)
        if corr_gain > 0:
            reasons.append(f"average correlation improves by {corr_gain:.2f}")
        if div_gain > 0:
            reasons.append(f"diversification ratio improves by {div_gain:.2f}")
        if cluster_gain > 0:
            reasons.append(f"largest high-correlation cluster shrinks by {cluster_gain}")
        out.append(
            {
                "remove": remove,
                "add": add,
                "symbols": proposed_symbols,
                "reasons": reasons,
                "before": {
                    "average_correlation": current.get("average_correlation"),
                    "max_correlation": current.get("max_correlation"),
                    "diversification_ratio": current.get("diversification_ratio"),
                    "largest_cluster_size": current.get("largest_cluster_size"),
                    "equal_weight_return_pct": current.get("equal_weight_return_pct"),
                    "equal_weight_sharpe": current.get("equal_weight_sharpe"),
                },
                "after": {
                    "average_correlation": deep.get("average_correlation"),
                    "max_correlation": deep.get("max_correlation"),
                    "diversification_ratio": deep.get("diversification_ratio"),
                    "largest_cluster_size": deep.get("largest_cluster_size"),
                    "equal_weight_return_pct": deep.get("equal_weight_return_pct"),
                    "equal_weight_sharpe": deep.get("equal_weight_sharpe"),
                    "erc_portfolio_volatility_pct": deep.get("erc_portfolio_volatility_pct"),
                },
            }
        )
        if len(out) >= max(0, int(limit)):
            break
    return out


def analyze_combination_health(
    prices: pd.DataFrame,
    symbols: list[str],
    params: BacktestParams | None = None,
    available_symbols: list[str] | None = None,
    holdout_days: int = 252,
    include_suggestions: bool = True,
    suggestion_limit: int = 5,
) -> dict:
    """Analyze a fixed combination without inspecting the final holdout."""
    params = params or BacktestParams()
    symbols = sorted(dict.fromkeys(str(s).upper() for s in symbols))
    if not symbols:
        raise ValueError("No symbols supplied.")
    missing = [s for s in symbols if s not in prices.columns]
    if missing:
        raise ValueError(f"Symbols not in price panel: {missing}")
    if holdout_days < 1 or len(prices) <= holdout_days + params.minimum_observations + 1:
        raise ValueError("Not enough history to reserve the untouched holdout and run health diagnostics.")

    research = prices.iloc[:-holdout_days].copy()
    holdout = prices.iloc[-holdout_days:]
    data_rows, min_recent = _data_quality(research, symbols)
    snap = _snapshot(research, symbols, params, solve_erc_flag=True)
    status, reasons = _status(snap, data_rows, params)
    scores = _health_score(snap, min_recent)

    suggestions = []
    if include_suggestions and status != "invalid":
        suggestions = _suggestions(
            research,
            symbols,
            available_symbols or list(prices.columns),
            params,
            snap,
            suggestion_limit,
        )

    return {
        "symbols": symbols,
        "status": status,
        "reasons": reasons,
        "score": scores,
        "research_only": True,
        "research_start": str(research.index[0].date()),
        "research_end": str(research.index[-1].date()),
        "reserved_holdout": {
            "start": str(holdout.index[0].date()),
            "end": str(holdout.index[-1].date()),
            "trading_days": int(len(holdout)),
            "used_for_health_or_suggestions": False,
        },
        "data_quality": data_rows,
        "correlation": {
            "short_window_days": SHORT_CORR_DAYS,
            "long_window_days": LONG_CORR_DAYS,
            "pair_policy": "max(63D,252D)",
            "average": snap.get("average_correlation"),
            "maximum": snap.get("max_correlation"),
            "high_pair_ratio": snap.get("high_pair_ratio"),
            "high_pairs": snap.get("high_correlation_pairs"),
            "very_high_pairs": snap.get("very_high_correlation_pairs"),
            "clusters": snap.get("clusters"),
            "largest_cluster_size": snap.get("largest_cluster_size"),
        },
        "diversification": {
            "ratio": snap.get("diversification_ratio"),
            "equal_weight_return_pct": snap.get("equal_weight_return_pct"),
            "equal_weight_volatility_pct": snap.get("equal_weight_volatility_pct"),
            "equal_weight_sharpe": snap.get("equal_weight_sharpe"),
            "equal_weight_mdd_pct": snap.get("equal_weight_mdd_pct"),
            "note": "Research-only 252D equal-weight diagnostic; not a forecast and not the Shannon/ERC strategy result.",
        },
        "erc": {
            "feasible": snap.get("erc_feasible"),
            "error": snap.get("erc_error"),
            "weights": snap.get("erc_weights"),
            "portfolio_volatility_pct": snap.get("erc_portfolio_volatility_pct"),
            "observations": snap.get("long_observations"),
        },
        "suggestions": suggestions,
    }
