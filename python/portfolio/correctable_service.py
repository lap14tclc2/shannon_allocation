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
from .institutional import InstitutionalBook
from .service import PortfolioService
from .validation import InputValidationError, normalize_event_payload


class CorrectablePortfolioService(PortfolioService):
    """Operational QPort service with corrections + institutional-lite controls."""

    def __init__(self, store=None, market=None) -> None:
        super().__init__(store=store, market=market)
        ensure_schema(self.store)
        # PortfolioService uses store.list_events throughout. Keep source rows
        # immutable and expose the corrected/effective journal to every derived
        # operational calculation.
        self.store.list_events = lambda start=None, end=None: effective_events(
            self.store, start=start, end=end
        )
        self.book = InstitutionalBook(self.store, today_fn=self.today_vn)

    def transactions(self) -> list[dict]:
        latest = latest_corrections(self.store)
        rows = []
        for event in reversed(effective_events(self.store)):
            row = self._serialize_event(event)
            correction = latest.get(int(event.id or 0))
            row["correction"] = (
                {
                    "id": correction["id"],
                    "action": "EDIT",
                    "reason": correction["reason"],
                    "created_by": correction["created_by"],
                    "created_at": correction["created_at"],
                }
                if correction and correction.get("action") == "EDIT"
                else None
            )
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
        latest_snapshot = self.store.latest_snapshot()
        eid = self.store.append_event(stored)
        history = None
        if latest_snapshot and event.event_date <= latest_snapshot["snapshot_date"]:
            self.book.mark_restatement(
                event.event_date,
                f"Historical transaction #{eid} was added after NAV snapshots existed.",
                correction_event_id=eid,
            )
            history = self._refresh_derived_history()
        return {"ok": True, "event_id": eid, "event": self._serialize_event(stored), "history": history}

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
        current = effective_event(self.store, int(event_id))
        if current is None:
            raise CorrectionError("Transaction not found or already deleted.")
        replacement = self._replacement_event(int(event_id), payload)
        candidate = [e for e in effective_events(self.store) if int(e.id or 0) != int(event_id)]
        candidate.append(replacement)
        self._validate_ledger(candidate)
        affected_from = min(current.event_date, replacement.event_date)
        correction_id = append_edit(self.store, int(event_id), replacement, reason=reason, created_by=created_by)
        self.book.mark_restatement(
            affected_from,
            f"EDIT transaction #{event_id}: {reason}",
            correction_event_id=int(event_id),
        )
        history = self._refresh_derived_history()
        return {
            "ok": True,
            "event_id": int(event_id),
            "correction_id": correction_id,
            "action": "EDIT",
            "event": self._serialize_event(replacement),
            "affected_from": affected_from,
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
        correction_id = append_delete(self.store, int(event_id), reason=reason, created_by=created_by)
        self.book.mark_restatement(
            current.event_date,
            f"DELETE transaction #{event_id}: {reason}",
            correction_event_id=int(event_id),
        )
        history = self._refresh_derived_history()
        return {
            "ok": True,
            "event_id": int(event_id),
            "correction_id": correction_id,
            "action": "DELETE",
            "affected_from": current.event_date,
            "history": history,
        }

    # ------------------------------------------------------------------
    # Institutional-lite operational APIs
    # ------------------------------------------------------------------
    def institutional_overview(self) -> dict:
        events = effective_events(self.store)
        state = derive_state(events)
        symbols = sorted(state.positions)
        prices = self.store.latest_prices(symbols)
        market = self._market_metadata(symbols, prices)
        snapshots = self.store.list_snapshots(limit=10000)
        return self.book.overview(
            events=events,
            state=state,
            prices=prices,
            snapshots=snapshots,
            preferences=self.preferences(),
            market_status=market["status"],
        )

    def reconcile_broker(self, payload: dict, created_by: str = "local") -> dict:
        return self.book.reconcile(self.current_state(), payload, created_by=created_by)

    def sync_corporate_actions(self, start: str | None = None, end: str | None = None) -> dict:
        symbols = sorted(self.current_state().positions)
        return self.book.sync_corporate_actions(symbols, start=start, end=end)

    def verify_corporate_action(self, action_id: int, source_url: str, verified_by: str = "local") -> dict:
        return self.book.verify_corporate_action(action_id, source_url, verified_by=verified_by)

    def record_corporate_action_receipt(self, action_id: int, payload: dict, created_by: str = "local") -> dict:
        return self.book.record_corporate_action_receipt(action_id, payload, created_by=created_by)

    def update_security(self, symbol: str, payload: dict) -> dict:
        return self.book.update_security(symbol, payload)

    def confirm_settlement(self, event_id: int, note: str = "") -> dict:
        return self.book.confirm_settlement(event_id, note=note)

    def lock_nav(self, snapshot_date: str) -> dict:
        return self.book.lock_nav(snapshot_date)

    def resolve_restatement(self, restatement_id: int) -> dict:
        return self.book.resolve_restatement(restatement_id)
