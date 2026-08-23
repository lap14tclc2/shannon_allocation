from __future__ import annotations

import pytest

from portfolio.validation import InputValidationError, normalize_event_payload, validate_cash_reserve, validate_reference_weights

TODAY = "2026-08-23"


def assert_code(code, fn):
    with pytest.raises(InputValidationError) as exc:
        fn()
    assert exc.value.code == code


def test_rejects_future_event_date():
    assert_code("FUTURE_DATE", lambda: normalize_event_payload({
        "event_type": "CASH_DEPOSIT", "event_date": "2026-08-24", "amount": 1_000_000,
    }, today=TODAY))


def test_rejects_thousand_unit_price_mistake():
    assert_code("PRICE_UNIT_SUSPECT", lambda: normalize_event_payload({
        "event_type": "POSITION_IMPORT", "event_date": TODAY,
        "symbol": "FPT", "quantity": 100, "price": 72,
    }, today=TODAY))


def test_rejects_invalid_symbol_and_zero_quantity():
    assert_code("INVALID_SYMBOL", lambda: normalize_event_payload({
        "event_type": "BUY", "event_date": TODAY,
        "symbol": "FPT!", "quantity": 100, "price": 72_000,
    }, today=TODAY))
    assert_code("REQUIRED_POSITIVE", lambda: normalize_event_payload({
        "event_type": "BUY", "event_date": TODAY,
        "symbol": "FPT", "quantity": 0, "price": 72_000,
    }, today=TODAY))


def test_irrelevant_fields_are_canonicalized_to_zero():
    clean = normalize_event_payload({
        "event_type": "CASH_DEPOSIT", "event_date": TODAY,
        "amount": 1_000_000, "symbol": "FPT", "quantity": 999,
        "price": 72_000, "fee": 100, "tax": 50, "ratio": 2,
    }, today=TODAY)
    assert clean["symbol"] is None
    assert clean["quantity"] == 0
    assert clean["price"] == 0
    assert clean["fee"] == 0
    assert clean["tax"] == 0
    assert clean["ratio"] == 0


def test_trade_costs_cannot_exceed_gross_value():
    assert_code("COSTS_EXCEED_GROSS", lambda: normalize_event_payload({
        "event_type": "BUY", "event_date": TODAY,
        "symbol": "FPT", "quantity": 1, "price": 1_000,
        "fee": 900, "tax": 200,
    }, today=TODAY))


def test_note_length_is_bounded():
    assert_code("NOTE_TOO_LONG", lambda: normalize_event_payload({
        "event_type": "CASH_DEPOSIT", "event_date": TODAY,
        "amount": 1_000_000, "note": "x" * 501,
    }, today=TODAY))


def test_reference_weights_must_match_holdings_and_total_100():
    assert_code("WEIGHT_SYMBOL_MISMATCH", lambda: validate_reference_weights(
        {"AAA": 1.0}, holdings={"AAA", "BBB"},
    ))
    assert_code("WEIGHTS_NOT_100", lambda: validate_reference_weights(
        {"AAA": 0.6, "BBB": 0.3}, holdings={"AAA", "BBB"},
    ))
    assert validate_reference_weights({"AAA": 0.6, "BBB": 0.4}, holdings={"AAA", "BBB"}) == {"AAA": 0.6, "BBB": 0.4}


def test_cash_reserve_must_be_explicit_and_nonnegative():
    assert_code("CASH_RESERVE_REQUIRED", lambda: validate_cash_reserve(None))
    assert_code("CASH_RESERVE_REQUIRED", lambda: validate_cash_reserve(""))
    assert validate_cash_reserve(0) == 0
    assert_code("VALUE_TOO_SMALL", lambda: validate_cash_reserve(-1))
