from __future__ import annotations

import pytest

from portfolio.accounting import AccountingError, derive_state
from portfolio.domain import EventType, LedgerEvent


def e(event_type, **kwargs):
    return LedgerEvent(
        id=None,
        event_type=EventType(event_type),
        event_date=kwargs.pop("event_date", "2026-01-02"),
        **kwargs,
    )


def test_position_import_is_external_value_without_cash_mutation():
    state = derive_state([
        e("POSITION_IMPORT", symbol="FPT", quantity=100, price=70000),
    ])
    assert state.cash == 0
    assert state.positions["FPT"].shares == 100
    assert state.positions["FPT"].average_cost == 70000
    assert state.external_contributions == 7_000_000


def test_buy_sell_dividend_and_stock_dividend_accounting():
    state = derive_state([
        e("CASH_DEPOSIT", amount=20_000_000),
        e("BUY", symbol="FPT", quantity=100, price=70_000, fee=3_500),
        e("STOCK_DIVIDEND", symbol="FPT", quantity=15),
        e("CASH_DIVIDEND", symbol="FPT", amount=200_000),
        e("SELL", symbol="FPT", quantity=15, price=80_000, fee=600, tax=1_200),
    ])
    assert state.positions["FPT"].shares == 100
    assert state.dividend_income == 200_000
    assert state.realized_pnl > 0
    assert state.cash > 0


def test_oversell_is_rejected():
    with pytest.raises(AccountingError):
        derive_state([
            e("POSITION_IMPORT", symbol="ACB", quantity=10, price=20_000),
            e("SELL", symbol="ACB", quantity=11, price=21_000),
        ])


def test_split_changes_shares_not_cost_basis():
    state = derive_state([
        e("POSITION_IMPORT", symbol="ABC", quantity=100, price=50_000),
        e("SPLIT", symbol="ABC", ratio=2.0),
    ])
    p = state.positions["ABC"]
    assert p.shares == 200
    assert p.cost_basis == 5_000_000
    assert p.average_cost == 25_000
