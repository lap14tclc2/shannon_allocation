from __future__ import annotations

import pytest

from portfolio.corporate_actions import CorporateAction
from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.storage import PortfolioStore
from portfolio.validation import InputValidationError


def service(tmp_path):
    return CorrectablePortfolioService(PortfolioStore(tmp_path / "import.sqlite3"))


def current_payload(**overrides):
    payload = {
        "mode": "CURRENT",
        "cost_basis_adjusted": True,
        "rows": [
            {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 1000, "price": 92_000, "broker_code": "TCBS"},
        ],
    }
    payload.update(overrides)
    return payload


def test_current_import_preview_and_commit_are_atomic_and_idempotent(tmp_path):
    svc = service(tmp_path)
    payload = {
        "mode": "CURRENT",
        "cost_basis_adjusted": True,
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
    assert all(row["metadata"]["cost_basis_adjusted"] is True for row in svc.transactions())
    assert all(row["metadata"]["tracking_start_date"] == svc.today_vn() for row in svc.transactions())
    assert all(row["metadata"]["cost_basis_confirmed_at"] for row in svc.transactions())
    assert svc._tracking_boundary()["initialization_mode"] == "CURRENT"
    assert svc._tracking_boundary()["tracking_start_date"] == svc.today_vn()


def test_current_import_rejects_without_cost_basis_confirmation(tmp_path):
    svc = service(tmp_path)
    with pytest.raises(InputValidationError) as error:
        svc.preview_import({"mode": "CURRENT", "rows": [
            {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 100, "price": 70_000},
        ]})
    assert error.value.code == "COST_BASIS_CONFIRMATION_REQUIRED"
    with pytest.raises(InputValidationError) as error:
        svc.import_events({"mode": "CURRENT", "cost_basis_adjusted": False, "rows": [
            {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 100, "price": 70_000},
        ]})
    assert error.value.code == "COST_BASIS_CONFIRMATION_REQUIRED"
    assert svc.transactions() == []


def test_current_import_rejects_historical_trade_without_partial_write(tmp_path):
    svc = service(tmp_path)
    with pytest.raises(InputValidationError) as error:
        svc.import_events(current_payload(rows=[
            {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 100, "price": 70_000},
            {"event_type": "BUY", "symbol": "HPG", "quantity": 100, "price": 25_000},
        ]))
    assert error.value.code == "CURRENT_IMPORT_EVENT_TYPE"
    assert svc.transactions() == []


def test_historical_import_feature_is_rejected_without_partial_write(tmp_path):
    svc = service(tmp_path)
    payload = {
        "mode": "HISTORICAL",
        "rows": [
            {"event_type": "CASH_DEPOSIT", "event_date": "2024-01-01", "amount": 200_000_000},
        ],
    }
    with pytest.raises(InputValidationError) as error:
        svc.preview_import(payload)
    assert error.value.code == "INVALID_IMPORT_MODE"
    with pytest.raises(InputValidationError) as error:
        svc.import_events(payload)
    assert error.value.code == "INVALID_IMPORT_MODE"
    assert svc.transactions() == []


def test_idempotency_key_cannot_be_reused_for_other_payload(tmp_path):
    svc = service(tmp_path)
    key = "import:client-retry-0001"
    svc.import_events({**current_payload(), "idempotency_key": key})
    with pytest.raises(InputValidationError) as error:
        svc.import_events(current_payload(rows=[
            {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 101, "price": 70_000},
        ], idempotency_key=key))
    assert error.value.code == "IDEMPOTENCY_KEY_REUSED"
    assert len(svc.transactions()) == 1


def test_current_import_ignores_client_sent_date_and_uses_system_today(tmp_path):
    svc = service(tmp_path)
    svc.import_events(current_payload(rows=[
        # A malicious or stale client could send any event_date; the server must override it.
        {"event_type": "POSITION_IMPORT", "event_date": "2020-01-01", "symbol": "FPT", "quantity": 100, "price": 70_000},
    ]))
    assert len(svc.transactions()) == 1
    assert svc.transactions()[0]["event_date"] == svc.today_vn()
    assert svc.transactions()[0]["event_date"] != "2020-01-01"


def test_current_import_requires_adjusted_cost_basis_price(tmp_path):
    svc = service(tmp_path)
    for bad_price in (None, 0, -1, float("nan"), 72):
        rows = [{"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 100, "price": bad_price}]
        with pytest.raises(InputValidationError) as error:
            svc.preview_import(current_payload(rows=rows))
        assert error.value.code in ("REQUIRED_POSITIVE", "INVALID_NUMBER", "PRICE_UNIT_SUSPECT", "VALUE_TOO_SMALL")
    assert svc.transactions() == []


def test_opening_position_is_not_double_adjusted_by_past_corporate_actions(tmp_path):
    svc = service(tmp_path)
    svc.import_events(current_payload(rows=[
        # Quantity and adjusted cost basis are the CURRENT post-corporate-action state.
        {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 200, "price": 50_000},
    ]))
    state = svc.current_state()
    position = state.positions["FPT"]
    # QPort must not re-apply past splits/stock dividends on top of the opening position.
    assert position.shares == 200
    assert position.cost_basis == 200 * 50_000
    assert position.average_cost == 50_000


def test_corporate_action_after_start_date_still_updates_ledger_state(tmp_path):
    svc = service(tmp_path)
    svc.import_events(current_payload(rows=[
        {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 100, "price": 50_000},
    ]))
    # A split AFTER the start date is a normal, explicit ledger event.
    svc.append_event({"event_type": "SPLIT", "symbol": "FPT", "ratio": 2})
    state = svc.current_state()
    position = state.positions["FPT"]
    assert position.shares == 200
    # The split re-bases quantity but leaves total cost basis unchanged.
    assert position.cost_basis == 100 * 50_000
    assert position.average_cost == 25_000


def _seed_corporate_action(svc, payment_date: str, *, ex_date: str | None = None, record_date: str | None = None) -> int:
    action = CorporateAction(
        external_key=f"manual-{ex_date or record_date or payment_date}-{payment_date}",
        symbol="FPT",
        action_type="CASH_DIVIDEND",
        announcement_date=ex_date or record_date or payment_date,
        ex_date=ex_date,
        record_date=record_date or ex_date or payment_date,
        payment_date=payment_date,
        cash_per_share=1_000,
    )
    svc.book.upsert_corporate_action(action)
    with svc.store.connect() as db:
        row = db.execute("SELECT id FROM corporate_actions WHERE external_key=?", (action.external_key,)).fetchone()
    return int(row["id"])


def test_current_portfolio_rejects_receipt_before_tracking_start(tmp_path):
    svc = service(tmp_path)
    svc.import_events(current_payload())
    action_id = _seed_corporate_action(svc, "2026-01-15")
    with pytest.raises(InputValidationError) as error:
        svc.record_corporate_action_receipt(action_id, {"received_date": "2026-01-15", "actual_cash": 100_000})
    assert error.value.code == "CORPORATE_ACTION_BEFORE_TRACKING_START"
    # Nothing was recorded.
    with svc.store.connect() as db:
        assert db.execute("SELECT COUNT(*) AS c FROM corporate_action_receipts").fetchone()["c"] == 0


def test_current_portfolio_accepts_receipt_after_tracking_start(tmp_path):
    svc = service(tmp_path)
    svc.import_events(current_payload())
    action_id = _seed_corporate_action(svc, svc.today_vn())
    result = svc.record_corporate_action_receipt(action_id, {"received_date": svc.today_vn(), "actual_cash": 100_000})
    assert result["ok"] is True


def test_legacy_historical_portfolio_still_allows_existing_receipts(tmp_path):
    svc = service(tmp_path)
    with svc.store.connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO app_meta(key, value) VALUES ('initialization_mode', 'HISTORICAL')"
        )
    action_id = _seed_corporate_action(svc, "2024-03-01")
    result = svc.record_corporate_action_receipt(
        action_id,
        {"received_date": "2024-03-01", "actual_cash": 100_000},
    )
    assert result["ok"] is True


def test_current_import_retry_after_midnight_is_deduplicated(monkeypatch, tmp_path):
    svc = service(tmp_path)
    monkeypatch.setattr(svc, "today_vn", lambda: "2026-08-24")
    payload = current_payload()
    preview = svc.preview_import(payload, created_by="alice")
    key = preview["idempotency_key"]
    first = svc.import_events({**payload, "idempotency_key": key}, created_by="alice")

    # Advance the server clock across midnight; the same business payload must
    # resolve back to the ORIGINAL batch instead of being rejected.
    monkeypatch.setattr(svc, "today_vn", lambda: "2026-08-25")
    second = svc.import_events({**payload, "idempotency_key": key}, created_by="alice")
    assert first["deduplicated"] is False
    assert second["deduplicated"] is True
    assert second["event_ids"] == first["event_ids"]
    assert len(svc.transactions()) == 1
    # The whole batch keeps the single captured server date.
    assert svc.transactions()[0]["event_date"] == "2026-08-24"
    assert svc.transactions()[0]["metadata"]["tracking_start_date"] == "2026-08-24"


def test_current_import_uses_one_server_date_for_whole_batch(monkeypatch, tmp_path):
    svc = service(tmp_path)
    monkeypatch.setattr(svc, "today_vn", lambda: "2026-08-24")
    result = svc.import_events(current_payload(rows=[
        {"event_type": "POSITION_IMPORT", "symbol": "FPT", "quantity": 100, "price": 70_000},
        {"event_type": "POSITION_IMPORT", "symbol": "HPG", "quantity": 50, "price": 25_000},
    ]))
    assert result["row_count"] == 2
    assert {row["event_date"] for row in svc.transactions()} == {"2026-08-24"}


def test_legacy_historical_portfolio_rejects_new_current_quick_import(tmp_path):
    svc = service(tmp_path)
    with svc.store.connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO app_meta(key, value) VALUES ('initialization_mode', 'HISTORICAL')"
        )
    with pytest.raises(InputValidationError) as error:
        svc.import_events(current_payload())
    assert error.value.code == "IMPORT_MODE_CONFLICT"
    assert svc.transactions() == []


def test_failed_import_does_not_persist_tracking_boundary(monkeypatch, tmp_path):
    svc = service(tmp_path)

    def fail_insert(*_args, **_kwargs):
        raise RuntimeError("simulated insert failure")

    monkeypatch.setattr(svc.store, "insert_event", fail_insert)
    with pytest.raises(RuntimeError, match="simulated insert failure"):
        svc.import_events(current_payload())
    assert svc.transactions() == []
    assert svc._tracking_boundary() == {
        "initialization_mode": None,
        "tracking_start_date": None,
    }


def test_retry_returns_original_tracking_metadata_after_midnight(monkeypatch, tmp_path):
    svc = service(tmp_path)
    monkeypatch.setattr(svc, "today_vn", lambda: "2026-08-24")
    payload = current_payload()
    first = svc.import_events(payload, created_by="alice")

    monkeypatch.setattr(svc, "today_vn", lambda: "2026-08-25")
    retry = svc.import_events(payload, created_by="alice")
    assert retry["deduplicated"] is True
    assert retry["tracking_start_date"] == first["tracking_start_date"] == "2026-08-24"
    assert retry["cost_basis_confirmed_at"] == first["cost_basis_confirmed_at"]


def test_current_portfolio_rejects_old_entitlement_paid_after_tracking_start(monkeypatch, tmp_path):
    svc = service(tmp_path)
    monkeypatch.setattr(svc, "today_vn", lambda: "2026-08-25")
    svc.import_events(current_payload())
    action_id = _seed_corporate_action(
        svc,
        "2026-09-10",
        ex_date="2026-08-20",
        record_date="2026-08-21",
    )

    with pytest.raises(InputValidationError) as error:
        svc.record_corporate_action_receipt(
            action_id,
            {"received_date": "2026-09-10", "actual_cash": 100_000},
        )
    assert error.value.code == "CORPORATE_ACTION_BEFORE_TRACKING_START"
