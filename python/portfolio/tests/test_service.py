from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from portfolio.service import PortfolioService
from portfolio.storage import PortfolioStore


class FakeMarket:
    def health(self):
        return {"provider": "fake", "policy": ["fake"]}

    def daily_history_with_source(self, symbol, start, end):
        end_date = date.fromisoformat(end)
        dates = pd.bdate_range(end=end_date, periods=320)
        t = np.arange(len(dates), dtype=float)
        offset = sum(ord(c) for c in symbol) % 7
        close = 20_000 + offset * 1_000 + 15 * t + 100 * np.sin(t / 11)
        df = pd.DataFrame(
            {
                "open": close * 0.997,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": np.full(len(dates), 1_000_000.0),
                "source": "fake",
            },
            index=dates,
        )
        return df, "fake"


def make_service(tmp_path: Path) -> PortfolioService:
    return PortfolioService(PortfolioStore(tmp_path / "portfolio.sqlite3"), FakeMarket())


def test_sync_creates_daily_snapshot_without_changing_shares(tmp_path):
    svc = make_service(tmp_path)
    svc.append_event({
        "event_type": "POSITION_IMPORT", "event_date": "2026-01-02",
        "symbol": "FPT", "quantity": 100, "price": 70_000,
    })
    before = svc.current_state().positions["FPT"].shares
    result = svc.sync_daily()
    after = svc.current_state().positions["FPT"].shares

    assert result["snapshot"]["nav"] > 0
    assert result["snapshot"]["official"] is True
    assert before == after == 100
    assert result["snapshot"]["positions"][0]["symbol"] == "FPT"


def test_buy_requires_funding_first(tmp_path):
    svc = make_service(tmp_path)
    with pytest.raises(Exception, match="cash negative"):
        svc.append_event({
            "event_type": "BUY", "event_date": "2026-01-02",
            "symbol": "FPT", "quantity": 100, "price": 70_000,
        })
    assert svc.transactions() == []


def test_contribution_suggestion_is_information_only(tmp_path):
    svc = make_service(tmp_path)
    svc.append_event({
        "event_type": "POSITION_IMPORT", "event_date": "2026-01-02",
        "symbol": "AAA", "quantity": 100, "price": 20_000,
    })
    svc.append_event({
        "event_type": "POSITION_IMPORT", "event_date": "2026-01-02",
        "symbol": "BBB", "quantity": 50, "price": 20_000,
    })
    svc.append_event({
        "event_type": "CASH_DEPOSIT", "event_date": "2026-01-02",
        "amount": 1_000_000,
    })
    svc.sync_daily()
    n_before = len(svc.transactions())
    suggestion = svc.contribution_suggestions()
    n_after = len(svc.transactions())

    assert suggestion["policy"] in {"EQUAL_WEIGHT_DEFICITS", "REFERENCE_WEIGHT_DEFICITS"}
    assert suggestion["suggestions"]
    assert n_before == n_after


def test_reference_weights_drive_hold_add_review_status_only(tmp_path):
    svc = make_service(tmp_path)
    for symbol in ("AAA", "BBB"):
        svc.append_event({
            "event_type": "POSITION_IMPORT", "event_date": "2026-01-02",
            "symbol": symbol, "quantity": 100, "price": 20_000,
        })
    svc.set_reference_weights({"AAA": 0.8, "BBB": 0.2})
    svc.sync_daily()
    dashboard = svc.dashboard()
    statuses = {p["symbol"]: p["status"] for p in dashboard["portfolio"]["positions"]}
    assert statuses["AAA"] in {"ADD", "HOLD", "REVIEW"}
    assert statuses["BBB"] in {"ADD", "HOLD", "REVIEW"}
    # Status calculation must never mutate ledger state.
    assert len(svc.transactions()) == 2


def test_event_ledger_has_no_application_delete_path(tmp_path):
    store = PortfolioStore(tmp_path / "portfolio.sqlite3")
    assert not hasattr(store, "delete_event")
    assert not hasattr(store, "update_event")
