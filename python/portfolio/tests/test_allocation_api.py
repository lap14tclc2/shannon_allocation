"""Allocation API integration tests.

Uses a real sqlite-backed PortfolioService with a fake market so the tests are
hermetic (no network, no Postgres). The valuation/candidate providers are
monkeypatched to deterministic fixtures.
"""
from __future__ import annotations

import pandas as pd
import pytest

from app import main
from portfolio.service import PortfolioService
from portfolio.storage import PortfolioStore


class FakeMarket:
    def health(self):
        return {"provider": "fake"}


def make_service(tmp_path, name="p.sqlite3") -> PortfolioService:
    from portfolio.corrections import ensure_schema

    store = PortfolioStore(tmp_path / name)
    ensure_schema(store)
    svc = PortfolioService(store, FakeMarket())
    svc.append_event({
        "event_type": "POSITION_IMPORT", "event_date": "2026-01-02",
        "symbol": "FPT", "quantity": 100, "price": 20_000,
    })
    svc.append_event({
        "event_type": "CASH_DEPOSIT", "event_date": "2026-08-20", "amount": 1_000_000,
    })
    svc.store.upsert_market_prices([{
        "symbol": "FPT", "trading_date": "2026-09-04",
        "open": 25_000, "high": 25_000, "low": 25_000, "close": 25_000,
        "volume": 1_000_000, "source": "fake", "is_final": True, "data_quality": "VALID",
    }])
    return svc


def signal_map(symbols):
    return {
        "FPT": {
            "symbol": "FPT", "quality_tier": "HIGH_QUALITY", "quality_score": 85,
            "hard_rejects": [], "valuation_status": "ATTRACTIVE",
            "actual_mos_pct": 30.0, "required_mos_pct": 25.0, "valuation_confidence": "MEDIUM",
        },
        "VNM": {
            "symbol": "VNM", "quality_tier": "EXCEPTIONAL", "quality_score": 92,
            "hard_rejects": [], "valuation_status": "HIGH_CONVICTION_VALUE",
            "actual_mos_pct": 42.0, "required_mos_pct": 25.0, "valuation_confidence": "HIGH",
        },
    }


@pytest.fixture
def endpoint_context(tmp_path, monkeypatch):
    svc = make_service(tmp_path)
    user = {"id": 1, "username": "tester", "role": "USER", "created_at": "2026-01-01T00:00:00Z"}
    selected = {"id": 7, "name": "Test portfolio", "schema_name": "u1_p7", "user_id": 1, "is_default": False}
    monkeypatch.setattr(main, "require_portfolio_user", lambda session: user)
    monkeypatch.setattr(main, "active_portfolio", lambda user_obj: selected)
    monkeypatch.setattr(main, "portfolio", lambda user_obj: svc)
    monkeypatch.setattr(main, "_allocation_valuation_map", lambda symbols: signal_map(symbols))
    monkeypatch.setattr(main, "_allocation_candidates", lambda: [])
    return {"svc": svc, "selected": selected}


def test_get_allocation_returns_stable_advisory_payload(endpoint_context):
    result = main.portfolio_allocation()
    assert result["ok"] is True
    assert result["informational_only"] is True
    assert result["policy"] == "INFORMATION_ONLY"
    allocation = result["allocation"]
    assert allocation["portfolio_id"] == 7
    assert isinstance(allocation["holdings"], list)
    assert any(d["symbol"] == "FPT" for d in allocation["holdings"])
    assert allocation["posture"] in ("HOLD_SELECTIVE_BUY", "KEEP_CASH", "ROTATE_OR_REVIEW")
    assert isinstance(allocation["no_action_required"], bool)
    assert "risk_summary" in allocation
    assert "data_quality" in allocation
    assert isinstance(allocation["reason_codes"], list)
    # HOLD is a valid successful output.
    fpt = next(d for d in allocation["holdings"] if d["symbol"] == "FPT")
    assert fpt["action"] in ("HOLD", "REDUCE", "SELL")


def test_get_allocation_is_deterministic(endpoint_context):
    a = main.portfolio_allocation()["allocation"]
    b = main.portfolio_allocation()["allocation"]
    assert a == b


def test_simulate_never_mutates_ledger(endpoint_context):
    svc = endpoint_context["svc"]
    events_before = [e.id for e in svc.store.list_events()]
    cash_before = svc.current_state().cash
    result = main.portfolio_allocation_simulate(body={"changes": [{"symbol": "VNM", "target_weight": 0.10}]})
    assert result["persisted"] is False
    assert result["policy"] == "SIMULATION_ONLY_NO_PERSISTENCE"
    events_after = [e.id for e in svc.store.list_events()]
    assert events_after == events_before
    assert svc.current_state().cash == pytest.approx(cash_before)
    assert result["allocation"]["simulation"]["persisted"] is False
    symbols = {d["symbol"] for d in result["allocation"]["holdings"]}
    assert "VNM" in symbols


def test_simulate_validates_changes(endpoint_context):
    with pytest.raises(main.ApiError):
        main.portfolio_allocation_simulate(body={"changes": [{"symbol": "BOGUS!!", "target_weight": 0.1}]})
    with pytest.raises(main.ApiError):
        main.portfolio_allocation_simulate(body={"changes": [{"symbol": "VNM", "target_weight": 1.5}]})
    with pytest.raises(main.ApiError):
        main.portfolio_allocation_simulate(body={"changes": "not-a-list"})


def test_simulate_infeasible_buy_is_skipped(endpoint_context):
    result = main.portfolio_allocation_simulate(body={"changes": [{"symbol": "VNM", "target_weight": 0.99}]})
    symbols = {d["symbol"] for d in result["allocation"]["holdings"]}
    # Single FPT holding (~0.5 NAV weight) cannot fund a 99% VNM buy from cash.
    assert "VNM" not in symbols
    assert result["allocation"]["simulation"]["persisted"] is False


def test_multi_portfolio_isolation(tmp_path, monkeypatch):
    svc_a = make_service(tmp_path, "a.sqlite3")
    svc_b = make_service(tmp_path, "b.sqlite3")
    user = {"id": 1, "username": "tester", "role": "USER"}
    sel_a = {"id": 1, "name": "A", "schema_name": "u1_p1", "user_id": 1}
    sel_b = {"id": 2, "name": "B", "schema_name": "u1_p2", "user_id": 1}
    monkeypatch.setattr(main, "require_portfolio_user", lambda session: user)
    monkeypatch.setattr(main, "_allocation_valuation_map", lambda symbols: signal_map(symbols))
    monkeypatch.setattr(main, "_allocation_candidates", lambda: [])

    monkeypatch.setattr(main, "portfolio", lambda user_obj: svc_a)
    monkeypatch.setattr(main, "active_portfolio", lambda user_obj: sel_a)
    report_a = main.portfolio_allocation()["allocation"]

    monkeypatch.setattr(main, "portfolio", lambda user_obj: svc_b)
    monkeypatch.setattr(main, "active_portfolio", lambda user_obj: sel_b)
    report_b = main.portfolio_allocation()["allocation"]

    assert report_a["portfolio_id"] == 1
    assert report_b["portfolio_id"] == 2
    # Independent evaluations must not cross-contaminate holdings.
    assert {d["symbol"] for d in report_a["holdings"]} == {"FPT"}
    assert {d["symbol"] for d in report_b["holdings"]} == {"FPT"}
    assert report_a["as_of"] == report_b["as_of"]


def test_existing_risk_and_valuation_routes_still_present():
    source = (main.__file__ and __import__("pathlib").Path(main.__file__).read_text(encoding="utf-8"))
    assert '"/api/portfolio/risk"' in source
    assert '"/api/portfolio/valuation/{symbol}"' in source
    assert '"/api/portfolio/screener"' in source
    assert "portfolio_risk(" in source  # canonical engine still used by /risk