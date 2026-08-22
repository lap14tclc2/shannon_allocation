"""Robustness tests for finalists: timing neighbourhood, symbol neighbourhood, concentration.

These turn a single historical result into a robustness statement: broad
plateaus are rewarded, narrow spikes and single-stock/year dependencies are
penalised.
"""

from __future__ import annotations

import random
from statistics import median

from ..candidate import Candidate, MAX_SYMBOLS, MIN_SYMBOLS, random_candidate, repair_allocation_days


def timing_neighbourhood(
    candidate: Candidate,
    eval_fn,
    radius: int = 5,
    min_gap: int = 40,
    max_day: int = 252,
    value_key: str = "net_twr_annualized_pct",
):
    """Backtest every Ti +/- 1..radius schedule; return stats + spike detection.

    `eval_fn` may return a plain metrics dict (value_key = 'net_twr_annualized_pct')
    or a walk-forward robust dict (value_key = 'robust_return'). The latter measures
    neighbourhood stability from OOS robust scores, which is what the ranking
    actually selected on — a single-window spike test cannot.
    """
    results = []
    base = candidate.allocation_days
    seen = set()
    for i in range(4):
        for delta in range(-radius, radius + 1):
            if delta == 0:
                continue
            days = list(base)
            days[i] = days[i] + delta
            repaired = repair_allocation_days(days, min_gap, max_day)
            if repaired is None:
                continue
            nb = Candidate(candidate.symbols, repaired)
            if nb.key() in seen:
                continue
            seen.add(nb.key())
            m = eval_fn(nb)
            if m is None or m.get("error"):
                continue
            val = m.get(value_key)
            if val is None:
                continue
            results.append({"candidate": nb, value_key: val, "metrics": m})
    vals = [r[value_key] for r in results]
    mean = sum(vals) / len(vals) if vals else 0.0
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1) if len(vals) > 1 else 0.0
    spike = bool(results) and max(vals) - median(vals) > max(2.0, 2.0 * (var ** 0.5))
    return {
        "n_neighbours": len(results),
        "mean": round(mean, 3),
        "median": round(median(vals), 3) if vals else None,
        "std": round(var ** 0.5, 3),
        "max": round(max(vals), 3) if vals else None,
        "min": round(min(vals), 3) if vals else None,
        "isolated_spike": spike,
        "neighbours": results,
    }


def symbol_neighbourhood(candidate: Candidate, universe, eval_fn, rng: random.Random, replacements: int = 1):
    """Replace one stock at a time with a random eligible stock; measure degradation."""
    results = []
    base_syms = list(candidate.symbols)
    for i in range(len(base_syms)):
        pool = [s for s in universe if s not in base_syms]
        if not pool:
            continue
        for _ in range(replacements):
            replacement = rng.choice(pool)
            syms = base_syms.copy()
            syms[i] = replacement
            nb = Candidate(tuple(sorted(syms)), candidate.allocation_days)
            m = eval_fn(nb)
            if m is not None and not m.get("error"):
                results.append(
                    {
                        "candidate": nb,
                        "replaced": base_syms[i],
                        "with": replacement,
                        "net_twr_ann": m["net_twr_annualized_pct"],
                        "metrics": m,
                    }
                )
    vals = [r["net_twr_ann"] for r in results]
    mean = sum(vals) / len(vals) if vals else 0.0
    return {
        "n_neighbours": len(results),
        "mean": round(mean, 3),
        "median": round(median(vals), 3) if vals else None,
        "std": round((sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5, 3) if len(vals) > 1 else 0.0,
        "results": results,
    }


def concentration(metrics: dict) -> dict:
    """Detect single-stock / single-year / single-event dependence."""
    out = {"single_stock": False, "single_year": False, "details": {}}
    contrib = metrics.get("stock_contributions") or {}
    total = sum(contrib.values())
    if total and contrib:
        largest = max(contrib.values())
        out["single_stock"] = largest / total > 0.5
        out["details"]["largest_stock_share"] = round(largest / total, 3)
        out["details"]["largest_stock"] = max(contrib, key=contrib.get)
    annual = metrics.get("annual_returns") or {}
    if len(annual) >= 2:
        best = max(annual.values())
        out["single_year"] = best > 8.0 and best > 1.5 * max((v for v in annual.values() if v != best), default=0.0)
    return out