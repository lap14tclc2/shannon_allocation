"""T12 — Forward outcomes tests."""
from __future__ import annotations

import pandas as pd
import pytest

from portfolio.research.outcomes import (
    build_outcomes,
    forward_benchmark_return,
    forward_excess_return,
    forward_stock_return,
)


def _stock_frame(closes, start="2023-01-02"):
    return pd.DataFrame({"close": closes}, index=pd.bdate_range(start, periods=len(closes)))


def _benchmark_frame(closes, start="2023-01-02"):
    return pd.DataFrame({"close": closes, "source": "fake"}, index=pd.bdate_range(start, periods=len(closes)))


def _snapshot(symbol="FPT", date="2023-01-02"):
    return {"snapshot_date": date, "symbol": symbol, "source_hash": "abc", "created_at": "x"}


def test_future_return_horizon_exact():
    stock = _stock_frame([100.0, 110.0, 121.0, 133.1, 146.41, 161.05])
    # 2-session forward return from 2023-01-02: 121/100 - 1 = 21%.
    assert forward_stock_return(stock, "2023-01-02", 2) == pytest.approx(0.21)
    # 4-session: 146.41/100 - 1.
    assert forward_stock_return(stock, "2023-01-02", 4) == pytest.approx(0.4641)


def test_unresolved_future_remains_missing():
    stock = _stock_frame([100.0, 110.0])
    assert forward_stock_return(stock, "2023-01-02", 5) is None
    assert forward_stock_return(stock, "2023-01-03", 1) is None  # no session after


def test_excess_return_exact():
    stock = _stock_frame([100.0, 110.0, 121.0, 133.1, 146.41, 161.05])
    benchmark = _benchmark_frame([1000.0, 1010.0, 1020.0, 1030.0, 1040.0, 1050.0])
    stock_r, bench_r, excess = forward_excess_return(stock, benchmark, "2023-01-02", 2)
    assert stock_r == pytest.approx(0.21)
    assert bench_r == pytest.approx(0.02)
    assert excess == pytest.approx(0.19)


def test_missing_benchmark_means_missing_excess():
    stock = _stock_frame([100.0, 110.0, 121.0, 133.1, 146.41, 161.05])
    empty_benchmark = pd.DataFrame(columns=["close"])
    _, _, excess = forward_excess_return(stock, empty_benchmark, "2023-01-02", 3)
    assert excess is None


def test_no_leakage_of_outcomes_into_factor_computation():
    # The outcomes module only reads future labels; it never mutates snapshots.
    snap = _snapshot()
    price_provider = lambda symbol: _stock_frame([100.0, 110.0, 121.0])
    benchmark = _benchmark_frame([1000.0, 1005.0, 1010.0])
    rows = build_outcomes(price_provider, benchmark, [snap], horizons=(2,))
    assert rows[0]["forward_excess_return_2"] is not None
    assert "forward_excess_return_2" in rows[0]
    # Snapshot input is not mutated.
    assert "forward_excess_return_2" not in snap


def test_benchmark_alignment_uses_last_available_before_date():
    stock = _stock_frame([100.0, 110.0, 121.0])
    benchmark = _benchmark_frame([1000.0, 1010.0, 1020.0, 1030.0, 1040.0, 1050.0])
    # End date (2023-01-04) aligns to benchmark close on that date.
    stock_r, bench_r, excess = forward_excess_return(stock, benchmark, "2023-01-02", 2)
    assert bench_r == pytest.approx(0.02)


def test_stock_suspension_missing_day_policy_explicit():
    # A stock series with a gap: forward return uses the stock's own sessions,
    # so a missing internal day still uses the h-th session in the series.
    stock = _stock_frame([100.0, 110.0, 121.0, 133.1, 146.41, 161.05])
    assert forward_stock_return(stock, "2023-01-02", 2) == pytest.approx(0.21)


def test_outcomes_never_forward_filled():
    rows = build_outcomes(
        lambda symbol: _stock_frame([100.0, 110.0]),
        _benchmark_frame([1000.0, 1010.0]),
        [_snapshot(date="2023-01-02")],
        horizons=(21, 63),
    )
    # Late snapshot with no future sessions -> missing, not filled.
    assert rows[0]["forward_stock_return_21"] is None