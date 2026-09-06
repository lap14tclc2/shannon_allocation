"""T10 — VNIndex benchmark tests."""
from __future__ import annotations

import pandas as pd
import pytest

from portfolio.research.benchmark import (
    BenchmarkError,
    VNIndexBenchmark,
    benchmark_return_exact,
    forward_benchmark_return,
    normalize_benchmark,
    validate_benchmark_points,
)


def _frame(closes, start="2023-01-02", periods=None):
    dates = pd.bdate_range(start=start, periods=periods or len(closes))
    return pd.DataFrame({"close": closes, "source": "fake"}, index=dates)


def _provider_for(df, symbol="VNINDEX"):
    class FakeMarket:
        name = "fake"
        def daily_history(self, sym, start, end):
            assert str(sym).upper() == symbol.upper()
            return df.loc[(df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))].copy()
        def health(self):
            return {"provider": "fake"}
    return FakeMarket()


def test_vnindex_fetch_normalize_contract():
    market = _provider_for(_frame([1100.0, 1110.0, 1090.0]))
    bench = VNIndexBenchmark(market=market)
    history = bench.history("2023-01-01", "2023-01-10")
    assert list(history.columns) == ["benchmark", "close", "source"]
    assert history["benchmark"].iloc[0] == "VNINDEX"
    # Index points are NOT scaled like VND prices.
    assert history["close"].iloc[0] == 1100.0


def test_vnindex_points_not_vnd_scaled():
    # Even when the index dips below 1000, no canonical_vnd_price scaling.
    df = _frame([900.0, 910.0])
    normalized = normalize_benchmark(df, "VNINDEX")
    assert normalized["close"].iloc[0] == 900.0
    assert normalized["close"].iloc[-1] == 910.0


def test_invalid_benchmark_handling():
    with pytest.raises(BenchmarkError):
        normalize_benchmark(pd.DataFrame())
    flat = _frame([100.0, 100.0, 100.0])
    with pytest.raises(BenchmarkError):
        validate_benchmark_points(flat["close"], "VNINDEX")
    market = _provider_for(_frame([0.0, -5.0]))
    with pytest.raises(BenchmarkError):
        VNIndexBenchmark(market=market).history("2023-01-01", "2023-01-10")


def test_unsupported_benchmark_rejected():
    market = _provider_for(_frame([100.0]))
    with pytest.raises(BenchmarkError):
        VNIndexBenchmark(market=market, symbol="VN30").history("2023-01-01", "2023-01-10")


def test_deterministic_return_math():
    close = pd.Series([100.0, 110.0, 121.0], index=pd.bdate_range("2023-01-02", periods=3))
    # R(t,2) = 121/100 - 1 = 21%
    assert forward_benchmark_return(close, "2023-01-02", 2) == pytest.approx(0.21)
    assert benchmark_return_exact(close, "2023-01-02", "2023-01-04") == pytest.approx(0.21)
    # Unresolved horizon beyond the series -> None.
    assert forward_benchmark_return(close, "2023-01-02", 3) is None
    # Base date missing -> None.
    assert forward_benchmark_return(close, "2022-01-02", 1) is None


def test_trading_date_alignment_and_missing_day_policy():
    close = pd.Series([100.0, 110.0, 121.0, 133.1], index=pd.bdate_range("2023-01-02", periods=4))
    # A date not in the series aligns to the last available before it.
    assert benchmark_return_exact(close, "2023-01-02", "2023-01-07") == pytest.approx(133.1 / 100.0 - 1.0)
    # End beyond the series aligns to the last available close (documented).
    assert benchmark_return_exact(close, "2023-01-02", "2024-01-02") == pytest.approx(133.1 / 100.0 - 1.0)
    # Start before the series -> None (no fabricated base).
    assert benchmark_return_exact(close, "2022-01-02", "2023-01-03") is None


def test_no_forward_leakage_in_benchmark():
    # history() must only return rows in the requested window.
    df = _frame([100.0, 110.0, 120.0, 130.0], start="2023-01-02")
    bench = VNIndexBenchmark(market=_provider_for(df))
    history = bench.history("2023-01-02", "2023-01-03")
    assert len(history) == 2


def test_verify_reports_mapping_evidence():
    df = _frame([1100.0, 1110.0])
    bench = VNIndexBenchmark(market=_provider_for(df))
    report = bench.verify("2023-01-01", "2023-01-10")
    assert report["ok"] is True
    assert report["symbol"] == "VNINDEX"
    assert report["points"] == 2
    assert report["last_close"] == 1110.0


def test_verify_failure_is_reported_not_assumed():
    class Broken:
        name = "broken"
        def daily_history(self, sym, start, end):
            raise RuntimeError("provider down")
        def health(self):
            return {"provider": "broken", "available": False}
    bench = VNIndexBenchmark(market=Broken())
    report = bench.verify("2023-01-01", "2023-01-10")
    assert report["ok"] is False
    assert "provider down" in report["error"]