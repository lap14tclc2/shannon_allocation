from __future__ import annotations

from pathlib import Path

import pytest

from portfolio.accounting import AccountingError, derive_state
from portfolio.activity import append_activity, list_activity, verify_activity_chain
from portfolio.domain import EventType, LedgerEvent
from portfolio.security_reference import VnstockSecurityReferenceProvider
from portfolio.storage import PortfolioStore
from portfolio.validation import InputValidationError, normalize_event_payload

TODAY = "2026-08-23"


def event(event_id, event_type, date, *, broker="UNASSIGNED", account="PRIMARY", **kwargs):
    metadata = dict(kwargs.pop("metadata", {}) or {})
    metadata.update({"broker_code": broker, "account_id": account})
    return LedgerEvent(id=event_id, event_type=EventType(event_type), event_date=date, metadata=metadata, **kwargs)


def test_broker_specific_fifo_does_not_cross_accounts():
    state = derive_state([
        event(1, "POSITION_IMPORT", "2026-01-02", broker="TCBS", symbol="FPT", quantity=100, price=70_000),
        event(2, "POSITION_IMPORT", "2026-02-02", broker="SSI", symbol="FPT", quantity=100, price=80_000),
        event(3, "SELL", "2026-03-02", broker="SSI", symbol="FPT", quantity=50, price=90_000),
    ])
    p = state.positions["FPT"]
    assert p.shares == pytest.approx(150)
    by_broker = {lot.broker_code: lot for lot in p.lots}
    assert by_broker["TCBS"].remaining_quantity == pytest.approx(100)
    assert by_broker["SSI"].remaining_quantity == pytest.approx(50)
    assert state.realized_pnl == pytest.approx(500_000)


def test_broker_specific_sell_is_blocked_even_when_consolidated_shares_are_enough():
    with pytest.raises(AccountingError, match="SSI/PRIMARY"):
        derive_state([
            event(1, "POSITION_IMPORT", "2026-01-02", broker="TCBS", symbol="FPT", quantity=100, price=70_000),
            event(2, "POSITION_IMPORT", "2026-02-02", broker="SSI", symbol="FPT", quantity=10, price=80_000),
            event(3, "SELL", "2026-03-02", broker="SSI", symbol="FPT", quantity=50, price=90_000),
        ])


def test_broker_validation_accepts_known_and_rejects_unknown():
    clean = normalize_event_payload({
        "event_type": "POSITION_IMPORT", "event_date": TODAY,
        "symbol": "FPT", "quantity": 100, "price": 70_000,
        "broker_code": "tcbs", "account_id": "main-01",
    }, today=TODAY)
    assert clean["metadata"]["broker_code"] == "TCBS"
    assert clean["metadata"]["account_id"] == "MAIN-01"
    with pytest.raises(InputValidationError) as exc:
        normalize_event_payload({
            "event_type": "POSITION_IMPORT", "event_date": TODAY,
            "symbol": "FPT", "quantity": 100, "price": 70_000,
            "broker_code": "random-broker",
        }, today=TODAY)
    assert exc.value.code == "UNKNOWN_BROKER"


def test_activity_log_hash_chain_detects_mutation(tmp_path: Path):
    store = PortfolioStore(tmp_path / "activity.sqlite3")
    append_activity(store, actor_type="USER", actor_id="local", category="LEDGER", action="CREATE", summary="Created trade")
    append_activity(store, actor_type="SYSTEM", actor_id="scheduler", category="MARKET_DATA", action="SYNC", summary="Synced prices")
    assert len(list_activity(store)) == 2
    assert verify_activity_chain(store)["status"] == "VERIFIED"
    with store.connect() as db:
        db.execute("UPDATE activity_log SET summary='tampered' WHERE id=1")
    result = verify_activity_chain(store)
    assert result["status"] == "BROKEN"
    assert result["first_bad_id"] == 1


class Frame:
    def __init__(self, rows): self.rows = rows
    def to_dict(self, orient):
        assert orient == "records"
        return self.rows


class CompanyV4:
    def __init__(self, rows): self.rows = rows
    def info(self, symbol=None): return Frame([{**row, "symbol": symbol} for row in self.rows])


class ReferenceV4:
    def __init__(self, rows): self.company = CompanyV4(rows)


def test_security_resolver_uses_real_isin_from_reference_row():
    provider = VnstockSecurityReferenceProvider(
        reference_factory=lambda: ReferenceV4([{"isin": "VN000000FPT1", "exchange": "HOSE", "company_name": "FPT Corporation", "lot_size": 100}]),
        provider_name="mock",
    )
    result = provider.resolve("FPT")
    assert result["status"] == "RESOLVED"
    assert result["isin"] == "VN000000FPT1"
    assert result["exchange"] == "HOSE"


def test_security_resolver_never_fabricates_isin_from_ticker():
    provider = VnstockSecurityReferenceProvider(
        reference_factory=lambda: ReferenceV4([{"exchange": "HOSE", "company_name": "FPT Corporation"}]),
        provider_name="mock",
    )
    result = provider.resolve("FPT")
    assert result["status"] == "PARTIAL"
    assert result["isin"] is None
