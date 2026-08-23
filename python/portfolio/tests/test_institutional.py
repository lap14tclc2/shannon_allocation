from __future__ import annotations

from pathlib import Path

import pytest

from portfolio.accounting import derive_state
from portfolio.corporate_actions import CorporateAction
from portfolio.domain import EventType, LedgerEvent
from portfolio.institutional import InstitutionalBook
from portfolio.storage import PortfolioStore


class NoopCAProvider:
    name = "noop"
    def health(self): return {"provider": "noop", "available": True}
    def events(self, symbols, start, end): return []


def ev(event_id, event_type, event_date, **kwargs):
    return LedgerEvent(id=event_id, event_type=EventType(event_type), event_date=event_date, **kwargs)


def book(tmp_path: Path, today="2026-08-23"):
    store = PortfolioStore(tmp_path / "book.sqlite3")
    return store, InstitutionalBook(store, today_fn=lambda: today, corporate_action_provider=NoopCAProvider())


def test_fifo_tax_lots_drive_realized_pnl():
    state = derive_state([
        ev(1, "POSITION_IMPORT", "2026-01-02", symbol="FPT", quantity=100, price=70_000),
        ev(2, "POSITION_IMPORT", "2026-02-02", symbol="FPT", quantity=100, price=80_000),
        ev(3, "SELL", "2026-03-02", symbol="FPT", quantity=150, price=90_000),
    ])
    p = state.positions["FPT"]
    assert p.shares == pytest.approx(50)
    assert p.cost_basis == pytest.approx(4_000_000)
    assert p.average_cost == pytest.approx(80_000)
    # FIFO disposed cost = 100*70k + 50*80k = 11m; proceeds = 13.5m.
    assert state.realized_pnl == pytest.approx(2_500_000)
    assert len(p.lots) == 1
    assert p.lots[0].remaining_quantity == pytest.approx(50)


def test_stock_dividend_preserves_lot_cost_basis():
    state = derive_state([
        ev(1, "POSITION_IMPORT", "2026-01-02", symbol="FPT", quantity=100, price=60_000),
        ev(2, "STOCK_DIVIDEND", "2026-04-01", symbol="FPT", quantity=20),
    ])
    p = state.positions["FPT"]
    assert p.shares == pytest.approx(120)
    assert p.cost_basis == pytest.approx(6_000_000)
    assert p.average_cost == pytest.approx(50_000)
    assert p.lots[0].remaining_quantity == pytest.approx(120)


def test_settlement_view_separates_settled_and_projected_cash(tmp_path):
    _, ibor = book(tmp_path)
    events = [
        ev(1, "CASH_DEPOSIT", "2026-08-20", amount=100_000_000),
        ev(2, "BUY", "2026-08-21", symbol="FPT", quantity=100, price=70_000,
           metadata={"trade_date": "2026-08-21", "settlement_date": "2026-08-25", "account_id": "PRIMARY"}),
    ]
    state = derive_state(events)
    view = ibor.settlement_view(events, state.cash, reserve=20_000_000)
    assert state.cash == pytest.approx(93_000_000)
    assert view["settled_cash"] == pytest.approx(100_000_000)
    assert view["projected_cash"] == pytest.approx(93_000_000)
    assert view["unsettled_payable"] == pytest.approx(7_000_000)
    assert view["available_to_invest"] == pytest.approx(73_000_000)
    assert view["trades"][0]["status"] == "EXPECTED"


def test_broker_reconciliation_persists_match_and_mismatch(tmp_path):
    _, ibor = book(tmp_path)
    state = derive_state([ev(1, "POSITION_IMPORT", "2026-01-02", symbol="ACB", quantity=100, price=20_000)])
    state.cash = 50_000_000
    matched = ibor.reconcile(state, {"cash": 50_000_000, "positions": {"ACB": 100}, "as_of_date": "2026-08-23"})
    assert matched["status"] == "MATCH"
    mismatch = ibor.reconcile(state, {"cash": 49_000_000, "positions": {"ACB": 99}, "as_of_date": "2026-08-23"})
    assert mismatch["status"] == "MISMATCH"
    assert ibor.reconciliations()[0]["id"] == mismatch["run_id"]


def test_corporate_action_entitlement_is_derived_from_record_date_holdings(tmp_path):
    _, ibor = book(tmp_path)
    action = CorporateAction(
        external_key="manual:FPT:1", symbol="FPT", action_type="STOCK_DIVIDEND",
        record_date="2026-06-01", stock_ratio=0.10, source="manual",
    )
    ibor.upsert_corporate_action(action)
    events = [ev(1, "POSITION_IMPORT", "2026-01-02", symbol="FPT", quantity=3000, price=70_000)]
    row = ibor.corporate_actions(events)[0]
    assert row["held_on_record_date"] == pytest.approx(3000)
    assert row["expected_shares"] == pytest.approx(300)
    assert row["status"] == "ENTITLEMENT_READY"
    ibor.record_corporate_action_receipt(row["id"], {"received_date": "2026-06-20", "actual_shares": 300})
    assert ibor.corporate_actions(events)[0]["status"] == "RECONCILED"


def test_security_master_uses_stable_internal_id(tmp_path):
    _, ibor = book(tmp_path)
    ibor.ensure_securities(["FPT", "ACB"])
    updated = ibor.update_security("FPT", {"exchange": "HOSE", "isin": "VN000000FPT1", "lot_size": 100})
    assert updated["security_id"] == "VN-EQ-FPT"
    assert updated["exchange"] == "HOSE"
    assert updated["currency"] == "VND"


def test_pnl_attribution_separates_unrealized_and_dividend(tmp_path):
    _, ibor = book(tmp_path)
    events = [
        ev(1, "POSITION_IMPORT", "2026-01-02", symbol="FPT", quantity=100, price=70_000),
        ev(2, "CASH_DIVIDEND", "2026-05-01", symbol="FPT", amount=200_000),
    ]
    rows = ibor.pnl_attribution(events, {"FPT": {"close": 75_000}})
    assert rows[0]["unrealized_pnl"] == pytest.approx(500_000)
    assert rows[0]["dividend_income"] == pytest.approx(200_000)
    assert rows[0]["total_contribution_vnd"] == pytest.approx(700_000)
