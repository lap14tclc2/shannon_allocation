from __future__ import annotations

import math
import re
from datetime import date

from .domain import EventType

SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,10}$")
ACCOUNT_RE = re.compile(r"^[A-Z0-9_.-]{1,32}$")
BROKER_RE = re.compile(r"^[A-Z0-9_.-]{2,20}$")
KNOWN_BROKERS = {"UNASSIGNED", "TCBS", "SSI", "DNSE", "VPS", "VCBS", "HSC", "VNDIRECT", "OTHER"}
MAX_NOTE_LENGTH = 500
MAX_SHARES = 1_000_000_000.0
MAX_PRICE_VND = 10_000_000.0
MIN_EQUITY_PRICE_VND = 1_000.0
MAX_MONEY_VND = 10_000_000_000_000_000.0
MAX_RATIO = 100.0


class InputValidationError(ValueError):
    def __init__(self, code: str, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.field = field
        self.message = message

    def as_dict(self) -> dict:
        return {"error": self.message, "code": self.code, "field": self.field}


def _finite_number(value, field: str, *, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError) as exc:
        raise InputValidationError("INVALID_NUMBER", f"{field} must be a valid number.", field) from exc
    if not math.isfinite(number):
        raise InputValidationError("INVALID_NUMBER", f"{field} must be finite.", field)
    if minimum is not None and number < minimum:
        raise InputValidationError("VALUE_TOO_SMALL", f"{field} must be at least {minimum:g}.", field)
    if maximum is not None and number > maximum:
        raise InputValidationError("VALUE_TOO_LARGE", f"{field} must not exceed {maximum:g}.", field)
    return number


def _positive(value, field: str, maximum: float) -> float:
    number = _finite_number(value, field, minimum=0, maximum=maximum)
    if number <= 0:
        raise InputValidationError("REQUIRED_POSITIVE", f"{field} must be greater than 0.", field)
    return number


def _iso_date(value, field: str) -> tuple[str, date]:
    text = str(value or "").strip()
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise InputValidationError("INVALID_DATE", f"{field} must use YYYY-MM-DD.", field) from exc
    return text, parsed


def normalize_symbol(value) -> str | None:
    symbol = str(value or "").strip().upper()
    if not symbol:
        return None
    if not SYMBOL_RE.fullmatch(symbol):
        raise InputValidationError("INVALID_SYMBOL", "symbol must contain only 2–10 uppercase letters/digits (for example FPT).", "symbol")
    return symbol


def normalize_broker(value) -> str:
    broker = str(value or "UNASSIGNED").strip().upper()
    if not BROKER_RE.fullmatch(broker):
        raise InputValidationError("INVALID_BROKER", "broker_code may contain only letters, digits, underscore, dash and dot.", "broker_code")
    if broker not in KNOWN_BROKERS:
        raise InputValidationError("UNKNOWN_BROKER", f"Unknown broker_code {broker}. Use one of: {', '.join(sorted(KNOWN_BROKERS))}.", "broker_code")
    return broker


def normalize_account(value) -> str:
    account_id = str(value or "PRIMARY").strip().upper()
    if not ACCOUNT_RE.fullmatch(account_id):
        raise InputValidationError("INVALID_ACCOUNT_ID", "account_id may contain only letters, digits, underscore, dash and dot.", "account_id")
    return account_id


def normalize_event_payload(payload: dict, *, today: str) -> dict:
    """Validate and canonicalize one ledger event request."""
    if not isinstance(payload, dict):
        raise InputValidationError("INVALID_PAYLOAD", "Request body must be an object.")
    try:
        event_type = EventType(str(payload.get("event_type") or "").strip().upper())
    except ValueError as exc:
        raise InputValidationError("INVALID_EVENT_TYPE", "Unknown event type.", "event_type") from exc

    event_date, parsed_date = _iso_date(payload.get("event_date") or today, "event_date")
    _, today_date = _iso_date(today, "today")
    if parsed_date > today_date:
        raise InputValidationError("FUTURE_DATE", "event_date cannot be in the future.", "event_date")

    note = str(payload.get("note") or "").strip()
    if len(note) > MAX_NOTE_LENGTH:
        raise InputValidationError("NOTE_TOO_LONG", f"note must be at most {MAX_NOTE_LENGTH} characters.", "note")

    metadata_raw = payload.get("metadata") or {}
    if not isinstance(metadata_raw, dict):
        raise InputValidationError("INVALID_METADATA", "metadata must be an object.", "metadata")
    metadata = dict(metadata_raw)
    metadata["broker_code"] = normalize_broker(payload.get("broker_code") or metadata.get("broker_code"))
    metadata["account_id"] = normalize_account(payload.get("account_id") or metadata.get("account_id"))
    if event_type == EventType.SELL and metadata["broker_code"] == "UNASSIGNED":
        raise InputValidationError(
            "SELL_BROKER_REQUIRED",
            "SELL requires the custody broker. Assign the holding to DNSE, TCBS or the actual broker before selling.",
            "broker_code",
        )

    symbol_required = event_type in {EventType.POSITION_IMPORT, EventType.BUY, EventType.RIGHTS_ISSUE, EventType.SELL, EventType.CASH_DIVIDEND, EventType.STOCK_DIVIDEND, EventType.SPLIT}
    symbol = normalize_symbol(payload.get("symbol"))
    if symbol_required and not symbol:
        raise InputValidationError("SYMBOL_REQUIRED", "symbol is required for this event.", "symbol")
    if not symbol_required:
        symbol = None

    quantity = 0.0
    if event_type in {EventType.POSITION_IMPORT, EventType.BUY, EventType.RIGHTS_ISSUE, EventType.SELL, EventType.STOCK_DIVIDEND}:
        quantity = _positive(payload.get("quantity"), "quantity", MAX_SHARES)

    price = 0.0
    if event_type in {EventType.POSITION_IMPORT, EventType.BUY, EventType.RIGHTS_ISSUE, EventType.SELL}:
        price = _positive(payload.get("price"), "price", MAX_PRICE_VND)
        if price < MIN_EQUITY_PRICE_VND:
            raise InputValidationError("PRICE_UNIT_SUSPECT", "price must be full VND per share (for example 72,000, not 72).", "price")

    amount = 0.0
    if event_type in {EventType.CASH_DEPOSIT, EventType.CASH_WITHDRAW, EventType.CASH_DIVIDEND, EventType.FEE}:
        amount = _positive(payload.get("amount"), "amount", MAX_MONEY_VND)

    ratio = 0.0
    if event_type == EventType.SPLIT:
        ratio = _positive(payload.get("ratio"), "ratio", MAX_RATIO)

    fee = 0.0
    tax = 0.0
    if event_type in {EventType.BUY, EventType.SELL, EventType.CASH_DIVIDEND}:
        tax = _finite_number(payload.get("tax"), "tax", minimum=0, maximum=MAX_MONEY_VND)
    if event_type in {EventType.BUY, EventType.SELL}:
        fee = _finite_number(payload.get("fee"), "fee", minimum=0, maximum=MAX_MONEY_VND)
        gross = quantity * price
        if fee + tax > gross:
            raise InputValidationError("COSTS_EXCEED_GROSS", "fee + tax cannot exceed the gross trade value.", "fee")
        metadata["trade_date"] = event_date
        settlement_raw = metadata.get("settlement_date") or payload.get("settlement_date")
        if settlement_raw:
            settlement_text, settlement_date = _iso_date(settlement_raw, "settlement_date")
            if settlement_date < parsed_date:
                raise InputValidationError("SETTLEMENT_BEFORE_TRADE", "settlement_date cannot be before the trade date.", "settlement_date")
            metadata["settlement_date"] = settlement_text
        else:
            metadata.pop("settlement_date", None)
        metadata.pop("settlement_confirmed", None)
        metadata.pop("settlement_status", None)
    else:
        for key in ("trade_date", "settlement_date", "settlement_confirmed", "settlement_status"):
            metadata.pop(key, None)

    if event_type == EventType.CASH_DIVIDEND and tax > amount:
        raise InputValidationError("COSTS_EXCEED_GROSS", "cash-dividend tax cannot exceed the gross dividend amount.", "tax")

    return {
        "event_type": event_type,
        "event_date": event_date,
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "fee": fee,
        "tax": tax,
        "amount": amount,
        "ratio": ratio,
        "note": note,
        "metadata": metadata,
    }


def validate_reference_weights(weights: dict, *, holdings: set[str]) -> dict[str, float]:
    if not isinstance(weights, dict):
        raise InputValidationError("INVALID_WEIGHTS", "reference weights must be an object.", "weights")
    if not weights:
        return {}
    normalized: dict[str, float] = {}
    for raw_symbol, raw_weight in weights.items():
        symbol = normalize_symbol(raw_symbol)
        if not symbol:
            raise InputValidationError("INVALID_SYMBOL", "reference weight symbol is required.", "weights")
        value = _finite_number(raw_weight, f"weight[{symbol}]", minimum=0, maximum=1)
        if value <= 0:
            raise InputValidationError("INVALID_WEIGHT", f"weight[{symbol}] must be greater than 0.", "weights")
        normalized[symbol] = value
    if set(normalized) != set(holdings):
        missing = sorted(set(holdings) - set(normalized))
        extra = sorted(set(normalized) - set(holdings))
        detail = []
        if missing:
            detail.append(f"missing: {', '.join(missing)}")
        if extra:
            detail.append(f"not held: {', '.join(extra)}")
        raise InputValidationError("WEIGHT_SYMBOL_MISMATCH", "Reference weights must cover exactly the current holdings" + (f" ({'; '.join(detail)})." if detail else "."), "weights")
    total = sum(normalized.values())
    if abs(total - 1.0) > 1e-6:
        raise InputValidationError("WEIGHTS_NOT_100", f"Reference weights must total 100%; current total is {total * 100:.2f}%.", "weights")
    return normalized


def validate_cash_reserve(value) -> float:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise InputValidationError("CASH_RESERVE_REQUIRED", "cash_reserve is required; use 0 only when you explicitly want no reserve.", "cash_reserve")
    return _finite_number(value, "cash_reserve", minimum=0, maximum=MAX_MONEY_VND)