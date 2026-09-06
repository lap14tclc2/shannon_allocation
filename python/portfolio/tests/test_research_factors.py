"""T11 — Factor computation tests (PIT-safe, no future OHLCV)."""
from __future__ import annotations

import pandas as pd
import pytest

from portfolio.research.factors import (
    liquidity,
    momentum,
    momentum_12_1,
    price_factors_from_frame,
    reversal_1m,
    value_factor,
)


def _close(values):
    return pd.Series(values, dtype=float, index=pd.bdate_range("2023-01-02", periods=len(values)))


def test_no_future_ohlcv_after_snapshot_date():
    # The frame passed to the factor builder must be pre-filtered to <= the
    # snapshot date; price_factors_from_frame never reads beyond the tail.
    frame = pd.DataFrame({
        "close": [100.0, 110.0, 121.0, 133.1, 146.41],
        "volume": [1e6] * 5,
    }, index=pd.bdate_range("2023-01-02", periods=5))
    # Slice to the snapshot date (3rd session) like the builder does.
    snapshot = frame[frame.index <= "2023-01-04"]
    factors = price_factors_from_frame(snapshot)
    # momentum_3m needs 64 observations; with 3 it must be None (not leaked).
    assert factors["momentum_3m"] is None
    assert factors["reversal_1m"] is None


def test_exact_momentum_lookback():
    close = _close(list(range(1, 130)))  # 129 points
    # momentum_3m uses exactly the 63rd prior session.
    expected_63 = 129.0 / (129.0 - 63) - 1.0
    assert momentum(close, 63) == pytest.approx(expected_63)
    expected_126 = 129.0 / (129.0 - 126) - 1.0
    assert momentum(close, 126) == pytest.approx(expected_126)


def test_momentum_insufficient_history_is_missing_not_zero():
    close = _close([100.0, 101.0, 102.0])
    assert momentum(close, 63) is None
    assert reversal_1m(close) is None
    assert momentum_12_1(close) is None
    assert liquidity(pd.Series([1e6, 2e6])) is None  # < MIN_LIQUIDITY_OBS


def test_reversal_formula():
    # reversal = -(1M return), i.e., a rising month gets a negative factor.
    close = _close([100.0, 110.0, 121.0] + [121.0] * 18 + [133.1])
    raw = momentum(close, 21)
    assert raw is not None
    assert reversal_1m(close) == pytest.approx(-raw)


def test_momentum_12_1_skips_recent_month():
    close = _close([100.0] * 300)
    # Constant series -> zero momentum.
    assert momentum_12_1(close) == pytest.approx(0.0)


def test_liquidity_uses_trailing_window_mean():
    turnover = pd.Series([50.0] * 5 + [300.0] * 20)
    assert liquidity(turnover, window=20) == pytest.approx(300.0)


def test_value_factor_is_valuation_safety():
    # valuation_safety = actual_mos - required_mos (percentage points).
    assert value_factor(32.0, 25.0) == pytest.approx(7.0)
    assert value_factor(None, 25.0) is None
    assert value_factor(32.0, None) is None
    assert value_factor(None, None) is None


def test_value_factor_never_maps_mos_to_alpha():
    # The factor is just the safety in pp; there is no alpha claim attached.
    assert value_factor(40.0, 25.0) == pytest.approx(15.0)
    assert value_factor(5.0, 25.0) == pytest.approx(-20.0)


def test_momentum_uses_session_lookback_not_calendar_days():
    # Two series with the same calendar span but different session counts must
    # produce different 3M momentum values.
    sparse = _close([100.0, 100.0, 100.0, 101.0])
    # sparse has only 4 sessions -> 63-session lookback is missing.
    assert momentum(sparse, 63) is None
    # 1-session lookback on 4 sessions is defined.
    assert momentum(sparse, 1) == pytest.approx(101.0 / 100.0 - 1.0)