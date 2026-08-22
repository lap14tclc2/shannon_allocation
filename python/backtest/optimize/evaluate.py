"""Candidate evaluation: run backtest, extract metrics, cache, map to objectives.

The optimizer is growth-first: TRAIN search rewards return and risk-adjusted
growth, while drawdown/CDaR are enforced later as rolling OOS/final risk gates.
ERC, Shannon, transaction costs and risk-overlay mechanics remain unchanged.

Static portfolios receive an independent INITIAL DEPLOYMENT event as before.
Dynamic-alpha portfolios instead initialize themselves at the first strictly-past
date where alpha selection, ERC and risk targeting are all deployable; their
candidate genome therefore controls recalibration timing, not the stock names.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os

import pandas as pd

from ..config import BacktestParams
from ..erc import ERCError, log_returns_from_window, solve_erc
from ..risk import risk_adjusted_targets
from ..simulation import simulate_combination
from ..dynamic_simulation import simulate_dynamic_alpha
from ..candidate import Candidate, resolve_allocation_dates, schedule_for_window

OPTIMIZER_METRIC_SCHEMA = "growth-v10-dynamic-alpha-soft-live-quality"


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
        "dynamic_alpha_enabled",
        "dynamic_alpha_portfolio_size",
        "alpha_min_observations",
        "alpha_short_lookback",
        "alpha_medium_lookback",
        "alpha_long_lookback",
        "alpha_correlation_lookback",
        "alpha_max_pair_correlation",
    ]
    payload = {k: getattr(params, k) for k in keys}
    raw = json.dumps(payload, sort_keys=True) + "|" + data_version + "|" + OPTIMIZER_METRIC_SCHEMA
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _growth_score(result) -> float:
    """TRAIN-only scalar used by the surrogate/racing fallback."""
    return float(
        result.twr_annualized
        + 4.0 * result.sharpe
        + 1.5 * result.sortino
        + 2.0 * result.calmar
        + 2.0 * result.positive_year_ratio
        - 0.02 * result.turnover
        - 1.5 * result.cost_pct_of_nav
    )


def result_metrics(result) -> dict:
    """Extract scalar NET metrics used by optimization/validation/reporting."""
    alpha_history = list(getattr(result, "alpha_selection_history", []) or [])
    alpha_unique = list(getattr(result, "alpha_unique_symbols", []) or [])
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
        "dynamic_alpha": bool(alpha_history),
        "alpha_selection_count": len(alpha_history),
        "alpha_unique_symbols": alpha_unique,
        "alpha_unique_symbol_count": len(alpha_unique),
        "alpha_membership_turnover": float(getattr(result, "alpha_membership_turnover", 0.0) or 0.0),
        "alpha_selection_history": alpha_history,
        "score": _growth_score(result),
        "legacy_score": result.score,
        "error": result.error,
    }


def _simulation_bounds(prices: pd.DataFrame, start, end, warmup_days: int) -> tuple[int, int]:
    """Return inclusive raw-price bounds matching simulate_combination warm-up semantics."""
    if prices.empty:
        return 0, -1
    if start:
        start_idx = int(prices.index.searchsorted(pd.Timestamp(start)))
        lo = max(0, start_idx - max(0, int(warmup_days)))
    else:
        lo = 0
    if end:
        hi = int(prices.index.searchsorted(pd.Timestamp(end), side="right")) - 1
    else:
        hi = len(prices) - 1
    return lo, min(hi, len(prices) - 1)


def initial_deployment_date(
    candidate: Candidate,
    prices: pd.DataFrame,
    params: BacktestParams,
    window: tuple[str | None, str | None] = (None, None),
    warmup_days: int | None = None,
):
    """Earliest look-ahead-free date at which a STATIC portfolio can deploy."""
    if prices.empty:
        return None
    symbols = list(candidate.symbols)
    if any(s not in prices.columns for s in symbols):
        return None

    raw = prices[symbols].dropna(how="all")
    if raw.empty:
        return None

    warmup = params.lookback_days if warmup_days is None else max(0, int(warmup_days))
    start, end = window
    lo, hi = _simulation_bounds(raw, start, end, warmup)
    if hi <= lo:
        return None

    aligned = raw[symbols].notna().all(axis=1).astype(int)
    past_counts = (
        aligned.shift(1, fill_value=0)
        .rolling(window=max(1, int(params.lookback_days)), min_periods=1)
        .sum()
    )
    required = max(2, int(params.minimum_observations))
    eligible_positions = [
        pos
        for pos in range(lo, hi + 1)
        if float(past_counts.iloc[pos]) >= required
    ]

    for pos in eligible_positions:
        hist_start = max(0, pos - int(params.lookback_days))
        hist = raw.iloc[hist_start:pos][symbols].dropna()
        if len(hist) < required:
            continue
        try:
            returns = log_returns_from_window(hist.to_numpy(dtype=float))
            erc = solve_erc(returns, params)
        except ERCError:
            continue

        relative = dict(zip(symbols, erc.weights.tolist()))
        if not params.risk_overlay_enabled:
            return raw.index[pos]

        live_targets, _risk_info = risk_adjusted_targets(
            raw, symbols, pos, relative, params
        )
        if sum(float(v) for v in live_targets.values()) > 1e-12:
            return raw.index[pos]

    return None


def allocation_dates_with_initialization(
    candidate: Candidate,
    prices: pd.DataFrame,
    params: BacktestParams,
    all_dates,
    window: tuple[str | None, str | None] = (None, None),
    warmup_days: int | None = None,
):
    """Static candidate recalibration dates plus independent initial deployment."""
    scheduled = schedule_for_window(candidate, all_dates)
    init = initial_deployment_date(candidate, prices, params, window, warmup_days)
    if init is None:
        return scheduled, None
    merged = sorted({pd.Timestamp(d).normalize() for d in scheduled} | {pd.Timestamp(init).normalize()})
    return merged, pd.Timestamp(init).normalize()


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
    """Run (or fetch from cache) one timing/static candidate over a date window."""
    start, end = window
    key = f"{start or ''}|{end or ''}"
    if cache:
        hit = cache.get(candidate, key, cfg)
        if hit is not None:
            return hit

    effective_warmup = params.lookback_days if warmup_days is None else warmup_days
    run_params = dataclasses.replace(params, start_date=start, end_date=end)

    if params.dynamic_alpha_enabled:
        alloc_dates = schedule_for_window(candidate, all_dates)
        result = simulate_dynamic_alpha(
            prices,
            run_params,
            allocation_dates=alloc_dates,
            warmup_days=effective_warmup,
            metrics_from="window_start",
        )
        init_text = None
        for record in result.allocations:
            if record.get("allocation_role") == "INITIAL_DEPLOYMENT":
                init_text = record.get("allocation_date")
                break
        init_date = pd.Timestamp(init_text) if init_text else None
    else:
        alloc_dates, init_date = allocation_dates_with_initialization(
            candidate,
            prices,
            params,
            all_dates,
            window,
            effective_warmup,
        )
        result = simulate_combination(
            list(candidate.symbols),
            prices,
            run_params,
            allocation_dates=alloc_dates,
            warmup_days=effective_warmup,
            metrics_from="window_start",
        )
        init_text = str(init_date.date()) if init_date is not None else None
        if init_text:
            for record in result.allocations:
                if record.get("allocation_date") == init_text:
                    record["allocation_role"] = "INITIAL_DEPLOYMENT"
                else:
                    record.setdefault("allocation_role", "SCHEDULED_RECALIBRATION")

    metrics = result_metrics(result)
    metrics["initial_deployment_date"] = init_text
    if init_date is not None and start:
        metrics["initial_deployment_before_measurement"] = bool(init_date < pd.Timestamp(start))
    else:
        metrics["initial_deployment_before_measurement"] = False

    try:
        _, mapping = resolve_allocation_dates(candidate, all_dates, max_allocation_day)
        metrics["n_clamped_allocations"] = sum(1 for m in mapping if m.get("clamped"))
        metrics["n_skipped_allocations"] = sum(1 for m in mapping if m.get("skipped"))
    except Exception:
        metrics["n_clamped_allocations"] = 0
        metrics["n_skipped_allocations"] = 0

    if cache:
        cache.put(candidate, key, cfg, metrics)
    return metrics


def objectives(metrics: dict) -> list[float]:
    """Growth-first TRAIN objective vector for NSGA-II (all maximised)."""
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
