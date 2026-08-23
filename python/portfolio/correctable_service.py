from __future__ import annotations

from urllib.parse import urlparse

from .accounting import AccountingError, apply_event, derive_state
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

AUTHORITATIVE_CA_HOSTS = ("vsd.vn", "hnx.vn", "hsx.vn", "hose.vn")


class CorrectablePortfolioService(PortfolioService):
    """Operational QPort service with corrections + institutional-lite controls."""

    def __init__(self, store=None, market=None) -> None:
        super().__init__(store=store, market=market)
        ensure_schema(self.store)
        self.store.list_events = lambda start=None, end=None: effective_events(self.store, start=start, end=end)
        self.book = InstitutionalBook(self.store, today_fn=self.today_vn)
        with self.store.connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS corporate_action_postings (
                    action_id INTEGER NOT NULL,
                    posting_type TEXT NOT NULL,
                    event_id INTEGER NOT NULL,
                    created_by TEXT NOT NULL DEFAULT 'local',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(action_id, posting_type),
                    FOREIGN KEY(action_id) REFERENCES corporate_actions(id),
                    FOREIGN KEY(event_id) REFERENCES ledger_events(id)
                )
                """
            )

    def transactions(self) -> list[dict]:
        latest = latest_corrections(self.store)
        rows = []
        for event in reversed(effective_events(self.store)):
            row = self._serialize_event(event)
            correction = latest.get(int(event.id or 0))
            row["correction"] = (
                {"id": correction["id"], "action": "EDIT", "reason": correction["reason"], "created_by": correction["created_by"], "created_at": correction["created_at"]}
                if correction and correction.get("action") == "EDIT" else None
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
                raise AccountingError(f"Ledger would make cash negative after transaction #{event.id}. Correct the funding/cash event first.")

    @staticmethod
    def _event_from_clean(clean: dict, *, event_id: int | None, created_by: str, created_at=None) -> LedgerEvent:
        return LedgerEvent(
            id=event_id, event_type=clean["event_type"], event_date=clean["event_date"], symbol=clean["symbol"],
            quantity=clean["quantity"], price=clean["price"], fee=clean["fee"], tax=clean["tax"],
            amount=clean["amount"], ratio=clean["ratio"], note=clean["note"], created_by=created_by,
            created_at=created_at, metadata=clean["metadata"],
        )

    def append_event(self, payload: dict, created_by: str = "local") -> dict:
        clean = normalize_event_payload(payload, today=self.today_vn())
        source = raw_events(self.store)
        next_id = max((int(e.id or 0) for e in source), default=0) + 1
        event = self._event_from_clean(clean, event_id=next_id, created_by=str(payload.get("created_by") or created_by or "local")[:100])
        self._validate_ledger(effective_events(self.store) + [event])
        stored = LedgerEvent(
            id=None, event_type=event.event_type, event_date=event.event_date, symbol=event.symbol,
            quantity=event.quantity, price=event.price, fee=event.fee, tax=event.tax, amount=event.amount,
            ratio=event.ratio, note=event.note, created_by=event.created_by, metadata=event.metadata,
        )
        latest_snapshot = self.store.latest_snapshot()
        eid = self.store.append_event(stored)
        history = None
        if latest_snapshot and event.event_date <= latest_snapshot["snapshot_date"]:
            self.book.mark_restatement(event.event_date, f"Historical transaction #{eid} was added after NAV snapshots existed.", correction_event_id=eid)
            history = self._refresh_derived_history()
        return {"ok": True, "event_id": eid, "event": self._serialize_event(stored), "history": history}

    def _replacement_event(self, event_id: int, payload: dict) -> LedgerEvent:
        current = effective_event(self.store, event_id)
        if current is None:
            raise CorrectionError("Transaction not found or already deleted.")
        merged = self._serialize_event(current)
        for key in ("event_type", "event_date", "symbol", "quantity", "price", "fee", "tax", "amount", "ratio", "note", "metadata"):
            if key in payload:
                merged[key] = payload[key]
        clean = normalize_event_payload(merged, today=self.today_vn())
        return self._event_from_clean(clean, event_id=int(event_id), created_by=current.created_by, created_at=current.created_at)

    def _refresh_derived_history(self) -> dict:
        with self.store.connect() as db:
            db.execute("DELETE FROM snapshot_positions")
            db.execute("DELETE FROM portfolio_snapshots")
        try:
            return self._rebuild_snapshot_history()
        except Exception as exc:
            return {"snapshots": 0, "official": 0, "tracking_start": None, "error": str(exc)}

    def _mark_restatement_if_needed(self, affected_from: str, reason: str, event_id: int) -> None:
        latest = self.store.latest_snapshot()
        if latest and affected_from <= latest["snapshot_date"]:
            self.book.mark_restatement(affected_from, reason, correction_event_id=event_id)

    def update_event(self, event_id: int, payload: dict, created_by: str = "local") -> dict:
        reason = str(payload.get("correction_reason") or payload.get("reason") or "").strip()
        if not reason:
            raise InputValidationError("CORRECTION_REASON_REQUIRED", "correction_reason is required when editing a transaction.", "correction_reason")
        current = effective_event(self.store, int(event_id))
        if current is None:
            raise CorrectionError("Transaction not found or already deleted.")
        replacement = self._replacement_event(int(event_id), payload)
        self._validate_ledger([e for e in effective_events(self.store) if int(e.id or 0) != int(event_id)] + [replacement])
        affected_from = min(current.event_date, replacement.event_date)
        correction_id = append_edit(self.store, int(event_id), replacement, reason=reason, created_by=created_by)
        self._mark_restatement_if_needed(affected_from, f"EDIT transaction #{event_id}: {reason}", int(event_id))
        history = self._refresh_derived_history()
        return {"ok": True, "event_id": int(event_id), "correction_id": correction_id, "action": "EDIT", "event": self._serialize_event(replacement), "affected_from": affected_from, "history": history}

    def delete_event(self, event_id: int, reason: str, created_by: str = "local") -> dict:
        reason = str(reason or "").strip()
        if not reason:
            raise InputValidationError("DELETION_REASON_REQUIRED", "reason is required when deleting a transaction.", "reason")
        current = effective_event(self.store, int(event_id))
        if current is None:
            raise CorrectionError("Transaction not found or already deleted.")
        self._validate_ledger([e for e in effective_events(self.store) if int(e.id or 0) != int(event_id)])
        correction_id = append_delete(self.store, int(event_id), reason=reason, created_by=created_by)
        self._mark_restatement_if_needed(current.event_date, f"DELETE transaction #{event_id}: {reason}", int(event_id))
        history = self._refresh_derived_history()
        return {"ok": True, "event_id": int(event_id), "correction_id": correction_id, "action": "DELETE", "affected_from": current.event_date, "history": history}

    def institutional_overview(self) -> dict:
        events = effective_events(self.store)
        state = derive_state(events)
        symbols = sorted(state.positions)
        prices = self.store.latest_prices(symbols)
        market = self._market_metadata(symbols, prices)
        snapshots = self.store.list_snapshots(limit=10000)
        overview = self.book.overview(events=events, state=state, prices=prices, snapshots=snapshots, preferences=self.preferences(), market_status=market["status"])
        with self.store.connect() as db:
            postings = [dict(r) for r in db.execute("SELECT * FROM corporate_action_postings ORDER BY action_id, posting_type").fetchall()]
        posting_map = {}
        for posting in postings:
            posting_map.setdefault(int(posting["action_id"]), []).append(posting)
        for action in overview.get("corporate_actions") or []:
            action["postings"] = posting_map.get(int(action["id"]), [])
            action["ledger_posted"] = bool(action["postings"])
        return overview

    def reconcile_broker(self, payload: dict, created_by: str = "local") -> dict:
        events = effective_events(self.store)
        state = derive_state(events)
        prefs = self.preferences()
        reserve = prefs.get("cash_reserve") if prefs.get("cash_reserve_configured") else None
        settlement = self.book.settlement_view(events, state.cash, reserve=reserve)
        state.cash = float(settlement["settled_cash"])
        result = self.book.reconcile(state, payload, created_by=created_by)
        result["cash_basis"] = "SETTLED_CASH"
        return result

    def sync_corporate_actions(self, start: str | None = None, end: str | None = None) -> dict:
        return self.book.sync_corporate_actions(sorted(self.current_state().positions), start=start, end=end)

    @staticmethod
    def _authoritative_corporate_action_url(source_url: str) -> bool:
        host = (urlparse(str(source_url or "")).hostname or "").lower().strip(".")
        return any(host == allowed or host.endswith("." + allowed) for allowed in AUTHORITATIVE_CA_HOSTS)

    def verify_corporate_action(self, action_id: int, source_url: str, verified_by: str = "local") -> dict:
        if not self._authoritative_corporate_action_url(source_url):
            raise InputValidationError(
                "NON_AUTHORITATIVE_CORPORATE_ACTION_SOURCE",
                "VERIFIED requires an authoritative VSDC/HOSE/HNX source URL. Other sources may be used only for discovery/cross-checking.",
                "source_url",
            )
        return self.book.verify_corporate_action(action_id, source_url, verified_by=verified_by)

    def record_corporate_action_receipt(self, action_id: int, payload: dict, created_by: str = "local") -> dict:
        return self.book.record_corporate_action_receipt(action_id, payload, created_by=created_by)

    def post_corporate_action_receipt(self, action_id: int, created_by: str = "local") -> dict:
        actions = {int(a["id"]): a for a in self.book.corporate_actions(effective_events(self.store))}
        action = actions.get(int(action_id))
        if not action:
            raise InputValidationError("CORPORATE_ACTION_NOT_FOUND", "Corporate action not found.", "action_id")
        if action.get("verification_status") != "VERIFIED":
            raise InputValidationError("CORPORATE_ACTION_NOT_VERIFIED", "Verify the corporate action against VSDC/HOSE/HNX before posting it to the ledger.", "action_id")
        if action.get("status") != "RECONCILED":
            raise InputValidationError("CORPORATE_ACTION_NOT_RECONCILED", "Record and reconcile the actual broker receipt before posting it to the ledger.", "action_id")
        receipt = action.get("receipt") or {}
        with self.store.connect() as db:
            existing = {r["posting_type"]: int(r["event_id"]) for r in db.execute("SELECT posting_type,event_id FROM corporate_action_postings WHERE action_id=?", (int(action_id),)).fetchall()}
        created = []
        metadata = {"corporate_action_id": int(action_id), "corporate_action_source": action.get("source_url") or action.get("source")}
        if float(receipt.get("actual_cash") or 0) > 0 and "CASH" not in existing:
            result = self.append_event({
                "event_type": "CASH_DIVIDEND", "event_date": receipt["received_date"], "symbol": action["symbol"],
                "amount": float(receipt["actual_cash"]), "note": f"Corporate action #{action_id} cash receipt", "metadata": metadata,
            }, created_by=created_by)
            with self.store.connect() as db:
                db.execute("INSERT INTO corporate_action_postings(action_id,posting_type,event_id,created_by,created_at) VALUES (?,?,?,?,datetime('now'))", (int(action_id), "CASH", int(result["event_id"]), str(created_by)[:100]))
            created.append(result["event_id"])
        if float(receipt.get("actual_shares") or 0) > 0 and "STOCK" not in existing:
            result = self.append_event({
                "event_type": "STOCK_DIVIDEND", "event_date": receipt["received_date"], "symbol": action["symbol"],
                "quantity": float(receipt["actual_shares"]), "note": f"Corporate action #{action_id} stock receipt", "metadata": metadata,
            }, created_by=created_by)
            with self.store.connect() as db:
                db.execute("INSERT INTO corporate_action_postings(action_id,posting_type,event_id,created_by,created_at) VALUES (?,?,?,?,datetime('now'))", (int(action_id), "STOCK", int(result["event_id"]), str(created_by)[:100]))
            created.append(result["event_id"])
        if not created and existing:
            raise InputValidationError("CORPORATE_ACTION_ALREADY_POSTED", "Corporate-action receipt has already been posted to the ledger.", "action_id")
        if not created:
            raise InputValidationError("CORPORATE_ACTION_EMPTY_RECEIPT", "Receipt has no cash or shares to post.", "action_id")
        return {"ok": True, "action_id": int(action_id), "event_ids": created, "posting_policy": "USER_CONFIRMED_ONLY"}

    def update_security(self, symbol: str, payload: dict) -> dict:
        return self.book.update_security(symbol, payload)

    def confirm_settlement(self, event_id: int, note: str = "") -> dict:
        return self.book.confirm_settlement(event_id, note=note)

    def lock_nav(self, snapshot_date: str) -> dict:
        return self.book.lock_nav(snapshot_date)

    def resolve_restatement(self, restatement_id: int) -> dict:
        with self.store.connect() as db:
            row = db.execute("SELECT affected_from_date FROM nav_restatements WHERE id=?", (int(restatement_id),)).fetchone()
        result = self.book.resolve_restatement(restatement_id)
        if row:
            with self.store.connect() as db:
                db.execute("UPDATE nav_controls SET status='RESTATED',updated_at=datetime('now') WHERE snapshot_date >= ? AND status='OFFICIAL'", (row["affected_from_date"],))
        result["nav_status"] = "RESTATED"
        return result

    def performance(self) -> dict:
        result = super().performance()
        result["methodology_policy"] = {
            "policy_version": "QPORT_PERF_V2",
            "valuation_frequency": "EOD",
            "position_recognition": "TRADE_DATE",
            "cost_method": "FIFO_TAX_LOTS",
            "external_flows": ["CASH_DEPOSIT", "CASH_WITHDRAW", "POSITION_IMPORT_OPENING_BALANCE"],
            "transaction_costs": "INCLUDED",
            "opening_imports": "NOT_HISTORICAL_PERFORMANCE",
            "twr": "DAILY_CHAIN_LINKED_WHEN_OFFICIAL_SNAPSHOTS_EXIST",
            "xirr": "BLOCKED_WHEN_OPENING_BALANCE_DATES_DO_NOT_PROVE_INVESTOR_CASHFLOWS",
            "gips_claim": "NONE",
        }
        return result
