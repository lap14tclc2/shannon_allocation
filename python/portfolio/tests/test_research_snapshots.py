"""T11 — Factor snapshot builder + persistence tests."""
from __future__ import annotations

import pandas as pd
import pytest

from portfolio.research.snapshots import SnapshotDeps, build_snapshot_row, build_snapshots
from portfolio.research.store import ResearchStore, _sqlite_factory


def _facts():
    return [
        {
            "symbol": "FPT", "line_item_code": "IS.PROFIT.NET", "value": 100.0,
            "period_type": "FY", "fiscal_year": 2022, "fiscal_quarter": None,
            "period_end": "2022-12-31", "observed_at": "2024-01-01T00:00:00Z",
        },
        {
            "symbol": "FPT", "line_item_code": "BS.EQUITY.TOTAL", "value": 500.0,
            "period_type": "FY", "fiscal_year": 2022, "fiscal_quarter": None,
            "period_end": "2022-12-31", "observed_at": "2024-01-01T00:00:00Z",
        },
    ]


def _prices():
    closes = [100.0 + i for i in range(300)]
    return pd.DataFrame({"close": closes}, index=pd.bdate_range("2023-01-02", periods=len(closes)))


def _deps(valuator=None, quality=None, price=None, facts=None):
    def fact_provider(symbol, as_of):
        return [dict(f) for f in facts or _facts()]

    def price_provider(symbol, as_of):
        frame = price if price is not None else _prices()
        return frame[frame.index <= pd.Timestamp(as_of)]

    def default_valuator(facts_, price_):
        if not facts_:
            return (None, None)
        return (30.0, 25.0)

    def default_quality(facts_):
        return (85, "HIGH_QUALITY")

    return SnapshotDeps(
        fact_provider=fact_provider,
        price_provider=price_provider,
        pit_valuator=valuator or default_valuator,
        pit_quality=quality or default_quality,
    )


def test_snapshot_uses_only_pit_facts_for_value_and_quality():
    captured = {}

    def valuator(facts, price):
        # The facts seen by the value valuator must all be PIT-available.
        for fact in facts:
            assert fact["available_from"] <= "2023-04-01"
        captured["value_facts"] = len(facts)
        return (30.0, 25.0)

    def quality(facts):
        # The facts seen by the quality scorer must all be PIT-available too.
        for fact in facts:
            assert fact["available_from"] <= "2023-04-01"
        captured["quality_facts"] = len(facts)
        return (85, "HIGH_QUALITY")

    deps = _deps(valuator=valuator, quality=quality)
    row = build_snapshot_row(deps, symbol="FPT", snapshot_date="2023-04-01")
    assert captured["value_facts"] >= 2
    assert captured["quality_facts"] >= 2
    assert row["value_factor"] == pytest.approx(5.0)  # 30 - 25
    assert row["quality_factor"] == 85


def test_future_facts_invisible_to_snapshot():
    future_fact = {
        "symbol": "FPT", "line_item_code": "IS.PROFIT.NET", "value": 999.0,
        "period_type": "FY", "fiscal_year": 2022, "fiscal_quarter": None,
        "period_end": "2022-12-31", "observed_at": "2025-01-01T00:00:00Z",
    }
    # A fact crawled "now" for an old period is still invisible at an early date
    # because availability uses the governance lag, not observed_at.
    deps = _deps(facts=[future_fact])
    row = build_snapshot_row(deps, symbol="FPT", snapshot_date="2023-01-31")
    assert row["value_factor"] is None


def test_no_future_ohlcv_used_in_snapshot():
    seen = {}
    max_date = str(_prices().index.max().date())

    def price_provider(symbol, as_of):
        frame = _prices()
        sliced = frame[frame.index <= pd.Timestamp(as_of)]
        seen["max_date"] = str(sliced.index.max().date())
        return sliced

    deps = _deps(price=price_provider("FPT", max_date))
    row = build_snapshot_row(deps, symbol="FPT", snapshot_date=max_date)
    assert seen["max_date"] == max_date
    # Momentum factors use only the sliced tail.
    assert row["momentum_3m"] is not None


def test_insufficient_history_means_missing_momentum():
    deps = _deps(price=pd.DataFrame({"close": [100.0, 101.0]}, index=pd.bdate_range("2023-01-02", periods=2)))
    row = build_snapshot_row(deps, symbol="FPT", snapshot_date="2023-01-03")
    assert row["momentum_3m"] is None
    assert row["momentum_12m"] is None


def test_same_input_same_source_hash_reproducible():
    a = build_snapshot_row(_deps(), symbol="FPT", snapshot_date="2023-03-01")
    b = build_snapshot_row(_deps(), symbol="FPT", snapshot_date="2023-03-01")
    assert a["source_hash"] == b["source_hash"]
    assert a["value_factor"] == b["value_factor"]
    # Different snapshot date -> different hash (different input state).
    c = build_snapshot_row(_deps(), symbol="FPT", snapshot_date="2023-03-15")
    assert a["source_hash"] != c["source_hash"]


def test_snapshot_row_records_provenance():
    row = build_snapshot_row(_deps(), symbol="FPT", snapshot_date="2023-03-01")
    for key in ("snapshot_date", "symbol", "source_hash", "factor_version", "created_at"):
        assert key in row
    assert row["factor_version"] == "1.0.0"


def test_store_schema_and_snapshot_roundtrip(tmp_path):
    store = ResearchStore(connection_factory=_sqlite_factory(str(tmp_path / "research.sqlite3")))
    store.create_schema()
    rows = build_snapshots(
        _deps(),
        symbols=["FPT", "VNM"],
        snapshot_dates=["2023-03-01", "2023-03-02"],
    )
    count = store.write_snapshots("run-1", rows)
    assert count == 4
    loaded = store.read_snapshots("run-1")
    assert len(loaded) == 4
    assert {r["symbol"] for r in loaded} == {"FPT", "VNM"}
    # Determinism: same run id re-write is idempotent.
    store.write_snapshots("run-1", rows)
    assert len(store.read_snapshots("run-1")) == 4


def test_store_benchmark_prices_roundtrip(tmp_path):
    store = ResearchStore(connection_factory=_sqlite_factory(str(tmp_path / "bench.sqlite3")))
    store.create_schema()
    rows = [
        {"benchmark": "VNINDEX", "trading_date": "2023-01-02", "close": 1100.0,
         "source": "fake", "fetched_at": "x", "data_quality": "VALID"},
        {"benchmark": "VNINDEX", "trading_date": "2023-01-03", "close": 1110.0,
         "source": "fake", "fetched_at": "x", "data_quality": "VALID"},
    ]
    store.write_benchmark_prices(rows)
    loaded = store.read_benchmark_prices("VNINDEX")
    assert len(loaded) == 2
    assert loaded[0]["close"] == 1100.0


def test_store_outcomes_roundtrip(tmp_path):
    store = ResearchStore(connection_factory=_sqlite_factory(str(tmp_path / "out.sqlite3")))
    store.create_schema()
    snap = build_snapshot_row(_deps(), symbol="FPT", snapshot_date="2023-01-02")
    from portfolio.research.outcomes import build_outcomes

    stock = pd.DataFrame({"close": [100.0, 110.0, 121.0, 133.1, 146.41, 161.05, 177.16]},
                         index=pd.bdate_range("2023-01-02", periods=7))
    benchmark = pd.DataFrame({"close": [1000.0] * 7}, index=stock.index)
    outcomes = build_outcomes(lambda s: stock, benchmark, [snap], horizons=(21, 63))
    count = store.write_outcomes("run-1", outcomes)
    # The store persists all standard horizons (21/63/126/252) per snapshot;
    # unresolved horizons stay NULL.
    assert count == 4
    with store._connect() as db:
        fetched = db.execute(
            "SELECT horizon_sessions, forward_excess_return FROM research_factor_outcomes "
            "WHERE run_id = ? ORDER BY horizon_sessions",
            ("run-1",),
        ).fetchall()
    assert [row["horizon_sessions"] for row in fetched] == [21, 63, 126, 252]
    # Short series -> unresolved horizons are NULL, never forward-filled.
    assert fetched[0]["forward_excess_return"] is None