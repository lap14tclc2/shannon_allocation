from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from portfolio.market_data import canonical_vnd_price, frame_to_price_rows
from portfolio.service import PortfolioService
from portfolio.storage import PortfolioStore


class DummyMarket:
    def health(self):
        return {"provider": "dummy", "available": True}


@pytest.mark.parametrize(
    ("source", "raw", "expected"),
    [
        ("vndirect", 22.75, 22_750.0),
        ("vnstock", 72.0, 72_000.0),
        ("vndirect", 43_050.0, 43_050.0),
        ("fake", 72.0, 72.0),
    ],
)
def test_canonical_vnd_price_is_provider_aware_and_idempotent(source, raw, expected):
    assert canonical_vnd_price(raw, source) == expected


def test_frame_to_price_rows_normalizes_all_ohlc_to_absolute_vnd():
    df = pd.DataFrame(
        {
            "open": [71.5],
            "high": [72.5],
            "low": [71.0],
            "close": [72.0],
            "volume": [1_000_000],
            "source": ["vndirect"],
        },
        index=pd.to_datetime(["2026-08-21"]),
    )
    row = frame_to_price_rows("FPT", df, source="vndirect")[0]
    assert row["open"] == 71_500
    assert row["high"] == 72_500
    assert row["low"] == 71_000
    assert row["close"] == 72_000
    assert row["source"] == "vndirect"


def test_existing_legacy_provider_prices_are_migrated_once(tmp_path: Path):
    path = tmp_path / "portfolio.sqlite3"
    store = PortfolioStore(path)
    store.upsert_market_prices([
        {
            "symbol": "FPT",
            "trading_date": "2026-08-21",
            "open": 71.5,
            "high": 72.5,
            "low": 71.0,
            "close": 72.0,
            "volume": 1_000_000,
            "source": "vndirect",
            "is_final": True,
            "data_quality": "VALID",
        }
    ])
    # Simulate a DB produced by the pre-fix build, before this migration marker
    # existed. Re-opening the store must repair it exactly once.
    with store.connect() as db:
        db.execute("DELETE FROM app_meta WHERE key = 'price_units_vnd_v1'")

    migrated = PortfolioStore(path)
    row = migrated.latest_price("FPT")
    assert row["open"] == 71_500
    assert row["high"] == 72_500
    assert row["low"] == 71_000
    assert row["close"] == 72_000
    assert migrated.get_meta("price_units_vnd_v1") == "migrated:1"

    # A second initialization is idempotent: 72,000 must not become 72,000,000.
    reopened = PortfolioStore(path)
    assert reopened.latest_price("FPT")["close"] == 72_000


def test_dashboard_market_value_and_unrealized_pnl_use_vnd_units(tmp_path: Path):
    store = PortfolioStore(tmp_path / "portfolio.sqlite3")
    svc = PortfolioService(store, DummyMarket())
    svc.append_event({
        "event_type": "POSITION_IMPORT",
        "event_date": "2026-01-02",
        "symbol": "FPT",
        "quantity": 3_000,
        "price": 74_025,
    })
    store.upsert_market_prices([
        {
            "symbol": "FPT",
            "trading_date": "2026-08-21",
            "open": 71_500,
            "high": 72_500,
            "low": 71_000,
            "close": 72_000,
            "volume": 1_000_000,
            "source": "vndirect",
            "is_final": True,
            "data_quality": "VALID",
        }
    ])

    position = svc.dashboard()["portfolio"]["positions"][0]
    assert position["price"] == 72_000
    assert position["market_value"] == 216_000_000
    assert position["unrealized_pnl"] == -6_075_000
    assert position["unrealized_return"] == pytest.approx(-6_075_000 / 222_075_000)
