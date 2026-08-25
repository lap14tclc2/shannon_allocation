from __future__ import annotations

from pathlib import Path

import pytest

from portfolio.accounting import AccountingError
from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.corporate_actions import CorporateAction
from portfolio.corrections import CorrectionError, raw_events
from portfolio.storage import PortfolioStore
from portfolio.validation import InputValidationError


class NoMarket:
    def health(self): return {"provider": "none"}


def make_service(tmp_path: Path) -> CorrectablePortfolioService:
    return CorrectablePortfolioService(PortfolioStore(tmp_path / "portfolio.sqlite3"), NoMarket())


def test_edit_changes_effective_state_but_preserves_source_row(tmp_path):
    svc=make_service(tmp_path)
    event_id=svc.append_event({"event_type":"POSITION_IMPORT","event_date":"2026-08-20","symbol":"FPT","quantity":100,"price":70_000})["event_id"]
    result=svc.update_event(event_id,{"price":71_000,"correction_reason":"Correct broker import price"})
    assert result["action"]=="EDIT"
    assert svc.current_state().positions["FPT"].average_cost==pytest.approx(71_000)
    assert raw_events(svc.store)[0].price==pytest.approx(70_000)
    assert svc.transactions()[0]["price"]==pytest.approx(71_000)
    assert svc.transaction_audit()[0]["original"]["price"]==pytest.approx(70_000)
    # There was no NAV history yet, so a data cleanup must not invent a restatement exception.
    assert svc.book.restatements()==[]


def test_soft_delete_preserves_source_row_and_updates_effective_cash(tmp_path):
    svc=make_service(tmp_path)
    keep=svc.append_event({"event_type":"CASH_DEPOSIT","event_date":"2026-08-20","amount":50_000_000})
    extra=svc.append_event({"event_type":"CASH_DEPOSIT","event_date":"2026-08-20","amount":10_000_000})

    result=svc.delete_event(extra["event_id"],"Duplicate cash entry")

    assert result["action"]=="SOFT_DELETE"
    assert result["status"]=="SOFT_DELETED"
    assert svc.current_state().cash==pytest.approx(50_000_000)
    assert [e.id for e in raw_events(svc.store)]==[keep["event_id"],extra["event_id"]]

    rows={row["id"]:row for row in svc.transactions()}
    assert len(rows)==2
    assert rows[keep["event_id"]]["status"]=="ACTIVE"
    assert rows[extra["event_id"]]["status"]=="SOFT_DELETED"
    assert rows[extra["event_id"]]["correction"]["reason"]=="Duplicate cash entry"
    assert svc.transaction_audit()[0]["action"]=="SOFT_DELETE"


def test_soft_delete_buy_rebuilds_holdings_and_restores_cash(tmp_path):
    svc=make_service(tmp_path)
    svc.append_event({"event_type":"CASH_DEPOSIT","event_date":"2026-08-20","amount":10_000_000})
    buy=svc.append_event({
        "event_type":"BUY",
        "event_date":"2026-08-21",
        "symbol":"FPT",
        "quantity":100,
        "price":70_000,
    })
    before=svc.current_state()
    assert before.positions["FPT"].shares==pytest.approx(100)
    assert before.cash==pytest.approx(3_000_000)

    svc.delete_event(buy["event_id"],"Trade was entered by mistake")

    after=svc.current_state()
    assert "FPT" not in after.positions
    assert after.cash==pytest.approx(10_000_000)


def test_delete_never_removes_required_funding(tmp_path):
    svc=make_service(tmp_path)
    funding=svc.append_event({"event_type":"CASH_DEPOSIT","event_date":"2026-08-20","amount":10_000_000})
    svc.append_event({"event_type":"BUY","event_date":"2026-08-21","symbol":"FPT","quantity":100,"price":70_000})
    with pytest.raises(AccountingError,match="cash negative"):
        svc.delete_event(funding["event_id"],"Funding was wrong")
    assert len(svc.transactions())==2
    assert svc.transaction_audit()==[]


def test_edit_reuses_clean_input_validation(tmp_path):
    svc=make_service(tmp_path)
    event_id=svc.append_event({"event_type":"POSITION_IMPORT","event_date":"2026-08-20","symbol":"FPT","quantity":100,"price":70_000})["event_id"]
    with pytest.raises(InputValidationError) as exc: svc.update_event(event_id,{"price":72,"correction_reason":"test"})
    assert exc.value.code=="PRICE_UNIT_SUSPECT"
    with pytest.raises(InputValidationError) as exc: svc.update_event(event_id,{"price":71_000})
    assert exc.value.code=="CORRECTION_REASON_REQUIRED"


def test_edit_only_allows_quantity_price_and_broker(tmp_path):
    svc=make_service(tmp_path)
    event_id=svc.append_event({
        "event_type":"POSITION_IMPORT",
        "event_date":"2026-08-20",
        "symbol":"FPT",
        "quantity":100,
        "price":70_000,
        "broker_code":"DNSE",
        "account_id":"PRIMARY",
    })["event_id"]

    result=svc.update_event(event_id,{
        "quantity":120,
        "price":71_000,
        "broker_code":"TCBS",
        "correction_reason":"Correct quantity, price and broker",
    })
    assert result["event"]["quantity"]==pytest.approx(120)
    assert result["event"]["price"]==pytest.approx(71_000)
    assert result["event"]["metadata"]["broker_code"]=="TCBS"

    with pytest.raises(CorrectionError, match="event_date"):
        svc.update_event(event_id,{"event_date":"2026-08-21","correction_reason":"not allowed"})
    with pytest.raises(CorrectionError, match="symbol"):
        svc.update_event(event_id,{"symbol":"ACB","correction_reason":"not allowed"})
    with pytest.raises(CorrectionError, match="account_id"):
        svc.update_event(event_id,{"account_id":"MARGIN","correction_reason":"not allowed"})


def test_corporate_action_requires_authoritative_verification_and_explicit_post(tmp_path):
    svc=make_service(tmp_path)
    svc.append_event({"event_type":"POSITION_IMPORT","event_date":"2026-08-01","symbol":"FPT","quantity":1000,"price":70_000})
    svc.book.upsert_corporate_action(CorporateAction(
        external_key="test:FPT:stock-div", symbol="FPT", action_type="STOCK_DIVIDEND",
        record_date="2026-08-20", stock_ratio=.10, source="vnstock_data",
    ))
    action=svc.book.corporate_actions(svc.store.list_events())[0]
    with pytest.raises(InputValidationError) as exc:
        svc.verify_corporate_action(action["id"],"https://cafef.vn/example")
    assert exc.value.code=="NON_AUTHORITATIVE_CORPORATE_ACTION_SOURCE"
    svc.verify_corporate_action(action["id"],"https://vsd.vn/vi/ad/example")
    svc.record_corporate_action_receipt(action["id"],{"received_date":"2026-08-23","actual_shares":100})
    before=svc.current_state().positions["FPT"].shares
    posted=svc.post_corporate_action_receipt(action["id"])
    assert posted["posting_policy"]=="USER_CONFIRMED_ONLY"
    assert svc.current_state().positions["FPT"].shares==pytest.approx(before+100)
    with pytest.raises(InputValidationError) as exc:
        svc.post_corporate_action_receipt(action["id"])
    assert exc.value.code=="CORPORATE_ACTION_ALREADY_POSTED"
