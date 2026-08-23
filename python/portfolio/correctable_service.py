from __future__ import annotations

from .accounting import AccountingError, apply_event
from .corrections import (
    CorrectionError,
    append_delete,
    append_edit,
    audit_log,
    effective_event,
    effective_events,
    ensure_schema,
    latest_corrections,
    raw_events,
)
from .domain import EventType, LedgerEvent, PortfolioState
from .service import PortfolioService
from .validation import InputValidationError, normalize_event_payload


class CorrectablePortfolioService(PortfolioService):
    """PortfolioService with an append-only correction journal.

    Source ledger rows are never physically updated or deleted. Edit/Delete are
    user-facing correction actions stored separately. All portfolio calculations
    consume the effective ledger after applying the latest correction per event.
    """

    def __init__(self, store=None, market=None) -> None:
        super().__init__(store=store, market=market)
        ensure_schema(self.store)
        # Existing PortfolioService code calls store.list_events in several
        # places. Override only this store instance so all operational paths use
        # the effective corrected ledger, while corrections.py reads source rows
        # directly from SQLite and therefore cannot recurse.
        self.store.list_events = lambda start=None, end=None: effective_events(
            self.store, start=start, end=end
        )

    def transactions(self) -> list[dict]:
        latest = latest_corrections(self.store)
        rows = []
        for event in reversed(effective_events(self.store)):
            row = self._serialize_event(event)
            correction = latest.get(int(event.id or 0))
            if correction and correction.get("action") == "EDIT":
                row["correction"] = {
                    "id": correction["id"],
                    "action": "EDIT",
                    "reason": correction["reason"],
                    "created_by": correction["created_by"],
                    "created_at": correction["created_at"],
                }
            else:
                row["correction"] = None
            rows.append(row)
        return rows

    def transaction_audit(self) -> list[dict]:
        return audit_log(self.store)

    @staticmethod
    def _validate_ledger(events: list[LedgerEvent]) -> None:
        state = PortfolioState()
        for event in sorted(events, key=lambda e: (e.event_date, int(e.id or 0))):
            apply_event(state, event)
            if event.event_type in {EventType.BUY, EventType.CASH_WITHDRAW, EventType.FEE} and state.cash < -1e-6:
                raise AccountingError(
                    f"Ledger would make cash negative after transaction #{event.id}. "
                    "Correct the funding/cash event first."
                )

    @staticmethod
    def _event_from_clean(clean: dict, *, event_id: int | None, created_by: str, created_at=None) -> LedgerEvent:
        return LedgerEvent(
            id=event_id,
            event_type=clean["event_type"],
            event_date=clean["event_date"],
            symbol=clean["symbol"],
            quantity=clean["quantity"],
            price=clean["price"],
            fee=clean["fee"],
            tax=clean["tax"],
            amount=clean["amount"],
            ratio=clean["ratio"],
            note=clean["note"],
            created_by=created_by,
            created_at=created_at,
            metadata=clean["metadata"],
        )

    def append_event(self, payload: dict, created_by: str = "local") -> dict:
        clean = normalize_event_payload(payload, today=self.today_vn())
        source = raw_events(self.store)
        next_id = max((int(e.id or 0) for e in source), default=0) + 1
        event = self._event_from_clean(
            clean,
            event_id=next_id,
            created_by=str(payload.get("created_by") or created_by or "local")[:100],
        )
        candidate = effective_events(self.store) + [event]
        self._validate_ledger(candidate)
        # SQLite owns the real ID. next_id is used only to validate same-day
        # ordering before insertion and should equal the next autoincrement ID.
        stored = LedgerEvent(
            id=None,
            event_type=event.event_type,
            event_date=event.event_date,
            symbol=event.symbol,
            quantity=event.quantity,
            price=event.price,
            fee=event.fee,
            tax=event.tax,
            amount=event.amount,
            ratio=event.ratio,
            note=event.note,
            created_by=event.created_by,
            metadata=event.metadata,
        )
        eid = self.store.append_event(stored)
        return {"ok": True, "event_id": eid, "event": self._serialize_event(stored)}

    def _replacement_event(self, event_id: int, payload: dict) -> LedgerEvent:
        current = effective_event(self.store, event_id)
        if current is None:
            raise CorrectionError("Transaction not found or already deleted.")
        merged = self._serialize_event(current)
        for key in (
            "event_type", "event_date", "symbol", "quantity", "price", "fee",
            "tax", "amount", "ratio", "note", "metadata",
        ):
            if key in payload:
                merged[key] = payload[key]
        clean = normalize_event_payload(merged, today=self.today_vn())
        return self._event_from_clean(
            clean,
            event_id=int(event_id),
            created_by=current.created_by,
            created_at=current.created_at,
        )

    def _refresh_derived_history(self) -> dict:
        with self.store.connect() as db:
            db.execute("DELETE FROM snapshot_positions")
            db.execute("DELETE FROM portfolio_snapshots")
        try:
            return self._rebuild_snapshot_history()
        except Exception as exc:
            return {"snapshots": 0, "official": 0, "tracking_start": None, "error": str(exc)}

    def update_event(self, event_id: int, payload: dict, created_by: str = "local") -> dict:
        reason = str(payload.get("correction_reason") or payload.get("reason") or "").strip()
        if not reason:
            raise InputValidationError(
                "CORRECTION_REASON_REQUIRED",
                "correction_reason is required when editing a transaction.",
                "correction_reason",
            )
        replacement = self._replacement_event(int(event_id), payload)
        candidate = [e for e in effective_events(self.store) if int(e.id or 0) != int(event_id)]
        candidate.append(replacement)
        self._validate_ledger(candidate)
        correction_id = append_edit(
            self.store, int(event_id), replacement, reason=reason, created_by=created_by
        )
        history = self._refresh_derived_history()
        return {
            "ok": True,
            "event_id": int(event_id),
            "correction_id": correction_id,
            "action": "EDIT",
            "event": self._serialize_event(replacement),
            "history": history,
        }

    def delete_event(self, event_id: int, reason: str, created_by: str = "local") -> dict:
        reason = str(reason or "").strip()
        if not reason:
            raise InputValidationError(
                "DELETION_REASON_REQUIRED",
                "reason is required when deleting a transaction.",
                "reason",
            )
        current = effective_event(self.store, int(event_id))
        if current is None:
            raise CorrectionError("Transaction not found or already deleted.")
        candidate = [e for e in effective_events(self.store) if int(e.id or 0) != int(event_id)]
        self._validate_ledger(candidate)
        correction_id = append_delete(
            self.store, int(event_id), reason=reason, created_by=created_by
        )
        history = self._refresh_derived_history()
        return {
            "ok": True,
            "event_id": int(event_id),
            "correction_id": correction_id,
            "action": "DELETE",
            "history": history,
        }
