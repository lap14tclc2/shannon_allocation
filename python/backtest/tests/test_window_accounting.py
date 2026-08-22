"""Regression tests for walk-forward measurement-window accounting."""

import pandas as pd

from backtest.simulation import SimulationResult, _fill_performance


def _fill(result, navs, dates, deposit_dates=None, deposit_amounts=None):
    deposit_dates = deposit_dates or []
    deposit_amounts = deposit_amounts or []
    deposit_indices = {
        i for i, d in enumerate(dates) if any(d == dd for dd in deposit_dates)
    }
    _fill_performance(
        result,
        net_nav_series=navs,
        gross_nav_series=navs,
        dates=dates,
        deposit_indices=deposit_indices,
        perf_start=0,
        first_invested_idx=0,
        allocation_indices=[0],
        deposit_dates=deposit_dates,
        deposit_amounts=deposit_amounts,
        initial_balance=100.0,
        cumulative_cost_series=[0.0] * len(navs),
        cumulative_traded_value_series=[0.0] * len(navs),
        cumulative_trade_count_series=[0] * len(navs),
        actual_equity_exposure_series=[1.0] * len(navs),
        metrics_from="window_start",
    )


def test_external_deposit_does_not_create_return_or_drawdown():
    dates = [
        pd.Timestamp("2025-01-02"),
        pd.Timestamp("2025-07-02"),
        pd.Timestamp("2026-01-02"),
    ]
    result = SimulationResult(symbols=("A", "B", "C", "D", "E"))
    # Portfolio is economically flat: the jump from 100 -> 150 is a 50 deposit.
    _fill(
        result,
        navs=[100.0, 150.0, 150.0],
        dates=dates,
        deposit_dates=[dates[1]],
        deposit_amounts=[50.0],
    )
    assert abs(result.twr) < 1e-9
    assert abs(result.xirr) < 1e-6
    assert abs(result.max_drawdown_pct) < 1e-9
    assert result.measurement_external_contributions == 50.0
    assert abs(result.measurement_profit) < 1e-9


def test_warmup_costs_are_not_charged_to_measured_window():
    dates = [pd.Timestamp("2025-01-02"), pd.Timestamp("2026-01-02")]
    result = SimulationResult(symbols=("A", "B", "C", "D", "E"))
    _fill_performance(
        result,
        net_nav_series=[100.0, 110.0],
        gross_nav_series=[110.0, 121.0],
        dates=dates,
        deposit_indices=set(),
        perf_start=0,
        first_invested_idx=0,
        allocation_indices=[0],
        deposit_dates=[],
        deposit_amounts=[],
        initial_balance=100.0,
        cumulative_cost_series=[10.0, 12.0],
        cumulative_traded_value_series=[100.0, 150.0],
        cumulative_trade_count_series=[5, 7],
        actual_equity_exposure_series=[0.8, 0.9],
        metrics_from="window_start",
    )
    assert result.transaction_cost == 2.0
    assert result.trade_count == 2
    assert abs(result.avg_equity_exposure - 0.85) < 1e-12
