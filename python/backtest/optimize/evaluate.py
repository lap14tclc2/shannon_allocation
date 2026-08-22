"""Candidate evaluation: run the backtest for a candidate, extract objectives, cache.

The evaluator is the single point that maps a Candidate (+ optional date window)
to a metrics dict used by NSGA-II, random search, walk-forward and robustness.

NET performance (after transaction costs) is always used for optimization.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os

import pandas as pd

from ..config import BacktestParams
from ..simulation import simulate_combination
from ..candidate import Candidate, schedule_for_window


def config_fingerprint(params: BacktestParams, data_version: str = "v1") -> str:
    """Fingerprint of every quant-affecting parameter (so cached results are safe)."""
    keys = [
        "price_scale",
        "initial_balance",
        "annual_deposit",
        "deposit_at_start_year",
        "annualization_factor",
        "minimum_observations",
        "lookback_days",
        "normal_band",
        "soft_band",
        "fractional_shares",
        "rebalance_every_days",
        "execution_lag",
        "fee_buy_bps",
        "fee_sell_bps",
        "tax_sell_bps",
        "slippage_bps",
    ]
    payload = {k: getattr(params, k) for k in keys}
    raw = json.dumps(payload, sort_keys=True) + "|" + data_version
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def result_metrics(result) -> dict:
    """Extract the scalar metrics that define the objective vector (all NET)."""
    return {
        "net_twr_annualized_pct": result.twr_annualized,
        "net_xirr_pct": result.xirr,
        "sharpe": result.sharpe,
        "sortino": result.sortino,
        "calmar": result.calmar,
        "max_drawdown_pct": result.max_drawdown_pct,
        "turnover_pct": result.turnover,
        "cost_pct_of_nav": result.cost_pct_of_nav,
        "transaction_cost": result.transaction_cost,
        "trade_count": result.trade_count,
        "gross_twr_annualized_pct": result.gross_twr_annualized,
        "gross_xirr_pct": result.gross_xirr,
        "worst_year": result.worst_year,
        "positive_year_ratio": result.positive_year_ratio,
        "annual_returns": result.annual_returns,
        "stock_contributions": result.stock_contributions,
        "final_nav": result.final_nav,
        "n_allocations": len(result.allocations),
        "first_allocation_date": result.first_allocation_date,
        "error": result.error,
    }


class EvaluationCache:
    """In-memory + JSON-file cache keyed by candidate, window and config fingerprint."""

    def __init__(self, path: str | None = None):
        self._mem: dict[str, dict] = {}
        self.path = path
        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    self._mem = json.load(fh)
            except Exception:
                self._mem = {}

    def _key(self, candidate: Candidate, window: str, cfg: str) -> str:
        return f"{cfg}|{window}|{candidate.key()}"

    def get(self, candidate, window, cfg):
        return self._mem.get(self._key(candidate, window, cfg))

    def put(self, candidate, window, cfg, metrics):
        self._mem[self._key(candidate, window, cfg)] = metrics

    def flush(self):
        if self.path:
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self._mem, fh)


def evaluate_candidate(
    candidate: Candidate,
    prices: pd.DataFrame,
    params: BacktestParams,
    all_dates,
    window: tuple[str | None, str | None] = (None, None),
    cache: EvaluationCache | None = None,
    cfg: str = "",
) -> dict:
    """Run (or fetch from cache) the backtest for `candidate` over a date window.

    Returns the metrics dict. window = (start_date, end_date) strings or None.
    """
    start, end = window
    key = f"{start or ''}|{end or ''}"
    if cache:
        hit = cache.get(candidate, key, cfg)
        if hit is not None:
            return hit

    alloc_dates = schedule_for_window(candidate, all_dates)
    run_params = dataclasses.replace(params, start_date=start, end_date=end)
    result = simulate_combination(
        list(candidate.symbols),
        prices,
        run_params,
        allocation_dates=alloc_dates,
    )
    metrics = result_metrics(result)

    if cache:
        cache.put(candidate, key, cfg, metrics)
    return metrics


def objectives(metrics: dict) -> list[float]:
    """Objective vector for NSGA-II (all maximised).

    maximise: net TWR annualized, Sharpe, Sortino, Calmar, MDD (less negative)
    minimise (negated): turnover, transaction cost, instability
    """
    instability = _instability(metrics)
    return [
        metrics.get("net_twr_annualized_pct", 0.0),
        metrics.get("sharpe", 0.0),
        metrics.get("sortino", 0.0),
        metrics.get("calmar", 0.0),
        metrics.get("max_drawdown_pct", 0.0),           # maximise (closer to 0 better)
        -metrics.get("turnover_pct", 0.0),
        -metrics.get("cost_pct_of_nav", 0.0),
        -instability,
    ]


OBJECTIVE_NAMES = [
    "net_twr_ann",
    "sharpe",
    "sortino",
    "calmar",
    "mdd",
    "turnover",
    "cost",
    "instability",
]


def _instability(metrics: dict) -> float:
    """Proxy for single-period instability: std of annual returns (or 0)."""
    annual = metrics.get("annual_returns") or {}
    vals = [v for v in annual.values()]
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    return float(var ** 0.5)