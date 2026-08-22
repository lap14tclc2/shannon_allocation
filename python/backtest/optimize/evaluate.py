"""Candidate evaluation: run backtest, extract metrics, cache, map to objectives.

The optimizer is now growth-first: TRAIN search rewards return and risk-adjusted
growth, while drawdown/CDaR are enforced later as rolling OOS/final risk gates.
ERC, Shannon, transaction costs and risk-overlay mechanics are unchanged.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os

import pandas as pd

from ..config import BacktestParams
from ..simulation import simulate_combination
from ..candidate import Candidate, resolve_allocation_dates, schedule_for_window


def config_fingerprint(params: BacktestParams, data_version: str = "v1") -> str:
    """Fingerprint every quant-affecting parameter so cached results are safe."""
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
        "risk_overlay_enabled",
        "target_volatility",
        "risk_fast_lookback",
        "risk_slow_lookback",
        "risk_refresh_days",
        "min_equity_exposure",
        "risk_missing_data_exposure",
        "max_position_weight",
    ]
    payload = {k: getattr(params, k) for k in keys}
    raw = json.dumps(payload, sort_keys=True) + "|" + data_version
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def result_metrics(result) -> dict:
    """Extract scalar NET metrics used by optimization/validation/reporting."""
    return {
        "net_twr_annualized_pct": result.twr_annualized,
        "net_xirr_pct": result.xirr,
        "sharpe": result.sharpe,
        "sortino": result.sortino,
        "calmar": result.calmar,
        "max_drawdown_pct": result.max_drawdown_pct,
        "cdar95_pct": result.cdar95_pct,
        "underwater_ratio": result.underwater_ratio,
        "max_underwater_days": result.max_underwater_days,
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
        "measurement_start_date": result.measurement_start_date,
        "measurement_start_nav": result.measurement_start_nav,
        "measurement_external_contributions": result.measurement_external_contributions,
        "measurement_profit": result.measurement_profit,
        "n_allocations": len(result.allocations),
        "first_allocation_date": result.first_allocation_date,
        "min_equity_exposure": result.min_equity_exposure,
        "avg_equity_exposure": result.avg_equity_exposure,
        "score": result.score,
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
    warmup_days: int | None = None,
    max_allocation_day: int = 252,
) -> dict:
    """Run (or fetch from cache) the backtest for ``candidate`` over a date window."""
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
        warmup_days=params.lookback_days if warmup_days is None else warmup_days,
        metrics_from="window_start",
    )
    metrics = result_metrics(result)

    try:
        _, mapping = resolve_allocation_dates(candidate, all_dates, max_allocation_day)
        metrics["n_clamped_allocations"] = sum(1 for m in mapping if m.get("clamped"))
    except Exception:
        metrics["n_clamped_allocations"] = 0

    if cache:
        cache.put(candidate, key, cfg, metrics)
    return metrics


def objectives(metrics: dict) -> list[float]:
    """Growth-first TRAIN objective vector for NSGA-II (all maximised).

    MDD/CDaR are intentionally not separate TRAIN objectives anymore.  They remain
    reported and, more importantly, are enforced by rolling OOS/final drawdown
    gates.  This prevents the search from spending too much Pareto capacity on
    ultra-defensive low-return portfolios while still failing closed on risk.
    """
    return [
        metrics.get("net_twr_annualized_pct", 0.0),
        metrics.get("sharpe", 0.0),
        metrics.get("sortino", 0.0),
        metrics.get("calmar", 0.0),
        metrics.get("positive_year_ratio", 0.0),
        -metrics.get("turnover_pct", 0.0),
        -metrics.get("cost_pct_of_nav", 0.0),
    ]


OBJECTIVE_NAMES = [
    "net_twr_ann",
    "sharpe",
    "sortino",
    "calmar",
    "positive_year_ratio",
    "turnover",
    "cost",
]
