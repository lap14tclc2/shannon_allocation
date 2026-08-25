from __future__ import annotations

import pytest

from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.storage import PortfolioStore
from portfolio.validation import InputValidationError


def service(tmp_path):
    return CorrectablePortfolioService(PortfolioStore(tmp_path / "import.sqlite3"))


def test_current_import_preview_and_commit_are_atomic_and_idempotent(tmp_path):
    svc = service(tmp_path)
    payload = {
        "mode": "CURRENT",
        "source_name": "broker.csv",
        "rows": [
            {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 1000, "price": 92_000, "broker_code": "TCBS"},
            {"event_type": "CASH_DEPOSIT", "amount": 20_000_000},
        ],
    }

    preview = svc.preview_import(payload, created_by="alice")
    assert preview["row_count"] == 2
    assert preview["reconciliation"]["holdings"][0]["shares"] == 1000
    assert svc.transactions() == []

    first = svc.import_events({**payload, "idempotency_key": preview["idempotency_key"]}, created_by="alice")
    second = svc.import_events({**payload, "idempotency_key": preview["idempotency_key"]}, created_by="alice")
    assert first["deduplicated"] is False
    assert second["deduplicated"] is True
    assert second["event_ids"] == first["event_ids"]
    assert len(svc.transactions()) == 2
    assert all(row["event_date"] == svc.today_vn() for row in svc.transactions())
    assert all(row["metadata"]["import_batch_id"] == preview["idempotency_key"] for row in svc.transactions())


def test_current_import_rejects_historical_trade_without_partial_write(tmp_path):
    svc = service(tmp_path)
    with pytest.raises(InputValidationError) as error:
        svc.import_events({
            "mode": "CURRENT",
            "rows": [
                {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 100, "price": 70_000},
                {"event_type": "BUY", "symbol": "HPG", "quantity": 100, "price": 25_000},
            ],
        })
    assert error.value.code == "CURRENT_IMPORT_EVENT_TYPE"
    assert svc.transactions() == []


def test_historical_import_keeps_every_supported_transaction_type(tmp_path):
    svc = service(tmp_path)
    rows = [
        {"event_type": "CASH_DEPOSIT", "event_date": "2024-01-01", "amount": 200_000_000},
        {"event_type": "POSITION_IMPORT", "event_date": "2024-01-01", "symbol": "FPT", "quantity": 100, "price": 60_000, "broker_code": "TCBS"},
        {"event_type": "BUY", "event_date": "2024-01-02", "symbol": "FPT", "quantity": 100, "price": 70_000, "broker_code": "TCBS"},
        {"event_type": "RIGHTS_ISSUE", "event_date": "2024-02-01", "symbol": "FPT", "quantity": 20, "price": 40_000, "broker_code": "TCBS"},
        {"event_type": "CASH_DIVIDEND", "event_date": "2024-03-01", "symbol": "FPT", "amount": 200_000, "tax": 10_000, "broker_code": "TCBS"},
        {"event_type": "STOCK_DIVIDEND", "event_date": "2024-04-01", "symbol": "FPT", "quantity": 22, "broker_code": "TCBS"},
        {"event_type": "SPLIT", "event_date": "2024-05-01", "symbol": "FPT", "ratio": 2, "broker_code": "TCBS"},
        {"event_type": "SELL", "event_date": "2024-06-01", "symbol": "FPT", "quantity": 20, "price": 80_000, "broker_code": "TCBS"},
        {"event_type": "CASH_WITHDRAW", "event_date": "2024-07-01", "amount": 1_000_000},
        {"event_type": "FEE", "event_date": "2024-08-01", "amount": 100_000},
    ]
    result = svc.import_events({"mode": "HISTORICAL", "rows": rows}, created_by="alice")
    assert result["row_count"] == len(rows)
    retry = svc.import_events({"mode": "HISTORICAL", "rows": rows}, created_by="alice")
    assert retry["deduplicated"] is True
    assert retry["event_ids"] == result["event_ids"]
    assert {row["event_type"] for row in svc.transactions()} == {
        "POSITION_IMPORT", "CASH_DEPOSIT", "BUY", "SELL", "RIGHTS_ISSUE",
        "CASH_WITHDRAW", "CASH_DIVIDEND", "STOCK_DIVIDEND", "SPLIT", "FEE",
    }


def test_idempotency_key_cannot_be_reused_for_other_payload(tmp_path):
    svc = service(tmp_path)
    key = "import:client-retry-0001"
    svc.import_events({"mode": "CURRENT", "idempotency_key": key, "rows": [
        {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 100, "price": 70_000},
    ]})
    with pytest.raises(InputValidationError) as error:
        svc.import_events({"mode": "CURRENT", "idempotency_key": key, "rows": [
            {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 101, "price": 70_000},
        ]})
    assert error.value.code == "IDEMPOTENCY_KEY_REUSED"
    assert len(svc.transactions()) == 1


def test_current_import_ignores_client_sent_date_and_uses_system_today(tmp_path):
    svc = service(tmp_path)
    svc.import_events({
        "mode": "CURRENT",
        "rows": [
            # A malicious or stale client could send any event_date; the server must override it.
            {"event_type": "POSITION_IMPORT", "event_date": "2020-01-01", "symbol": "FPT", "quantity": 100, "price": 70_000},
        ],
    })
    assert len(svc.transactions()) == 1
    assert svc.transactions()[0]["event_date"] == svc.today_vn()
    assert svc.transactions()[0]["event_date"] != "2020-01-01"


def test_current_import_requires_adjusted_cost_basis_price(tmp_path):
    svc = service(tmp_path)
    for bad_price in (None, 0, -1, float("nan"), 72):
        rows = [{"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 100, "price": bad_price}]
        with pytest.raises(InputValidationError) as error:
            svc.preview_import({"mode": "CURRENT", "rows": rows})
        assert error.value.code in ("REQUIRED_POSITIVE", "INVALID_NUMBER", "PRICE_UNIT_SUSPECT", "VALUE_TOO_SMALL")
    assert svc.transactions() == []


def test_opening_position_is_not_double_adjusted_by_past_corporate_actions(tmp_path):
    svc = service(tmp_path)
    svc.import_events({"mode": "CURRENT", "rows": [
        # Quantity and adjusted cost basis are the CURRENT post-corporate-action state.
        {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 200, "price": 50_000},
    ]})
    state = svc.current_state()
    position = state.positions["FPT"]
    # QPort must not re-apply past splits/stock dividends on top of the opening position.
    assert position.shares == 200
    assert position.cost_basis == 200 * 50_000
    assert position.average_cost == 50_000


def test_corporate_action_after_start_date_still_updates_ledger_state(tmp_path):
    svc = service(tmp_path)
    svc.import_events({"mode": "CURRENT", "rows": [
        {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 100, "price": 50_000},
    ]})
    # A split AFTER the start date is a normal, explicit ledger event.
    svc.append_event({"event_type": "SPLIT", "symbol": "FPT", "ratio": 2})
    state = svc.current_state()
    position = state.positions["FPT"]
    assert position.shares == 200
    # The split re-bases quantity but leaves total cost basis unchanged.
    assert position.cost_basis == 100 * 50_000
    assert position.average_cost == 25_000
