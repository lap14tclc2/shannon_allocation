"""Walk-forward simulation of one portfolio candidate.

Look-ahead free by construction:
  - ERC targets are calibrated using raw price data strictly BEFORE the signal day
  - the absolute-risk overlay also uses data strictly before the signal day
  - a signal (allocation or band rebalance) is computed at close[t]
  - orders execute at close[t+1] (execution_lag=1), applying transaction costs

The raw price panel is never forward-filled for risk estimation.  A separate
forward-filled valuation panel is used only to mark existing holdings to their
last known close on dates where a symbol has no print.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import BacktestParams
from .erc import ERCError, log_returns_from_window, solve_erc
from .risk import risk_adjusted_targets
from .strategy import compute_recommendations, snapshot_holdings, total_nav
from . import metrics as mt


@dataclass
class SimulationResult:
    symbols: tuple[str, ...]
    nav_history: list[tuple[str, float]] = field(default_factory=list)
    gross_nav_history: list[tuple[str, float]] = field(default_factory=list)
    allocations: list[dict] = field(default_factory=list)
    allocation_schedule: list = field(default_factory=list)
    final_nav: float = 0.0
    total_deposits: float = 0.0
    total_return_pct: float = 0.0
    cagr_pct: float = 0.0
    annualized_volatility_pct: float = 0.0
    sharpe: float = 0.0
    max_drawdown_pct: float = 0.0

    cdar95_pct: float = 0.0
    underwater_ratio: float = 0.0
    max_underwater_days: int = 0

    first_allocation_date: str = ""
    twr: float = 0.0
    twr_annualized: float = 0.0
    xirr: float = 0.0
    sortino: float = 0.0
    calmar: float = 0.0
    absolute_profit: float = 0.0
    annual_returns: dict = field(default_factory=dict)
    worst_year: float = 0.0
    positive_year_ratio: float = 0.0
    turnover: float = 0.0
    trade_count: int = 0
    score: float = 0.0

    gross_twr: float = 0.0
    gross_twr_annualized: float = 0.0
    gross_xirr: float = 0.0

    transaction_cost: float = 0.0
    cost_pct_of_nav: float = 0.0

    min_equity_exposure: float = 1.0
    avg_equity_exposure: float = 1.0

    stock_contributions: dict = field(default_factory=dict)
    error: str | None = None


QUARTER_MONTHS = (1, 4, 7, 10)


def _compute_targets(prices: pd.DataFrame, symbols: list[str], pos: int, params: BacktestParams):
    """Return relative ERC targets calibrated strictly before ``pos``."""
    start = max(0, pos - params.lookback_days)
    window = prices.iloc[start:pos][symbols].dropna()
    if len(window) < params.minimum_observations:
        return None
    try:
        returns = log_returns_from_window(window.values)
        erc = solve_erc(returns, params)
    except ERCError:
        return None
    targets = dict(zip(symbols, erc.weights.tolist()))
    diagnostics = {
        "observations": int(erc.observations),
        "window_start": str(window.index[0].date()),
        "window_end": str(window.index[-1].date()),
        "portfolio_risk": round(float(erc.portfolio_risk), 6),
        "portfolio_variance": round(float(erc.portfolio_variance), 6),
        "erc_error": round(float(erc.erc_error), 10),
        "risk_contributions": {s: round(float(rc), 6) for s, rc in zip(symbols, erc.risk_contributions)},
        "weights": {s: round(float(w), 6) for s, w in zip(symbols, erc.weights)},
    }
    return targets, diagnostics


def simulate_combination(
    symbols: list[str],
    prices: pd.DataFrame,
    params: BacktestParams,
    allocation_dates: list | None = None,
    warmup_days: int | None = None,
    metrics_from: str = "first_allocation",
) -> SimulationResult:
    """Simulate one candidate from a raw non-forward-filled price panel."""
    symbols = sorted(symbols)
    result = SimulationResult(symbols=tuple(symbols))

    raw = prices[symbols].dropna(how="all")
    if len(raw) < params.minimum_observations + 1:
        result.error = "Not enough history."
        return result

    perf_start_idx = 0
    if params.start_date:
        ts = pd.Timestamp(params.start_date)
        idx = raw.index.searchsorted(ts)
        if warmup_days:
            lo = max(0, idx - warmup_days)
            raw = raw.iloc[lo:]
            perf_start_idx = idx - lo
        else:
            raw = raw.iloc[idx:]
    if params.end_date:
        raw = raw[raw.index <= pd.Timestamp(params.end_date)]
    if len(raw) < 2:
        result.error = "Empty date window."
        return result

    valuation = raw.ffill()
    dates = list(raw.index)

    alloc_set = None
    if allocation_dates is not None:
        alloc_set = {pd.Timestamp(x).normalize() for x in allocation_dates}
        result.allocation_schedule = sorted(str(x) for x in alloc_set)

    shares: dict[str, float] = {s: 0.0 for s in symbols}
    cash = params.initial_balance
    result.total_deposits = params.initial_balance
    cumulative_cost = 0.0
    net_invested: dict[str, float] = {s: 0.0 for s in symbols}

    relative_targets: dict[str, float] | None = None
    allocated = False
    net_nav_series: list[float] = []
    gross_nav_series: list[float] = []
    nav_history: list[tuple[str, float]] = []
    gross_nav_history: list[tuple[str, float]] = []
    exposure_history: list[float] = []
    rebalances_since_allocation = 0
    pending = None
    allocation_indices: list[int] = []

    deposit_indices: set[int] = set()
    deposit_dates: list = []
    deposit_amounts: list[float] = []
    total_traded_value = 0.0
    trade_count = 0
    first_invested_idx: int | None = None

    def execute_pending(pos: int, d, px):
        """Execute pending orders at close[t+1] with explicit slippage + costs.

        ``execution_price`` remains the next-session reference close for backward
        compatible auditing. ``actual_execution_price`` records the adverse
        slippage-adjusted fill that is used for cash and holdings accounting.
        """
        nonlocal cash, cumulative_cost, total_traded_value, trade_count, first_invested_idx
        for rec in pending["recs"]:
            sym = rec["symbol"]
            rec["execution_date"] = str(d.date())
            side = rec["recommendation"]
            amount = rec["funded_trade_amount"]
            reference_price = px[sym]
            if side == "HOLD" or amount <= 0 or reference_price <= 0:
                continue

            if side == "BUY":
                exec_price = reference_price * (1.0 + params.slippage_bps / 10000.0)
                fee_rate = params.fee_buy_bps / 10000.0
                qty = amount / exec_price
                if not params.fractional_shares:
                    qty = _floor(qty)
                affordable = cash / (exec_price * (1.0 + fee_rate)) if exec_price > 0 else 0.0
                qty = min(qty, affordable)
                if not params.fractional_shares:
                    qty = _floor(qty)
                exec_notional = qty * exec_price
                reference_notional = qty * reference_price
                fee = exec_notional * fee_rate
                slippage_cost = max(0.0, exec_notional - reference_notional)
                if qty <= 0 or exec_notional + fee > cash + 1e-6:
                    continue
                shares[sym] = shares.get(sym, 0.0) + qty
                cash -= exec_notional + fee
                cumulative_cost += fee + slippage_cost
                total_traded_value += reference_notional
                trade_count += 1
                net_invested[sym] += exec_notional + fee
                rec["execution_price"] = round(reference_price, 2)
                rec["actual_execution_price"] = round(exec_price, 2)
                rec["shares_to_trade"] = round(qty, 4)
                rec["executed_notional"] = round(exec_notional, 2)
                rec["cost"] = round(fee + slippage_cost, 2)
                rec["slippage_cost"] = round(slippage_cost, 2)
            else:
                exec_price = reference_price * (1.0 - params.slippage_bps / 10000.0)
                qty = min(amount / max(exec_price, 1e-9), shares.get(sym, 0.0))
                if not params.fractional_shares:
                    qty = _floor(qty)
                if qty <= 0:
                    continue
                exec_notional = qty * exec_price
                reference_notional = qty * reference_price
                fee = exec_notional * params.fee_sell_bps / 10000.0
                tax = exec_notional * params.tax_sell_bps / 10000.0
                slippage_cost = max(0.0, reference_notional - exec_notional)
                explicit_cost = fee + tax
                shares[sym] = shares.get(sym, 0.0) - qty
                cash += exec_notional - explicit_cost
                cumulative_cost += explicit_cost + slippage_cost
                total_traded_value += reference_notional
                trade_count += 1
                net_invested[sym] -= exec_notional - explicit_cost
                rec["execution_price"] = round(reference_price, 2)
                rec["actual_execution_price"] = round(exec_price, 2)
                rec["shares_to_trade"] = round(qty, 4)
                rec["executed_notional"] = round(exec_notional, 2)
                rec["cost"] = round(explicit_cost + slippage_cost, 2)
                rec["slippage_cost"] = round(slippage_cost, 2)

        record = pending.get("record")
        if record is not None:
            nav_after = total_nav(shares, cash, px)
            record["execution_date"] = str(d.date())
            record["nav_after"] = round(nav_after, 2)
            record["cash_after"] = round(cash, 2)
            record["holdings_after"] = snapshot_holdings(shares, px, nav_after)
            if record["initial_allocation"] and first_invested_idx is None:
                first_invested_idx = pos

    def is_allocation_date(d, prev, pos) -> bool:
        if alloc_set is not None:
            return d in alloc_set
        new_year = prev is not None and d.year != prev.year
        quarter_start = prev is not None and d.month != prev.month and d.month in QUARTER_MONTHS
        if params.allocation_frequency == "quarterly":
            return new_year or quarter_start
        return new_year

    for pos, d in enumerate(dates):
        prices_now = valuation.loc[d].fillna(0.0).to_dict()
        prev = dates[pos - 1] if pos > 0 else None

        if pending is not None:
            execute_pending(pos, d, prices_now)
            pending = None

        new_year = prev is not None and d.year != prev.year
        if new_year and params.deposit_at_start_year:
            cash += params.annual_deposit
            result.total_deposits += params.annual_deposit
            deposit_indices.add(pos)
            deposit_dates.append(d)
            deposit_amounts.append(params.annual_deposit)

        if is_allocation_date(d, prev, pos):
            computed = _compute_targets(raw, symbols, pos, params)
            if computed is not None:
                new_relative_targets, erc_info = computed
                live_targets, risk_info = risk_adjusted_targets(
                    raw, symbols, pos, new_relative_targets, params
                )
                relative_targets = new_relative_targets
                exposure_history.append(float(risk_info.get("equity_exposure", 1.0)))
                nav_before = total_nav(shares, cash, prices_now)
                holdings_before = snapshot_holdings(shares, prices_now, nav_before)
                recs, funding = compute_recommendations(
                    shares, cash, prices_now, live_targets, params
                )
                allocated = True
                record = {
                    "year": int(d.year),
                    "quarter": (int(d.month) - 1) // 3 + 1,
                    "allocation_date": str(d.date()),
                    "signal_date": str(d.date()),
                    "execution_date": None,
                    "initial_allocation": not result.allocations,
                    "deposit_amount": params.annual_deposit if new_year else 0.0,
                    "rebalances_since_last_allocation": rebalances_since_allocation,
                    "nav_before": round(nav_before, 2),
                    "cash_before": round(cash, 2),
                    "nav_after": None,
                    "cash_after": None,
                    "erc": erc_info,
                    "relative_targets": {
                        s: round(t, 6) for s, t in new_relative_targets.items()
                    },
                    "targets": {s: round(t, 6) for s, t in live_targets.items()},
                    "risk_overlay": risk_info,
                    "holdings_before": holdings_before,
                    "recommendations": recs,
                    "holdings_after": None,
                    "funding": {k: round(v, 4) for k, v in funding.items()},
                }
                result.allocations.append(record)
                rebalances_since_allocation = 0
                allocation_indices.append(pos)
                pending = {
                    "recs": recs,
                    "record": record,
                    "kind": "allocation",
                    "signal_pos": pos,
                }
        elif allocated and relative_targets is not None and pos % params.rebalance_every_days == 0:
            live_targets, risk_info = risk_adjusted_targets(
                raw, symbols, pos, relative_targets, params
            )
            exposure_history.append(float(risk_info.get("equity_exposure", 1.0)))
            recs, _ = compute_recommendations(
                shares, cash, prices_now, live_targets, params
            )
            if any(r["recommendation"] != "HOLD" for r in recs):
                pending = {
                    "recs": recs,
                    "record": None,
                    "kind": "rebalance",
                    "signal_pos": pos,
                }
                rebalances_since_allocation += 1

        nav = total_nav(shares, cash, prices_now)
        gross = nav + cumulative_cost
        net_nav_series.append(nav)
        gross_nav_series.append(gross)
        nav_history.append((d.strftime("%Y-%m-%d"), float(nav)))
        gross_nav_history.append((d.strftime("%Y-%m-%d"), float(gross)))

    if not allocated or first_invested_idx is None:
        result.error = "ERC never calibrated (insufficient aligned history)."
        return result

    result.final_nav = net_nav_series[-1]
    result.nav_history = nav_history
    result.gross_nav_history = gross_nav_history
    result.transaction_cost = cumulative_cost
    result.stock_contributions = {
        s: round(
            shares.get(s, 0.0) * prices_now.get(s, 0.0) - net_invested.get(s, 0.0),
            2,
        )
        for s in symbols
    }
    if exposure_history:
        result.min_equity_exposure = min(exposure_history)
        result.avg_equity_exposure = sum(exposure_history) / len(exposure_history)

    perf_start = perf_start_idx if metrics_from == "window_start" else first_invested_idx
    _fill_performance(
        result,
        net_nav_series,
        gross_nav_series,
        dates,
        deposit_indices,
        perf_start,
        first_invested_idx,
        allocation_indices,
        total_traded_value,
        trade_count,
        deposit_dates,
        deposit_amounts,
        params.initial_balance,
        cumulative_cost,
        metrics_from,
    )
    return result


def _fill_performance(
    result: SimulationResult,
    net_nav_series: list[float],
    gross_nav_series: list[float],
    dates,
    deposit_indices: set[int],
    perf_start: int,
    first_invested_idx: int,
    allocation_indices: list[int],
    total_traded_value: float,
    trade_count: int,
    deposit_dates,
    deposit_amounts,
    initial_balance: float,
    cumulative_cost: float,
    metrics_from: str = "first_allocation",
) -> None:
    arr = np.asarray(net_nav_series, dtype=float)
    gross_arr = np.asarray(gross_nav_series, dtype=float)
    deposits = result.total_deposits
    end_idx = len(arr) - 1

    result.total_return_pct = (
        (arr[-1] / deposits - 1.0) * 100.0 if deposits > 0 else 0.0
    )
    years_data = len(arr) / 252.0
    if years_data > 0 and arr[-1] > 0:
        result.cagr_pct = ((arr[-1] / deposits) ** (1.0 / years_data) - 1.0) * 100.0

    days = (dates[end_idx].toordinal() - dates[perf_start].toordinal()) + 1

    if metrics_from == "window_start":
        in_window = [i for i in allocation_indices if i >= perf_start]
        fa_idx = min(in_window) if in_window else first_invested_idx
    else:
        fa_idx = first_invested_idx
    result.first_allocation_date = dates[fa_idx].strftime("%Y-%m-%d")
    twr = mt.time_weighted_return(net_nav_series, deposit_indices, perf_start, end_idx)
    result.twr = twr * 100.0
    ann_twr = mt.annualized_from_total(twr, days)
    result.twr_annualized = (ann_twr * 100.0) if ann_twr is not None else 0.0
    result.absolute_profit = arr[-1] - deposits

    period = arr[perf_start:]
    log_ret = np.diff(np.log(np.maximum(period, 1e-9)))
    if len(log_ret) > 1:
        result.annualized_volatility_pct = float(
            np.std(log_ret, ddof=1) * np.sqrt(252) * 100.0
        )
        sharpe, sortino = mt.sharpe_sortino(log_ret.tolist())
        result.sharpe = sharpe if sharpe is not None else 0.0
        result.sortino = sortino if sortino is not None else 0.0

    mdd = mt.max_drawdown(net_nav_series, perf_start, end_idx)
    cdar95 = mt.conditional_drawdown_at_risk(
        net_nav_series, perf_start, end_idx, 0.95
    )
    underwater_ratio, max_underwater_days = mt.underwater_stats(
        net_nav_series, dates, perf_start, end_idx
    )
    result.max_drawdown_pct = mdd * 100.0
    result.cdar95_pct = cdar95 * 100.0
    result.underwater_ratio = underwater_ratio
    result.max_underwater_days = max_underwater_days
    result.calmar = (
        ann_twr / abs(mdd) if (ann_twr is not None and mdd < 0) else 0.0
    )

    flow_anchor = perf_start if metrics_from == "window_start" else 0
    day0 = dates[flow_anchor].toordinal()
    flows = [(-initial_balance, day0)]
    for dd, amt in zip(deposit_dates, deposit_amounts):
        if dd.toordinal() >= day0:
            flows.append((-amt, dd.toordinal()))
    flows.append((arr[-1], dates[end_idx].toordinal()))
    xirr = mt.xirr(flows)
    result.xirr = (xirr * 100.0) if xirr is not None else 0.0

    annual = mt.annual_returns(
        net_nav_series, dates, deposit_indices, perf_start, end_idx
    )
    result.annual_returns = {y: round(v * 100.0, 2) for y, v in annual.items()}
    if result.annual_returns:
        result.worst_year = min(result.annual_returns.values())
        pos_years = sum(1 for v in result.annual_returns.values() if v > 0)
        result.positive_year_ratio = pos_years / len(result.annual_returns)

    mean_nav = (
        float(np.mean(arr[perf_start:])) if (end_idx - perf_start + 1) > 0 else 0.0
    )
    result.turnover = (
        total_traded_value / mean_nav * 100.0 if mean_nav > 0 else 0.0
    )
    result.trade_count = trade_count
    result.cost_pct_of_nav = (
        cumulative_cost / mean_nav * 100.0 if mean_nav > 0 else 0.0
    )

    gt = mt.time_weighted_return(
        gross_nav_series, deposit_indices, perf_start, end_idx
    )
    result.gross_twr = gt * 100.0
    gann = mt.annualized_from_total(gt, days)
    result.gross_twr_annualized = (gann * 100.0) if gann is not None else 0.0
    gflows = [(-initial_balance, day0)]
    for dd, amt in zip(deposit_dates, deposit_amounts):
        if dd.toordinal() >= day0:
            gflows.append((-amt, dd.toordinal()))
    gflows.append((float(gross_arr[-1]), dates[end_idx].toordinal()))
    gx = mt.xirr(gflows)
    result.gross_xirr = (gx * 100.0) if gx is not None else 0.0

    result.score = mt.portfolio_score(
        result.twr_annualized / 100.0,
        result.sharpe,
        result.max_drawdown_pct / 100.0,
        result.positive_year_ratio,
        result.cdar95_pct / 100.0,
    )


def _floor(shares: float) -> float:
    import math
    return math.floor(shares + 1e-9)
