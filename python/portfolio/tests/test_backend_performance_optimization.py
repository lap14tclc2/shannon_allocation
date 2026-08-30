"""
Regression contracts for TASK-20260829-061: backend CPU/RAM optimization.

Covers:
1. Request-scoped effective_events memo (same result, cleared on write).
2. Batched latest_prices / price_histories / list_snapshots keep contracts.
3. external_cache is bounded and still correct.
4. Connection pool exists, is lazy, and is bounded (no DB required).
"""
import pytest

from portfolio.external_cache import cached_external_call, clear_external_cache
from portfolio.corrections import (
    begin_request_memo,
    clear_request_memo,
    end_request_memo,
    effective_events,
    ensure_schema,
)
from portfolio.storage import PortfolioStore
from portfolio.service import PortfolioService
from portfolio.domain import EventType, LedgerEvent


def _make_store(tmp_path):
    store = PortfolioStore(str(tmp_path / "book.sqlite3"))
    store.initialize()
    ensure_schema(store)
    return store


def _add_deposit(store, date="2026-01-02", amount=1_000_000):
    store.append_event(
        LedgerEvent(
            id=None,
            event_type=EventType.CASH_DEPOSIT,
            event_date=date,
            amount=amount,
            created_by="t",
        )
    )


def test_request_memo_reuses_effective_events_within_scope(tmp_path):
    store = _make_store(tmp_path)
    _add_deposit(store)
    memo, token = begin_request_memo()
    try:
        first = effective_events(store)
        second = effective_events(store)
        assert first == second
        assert first is not second  # callers get a copy, cache cannot be corrupted
        clear_request_memo()
        third = effective_events(store)
        assert third == first
    finally:
        end_request_memo(token)


def test_request_memo_is_inactive_outside_http_request(tmp_path):
    # Tests/CLI (no begin_request_memo) never memoize -> always fresh objects.
    store = _make_store(tmp_path)
    _add_deposit(store)
    a = effective_events(store)
    b = effective_events(store)
    assert a == b


def test_latest_prices_batch_returns_latest_per_symbol(tmp_path):
    store = PortfolioStore(str(tmp_path / "book.sqlite3"))
    store.initialize()
    store.upsert_market_prices([
        {"symbol": "AAA", "trading_date": "2026-01-02", "close": 10.0, "source": "test"},
        {"symbol": "AAA", "trading_date": "2026-01-03", "close": 11.0, "source": "test"},
        {"symbol": "BBB", "trading_date": "2026-01-03", "close": 20.0, "source": "test"},
    ])
    out = store.latest_prices(["AAA", "BBB"])
    assert set(out) == {"AAA", "BBB"}
    assert out["AAA"]["close"] == pytest.approx(11.0)  # latest
    assert out["BBB"]["close"] == pytest.approx(20.0)
    # Empty input never errors.
    assert store.latest_prices([]) == {}


def test_price_histories_batch_returns_ascending_rows(tmp_path):
    store = PortfolioStore(str(tmp_path / "book.sqlite3"))
    store.initialize()
    store.upsert_market_prices([
        {"symbol": "AAA", "trading_date": "2026-01-01", "close": 10.0, "source": "test"},
        {"symbol": "AAA", "trading_date": "2026-01-02", "close": 11.0, "source": "test"},
        {"symbol": "AAA", "trading_date": "2026-01-03", "close": 12.0, "source": "test"},
    ])
    hist = store.price_histories(["AAA"], limit=100)
    dates = [r["trading_date"] for r in hist["AAA"]]
    assert dates == ["2026-01-01", "2026-01-02", "2026-01-03"]  # ascending
    assert store.price_histories([]) == {}


def test_list_snapshots_loads_positions_in_batch(tmp_path):
    store = PortfolioStore(str(tmp_path / "book.sqlite3"))
    store.initialize()
    store.save_snapshot(
        {
            "snapshot_date": "2026-01-02",
            "nav": 100_000.0,
            "equity_value": 100_000.0,
            "cash": 0.0,
            "official": True,
        },
        [
            {"symbol": "AAA", "shares": 100, "average_cost": 10, "price": 12, "cost_value": 1000,
             "market_value": 1200, "weight": 1.0, "unrealized_pnl": 200, "unrealized_return": 0.2,
             "risk_contribution": 1.0, "erc_reference_weight": 1.0, "status": "HOLD"},
        ],
    )
    store.save_snapshot(
        {
            "snapshot_date": "2026-01-03",
            "nav": 110_000.0,
            "equity_value": 110_000.0,
            "cash": 0.0,
            "official": True,
        },
        [
            {"symbol": "AAA", "shares": 100, "average_cost": 10, "price": 13, "cost_value": 1000,
             "market_value": 1300, "weight": 1.0, "unrealized_pnl": 300, "unrealized_return": 0.3,
             "risk_contribution": 1.0, "erc_reference_weight": 1.0, "status": "HOLD"},
        ],
    )
    snapshots = store.list_snapshots(limit=100)
    assert len(snapshots) == 2
    for snap in snapshots:
        assert len(snap["positions"]) == 1
        assert snap["positions"][0]["symbol"] == "AAA"


def test_external_cache_is_bounded():
    clear_external_cache()
    calls = {"n": 0}
    for i in range(600):  # exceeds default cap 512
        def _loader():
            calls["n"] += 1
            return {"i": i}
        cached_external_call("bulk", i, _loader, ttl_seconds=60)
    from portfolio import external_cache as ec
    assert len(ec._CACHE) <= ec._MAX_ENTRIES


def test_connection_pool_is_lazy_and_bounded():
    from portfolio import postgres as pg
    stats = pg.connection_pool_stats()
    assert stats["idle"] == 0
    assert stats["max_idle"] >= 1
    assert stats["max_total"] >= stats["max_idle"]
    pg.close_connection_pool()
    assert pg.connection_pool_stats()["idle"] == 0