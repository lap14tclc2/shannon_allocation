from __future__ import annotations

import json
from dataclasses import asdict

from .domain import EventType, LedgerEvent


class CorrectionError(ValueError):
    pass


_EDITABLE_STOCK_TYPES = {
    EventType.POSITION_IMPORT,
    EventType.BUY,
    EventType.RIGHTS_ISSUE,
    EventType.SELL,
}


_AUTOMATIC_TAX_METADATA = {
    "cash_dividend_withholding_rate",
    "cash_dividend_withholding_tax",
    "cash_dividend_gross_amount",
    "cash_dividend_net_amount",
    "stock_dividend_sale_tax_rate",
    "stock_dividend_sale_tax",
    "stock_dividend_taxable_quantity",
    "stock_dividend_tax_par_value",
    "stock_dividend_tax_basis_per_share",
    "stock_dividend_tax_basis_source",
}


def ensure_schema(store) -> None:
    with store.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS ledger_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('EDIT', 'DELETE')),
                replacement_json TEXT,
                reason TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT 'local',
                created_at TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES ledger_events(id)
            );
            CREATE INDEX IF NOT EXISTS idx_ledger_correction_event
                ON ledger_corrections(event_id, id);
            """
        )


def _event_to_payload(event: LedgerEvent) -> dict:
    row = asdict(event)
    row["event_type"] = event.event_type.value
    return row


def _payload_to_event(payload: dict, *, event_id: int, fallback: LedgerEvent) -> LedgerEvent:
    return LedgerEvent(
        id=event_id,
        event_type=EventType(str(payload.get("event_type") or fallback.event_type.value)),
        event_date=str(payload.get("event_date") or fallback.event_date),
        symbol=(str(payload.get("symbol")).upper() if payload.get("symbol") else None),
        quantity=float(payload.get("quantity") or 0),
        price=float(payload.get("price") or 0),
        fee=float(payload.get("fee") or 0),
        tax=float(payload.get("tax") or 0),
        amount=float(payload.get("amount") or 0),
        ratio=float(payload.get("ratio") or 0),
        note=str(payload.get("note") or ""),
        created_by=fallback.created_by,
        created_at=fallback.created_at,
        metadata=dict(payload.get("metadata") or {}),
    )


def raw_events(store) -> list[LedgerEvent]:
    with store.connect() as db:
        rows = db.execute("SELECT * FROM ledger_events ORDER BY event_date, id").fetchall()
    return [store._event_from_row(row) for row in rows]


def raw_event(store, event_id: int) -> LedgerEvent | None:
    with store.connect() as db:
        row = db.execute("SELECT * FROM ledger_events WHERE id = ?", (int(event_id),)).fetchone()
    return store._event_from_row(row) if row else None


def list_corrections(store, event_id: int | None = None) -> list[dict]:
    sql = "SELECT * FROM ledger_corrections"
    args: list[object] = []
    if event_id is not None:
        sql += " WHERE event_id = ?"
        args.append(int(event_id))
    sql += " ORDER BY id"
    with store.connect() as db:
        rows = db.execute(sql, args).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["replacement"] = json.loads(item.pop("replacement_json") or "null")
        except Exception:
            item["replacement"] = None
            item.pop("replacement_json", None)
        out.append(item)
    return out


def latest_corrections(store) -> dict[int, dict]:
    latest: dict[int, dict] = {}
    for row in list_corrections(store):
        latest[int(row["event_id"])] = row
    return latest


def transaction_versions(store) -> list[dict]:
    """Resolve every immutable source event to its current display version/status."""
    corrections_by_event: dict[int, list[dict]] = {}
    for correction in list_corrections(store):
        corrections_by_event.setdefault(int(correction["event_id"]), []).append(correction)

    out: list[dict] = []
    for original in raw_events(store):
        event = original
        status = "ACTIVE"
        latest = None
        for correction in corrections_by_event.get(int(original.id or 0), []):
            if (
                status == "ACTIVE"
                and correction["action"] == "EDIT"
                and correction.get("replacement")
            ):
                event = _payload_to_event(
                    correction["replacement"],
                    event_id=int(original.id),
                    fallback=event,
                )
            elif correction["action"] == "DELETE":
                status = "SOFT_DELETED"
            latest = correction
        out.append({
            "event": event,
            "status": status,
            "correction": latest,
        })
    return out


def effective_events(store, start: str | None = None, end: str | None = None) -> list[LedgerEvent]:
    """Return active ledger events without mutating immutable source rows."""
    out: list[LedgerEvent] = []
    for version in transaction_versions(store):
        if version["status"] == "SOFT_DELETED":
            continue
        event = version["event"]
        if start and event.event_date < start:
            continue
        if end and event.event_date > end:
            continue
        out.append(event)
    out.sort(key=lambda e: (e.event_date, int(e.id or 0)))
    return out


def effective_event(store, event_id: int) -> LedgerEvent | None:
    for event in effective_events(store):
        if int(event.id or 0) == int(event_id):
            return event
    return None


def _stable_metadata(event: LedgerEvent) -> dict:
    metadata = dict(event.metadata or {})
    for key in ("broker_code", "trade_date", "settlement_date", "settlement_confirmed", "settlement_status"):
        metadata.pop(key, None)
    for key in _AUTOMATIC_TAX_METADATA:
        metadata.pop(key, None)
    return metadata


def _enforce_edit_policy(current: LedgerEvent, replacement: LedgerEvent) -> None:
    """Allow stock-type corrections while keeping cash transaction types immutable."""
    if current.event_type != replacement.event_type and not (
        current.event_type in _EDITABLE_STOCK_TYPES
        and replacement.event_type in _EDITABLE_STOCK_TYPES
    ):
        raise CorrectionError(
            "Transaction type can only be changed among editable stock transaction types."
        )

    immutable_checks = (
        ("event_date", current.event_date, replacement.event_date),
        ("symbol", current.symbol, replacement.symbol),
        ("account_id", current.account_id, replacement.account_id),
        ("fee", float(current.fee or 0), float(replacement.fee or 0) if current.event_type == replacement.event_type else float(current.fee or 0)),
        ("amount", float(current.amount or 0), float(replacement.amount or 0)),
        ("ratio", float(current.ratio or 0), float(replacement.ratio or 0)),
        ("note", current.note or "", replacement.note or ""),
        ("settlement_date", current.settlement_date, replacement.settlement_date if current.event_type == replacement.event_type else current.settlement_date),
        ("metadata", _stable_metadata(current), _stable_metadata(replacement)),
    )
    changed = [name for name, before, after in immutable_checks if before != after]
    if changed:
        fields = ", ".join(changed)
        raise CorrectionError(
            f"Only stock transaction type, quantity, price and broker can be edited. Read-only field changed: {fields}."
        )


def append_edit(store, event_id: int, replacement: LedgerEvent, *, reason: str, created_by: str = "local") -> int:
    original = raw_event(store, event_id)
    if original is None:
        raise CorrectionError("Transaction not found.")
    current = effective_event(store, event_id)
    if current is None:
        raise CorrectionError("Deleted transactions cannot be edited.")
    reason = str(reason or "").strip()
    if not reason:
        raise CorrectionError("Correction reason is required.")
    if len(reason) > 500:
        raise CorrectionError("Correction reason must be at most 500 characters.")

    _enforce_edit_policy(current, replacement)

    payload = _event_to_payload(replacement)
    payload["id"] = int(event_id)
    with store.connect() as db:
        cur = db.execute(
            """
            INSERT INTO ledger_corrections(event_id, action, replacement_json, reason, created_by, created_at)
            VALUES (?, 'EDIT', ?, ?, ?, ?)
            """,
            (int(event_id), json.dumps(payload, ensure_ascii=False), reason, str(created_by or "local")[:100], store._now()),
        )
        return int(cur.lastrowid)


def append_delete(store, event_id: int, *, reason: str, created_by: str = "local") -> int:
    """Append a soft-delete marker while preserving the immutable source row."""
    if raw_event(store, event_id) is None:
        raise CorrectionError("Transaction not found.")
    if effective_event(store, event_id) is None:
        raise CorrectionError("Transaction is already soft-deleted.")
    reason = str(reason or "").strip()
    if not reason:
        raise CorrectionError("Discard reason is required.")
    if len(reason) > 500:
        raise CorrectionError("Discard reason must be at most 500 characters.")

    with store.connect() as db:
        cur = db.execute(
            """
            INSERT INTO ledger_corrections(event_id, action, replacement_json, reason, created_by, created_at)
            VALUES (?, 'DELETE', NULL, ?, ?, ?)
            """,
            (
                int(event_id),
                reason,
                str(created_by or "local")[:100],
                store._now(),
            ),
        )
        return int(cur.lastrowid)


def audit_log(store) -> list[dict]:
    corrections = list_corrections(store)
    originals = {int(e.id): _event_to_payload(e) for e in raw_events(store) if e.id is not None}
    out = []
    for row in reversed(corrections):
        out.append({
            **row,
            "action": "SOFT_DELETE" if row["action"] == "DELETE" else row["action"],
            "original": originals.get(int(row["event_id"])),
        })
    return out
