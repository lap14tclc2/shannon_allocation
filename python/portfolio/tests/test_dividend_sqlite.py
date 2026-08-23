from __future__ import annotations

from portfolio.accounting import derive_state
from portfolio.dividend_store import SqliteDividendService
from portfolio.dividends import DividendEvent
from portfolio.institutional import InstitutionalBook
from portfolio.storage import PortfolioStore


class StaticProvider:
    def __init__(self, name: str, events=None, error: Exception | None = None):
        self.name = name
        self._events = list(events or [])
        self._error = error
        self.calls = 0

    def health(self):
        return {"provider": self.name, "available": self._error is None}

    def events(self, symbol, start, end):
        self.calls += 1
        if self._error:
            raise self._error
        return list(self._events)


def test_dividend_cache_survives_restart_and_avoids_provider_on_hit(tmp_path):
    path = tmp_path / "portfolio.sqlite3"
    provider = StaticProvider(
        "test_provider",
        [
            DividendEvent(
                symbol="FPT",
                dividend_type="CASH_DIVIDEND",
                source="test_provider",
                source_event_id="old",
                record_date="2025-05-20",
                payment_date="2025-06-10",
                cash_per_share=1000,
            ),
            DividendEvent(
                symbol="FPT",
                dividend_type="STOCK_DIVIDEND",
                source="test_provider",
                source_event_id="new",
                record_date="2026-07-20",
                payment_date="2026-08-10",
                stock_ratio=0.15,
            ),
        ],
    )

    store = PortfolioStore(path)
    service = SqliteDividendService(store, [provider], stop_on_first_data=True)
    first = service.history("FPT")

    assert first["data_origin"] == "PROVIDER_REFRESH"
    assert first["event_count"] == 2
    assert first["latest_event_date"] == "2026-07-20"
    assert provider.calls == 1

    cached = service.history("FPT")
    assert cached["data_origin"] == "SQLITE_CACHE"
    assert cached["cache_hit"] is True
    assert provider.calls == 1

    restarted = SqliteDividendService(PortfolioStore(path), [provider], stop_on_first_data=True)
    after_restart = restarted.history("FPT")
    assert after_restart["data_origin"] == "SQLITE_CACHE"
    assert after_restart["event_count"] == 2
    assert provider.calls == 1


def test_force_refresh_calls_provider_and_does_not_duplicate_history(tmp_path):
    provider = StaticProvider(
        "test_provider",
        [
            DividendEvent(
                symbol="ACB",
                dividend_type="CASH_DIVIDEND",
                source="test_provider",
                source_event_id="cash",
                record_date="2026-06-16",
                payment_date="2026-07-01",
                cash_per_share=700,
            )
        ],
    )
    service = SqliteDividendService(
        PortfolioStore(tmp_path / "portfolio.sqlite3"),
        [provider],
        stop_on_first_data=True,
    )

    assert service.history("ACB")["event_count"] == 1
    refreshed = service.history("ACB", force_refresh=True)
    assert refreshed["data_origin"] == "PROVIDER_REFRESH"
    assert refreshed["event_count"] == 1
    assert provider.calls == 2


def test_cross_provider_rows_merge_into_one_canonical_event_family(tmp_path):
    vps = StaticProvider(
        "vps_events",
        [
            DividendEvent(
                symbol="ACB",
                dividend_type="CASH_DIVIDEND",
                source="vps_events",
                source_event_id="vps-cash",
                announcement_date="2026-06-05",
                ex_date="2026-06-15",
                record_date="2026-06-16",
                cash_per_share=700,
            ),
            DividendEvent(
                symbol="ACB",
                dividend_type="STOCK_DIVIDEND",
                source="vps_events",
                source_event_id="vps-stock",
                announcement_date="2026-06-05",
                ex_date="2026-06-15",
                record_date="2026-06-16",
                stock_ratio=0.13,
            ),
        ],
    )
    cafef = StaticProvider(
        "cafef_public",
        [
            DividendEvent(
                symbol="ACB",
                dividend_type="CASH_DIVIDEND",
                source="cafef_public",
                source_event_id="cafef-cash",
                ex_date="2026-06-15",
                cash_per_share=700,
            ),
            DividendEvent(
                symbol="ACB",
                dividend_type="STOCK_DIVIDEND",
                source="cafef_public",
                source_event_id="cafef-stock",
                ex_date="2026-06-15",
                stock_ratio=0.13,
            ),
        ],
    )
    service = SqliteDividendService(
        PortfolioStore(tmp_path / "portfolio.sqlite3"),
        [vps, cafef],
        stop_on_first_data=False,
    )

    result = service.history("ACB")

    assert result["event_count"] == 2
    assert {row["dividend_type"] for row in result["events"]} == {
        "CASH_DIVIDEND",
        "STOCK_DIVIDEND",
    }
    assert {row["source"] for row in result["events"]} == {"vps_events"}
    assert all(row["cross_source_match"] is True for row in result["events"])
    assert all(set(row["duplicate_sources"]) == {"vps_events", "cafef_public"} for row in result["events"])


def test_cash_percent_is_not_misreported_as_second_stock_dividend(tmp_path):
    title = "ACB 7% cash and 13% stock dividend"
    provider = StaticProvider(
        "vps_events",
        [
            DividendEvent(
                symbol="ACB",
                dividend_type="CASH_DIVIDEND",
                source="vps_events",
                source_event_id="combined",
                title=title,
                ex_date="2026-06-15",
                record_date="2026-06-16",
                cash_per_share=700,
            ),
            DividendEvent(
                symbol="ACB",
                dividend_type="STOCK_DIVIDEND",
                source="vps_events",
                source_event_id="combined",
                title=title,
                ex_date="2026-06-15",
                record_date="2026-06-16",
                stock_ratio=0.07,
            ),
            DividendEvent(
                symbol="ACB",
                dividend_type="STOCK_DIVIDEND",
                source="vps_events",
                source_event_id="real-stock",
                title=title,
                ex_date="2026-06-15",
                record_date="2026-06-16",
                stock_ratio=0.13,
            ),
        ],
    )
    service = SqliteDividendService(
        PortfolioStore(tmp_path / "portfolio.sqlite3"),
        [provider],
        stop_on_first_data=True,
    )

    result = service.history("ACB")
    stock_rows = [row for row in result["events"] if row["dividend_type"] == "STOCK_DIVIDEND"]

    assert result["event_count"] == 2
    assert len(stock_rows) == 1
    assert stock_rows[0]["stock_ratio"] == 0.13


def test_empty_provider_result_is_negative_cached(tmp_path):
    provider = StaticProvider("empty_provider", [])
    service = SqliteDividendService(
        PortfolioStore(tmp_path / "portfolio.sqlite3"),
        [provider],
        stop_on_first_data=True,
    )

    first = service.history("DGC")
    second = service.history("DGC")

    assert first["found"] is False
    assert first["data_origin"] == "PROVIDER_REFRESH"
    assert second["found"] is False
    assert second["data_origin"] == "SQLITE_CACHE"
    assert provider.calls == 1


def test_dividend_tables_live_in_same_portfolio_database(tmp_path):
    path = tmp_path / "portfolio.sqlite3"
    store = PortfolioStore(path)
    SqliteDividendService(store, [StaticProvider("empty", [])])

    with store.connect() as db:
        tables = {
            row["name"]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

    assert "ledger_events" in tables
    assert "portfolio_snapshots" in tables
    assert "dividend_events" in tables
    assert "dividend_fetch_state" in tables


def test_operations_are_persisted_in_sqlite_across_service_restart(tmp_path):
    path = tmp_path / "portfolio.sqlite3"
    first_store = PortfolioStore(path)
    first_book = InstitutionalBook(first_store, today_fn=lambda: "2026-08-23")
    state = derive_state([])

    result = first_book.reconcile(
        state,
        {
            "cash": 0,
            "positions": {},
            "account_id": "PRIMARY",
            "as_of_date": "2026-08-23",
            "note": "persistence check",
        },
    )
    assert result["status"] == "MATCH"

    second_book = InstitutionalBook(PortfolioStore(path), today_fn=lambda: "2026-08-23")
    rows = second_book.reconciliations()

    assert rows
    assert rows[0]["id"] == result["run_id"]
    assert rows[0]["note"] == "persistence check"
