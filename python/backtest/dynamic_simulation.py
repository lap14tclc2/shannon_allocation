"""Walk-forward simulation with dynamic alpha portfolio membership.

The active stock set is re-selected at each scheduled recalibration from the
configured market universe using strictly-past data. ERC then solves relative
weights for that selected set, the existing risk overlay scales total equity
exposure, and the existing Shannon drift engine manages positions between
recalibrations.

This module intentionally reuses the production execution/accounting helpers so
dynamic selection changes *membership*, not transaction-cost or performance
measurement semantics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .alpha import select_alpha_symbols
from .config import BacktestParams
from .risk import risk_adjusted_targets
from .strategy import compute_recommendations, snapshot_holdings, total_nav
from .simulation import SimulationResult, _compute_targets, _fill_performance, _floor


def simulate_dynamic_alpha(
    prices: pd.DataFrame,
    params: BacktestParams,
    allocation_dates: list | None = None,
    warmup_days: int | None = None,
    metrics_from: str = "window_start",
) -> SimulationResult:
    """Simulate dynamic membership across all columns in ``prices``.

    Initial deployment is independent of the optimized annual schedule. Before
    the first investment the engine attempts a strictly-past alpha/ERC/risk
    initialization every session. Scheduled events only control subsequent
    membership/ERC recalibration.
    """
    universe = sorted(str(s) for s in prices.columns)
    result = SimulationResult(symbols=tuple(universe))
    result.alpha_selection_history = []
    result.alpha_unique_symbols = []
    result.alpha_membership_turnover = 0.0

    raw = prices.dropna(how="all")
    if len(raw) < params.minimum_observations + 1:
        result.error = "Not enough history."
        return result

    perf_start_idx = 0
    if params.start_date:
        ts = pd.Timestamp(params.start_date)
        idx = int(raw.index.searchsorted(ts))
        if warmup_days:
            lo = max(0, idx - int(warmup_days))
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
    alloc_set = {
        pd.Timestamp(x).normalize() for x in (allocation_dates or [])
    }
    result.allocation_schedule = sorted(str(x) for x in alloc_set)

    shares: dict[str, float] = {}
    cash = float(params.initial_balance)
    result.total_deposits = float(params.initial_balance)
    result.capital_events.append(
        {
            "date": str(dates[0].date()),
            "type": "INITIAL_CAPITAL",
            "amount": round(float(params.initial_balance), 2),
            "cash_after": round(cash, 2),
            "note": "Initial capital became available to the dynamic alpha portfolio.",
        }
    )

    cumulative_cost = 0.0
    total_traded_value = 0.0
    trade_count = 0
    net_invested: dict[str, float] = {}
    active_symbols: list[str] = []
    relative_targets: dict[str, float] | None = None
    allocated = False
    pending = None
    rebalances_since_allocation = 0

    net_nav_series: list[float] = []
    gross_nav_series: list[float] = []
    nav_history: list[tuple[str, float]] = []
    gross_nav_history: list[tuple[str, float]] = []
    actual_equity_exposure_series: list[float] = []
    cumulative_cost_series: list[float] = []
    cumulative_traded_value_series: list[float] = []
    cumulative_trade_count_series: list[int] = []
    allocation_indices: list[int] = []
    deposit_indices: set[int] = set()
    deposit_dates: list = []
    deposit_amounts: list[float] = []
    first_invested_idx: int | None = None

    def execute_pending(pos: int, d, px):
        nonlocal cash, cumulative_cost, total_traded_value, trade_count, first_invested_idx
        buy_cash_deployed = 0.0
        sell_cash_released = 0.0
        executed_trades = 0

        for rec in pending["recs"]:
            sym = rec["symbol"]
            rec["execution_date"] = str(d.date())
            side = rec["recommendation"]
            amount = float(rec["funded_trade_amount"] or 0.0)
            reference_price = float(px.get(sym, 0.0) or 0.0)
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
                executed_trades += 1
                buy_cash_deployed += exec_notional + fee
                net_invested[sym] = net_invested.get(sym, 0.0) + exec_notional + fee
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
                shares[sym] = max(0.0, shares.get(sym, 0.0) - qty)
                cash += exec_notional - explicit_cost
                cumulative_cost += explicit_cost + slippage_cost
                total_traded_value += reference_notional
                trade_count += 1
                executed_trades += 1
                sell_cash_released += exec_notional - explicit_cost
                net_invested[sym] = net_invested.get(sym, 0.0) - (exec_notional - explicit_cost)
                rec["execution_price"] = round(reference_price, 2)
                rec["actual_execution_price"] = round(exec_price, 2)
                rec["shares_to_trade"] = round(qty, 4)
                rec["executed_notional"] = round(exec_notional, 2)
                rec["cost"] = round(explicit_cost + slippage_cost, 2)
                rec["slippage_cost"] = round(slippage_cost, 2)

        if executed_trades:
            signal_pos = int(pending.get("signal_pos", max(0, pos - 1)))
            signal_date = dates[signal_pos] if 0 <= signal_pos < len(dates) else d
            result.deployment_events.append(
                {
                    "signal_date": str(signal_date.date()),
                    "execution_date": str(d.date()),
                    "kind": str(pending.get("kind", "rebalance")).upper(),
                    "buy_cash_deployed": round(buy_cash_deployed, 2),
                    "sell_cash_released": round(sell_cash_released, 2),
                    "net_cash_deployed": round(buy_cash_deployed - sell_cash_released, 2),
                    "trade_count": executed_trades,
                    "cash_after": round(cash, 2),
                }
            )

        record = pending.get("record")
        if record is not None:
            nav_after = total_nav(shares, cash, px)
            record["execution_date"] = str(d.date())
            record["nav_after"] = round(nav_after, 2)
            record["cash_after"] = round(cash, 2)
            record["holdings_after"] = snapshot_holdings(shares, px, nav_after)
            equity_after = sum(
                shares.get(s, 0.0) * float(px.get(s, 0.0) or 0.0) for s in shares
            )
            if record.get("allocation_role") == "INITIAL_DEPLOYMENT" and equity_after > 0 and first_invested_idx is None:
                first_invested_idx = pos

    def try_recalibrate(pos: int, d, prices_now: dict, role: str):
        nonlocal active_symbols, relative_targets, allocated, pending, rebalances_since_allocation
        selection = select_alpha_symbols(
            raw,
            universe,
            pos,
            params,
            params.dynamic_alpha_portfolio_size,
        )
        if len(selection.symbols) != int(params.dynamic_alpha_portfolio_size):
            return False

        selected = list(selection.symbols)
        computed = _compute_targets(raw, selected, pos, params)
        if computed is None:
            return False
        new_relative_targets, erc_info = computed
        live_targets, risk_info = risk_adjusted_targets(
            raw, selected, pos, new_relative_targets, params
        )
        # A missing risk estimate is fail-closed and is not considered a valid
        # initial deployment. Scheduled recalibrations may still de-risk to cash.
        target_exposure = sum(float(v) for v in live_targets.values())
        if role == "INITIAL_DEPLOYMENT" and target_exposure <= 1e-12:
            return False

        previous = tuple(active_symbols)
        active_symbols = selected
        relative_targets = new_relative_targets
        for s in selected:
            shares.setdefault(s, 0.0)
            net_invested.setdefault(s, 0.0)

        nav_before = total_nav(shares, cash, prices_now)
        holdings_before = snapshot_holdings(shares, prices_now, nav_before)
        recs, funding = compute_recommendations(
            shares, cash, prices_now, live_targets, params
        )
        record = {
            "year": int(d.year),
            "quarter": (int(d.month) - 1) // 3 + 1,
            "allocation_date": str(d.date()),
            "signal_date": str(d.date()),
            "execution_date": None,
            "initial_allocation": role == "INITIAL_DEPLOYMENT",
            "allocation_role": role,
            "deposit_amount": 0.0,
            "rebalances_since_last_allocation": rebalances_since_allocation,
            "nav_before": round(nav_before, 2),
            "cash_before": round(cash, 2),
            "nav_after": None,
            "cash_after": None,
            "selected_symbols": selected,
            "previous_selected_symbols": list(previous),
            "alpha_selection": selection.as_dict(),
            "erc": erc_info,
            "relative_targets": {s: round(t, 6) for s, t in new_relative_targets.items()},
            "targets": {s: round(t, 6) for s, t in live_targets.items()},
            "risk_overlay": risk_info,
            "holdings_before": holdings_before,
            "recommendations": recs,
            "holdings_after": None,
            "funding": {k: round(v, 4) for k, v in funding.items()},
        }
        result.allocations.append(record)
        result.alpha_selection_history.append(
            {
                "date": str(d.date()),
                "role": role,
                "selected_symbols": selected,
                "previous_selected_symbols": list(previous),
                "scores": selection.as_dict()["scores"],
                "max_selected_correlation": selection.diagnostics.get("max_selected_correlation"),
            }
        )
        allocation_indices.append(pos)
        rebalances_since_allocation = 0
        pending = {
            "recs": recs,
            "record": record,
            "kind": "allocation" if role != "INITIAL_DEPLOYMENT" else "initial_deployment",
            "signal_pos": pos,
        }
        allocated = True
        return True

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
            if params.annual_deposit > 0:
                result.capital_events.append(
                    {
                        "date": str(d.date()),
                        "type": "ANNUAL_CONTRIBUTION",
                        "amount": round(float(params.annual_deposit), 2),
                        "cash_after": round(float(cash), 2),
                        "note": "Annual contribution added on the first trading session of the year.",
                    }
                )

        if not allocated:
            try_recalibrate(pos, d, prices_now, "INITIAL_DEPLOYMENT")
        elif d.normalize() in alloc_set:
            try_recalibrate(pos, d, prices_now, "SCHEDULED_RECALIBRATION")
        elif relative_targets is not None and active_symbols and pos % params.rebalance_every_days == 0:
            live_targets, _risk_info = risk_adjusted_targets(
                raw, active_symbols, pos, relative_targets, params
            )
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
        equity_value = sum(
            shares.get(s, 0.0) * float(prices_now.get(s, 0.0) or 0.0) for s in shares
        )
        actual_exposure = equity_value / nav if nav > 0 else 0.0

        net_nav_series.append(float(nav))
        gross_nav_series.append(float(gross))
        nav_history.append((d.strftime("%Y-%m-%d"), float(nav)))
        gross_nav_history.append((d.strftime("%Y-%m-%d"), float(gross)))
        actual_equity_exposure_series.append(float(actual_exposure))
        cumulative_cost_series.append(float(cumulative_cost))
        cumulative_traded_value_series.append(float(total_traded_value))
        cumulative_trade_count_series.append(int(trade_count))

    if pending is not None:
        # There is no future execution session, so the last signal remains
        # unexecuted exactly like the standard simulator.
        pending = None

    if not allocated or first_invested_idx is None:
        result.error = "Dynamic alpha portfolio never reached a deployable ERC/risk state."
        return result

    result.final_nav = net_nav_series[-1]
    result.nav_history = nav_history
    result.gross_nav_history = gross_nav_history
    all_touched = sorted(set(shares) | set(net_invested))
    last_prices = valuation.iloc[-1].fillna(0.0).to_dict()
    result.stock_contributions = {
        s: round(
            shares.get(s, 0.0) * float(last_prices.get(s, 0.0) or 0.0)
            - net_invested.get(s, 0.0),
            2,
        )
        for s in all_touched
    }

    selections = [tuple(x["selected_symbols"]) for x in result.alpha_selection_history]
    result.alpha_unique_symbols = sorted({s for xs in selections for s in xs})
    if len(selections) >= 2:
        changes = []
        for before, after in zip(selections, selections[1:]):
            b, a = set(before), set(after)
            denom = max(1, len(a))
            changes.append(1.0 - len(a & b) / denom)
        result.alpha_membership_turnover = float(np.mean(changes)) if changes else 0.0

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
        deposit_dates,
        deposit_amounts,
        params.initial_balance,
        cumulative_cost_series,
        cumulative_traded_value_series,
        cumulative_trade_count_series,
        actual_equity_exposure_series,
        metrics_from,
    )
    return result
