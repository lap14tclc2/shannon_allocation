from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.candidate import Candidate
from backtest.config import BacktestParams
from backtest.optimize.evaluate import allocation_dates_with_initialization, initial_deployment_date
from backtest.risk import risk_adjusted_targets


def _panel(n=420, seed=17):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-03", periods=n)
    data = {}
    for i, symbol in enumerate("ABCDE"):
        returns = 0.0002 + (0.007 + i * 0.0005) * rng.standard_normal(n)
        data[symbol] = 100.0 * np.exp(np.cumsum(returns))
    return pd.DataFrame(data, index=dates)


def test_default_strategic_minimum_equity_exposure_is_zero():
    params = BacktestParams()
    assert params.min_equity_exposure == 0.0
    assert params.risk_missing_data_exposure == 0.0


def test_missing_risk_data_fails_closed_even_with_strategic_floor():
    prices = _panel(n=20)
    symbols = list("ABCDE")
    params = BacktestParams(
        risk_overlay_enabled=True,
        target_volatility=0.18,
        min_equity_exposure=0.50,
        risk_missing_data_exposure=0.0,
        risk_fast_lookback=63,
        risk_slow_lookback=252,
    )
    relative = {s: 0.2 for s in symbols}
    targets, info = risk_adjusted_targets(prices, symbols, 2, relative, params)
    assert sum(targets.values()) == 0.0
    assert info["equity_exposure"] == 0.0
    assert info["exposure_state"] == "risk_missing_fail_closed"
    assert info["strategic_floor_applied"] is False


def test_valid_risk_state_reports_volatility_derisking_separately():
    prices = _panel()
    symbols = list("ABCDE")
    params = BacktestParams(
        risk_overlay_enabled=True,
        target_volatility=0.05,
        min_equity_exposure=0.0,
        risk_fast_lookback=63,
        risk_slow_lookback=252,
    )
    relative = {s: 0.2 for s in symbols}
    targets, info = risk_adjusted_targets(prices, symbols, 350, relative, params)
    assert 0.0 < sum(targets.values()) < 1.0
    assert info["exposure_state"] == "volatility_de_risked"
    assert info["strategic_floor_applied"] is False


def test_initial_deployment_is_independent_from_late_annual_recalibration():
    prices = _panel()
    candidate = Candidate(tuple("ABCDE"), (221,))
    params = BacktestParams(
        minimum_observations=60,
        lookback_days=252,
        risk_overlay_enabled=False,
    )
    window = (str(prices.index[0].date()), str(prices.index[-1].date()))
    init = initial_deployment_date(candidate, prices, params, window, warmup_days=252)
    assert init is not None
    # The portfolio can initialize after enough past observations; it must not sit
    # in cash waiting for trading-session 221 of the calendar year.
    assert init <= prices.index[70]

    dates, returned_init = allocation_dates_with_initialization(
        candidate, prices, params, list(prices.index), window, warmup_days=252
    )
    assert returned_init == init
    assert init in dates
    assert any(pd.Timestamp(d) > init for d in dates)


def test_warmup_can_initialize_before_measurement_boundary():
    prices = _panel()
    candidate = Candidate(tuple("ABCDE"), (221,))
    params = BacktestParams(minimum_observations=60, lookback_days=252)
    start = prices.index[300]
    end = prices.index[-1]
    init = initial_deployment_date(
        candidate,
        prices,
        params,
        (str(start.date()), str(end.date())),
        warmup_days=252,
    )
    assert init is not None
    assert init < start
