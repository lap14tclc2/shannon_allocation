"""Persist a backtest run so a future web page can consume it.

Layout (stable schema):

    <output_dir>/runs/<run_id>/
        meta.json                        # run parameters + timestamp
        index.json                       # ranking board (one summary row per combination, by score)
        stats.json                       # cross-portfolio aggregate statistics
        combinations/<SLUG>.json         # full detail per combination (nav + allocations + metrics)
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from .config import BacktestParams
from .runner import ranking_rows, aggregate_stats
from .simulation import SimulationResult


def slug(symbols) -> str:
    return "_".join(sorted(symbols))


def _summary(results: list[SimulationResult]) -> list[dict]:
    rows = ranking_rows(results)
    ok = [r for r in rows if not r["error"]]
    ok.sort(key=lambda r: r["score"], reverse=True)
    for i, r in enumerate(ok, 1):
        r["rank"] = i
    return ok + [r for r in rows if r["error"]]


def save_run(
    params: BacktestParams,
    results: list[SimulationResult],
    output_dir: str,
    run_id: str | None = None,
) -> str:
    """Write the run artifacts and return the run directory path."""
    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(output_dir, "runs", run_id)
    combo_dir = os.path.join(base, "combinations")
    os.makedirs(combo_dir, exist_ok=True)

    meta = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "params": params.as_dict(),
    }
    with open(os.path.join(base, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    summaries = _summary(results)
    with open(os.path.join(base, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"run_id": run_id, "combinations": summaries}, fh, indent=2, ensure_ascii=False)

    stats = aggregate_stats(results)
    with open(os.path.join(base, "stats.json"), "w", encoding="utf-8") as fh:
        json.dump({"run_id": run_id, "stats": stats}, fh, indent=2, ensure_ascii=False)

    for r in results:
        if r.error:
            combo = {
                "symbols": list(r.symbols),
                "error": r.error,
            }
        else:
            combo = {
                "symbols": list(r.symbols),
                "final_nav": round(r.final_nav, 2),
                "total_deposits": round(r.total_deposits, 2),
                "absolute_profit": round(r.absolute_profit, 2),
                "total_return_pct": round(r.total_return_pct, 6),
                "twr_pct": round(r.twr, 6),
                "twr_annualized_pct": round(r.twr_annualized, 6),
                "xirr_pct": round(r.xirr, 6),
                "cagr_pct": round(r.cagr_pct, 6),
                "annualized_volatility_pct": round(r.annualized_volatility_pct, 6),
                "sharpe": round(r.sharpe, 6),
                "sortino": round(r.sortino, 6),
                "calmar": round(r.calmar, 6),
                "max_drawdown_pct": round(r.max_drawdown_pct, 6),
                "worst_year": round(r.worst_year, 6),
                "positive_year_ratio": round(r.positive_year_ratio, 6),
                "turnover_pct": round(r.turnover, 3),
                "trade_count": r.trade_count,
                "score": round(r.score, 6),
                "first_allocation_date": r.first_allocation_date,
                "annual_returns": {str(y): v for y, v in r.annual_returns.items()},
                "nav_history": [[d, v] for d, v in r.nav_history],
                "allocations": r.allocations,
            }
        with open(os.path.join(combo_dir, f"{slug(r.symbols)}.json"), "w", encoding="utf-8") as fh:
            json.dump(combo, fh, indent=2, ensure_ascii=False)

    return base
