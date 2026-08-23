from __future__ import annotations

from pathlib import Path

import pytest

from portfolio.accounting import AccountingError
from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.corrections import raw_events
from portfolio.storage import PortfolioStore
from portfolio.validation import InputValidationError


class NoMarket:
    def health(self):
        return {"provider": "none"}


def make_service(tmp_path: Path) -> CorrectablePortfolioService:
    return CorrectablePortfolioService(PortfolioStore(tmp_path / "portfolio.sqlite3"), NoMarket())


def test_edit_changes_effective_state_but_preserves_source_row(tmp_path):
    svc = make_service(tmp_path)
    created = svc.append_event({
        "event_type": "POSITION_IMPORT", "event_date": "2026-08-20",
        "symbol": "FPT", "quantity": 100, "price": 70_000,
    })
    event_id = created["event_id"]

    result = svc.update_event(event_id, {
        "price": 71_000,
        "correction_reason": "Correct broker import price",
    })

    assert result["action"] == "EDIT"
    assert svc.current_state().positions["FPT"].average_cost == pytest.approx(71_000)
    assert raw_events(svc.store)[0].price == pytest.approx(70_000)
    effective = svc.transactions()[0]
    assert effective["price"] == pytest.approx(71_000)
    assert effective["correction"]["action"] == "EDIT"
    audit = svc.transaction_audit()
    assert audit[0]["action"] == "EDIT"
    assert audit[0]["original"]["price"] == pytest.approx(70_000)


def test_delete_removes_event_from_effective_state_but_keeps_audit(tmp_path):
    svc = make_service(tmp_path)
    keep = svc.append_event({"event_type": "CASH_DEPOSIT", "event_date": "2026-08-20", "amount": 50_000_000})
    extra = svc.append_event({"event_type": "CASH_DEPOSIT", "event_date": "2026-08-20", "amount": 10_000_000})
    assert svc.current_state().cash == pytest.approx(60_000_000)

    svc.delete_event(extra["event_id"], "Duplicate cash entry")

    assert svc.current_state().cash == pytest.approx(50_000_000)
    assert [e.id for e in raw_events(svc.store)] == [keep["event_id"], extra["event_id"]]
    assert [row["id"] for row in svc.transactions()] == [keep["event_id"]]
    assert svc.transaction_audit()[0]["action"] == "DELETE"


def test_delete_is_blocked_when_remaining_ledger_would_make_cash_negative(tmp_path):
    svc = make_service(tmp_path)
    funding = svc.append_event({"event_type": "CASH_DEPOSIT", "event_date": "2026-08-20", "amount": 10_000_000})
    svc.append_event({
        "event_type": "BUY", "event_date": "2026-08-21",
        "symbol": "FPT", "quantity": 100, "price": 70_000,
    })

    with pytest.raises(AccountingError, match="cash negative"):
        svc.delete_event(funding["event_id"], "Funding was wrong")

    assert len(svc.transactions()) == 2
    assert svc.transaction_audit() == []


def test_edit_reuses_clean_input_validation(tmp_path):
    svc = make_service(tmp_path)
    event_id = svc.append_event({
        "event_type": "POSITION_IMPORT", "event_date": "2026-08-20",
        "symbol": "FPT", "quantity": 100, "price": 70_000,
    })["event_id"]

    with pytest.raises(InputValidationError) as exc:
        svc.update_event(event_id, {"price": 72, "correction_reason": "test"})
    assert exc.value.code == "PRICE_UNIT_SUSPECT"

    with pytest.raises(InputValidationError) as exc:
        svc.update_event(event_id, {"price": 71_000})
    assert exc.value.code == "CORRECTION_REASON_REQUIRED"
