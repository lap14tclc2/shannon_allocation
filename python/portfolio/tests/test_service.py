from __future__ import annotations

from datetime import date
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


def test_live_total_pnl_does_not_require_a_snapshot(tmp_path):
    svc = make_service(tmp_path)
    svc.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-01-02", "symbol": "FPT", "quantity": 100, "price": 20_000})
    svc.store.upsert_market_prices([{
        "symbol": "FPT", "trading_date": "2026-08-21",
        "open": 25_000, "high": 25_000, "low": 25_000, "close": 25_000,
        "volume": 1_000_000, "source": "fake", "is_final": True, "data_quality": "VALID",
    }])
    dashboard = svc.dashboard()
    assert dashboard["latest_snapshot"] is None
    assert dashboard["portfolio"]["cost_value"] == pytest.approx(2_000_000)
    assert dashboard["portfolio"]["equity_value"] == pytest.approx(2_500_000)
    assert dashboard["portfolio"]["unrealized_pnl"] == pytest.approx(500_000)
    assert dashboard["portfolio"]["total_pnl"] == pytest.approx(500_000)
    assert dashboard["portfolio"]["accounting_return"] == pytest.approx(0.25)
    assert dashboard["portfolio"]["positions"][0]["status"] == "MONITOR"


def test_no_history_drawdown_is_unknown_not_zero(tmp_path):
    svc = make_service(tmp_path)
    svc.append_event({"event_type": "POSITION_IMPORT", "event_date": svc.today_vn(), "symbol": "FPT", "quantity": 100, "price": 20_000})
    perf = svc.performance()
    assert perf["official_snapshot_count"] == 0
    assert perf["history_status"] == "NO_HISTORY"
    assert perf["current_drawdown"] is None
    assert perf["max_drawdown"] is None
    assert perf["xirr"] is None
    assert perf["xirr_status"] == "UNAVAILABLE_OPENING_BALANCE"
    assert perf["cashflow_history_quality"] == "OPENING_BALANCE_ONLY"


def test_cash_deposit_is_available_cash_and_does_not_change_shares(tmp_path):
    svc = make_service(tmp_path)
    svc.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-01-02", "symbol": "FPT", "quantity": 100, "price": 20_000})
    before = svc.current_state().positions["FPT"].shares
    svc.append_event({"event_type": "CASH_DEPOSIT", "event_date": "2026-08-20", "amount": 50_000_000})
    state = svc.current_state()
    assert state.cash == pytest.approx(50_000_000)
    assert state.positions["FPT"].shares == before


def test_first_sync_rebuilds_daily_performance_and_drawdown_history(tmp_path):
    svc = make_service(tmp_path)
    svc.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-01-02", "symbol": "FPT", "quantity": 100, "price": 20_000})
    result = svc.sync_daily()
    performance = svc.performance()
    assert result["history"]["official"] > 20
    assert performance["official_snapshot_count"] > 20
    assert performance["history_status"] == "SUFFICIENT"
    assert len(performance["series"]) > 20
    assert performance["current_drawdown"] is not None
    assert performance["max_drawdown"] is not None
    assert performance["latest_date"] is not None
    assert performance["total_pnl"] != 0


def test_sync_creates_snapshots_without_changing_shares(tmp_path):
    svc = make_service(tmp_path)
    svc.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-01-02", "symbol": "FPT", "quantity": 100, "price": 20_000})
    before = svc.current_state().positions["FPT"].shares
    result = svc.sync_daily()
    after = svc.current_state().positions["FPT"].shares
    assert result["snapshot"]["nav"] > 0
    assert result["snapshot"]["official"] is True
    assert before == after == 100
    assert result["snapshot"]["positions"][0]["symbol"] == "FPT"


def test_extended_risk_diagnostics_use_equity_normalized_concentration(tmp_path):
    svc = make_service(tmp_path)
    for symbol, qty in (("AAA", 100), ("BBB", 80), ("CCC", 60)):
        svc.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-01-02", "symbol": symbol, "quantity": qty, "price": 20_000})
    svc.append_event({"event_type": "CASH_DEPOSIT", "event_date": "2026-01-02", "amount": 5_000_000})
    svc.sync_daily()
    risk = svc.risk()
    for key in (
        "effective_positions", "effective_position_ratio", "equity_hhi", "max_equity_weight",
        "average_correlation", "max_correlation", "diversification_ratio", "daily_var_95",
        "daily_cvar_95", "downside_volatility", "largest_risk_symbol",
        "largest_risk_contribution", "risk_concentration_ratio",
    ):
        assert key in risk
    assert risk["status"] in {"VALID", "PARTIAL"}
    assert risk["quality"]["coverage_weight"] > 0
    assert risk["effective_position_ratio"] <= 1.000001
    assert risk["methodology"]["concentration_basis"] == "equity_normalized"


def test_buy_requires_funding_first(tmp_path):
    svc = make_service(tmp_path)
    with pytest.raises(Exception, match="cash negative"):
        svc.append_event({"event_type": "BUY", "event_date": "2026-01-02", "symbol": "FPT", "quantity": 100, "price": 70_000})
    assert svc.transactions() == []


def test_no_equal_weight_fallback_without_explicit_policy(tmp_path):
    svc = make_service(tmp_path)
    svc.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-01-02", "symbol": "AAA", "quantity": 100, "price": 20_000})
    svc.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-01-02", "symbol": "BBB", "quantity": 50, "price": 20_000})
    svc.append_event({"event_type": "CASH_DEPOSIT", "event_date": "2026-01-02", "amount": 1_000_000})
    svc.sync_daily()
    suggestion = svc.contribution_suggestions()
    assert suggestion["policy"] == "NO_ALLOCATION_POLICY"
    assert suggestion["deployable_cash"] is None
    assert suggestion["suggestions"] == []


def test_cash_suggestion_requires_explicit_reference_and_reserve(tmp_path):
    svc = make_service(tmp_path)
    for symbol, qty in (("AAA", 100), ("BBB", 50)):
        svc.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-01-02", "symbol": symbol, "quantity": qty, "price": 20_000})
    svc.append_event({"event_type": "CASH_DEPOSIT", "event_date": "2026-01-02", "amount": 1_000_000})
    svc.sync_daily()
    svc.set_reference_weights({"AAA": 0.5, "BBB": 0.5})
    assert svc.contribution_suggestions()["policy"] == "NO_CASH_RESERVE_POLICY"
    svc.set_cash_reserve(200_000)
    n_before = len(svc.transactions())
    suggestion = svc.contribution_suggestions()
    n_after = len(svc.transactions())
    assert suggestion["policy"] == "EXPLICIT_REFERENCE_WEIGHT_DEFICITS"
    assert suggestion["strategic_cash_reserve"] == pytest.approx(200_000)
    assert suggestion["deployable_cash"] <= 800_000 + 1e-6
    assert n_before == n_after


def test_reference_weights_drive_status_only(tmp_path):
    svc = make_service(tmp_path)
    for symbol in ("AAA", "BBB"):
        svc.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-01-02", "symbol": symbol, "quantity": 100, "price": 20_000})
    svc.set_reference_weights({"AAA": 0.8, "BBB": 0.2})
    svc.sync_daily()
    statuses = {p["symbol"]: p["status"] for p in svc.dashboard()["portfolio"]["positions"]}
    assert statuses["AAA"] in {"ADD", "HOLD", "REVIEW"}
    assert statuses["BBB"] in {"ADD", "HOLD", "REVIEW"}
    assert len(svc.transactions()) == 2


def test_market_metadata_and_lineage_are_explicit(tmp_path):
    svc = make_service(tmp_path)
    svc.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-01-02", "symbol": "FPT", "quantity": 100, "price": 20_000})
    svc.sync_daily()
    dashboard = svc.dashboard()
    assert dashboard["market_data"]["market_date"] is not None
    assert dashboard["market_data"]["aligned"] is True
    assert dashboard["data_lineage"]["analytics"]["status"] == "UNVERIFIED"
    assert dashboard["data_lineage"]["analytics"]["corporate_action_adjusted"] is None


def test_event_ledger_has_no_application_delete_path(tmp_path):
    store = PortfolioStore(tmp_path / "portfolio.sqlite3")
    assert not hasattr(store, "delete_event")
    assert not hasattr(store, "update_event")
