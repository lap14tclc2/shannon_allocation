"""Integration and unit tests for TASK 142 — Vietnamese Semantics & Editable Portfolio Positions/Cash."""

import pytest
from portfolio.accounting import AccountingError
from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.domain import EventType
from portfolio.storage import PortfolioStore
from portfolio.validation import InputValidationError
from portfolio.value_engine.vietnamese_presenter import (
    ARCHETYPE_VIETNAMESE,
    CLASSIFICATION_VIETNAMESE,
    DETERIORATION_VIETNAMESE,
    STATUS_VIETNAMESE,
    VALUETRAP_VIETNAMESE,
    get_vietnamese_archetype,
    get_vietnamese_classification,
    get_vietnamese_deterioration,
    get_vietnamese_status,
    get_vietnamese_valuetrap,
)


class NoMarket:
    def health(self):
        return {"provider": "none"}


@pytest.fixture
def make_portfolio_service(tmp_path):
    """Factory fixture creating an isolated CorrectablePortfolioService instance."""
    def _create():
        import uuid
        db_path = tmp_path / f"portfolio_{uuid.uuid4().hex}.sqlite3"
        store = PortfolioStore(db_path)
        return CorrectablePortfolioService(store, NoMarket())
    return _create


# ============================================================================
# PART A: VIETNAMESE SEMANTIC PRESENTATION TESTS
# ============================================================================

def test_complete_classification_enum_coverage():
    """Verify all business classification enums have Vietnamese translations."""
    required_enums = [
        "POTENTIAL_COMPOUNDER",
        "COMPOUNDER",
        "WEAK_BUSINESS",
        "DETERIORATING_BUSINESS",
    ]
    for code in required_enums:
        assert code in CLASSIFICATION_VIETNAMESE
        vi_text = get_vietnamese_classification(code)
        assert vi_text != code
        assert len(vi_text) > 5


def test_complete_valuetrap_enum_coverage():
    """Verify all ValueTrap enums translate cleanly to investor Vietnamese."""
    required_enums = ["CLEAR", "WATCH", "HIGH_RISK", "INSUFFICIENT_DATA"]
    for code in required_enums:
        assert code in VALUETRAP_VIETNAMESE
        vi_text = get_vietnamese_valuetrap(code)
        assert vi_text != code
        assert "CLEAR" not in vi_text
        assert "HIGH_RISK" not in vi_text


def test_complete_deterioration_enum_coverage():
    """Verify all deterioration enums have human-readable Vietnamese semantics."""
    required_enums = [
        "NO_DETERIORATION",
        "LIKELY_CYCLICAL",
        "POSSIBLY_CYCLICAL",
        "POSSIBLY_STRUCTURAL",
        "STRUCTURAL",
        "UNKNOWN",
    ]
    for code in required_enums:
        assert code in DETERIORATION_VIETNAMESE
        vi_text = get_vietnamese_deterioration(code)
        assert vi_text != code
        assert "NO_DETERIORATION" not in vi_text


def test_status_distinctions_and_invariants():
    """Verify NULL != 0, UNKNOWN != PASS, and NOT_APPLICABLE != UNKNOWN."""
    assert get_vietnamese_status("PASS") == "Đạt"
    assert get_vietnamese_status("WATCH") == "Cần theo dõi"
    assert get_vietnamese_status("FAIL") == "Không đạt"
    assert get_vietnamese_status("UNKNOWN") == "Chưa đủ dữ liệu"
    assert get_vietnamese_status("NOT_APPLICABLE") == "Không áp dụng"

    # Distinct semantic meanings
    assert get_vietnamese_status("UNKNOWN") != get_vietnamese_status("NOT_APPLICABLE")
    assert get_vietnamese_status("PASS") != get_vietnamese_status("UNKNOWN")


def test_archetype_applicability_semantics():
    """Verify banking, securities, and normal enterprise archetype names."""
    assert get_vietnamese_archetype("BANK") == "Ngân hàng thương mại"
    assert get_vietnamese_archetype("SECURITIES") == "Công ty chứng khoán"
    assert get_vietnamese_archetype("NORMAL_ENTERPRISE") == "Doanh nghiệp sản xuất / thương mại thông thường"


# ============================================================================
# PART B: PORTFOLIO MUTATION & LEDGER INVARIANT TESTS
# ============================================================================

def test_add_stock_position_calculates_holdings_and_cost_basis(make_portfolio_service):
    """User can add a stock position, and holdings/cost basis update correctly."""
    svc = make_portfolio_service()

    # Add funding first
    svc.append_event({
        "event_type": "CASH_DEPOSIT",
        "event_date": "2026-08-01",
        "amount": 100_000_000,
    })

    # Add stock position (POSITION_IMPORT)
    res = svc.append_event({
        "event_type": "POSITION_IMPORT",
        "event_date": "2026-08-02",
        "symbol": "FPT",
        "quantity": 1000,
        "price": 70_000,
        "broker_code": "DNSE",
        "account_id": "PRIMARY",
    })

    assert res["ok"] is True
    assert "event_id" in res

    state = svc.current_state()
    assert "FPT" in state.positions
    assert state.positions["FPT"].shares == 1000
    assert state.positions["FPT"].cost_basis == 70_000_000


def test_edit_stock_position_preserves_ledger_integrity(make_portfolio_service):
    """User can safely edit/correct an existing stock position."""
    svc = make_portfolio_service()

    svc.append_event({
        "event_type": "CASH_DEPOSIT",
        "event_date": "2026-08-01",
        "amount": 100_000_000,
    })

    added = svc.append_event({
        "event_type": "POSITION_IMPORT",
        "event_date": "2026-08-02",
        "symbol": "FPT",
        "quantity": 1000,
        "price": 70_000,
        "broker_code": "DNSE",
        "account_id": "PRIMARY",
    })
    event_id = added["event_id"]

    # Edit position price & quantity with required correction_reason
    updated = svc.update_event(
        event_id,
        {
            "price": 75_000,
            "quantity": 1200,
            "correction_reason": "Adjusted fill price and shares according to broker statement",
        },
    )

    assert updated["ok"] is True

    # Ledger state recalculated accurately
    state = svc.current_state()
    assert state.positions["FPT"].shares == 1200
    assert state.positions["FPT"].cost_basis == 90_000_000


def test_cash_deposit_and_withdrawal(make_portfolio_service):
    """User can deposit and withdraw cash, updating total cash correctly."""
    svc = make_portfolio_service()

    # Deposit cash
    dep = svc.append_event({
        "event_type": "CASH_DEPOSIT",
        "event_date": "2026-08-01",
        "amount": 50_000_000,
        "note": "Nạp tiền mặt ban đầu",
    })
    assert dep["ok"] is True
    assert svc.current_state().cash == 50_000_000

    # Withdraw cash
    wdr = svc.append_event({
        "event_type": "CASH_WITHDRAW",
        "event_date": "2026-08-05",
        "amount": 20_000_000,
        "note": "Rút 20tr trang trải nhu cầu",
    })
    assert wdr["ok"] is True
    assert svc.current_state().cash == 30_000_000


def test_withdrawal_cannot_make_cash_negative(make_portfolio_service):
    """Cash withdrawal exceeding available cash raises AccountingError."""
    svc = make_portfolio_service()

    svc.append_event({
        "event_type": "CASH_DEPOSIT",
        "event_date": "2026-08-01",
        "amount": 10_000_000,
    })

    with pytest.raises(AccountingError):
        svc.append_event({
            "event_type": "CASH_WITHDRAW",
            "event_date": "2026-08-02",
            "amount": 20_000_000,
        })


def test_multi_portfolio_isolation(make_portfolio_service):
    """Portfolio A mutations must never affect Portfolio B."""
    svcA = make_portfolio_service()
    svcB = make_portfolio_service()

    # Mutate Portfolio A
    svcA.append_event({"event_type": "CASH_DEPOSIT", "event_date": "2026-08-01", "amount": 100_000_000})
    svcA.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-08-02", "symbol": "DGC", "quantity": 500, "price": 60_000})

    # Portfolio A holds DGC and cash
    stateA = svcA.current_state()
    assert stateA.cash == 100_000_000
    assert "DGC" in stateA.positions

    # Portfolio B remains completely isolated and empty
    stateB = svcB.current_state()
    assert stateB.cash == 0.0
    assert "DGC" not in stateB.positions


def test_validation_rejects_invalid_symbol_and_negative_values(make_portfolio_service):
    """Input validation rejects invalid symbols and non-positive numbers."""
    svc = make_portfolio_service()

    # Invalid symbol
    with pytest.raises(InputValidationError):
        svc.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-08-01", "symbol": "INVALID!", "quantity": 100, "price": 50_000})

    # Non-positive quantity
    with pytest.raises(InputValidationError):
        svc.append_event({"event_type": "POSITION_IMPORT", "event_date": "2026-08-01", "symbol": "FPT", "quantity": 0, "price": 50_000})

    # Non-positive cash deposit
    with pytest.raises(InputValidationError):
        svc.append_event({"event_type": "CASH_DEPOSIT", "event_date": "2026-08-01", "amount": -100})
