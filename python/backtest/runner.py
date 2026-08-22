"""Generate random symbol combinations and run the backtest for each."""

from __future__ import annotations

import random

import pandas as pd

from .config import BacktestParams
from .simulation import SimulationResult, simulate_combination


def generate_combinations(symbols: list[str], params: BacktestParams) -> list[list[str]]:
    rng = random.Random(params.seed)
    combos: set[tuple[str, ...]] = set()
    attempts = 0
    max_attempts = params.num_combinations * 100 + 1000
    while len(combos) < params.num_combinations and attempts < max_attempts:
        attempts += 1
        if params.portfolio_size is not None:
            n = int(params.portfolio_size)
            if n < 1 or n > len(symbols):
                raise ValueError(f"portfolio_size={n} outside available symbol range 1..{len(symbols)}")
        else:
            n = rng.randint(params.min_symbols, min(params.max_symbols, len(symbols)))
        combo = tuple(sorted(rng.sample(symbols, n)))
        combos.add(combo)
    return [list(c) for c in sorted(combos)]


def run_combinations(
    combos: list[list[str]],
    prices: pd.DataFrame,
    params: BacktestParams,
    progress: bool = True,
) -> list[SimulationResult]:
    results: list[SimulationResult] = []
    total = len(combos)
    for i, combo in enumerate(combos, 1):
        if progress:
            print(f"  [{i}/{total}] simulating {len(combo)} symbols: {' '.join(combo)}", flush=True)
        results.append(simulate_combination(combo, prices, params))
    return results


def ranking_rows(results: list[SimulationResult]) -> list[dict]:
    rows = []
    for r in results:
        rows.append(
            {
                "rank": 0,
                "symbols": " ".join(r.symbols),
                "slug": "_".join(r.symbols),
                "n_symbols": len(r.symbols),
                "n_allocations": len(r.allocations),
                "score": round(r.score, 2),
                "final_nav": round(r.final_nav, 0),
                "total_deposits": round(r.total_deposits, 0),
                "absolute_profit": round(r.absolute_profit, 0),
                "total_return_pct": round(r.total_return_pct, 2),
                "twr_pct": round(r.twr, 2),
                "twr_annualized_pct": round(r.twr_annualized, 2),
                "xirr_pct": round(r.xirr, 2),
                "cagr_pct": round(r.cagr_pct, 2),
                "ann_volatility_pct": round(r.annualized_volatility_pct, 2),
                "sharpe": round(r.sharpe, 3),
                "sortino": round(r.sortino, 3),
                "calmar": round(r.calmar, 3),
                "max_drawdown_pct": round(r.max_drawdown_pct, 2),
                "cdar95_pct": round(r.cdar95_pct, 2),
                "underwater_ratio": round(r.underwater_ratio, 3),
                "max_underwater_days": r.max_underwater_days,
                "min_equity_exposure": round(r.min_equity_exposure, 3),
                "avg_equity_exposure": round(r.avg_equity_exposure, 3),
                "worst_year": round(r.worst_year, 2),
                "positive_year_ratio": round(r.positive_year_ratio, 3),
                "turnover_pct": round(r.turnover, 1),
                "trade_count": r.trade_count,
                "first_allocation_date": r.first_allocation_date,
                "error": r.error,
            }
        )
    return rows


def _pctiles(values, probs=(0.10, 0.25, 0.50, 0.75, 0.90)):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    vals = sorted(vals)
    out = {}
    for p in probs:
        k = (len(vals) - 1) * p
        lo = int(k)
        hi = min(lo + 1, len(vals) - 1)
        frac = k - lo
        out[f"p{int(p * 100)}"] = round(vals[lo] + frac * (vals[hi] - vals[lo]), 3)
    return out


def aggregate_stats(results: list[SimulationResult]) -> dict:
    """Cross-portfolio statistics: percentiles, by portfolio size, per-symbol."""
    ok = [r for r in results if not r.error]
    out: dict = {
        "n_total": len(results),
        "n_success": len(ok),
        "summary": {
            "final_nav": _pctiles([r.final_nav for r in ok]),
            "twr_annualized_pct": _pctiles([r.twr_annualized for r in ok]),
            "xirr_pct": _pctiles([r.xirr for r in ok]),
            "sharpe": _pctiles([r.sharpe for r in ok]),
            "sortino": _pctiles([r.sortino for r in ok]),
            "max_drawdown_pct": _pctiles([r.max_drawdown_pct for r in ok]),
            "cdar95_pct": _pctiles([r.cdar95_pct for r in ok]),
            "score": _pctiles([r.score for r in ok]),
        },
    }

    by_n = {}
    for r in ok:
        by_n.setdefault(len(r.symbols), []).append(r)
    out["by_n"] = {
        str(n): {
            "count": len(grp),
            "avg_cagr_pct": round(sum(x.twr_annualized for x in grp) / len(grp), 2),
            "avg_sharpe": round(sum(x.sharpe for x in grp) / len(grp), 3),
            "avg_sortino": round(sum(x.sortino for x in grp) / len(grp), 3),
            "avg_mdd_pct": round(sum(x.max_drawdown_pct for x in grp) / len(grp), 2),
            "avg_cdar95_pct": round(sum(x.cdar95_pct for x in grp) / len(grp), 2),
            "avg_score": round(sum(x.score for x in grp) / len(grp), 2),
        }
        for n, grp in sorted(by_n.items())
    }

    sym_stats = {}
    for r in ok:
        for s in r.symbols:
            sym_stats.setdefault(s, []).append(r)
    out["per_symbol"] = {
        s: {
            "appearances": len(grp),
            "avg_twr_annualized_pct": round(sum(x.twr_annualized for x in grp) / len(grp), 2),
            "avg_sharpe": round(sum(x.sharpe for x in grp) / len(grp), 3),
            "avg_score": round(sum(x.score for x in grp) / len(grp), 2),
        }
        for s, grp in sorted(sym_stats.items(), key=lambda kv: -sum(x.score for x in kv[1]))
    }

    ok_sorted = sorted(ok, key=lambda r: r.score, reverse=True)
    out["top_by_score"] = [list(r.symbols) for r in ok_sorted[:10]]
    out["bottom_by_score"] = [list(r.symbols) for r in ok_sorted[-10:]]
    return out
