from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from .accounting import AccountingError, apply_event, derive_state
from .activity import append_activity, ensure_activity_schema, list_activity, reanchor_activity_chain, verify_activity_chain
from .corrections import (
    CorrectionError,
    append_delete,
    append_edit,
    audit_log,
    clear_request_memo,
    effective_event,
    effective_events,
    ensure_schema,
    raw_events,
    transaction_versions,
)
from .domain import EventType, LedgerEvent, PortfolioState
from .institutional import InstitutionalBook
from .security_reference import VnstockSecurityReferenceProvider
from .service import PortfolioService
from .validation import (
    InputValidationError,
    normalize_account,
    normalize_broker,
    normalize_event_payload,
)

AUTHORITATIVE_CA_HOSTS = ("vsd.vn", "hnx.vn", "hsx.vn", "hose.vn")
IMPORT_KEY_RE = re.compile(r"^[A-Za-z0-9_.:-]{8,128}$")
IMPORT_MODES = {"CURRENT"}
CURRENT_IMPORT_TYPES = {EventType.POSITION_IMPORT, EventType.CASH_DEPOSIT}


def _now_utc_day() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class CorrectablePortfolioService(PortfolioService):
    """Operational QPort service with corrections + institutional-lite controls."""

    def __init__(self, store=None, market=None) -> None:
        super().__init__(store=store, market=market)
        ensure_schema(self.store)
        ensure_activity_schema(self.store)
        self.store.list_events = lambda start=None, end=None: effective_events(self.store, start=start, end=end)
        self.book = InstitutionalBook(self.store, today_fn=self.today_vn)
        self.security_reference = VnstockSecurityReferenceProvider()
        self._ensure_extended_schema()
        self._log("SYSTEM", "qport", "SYSTEM", "SERVICE_INITIALIZED", "QPort operational service initialized.")

    def _ensure_extended_schema(self) -> None:
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
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS import_batches (
                    idempotency_key TEXT PRIMARY KEY,
                    payload_hash TEXT NOT NULL,
                    import_mode TEXT NOT NULL,
                    source_name TEXT NOT NULL DEFAULT '',
                    event_ids_json TEXT NOT NULL DEFAULT '[]',
                    created_by TEXT NOT NULL DEFAULT 'local',
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'COMMITTED'
                )
                """
            )
            security_cols = {r["name"] for r in db.execute("PRAGMA table_info(security_master)").fetchall()}
            for name, sql_type in (
                ("name", "TEXT"),
                ("master_data_source", "TEXT"),
                ("master_data_status", "TEXT NOT NULL DEFAULT 'UNRESOLVED'"),
                ("resolved_at", "TEXT"),
            ):
                if name not in security_cols:
                    db.execute(f"ALTER TABLE security_master ADD COLUMN {name} {sql_type}")
            recon_cols = {r["name"] for r in db.execute("PRAGMA table_info(reconciliation_runs)").fetchall()}
            if "broker_code" not in recon_cols:
                db.execute("ALTER TABLE reconciliation_runs ADD COLUMN broker_code TEXT NOT NULL DEFAULT 'UNASSIGNED'")

    def _log(
        self,
        actor_type: str,
        actor_id: str,
        category: str,
        action: str,
        summary: str,
        *,
        entity_type: str | None = None,
        entity_id=None,
        details: dict | None = None,
        status: str = "SUCCESS",
        idempotency_key: str | None = None,
    ) -> int | None:
        try:
            return append_activity(
                self.store,
                actor_type=actor_type,
                actor_id=actor_id,
                category=category,
                action=action,
                summary=summary,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                status=status,
                idempotency_key=idempotency_key,
            )
        except Exception:
            return None

    def log_failure(self, *, method: str, path: str, error: str, code: str | None = None) -> None:
        self._log(
            "USER", "local", "API", "REQUEST_FAILED", f"{method} {path} failed: {error}",
            status="FAILURE", details={"method": method, "path": path, "error": error, "code": code},
        )

    def log_client_activity(self, action: str, details: dict | None = None) -> dict:
        allowed = {"AI_EXPORT", "PAGE_OPERATION"}
        action = str(action or "").upper()
        if action not in allowed:
            raise InputValidationError("INVALID_ACTIVITY", "Unsupported client activity.", "action")
        details = details or {}
        # P0 audit (2026-08-29): AI exports are audit-only reads of the whole
        # portfolio. Repeated exports of the same schema on the same day must be
        # idempotent: one record per (actor, schema, UTC day), never one per export.
        idempotency_key = None
        if action == "AI_EXPORT":
            schema = str(details.get("schema") or "default").upper()[:80]
            day = _now_utc_day()
            idempotency_key = f"AI_EXPORT:{day}:{schema}"
        log_id = self._log("USER", "local", "CLIENT", action, action.replace("_", " ").title(), details=details, idempotency_key=idempotency_key)
        return {"ok": True, "log_id": log_id}

    def activity_log(self, limit: int = 500, category: str | None = None) -> dict:
        return {"logs": list_activity(self.store, limit=limit, category=category), "integrity": verify_activity_chain(self.store)}

    def activity_chain_trace(self, from_id: int, limit: int = 10) -> dict:
        """Return the audit trace requested by review from ``from_id``.

        Surfaces event_id, event_type, occurred_at, source, idempotency_key,
        previous_hash and current_hash so a broken chain can be inspected before
        an operator runs the repair tool.
        """
        from .activity import trace_activity_chain
        return trace_activity_chain(self.store, from_id=from_id, limit=limit)

    def activity_chain_reanchor(self, *, operator: str, reason: str) -> dict:
        """Explicitly start a verified segment after a confirmed legacy link break.

        This is intentionally a write operation and must never be called by
        dashboard/export/read paths. The activity module refuses payload/hash
        corruption and only accepts PREV_HASH_MISMATCH legacy link breaks.
        """
        return reanchor_activity_chain(
            self.store,
            operator=str(operator or "admin"),
            reason=str(reason or "legacy-link-break"),
        )

    def transactions(self) -> list[dict]:
        rows = []
        for version in reversed(transaction_versions(self.store)):
            event = version["event"]
            correction = version["correction"]
            row = self._serialize_event(event)
            row["status"] = version["status"]
            row["correction"] = (
                {
                    "id": correction["id"],
                    "action": (
                        "SOFT_DELETE"
                        if correction["action"] == "DELETE"
                        else correction["action"]
                    ),
                    "reason": correction["reason"],
                    "created_by": correction["created_by"],
                    "created_at": correction["created_at"],
                }
                if correction
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
            if event.event_type in {EventType.BUY, EventType.RIGHTS_ISSUE, EventType.CASH_WITHDRAW, EventType.FEE} and state.cash < -1e-6:
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
        clear_request_memo()
        history = None
        if latest_snapshot and event.event_date <= latest_snapshot["snapshot_date"]:
            self.book.mark_restatement(event.event_date, f"Historical transaction #{eid} was added after NAV snapshots existed.", correction_event_id=eid)
            history = self._refresh_derived_history()
        self._log(
            "USER", event.created_by, "LEDGER", "TRANSACTION_CREATED", f"Created {event.event_type.value} transaction #{eid}.",
            entity_type="TRANSACTION", entity_id=eid,
            details={"event_type": event.event_type.value, "event_date": event.event_date, "symbol": event.symbol, "broker_code": event.broker_code, "account_id": event.account_id},
        )
        return {"ok": True, "event_id": eid, "event": self._serialize_event(stored), "history": history}

    @staticmethod
    def _import_reconciliation(state) -> dict:
        books: dict[tuple[str, str, str], dict] = {}
        for symbol, position in sorted(state.positions.items()):
            for lot in position.lots:
                key = (symbol, lot.broker_code, lot.account_id)
                row = books.setdefault(key, {
                    "symbol": symbol,
                    "broker_code": lot.broker_code,
                    "account_id": lot.account_id,
                    "shares": 0.0,
                    "cost_basis": 0.0,
                })
                row["shares"] += float(lot.remaining_quantity)
                row["cost_basis"] += float(lot.cost_basis)
        holdings = []
        for row in books.values():
            row["average_cost"] = row["cost_basis"] / row["shares"] if row["shares"] > 0 else 0.0
            holdings.append(row)
        holdings.sort(key=lambda row: (row["symbol"], row["broker_code"], row["account_id"]))
        return {
            "cash": float(state.cash),
            "holdings": holdings,
            "holding_count": len(holdings),
            "total_shares": sum(float(row["shares"]) for row in holdings),
            "status": "BALANCED",
        }

    # ------------------------------------------------------------------
    # Tracking boundary (Quick Import "current balance" mode)
    # ------------------------------------------------------------------
    def _tracking_boundary(self, db=None) -> dict:
        """Return the portfolio initialization mode and server-decided start date."""
        if db is None:
            with self.store.connect() as connection:
                return self._tracking_boundary(connection)
        rows = db.execute(
            "SELECT key, value FROM app_meta WHERE key IN ('initialization_mode', 'tracking_start_date')"
        ).fetchall()
        values = {row["key"]: row["value"] for row in rows}
        return {
            "initialization_mode": values.get("initialization_mode"),
            "tracking_start_date": values.get("tracking_start_date") or None,
        }

    def _ensure_tracking_boundary(self, mode: str, db=None) -> dict:
        """Persist one initialization mode and reject attempts to mix import histories."""
        requested_mode = str(mode).upper()
        if db is None:
            with self.store.connect() as connection:
                return self._ensure_tracking_boundary(requested_mode, connection)
        boundary = self._tracking_boundary(db)
        existing_mode = boundary["initialization_mode"]
        if existing_mode:
            if existing_mode != requested_mode:
                raise InputValidationError(
                    "IMPORT_MODE_CONFLICT",
                    f"Portfolio was initialized in {existing_mode} mode and cannot import {requested_mode} data. "
                    "Create a new portfolio or explicitly reset its initialization data.",
                    "mode",
                )
            return boundary
        db.execute(
            "INSERT OR REPLACE INTO app_meta(key, value) VALUES ('initialization_mode', ?)",
            (requested_mode,),
        )
        if requested_mode == "CURRENT":
            db.execute(
                "INSERT OR REPLACE INTO app_meta(key, value) VALUES ('tracking_start_date', ?)",
                (self.today_vn(),),
            )
        return self._tracking_boundary(db)

    @staticmethod
    def _corporate_action_entitlement_date(action: dict) -> str:
        """Use the entitlement boundary, never the later cash/share receipt date."""
        return str(
            action.get("ex_date")
            or action.get("record_date")
            or action.get("effective_event_date")
            or action.get("announcement_date")
            or action.get("payment_date")
            or ""
        ).strip()

    def _guard_corporate_action_date(self, effective_date: str) -> None:
        """Reject posting a corporate action that predates a CURRENT tracking start."""
        boundary = self._tracking_boundary()
        if boundary.get("initialization_mode") != "CURRENT":
            return
        start = boundary.get("tracking_start_date")
        effective_date = str(effective_date or "").strip()
        if start and effective_date and effective_date < start:
            raise InputValidationError(
                "CORPORATE_ACTION_BEFORE_TRACKING_START",
                f"Corporate action dated {effective_date} predates the CURRENT tracking start ({start}) "
                "and is already reflected in the opening balance; it cannot be posted again.",
                "received_date",
            )

    def _annotate_corporate_actions(self, actions: list[dict]) -> list[dict]:
        boundary = self._tracking_boundary()
        start = boundary.get("tracking_start_date") if boundary.get("initialization_mode") == "CURRENT" else None
        for action in actions:
            effective = self._corporate_action_entitlement_date(action)
            before = bool(start and effective and effective < start)
            action["before_tracking_start"] = before
            if before:
                action["tracking_flag"] = "BEFORE_TRACKING_START"
        return actions

    def _prepare_import(self, payload: dict, *, created_by: str) -> dict:
        if not isinstance(payload, dict):
            raise InputValidationError("INVALID_IMPORT", "Import request must be an object.", "rows")
        mode = str(payload.get("mode") or "CURRENT").strip().upper()
        if mode not in IMPORT_MODES:
            raise InputValidationError("INVALID_IMPORT_MODE", "mode must be CURRENT.", "mode")
        rows = payload.get("rows")
        if not isinstance(rows, list) or not rows:
            raise InputValidationError("IMPORT_ROWS_REQUIRED", "Provide at least one import row.", "rows")
        if len(rows) > 1000:
            raise InputValidationError("IMPORT_TOO_LARGE", "One import may contain at most 1,000 rows.", "rows")

        source_name = str(payload.get("source_name") or "quick-paste").strip()[:160]
        # Capture ONE server-decided date for the whole batch so a retry across
        # midnight cannot split the batch across two dates or break idempotency.
        batch_date = self.today_vn()
        cost_basis_adjusted = bool(payload.get("cost_basis_adjusted") is True)
        if not cost_basis_adjusted:
            raise InputValidationError(
                "COST_BASIS_CONFIRMATION_REQUIRED",
                "Chế độ Số dư hiện tại yêu cầu xác nhận số lượng và giá vốn đã phản ánh toàn bộ chia/tách, "
                "cổ tức cổ phiếu và cổ phiếu thưởng trước hôm nay.",
                "cost_basis_adjusted",
            )
        confirmed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        clean_rows = []
        for index, raw in enumerate(rows, start=1):
            if not isinstance(raw, dict):
                raise InputValidationError("INVALID_IMPORT_ROW", f"Import row {index} must be an object.", f"rows[{index - 1}]")
            candidate = dict(raw)
            candidate["event_date"] = batch_date
            candidate["event_type"] = str(candidate.get("event_type") or "POSITION_IMPORT").upper()
            try:
                clean = normalize_event_payload(candidate, today=batch_date)
            except InputValidationError as exc:
                raise InputValidationError(exc.code, f"Dòng {index}: {exc.message}", f"rows[{index - 1}].{exc.field or 'row'}") from exc
            if clean["event_type"] not in CURRENT_IMPORT_TYPES:
                raise InputValidationError(
                    "CURRENT_IMPORT_EVENT_TYPE",
                    f"Dòng {index}: Nhập nhanh chỉ nhận POSITION_IMPORT hoặc CASH_DEPOSIT; {clean['event_type'].value} phải dùng form giao dịch thường.",
                    f"rows[{index - 1}].event_type",
                )
            clean_rows.append(clean)

        canonical = []
        for clean in clean_rows:
            canonical.append({
                "event_type": clean["event_type"].value,
                "event_date": clean["event_date"],
                "symbol": clean["symbol"],
                "quantity": clean["quantity"],
                "price": clean["price"],
                "fee": clean["fee"],
                "tax": clean["tax"],
                "amount": clean["amount"],
                "ratio": clean["ratio"],
                "note": clean["note"],
                "metadata": clean["metadata"],
            })

        # The idempotency hash covers the BUSINESS payload. For CURRENT imports the
        # event date is server policy, not client data, so it is excluded: a retry
        # across midnight must resolve to the original stored batch.
        hash_rows = [
            {key: value for key, value in row.items() if key != "event_date"}
            for row in canonical
        ]
        payload_hash = hashlib.sha256(json.dumps(
            {"mode": mode, "cost_basis_adjusted": cost_basis_adjusted, "rows": hash_rows},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        idempotency_key = str(payload.get("idempotency_key") or f"import:{payload_hash[:32]}").strip()
        if not IMPORT_KEY_RE.fullmatch(idempotency_key):
            raise InputValidationError("INVALID_IDEMPOTENCY_KEY", "idempotency_key must be 8–128 safe characters.", "idempotency_key")

        with self.store.connect() as db:
            existing = db.execute(
                "SELECT payload_hash, event_ids_json FROM import_batches WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if existing:
            if existing["payload_hash"] != payload_hash:
                raise InputValidationError(
                    "IDEMPOTENCY_KEY_REUSED",
                    "This idempotency_key was already used for different import data.",
                    "idempotency_key",
                )
            existing_event_ids = json.loads(existing["event_ids_json"] or "[]")
            event_by_id = {int(event.id or 0): event for event in raw_events(self.store)}
            stored_events = [event_by_id[event_id] for event_id in existing_event_ids if event_id in event_by_id]
            stored_rows = [{
                "event_type": event.event_type.value,
                "event_date": event.event_date,
                "symbol": event.symbol,
                "quantity": event.quantity,
                "price": event.price,
                "fee": event.fee,
                "tax": event.tax,
                "amount": event.amount,
                "ratio": event.ratio,
                "note": event.note,
                "metadata": event.metadata,
            } for event in stored_events]
            first_metadata = stored_events[0].metadata if stored_events else {}
            current_state = derive_state(effective_events(self.store))
            return {
                "mode": mode,
                "source_name": source_name,
                "payload_hash": payload_hash,
                "idempotency_key": idempotency_key,
                "tracking_start_date": first_metadata.get("tracking_start_date"),
                "cost_basis_confirmed_at": first_metadata.get("cost_basis_confirmed_at"),
                "events": [],
                "rows": stored_rows or canonical,
                "warnings": ["Dữ liệu này đã được ghi trước đó; xác nhận lại sẽ không tạo giao dịch trùng."],
                "reconciliation": self._import_reconciliation(current_state),
                "existing_event_ids": existing_event_ids,
            }

        actor = str(created_by or "local")[:100]
        source = raw_events(self.store)
        next_id = max((int(event.id or 0) for event in source), default=0) + 1
        events = []
        for index, clean in enumerate(clean_rows, start=1):
            metadata = dict(clean["metadata"])
            metadata.update({
                "import_batch_id": idempotency_key,
                "import_payload_hash": payload_hash,
                "import_mode": mode,
                "import_source": source_name,
                "import_row": index,
                "opening_balance": mode == "CURRENT",
            })
            if mode == "CURRENT":
                metadata.update({
                    "cost_basis_adjusted": True,
                    "cost_basis_confirmed_at": confirmed_at,
                    "tracking_start_date": batch_date,
                })
            row = dict(clean)
            row["metadata"] = metadata
            events.append(self._event_from_clean(row, event_id=next_id + index - 1, created_by=actor))

        projected = effective_events(self.store) + events
        self._validate_ledger(projected)
        projected_state = derive_state(sorted(projected, key=lambda event: (event.event_date, int(event.id or 0))))
        warnings = []
        if mode == "CURRENT":
            warnings.append("Số dư hiện tại bắt đầu đo hiệu suất từ hôm nay; QPort không dựng giao dịch mua giả trong quá khứ.")
        else:
            warnings.append("Lịch sử đầy đủ sẽ tính lại snapshot từ ngày giao dịch sớm nhất và có thể mất thêm thời gian.")
        return {
            "mode": mode,
            "source_name": source_name,
            "payload_hash": payload_hash,
            "idempotency_key": idempotency_key,
            "tracking_start_date": batch_date if mode == "CURRENT" else None,
            "cost_basis_confirmed_at": confirmed_at if mode == "CURRENT" else None,
            "events": events,
            "rows": canonical,
            "warnings": warnings,
            "reconciliation": self._import_reconciliation(projected_state),
        }

    def preview_import(self, payload: dict, created_by: str = "local") -> dict:
        prepared = self._prepare_import(payload, created_by=created_by)
        return {
            "ok": True,
            "preview": True,
            "mode": prepared["mode"],
            "row_count": len(prepared["rows"]),
            "idempotency_key": prepared["idempotency_key"],
            "payload_hash": prepared["payload_hash"],
            "tracking_start_date": prepared.get("tracking_start_date"),
            "cost_basis_confirmed_at": prepared.get("cost_basis_confirmed_at"),
            "rows": prepared["rows"],
            "warnings": prepared["warnings"],
            "reconciliation": prepared["reconciliation"],
        }

    def import_events(self, payload: dict, created_by: str = "local") -> dict:
        prepared = self._prepare_import(payload, created_by=created_by)
        key = prepared["idempotency_key"]
        payload_hash = prepared["payload_hash"]
        tracking = {
            "tracking_start_date": prepared.get("tracking_start_date"),
            "cost_basis_confirmed_at": prepared.get("cost_basis_confirmed_at"),
        }
        if "existing_event_ids" in prepared:
            self._ensure_tracking_boundary(prepared["mode"])
            return {
                "ok": True,
                "deduplicated": True,
                "idempotency_key": key,
                "event_ids": prepared["existing_event_ids"],
                "row_count": len(prepared["rows"]),
                "warnings": prepared["warnings"],
                "reconciliation": prepared["reconciliation"],
                **tracking,
            }
        with self.store.connect() as db:
            self._ensure_tracking_boundary(prepared["mode"], db)
            existing = db.execute(
                "SELECT * FROM import_batches WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if existing:
                if existing["payload_hash"] != payload_hash:
                    raise InputValidationError(
                        "IDEMPOTENCY_KEY_REUSED",
                        "This idempotency_key was already used for different import data.",
                        "idempotency_key",
                    )
                return {
                    "ok": True,
                    "deduplicated": True,
                    "idempotency_key": key,
                    "event_ids": json.loads(existing["event_ids_json"] or "[]"),
                    "row_count": len(prepared["events"]),
                    "reconciliation": prepared["reconciliation"],
                    **tracking,
                }

            event_ids = []
            for event in prepared["events"]:
                stored = LedgerEvent(
                    id=None, event_type=event.event_type, event_date=event.event_date,
                    symbol=event.symbol, quantity=event.quantity, price=event.price,
                    fee=event.fee, tax=event.tax, amount=event.amount, ratio=event.ratio,
                    note=event.note, created_by=event.created_by, metadata=event.metadata,
                )
                event_ids.append(self.store.insert_event(db, stored))
            db.execute(
                """
                INSERT INTO import_batches (
                    idempotency_key, payload_hash, import_mode, source_name,
                    event_ids_json, created_by, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'COMMITTED')
                """,
                (
                    key, payload_hash, prepared["mode"], prepared["source_name"],
                    json.dumps(event_ids), str(created_by or "local")[:100], self.store._now(),
                ),
            )

        history = None
        latest_snapshot = self.store.latest_snapshot()
        earliest = min(event.event_date for event in prepared["events"])
        clear_request_memo()
        if latest_snapshot and earliest <= latest_snapshot["snapshot_date"]:
            self.book.mark_restatement(
                earliest,
                f"Import batch {key} added historical ledger events.",
                correction_event_id=event_ids[0],
            )
            history = self._refresh_derived_history()
        self._log(
            "USER", str(created_by or "local")[:100], "LEDGER", "IMPORT_COMMITTED",
            f"Imported {len(event_ids)} transactions as one atomic batch.",
            entity_type="IMPORT_BATCH", entity_id=key,
            details={"mode": prepared["mode"], "source_name": prepared["source_name"], "event_ids": event_ids, "payload_hash": payload_hash},
        )
        return {
            "ok": True,
            "deduplicated": False,
            "idempotency_key": key,
            "event_ids": event_ids,
            "row_count": len(event_ids),
            "history": history,
            "warnings": prepared["warnings"],
            "reconciliation": prepared["reconciliation"],
            **tracking,
        }

    def _replacement_event(self, event_id: int, payload: dict) -> LedgerEvent:
        current = effective_event(self.store, event_id)
        if current is None:
            raise CorrectionError("Transaction not found or already deleted.")
        merged = self._serialize_event(current)
        for key in ("event_type", "event_date", "symbol", "quantity", "price", "fee", "tax", "amount", "ratio", "note", "metadata", "broker_code", "account_id", "settlement_date"):
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
        clear_request_memo()
        self._mark_restatement_if_needed(affected_from, f"EDIT transaction #{event_id}: {reason}", int(event_id))
        history = self._refresh_derived_history()
        self._log(
            "USER", created_by, "LEDGER", "TRANSACTION_CORRECTED", f"Corrected transaction #{event_id}.",
            entity_type="TRANSACTION", entity_id=event_id,
            details={"correction_id": correction_id, "reason": reason, "before": self._serialize_event(current), "after": self._serialize_event(replacement)},
        )
        return {"ok": True, "event_id": int(event_id), "correction_id": correction_id, "action": "EDIT", "event": self._serialize_event(replacement), "affected_from": affected_from, "history": history}

    def delete_event(self, event_id: int, reason: str, created_by: str = "local") -> dict:
        """Soft-delete a transaction and rebuild all state derived from the ledger."""
        reason = str(reason or "").strip()
        if not reason:
            raise InputValidationError(
                "DISCARD_REASON_REQUIRED",
                "reason is required when discarding a transaction.",
                "reason",
            )
        current = effective_event(self.store, int(event_id))
        if current is None:
            raise CorrectionError("Transaction not found or already soft-deleted.")
        if bool((current.metadata or {}).get("auto_generated")):
            raise InputValidationError(
                "AUTOMATED_TRANSACTION_DISCARD_FORBIDDEN",
                "Automatically generated transactions must be corrected through their source workflow.",
                "event_id",
            )

        remaining = [
            event
            for event in effective_events(self.store)
            if int(event.id or 0) != int(event_id)
        ]
        self._validate_ledger(remaining)
        correction_id = append_delete(
            self.store,
            int(event_id),
            reason=reason,
            created_by=created_by,
        )
        clear_request_memo()
        self._mark_restatement_if_needed(
            current.event_date,
            f"SOFT_DELETE transaction #{event_id}: {reason}",
            int(event_id),
        )
        history = self._refresh_derived_history()
        self._log(
            "USER",
            created_by,
            "LEDGER",
            "TRANSACTION_SOFT_DELETED",
            f"Soft-deleted transaction #{event_id} from the effective ledger.",
            entity_type="TRANSACTION",
            entity_id=event_id,
            details={
                "correction_id": correction_id,
                "reason": reason,
                "original": self._serialize_event(current),
            },
        )
        return {
            "ok": True,
            "event_id": int(event_id),
            "correction_id": correction_id,
            "action": "SOFT_DELETE",
            "status": "SOFT_DELETED",
            "affected_from": current.event_date,
            "history": history,
        }

    def set_reference_weights(self, weights: dict[str, float]) -> dict:
        result = super().set_reference_weights(weights)
        self._log("USER", "local", "SETTINGS", "REFERENCE_WEIGHTS_CHANGED", "Strategic reference weights changed.", details=result)
        return result

    def set_cash_reserve(self, amount) -> dict:
        result = super().set_cash_reserve(amount)
        self._log("USER", "local", "SETTINGS", "CASH_RESERVE_CHANGED", "Strategic cash reserve changed.", details=result)
        return result

    def sync_daily(self, actor_type: str = "SYSTEM", actor_id: str = "scheduler") -> dict:
        result = super().sync_daily()
        self._log(
            actor_type, actor_id, "MARKET_DATA", "DAILY_MARKET_SYNC", result.get("message") or "Daily market sync completed.",
            status="SUCCESS" if result.get("ok") else "PARTIAL", details={"snapshot_date": result.get("snapshot_date"), "errors": result.get("errors"), "history": result.get("history")},
        )
        return result

    def institutional_overview(self) -> dict:
        events = effective_events(self.store)
        state = derive_state(events)
        symbols = sorted(state.positions)
        self.book.ensure_securities(symbols)
        prices = self.store.latest_prices(symbols)
        market = self._market_metadata(symbols, prices)
        snapshots = self.store.list_snapshots(limit=10000)
        overview = self.book.overview(events=events, state=state, prices=prices, snapshots=snapshots, preferences=self.preferences(), market_status=market["status"])
        overview["tax_lots"] = [
            {
                "lot_id": lot.lot_id, "symbol": symbol, "acquisition_date": lot.acquisition_date,
                "source_event_id": lot.source_event_id, "original_quantity": lot.original_quantity,
                "remaining_quantity": lot.remaining_quantity, "unit_cost": lot.unit_cost, "cost_basis": lot.cost_basis,
                "broker_code": lot.broker_code, "account_id": lot.account_id, "cost_method": "FIFO",
            }
            for symbol, position in sorted(state.positions.items()) for lot in sorted(position.lots, key=lambda x: (x.acquisition_date, x.lot_id))
        ]
        event_map = {int(e.id or 0): e for e in events}
        for trade in (overview.get("settlement") or {}).get("trades") or []:
            event = event_map.get(int(trade.get("event_id") or 0))
            if event:
                trade["broker_code"] = event.broker_code
                trade["account_id"] = event.account_id
        with self.store.connect() as db:
            postings = [dict(r) for r in db.execute("SELECT * FROM corporate_action_postings ORDER BY action_id, posting_type").fetchall()]
        posting_map = {}
        for posting in postings:
            posting_map.setdefault(int(posting["action_id"]), []).append(posting)
        for action in overview.get("corporate_actions") or []:
            action["postings"] = posting_map.get(int(action["id"]), [])
            action["ledger_posted"] = bool(action["postings"])
        overview["corporate_actions"] = self._annotate_corporate_actions(overview.get("corporate_actions") or [])
        overview["tracking_boundary"] = self._tracking_boundary()
        overview["security_reference_provider"] = self.security_reference.health()
        overview["activity_integrity"] = verify_activity_chain(self.store)
        return overview

    def reconcile_broker(self, payload: dict, created_by: str = "local") -> dict:
        broker_code = normalize_broker(payload.get("broker_code"))
        account_id = normalize_account(payload.get("account_id"))
        all_events = effective_events(self.store)
        events = [e for e in all_events if e.broker_code == broker_code and e.account_id == account_id]
        state = derive_state(events)
        prefs = self.preferences()
        reserve = prefs.get("cash_reserve") if prefs.get("cash_reserve_configured") else None
        settlement = self.book.settlement_view(events, state.cash, reserve=reserve)
        state.cash = float(settlement["settled_cash"])
        clean_payload = {**payload, "broker_code": broker_code, "account_id": account_id}
        result = self.book.reconcile(state, clean_payload, created_by=created_by)
        with self.store.connect() as db:
            db.execute("UPDATE reconciliation_runs SET broker_code=? WHERE id=?", (broker_code, int(result["run_id"])))
        result.update({"cash_basis": "SETTLED_CASH", "broker_code": broker_code, "account_id": account_id})
        self._log(
            "USER", created_by, "RECONCILIATION", "BROKER_RECONCILIATION_RUN", f"Broker reconciliation {result['status']} for {broker_code}/{account_id}.",
            entity_type="RECONCILIATION", entity_id=result["run_id"], details=result,
        )
        return result

    def sync_corporate_actions(self, start: str | None = None, end: str | None = None) -> dict:
        boundary = self._tracking_boundary()
        if boundary.get("initialization_mode") == "CURRENT" and boundary.get("tracking_start_date"):
            start = start or boundary["tracking_start_date"]
            if start and start < boundary["tracking_start_date"]:
                start = boundary["tracking_start_date"]
        result = self.book.sync_corporate_actions(sorted(self.current_state().positions), start=start, end=end)
        self._log("USER", "local", "CORPORATE_ACTION", "CORPORATE_ACTION_SYNC", f"Corporate-action sync discovered {result.get('discovered', 0)} event(s).", details=result)
        return result

    @staticmethod
    def _authoritative_corporate_action_url(source_url: str) -> bool:
        host = (urlparse(str(source_url or "")).hostname or "").lower().strip(".")
        return any(host == allowed or host.endswith("." + allowed) for allowed in AUTHORITATIVE_CA_HOSTS)

    def verify_corporate_action(self, action_id: int, source_url: str, verified_by: str = "local") -> dict:
        if not self._authoritative_corporate_action_url(source_url):
            raise InputValidationError("NON_AUTHORITATIVE_CORPORATE_ACTION_SOURCE", "VERIFIED requires an authoritative VSDC/HOSE/HNX source URL. Other sources may be used only for discovery/cross-checking.", "source_url")
        result = self.book.verify_corporate_action(action_id, source_url, verified_by=verified_by)
        self._log("USER", verified_by, "CORPORATE_ACTION", "CORPORATE_ACTION_VERIFIED", f"Verified corporate action #{action_id}.", entity_type="CORPORATE_ACTION", entity_id=action_id, details={"source_url": source_url})
        return result

    def record_corporate_action_receipt(self, action_id: int, payload: dict, created_by: str = "local") -> dict:
        actions = {int(action["id"]): action for action in self.book.corporate_actions(effective_events(self.store))}
        action = actions.get(int(action_id))
        if not action:
            raise InputValidationError("CORPORATE_ACTION_NOT_FOUND", "Corporate action not found.", "action_id")
        self._guard_corporate_action_date(self._corporate_action_entitlement_date(action))
        result = self.book.record_corporate_action_receipt(action_id, payload, created_by=created_by)
        self._log("USER", created_by, "CORPORATE_ACTION", "CORPORATE_ACTION_RECEIPT_RECORDED", f"Recorded receipt for corporate action #{action_id}.", entity_type="CORPORATE_ACTION", entity_id=action_id, details=result)
        return result

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
        self._guard_corporate_action_date(self._corporate_action_entitlement_date(action))
        with self.store.connect() as db:
            existing = {r["posting_type"]: int(r["event_id"]) for r in db.execute("SELECT posting_type,event_id FROM corporate_action_postings WHERE action_id=?", (int(action_id),)).fetchall()}
        created = []
        metadata = {"corporate_action_id": int(action_id), "corporate_action_source": action.get("source_url") or action.get("source")}
        if float(receipt.get("actual_cash") or 0) > 0 and "CASH" not in existing:
            result = self.append_event({"event_type": "CASH_DIVIDEND", "event_date": receipt["received_date"], "symbol": action["symbol"], "amount": float(receipt["actual_cash"]), "note": f"Corporate action #{action_id} cash receipt", "metadata": metadata}, created_by=created_by)
            with self.store.connect() as db:
                db.execute("INSERT INTO corporate_action_postings(action_id,posting_type,event_id,created_by,created_at) VALUES (?,?,?,?,datetime('now'))", (int(action_id), "CASH", int(result["event_id"]), str(created_by)[:100]))
            created.append(result["event_id"])
        if float(receipt.get("actual_shares") or 0) > 0 and "STOCK" not in existing:
            result = self.append_event({"event_type": "STOCK_DIVIDEND", "event_date": receipt["received_date"], "symbol": action["symbol"], "quantity": float(receipt["actual_shares"]), "note": f"Corporate action #{action_id} stock receipt", "metadata": metadata}, created_by=created_by)
            with self.store.connect() as db:
                db.execute("INSERT INTO corporate_action_postings(action_id,posting_type,event_id,created_by,created_at) VALUES (?,?,?,?,datetime('now'))", (int(action_id), "STOCK", int(result["event_id"]), str(created_by)[:100]))
            created.append(result["event_id"])
        if not created and existing:
            raise InputValidationError("CORPORATE_ACTION_ALREADY_POSTED", "Corporate-action receipt has already been posted to the ledger.", "action_id")
        if not created:
            raise InputValidationError("CORPORATE_ACTION_EMPTY_RECEIPT", "Receipt has no cash or shares to post.", "action_id")
        result = {"ok": True, "action_id": int(action_id), "event_ids": created, "posting_policy": "USER_CONFIRMED_ONLY"}
        self._log("USER", created_by, "CORPORATE_ACTION", "CORPORATE_ACTION_POSTED", f"Posted corporate action #{action_id} to ledger.", entity_type="CORPORATE_ACTION", entity_id=action_id, details=result)
        return result

    def update_security(self, symbol: str, payload: dict) -> dict:
        result = self.book.update_security(symbol, payload)
        self._log("USER", "local", "SECURITY_MASTER", "SECURITY_MASTER_UPDATED", f"Updated security master for {symbol.upper()}.", entity_type="SECURITY", entity_id=symbol.upper(), details=result)
        return result

    def resolve_security(self, symbol: str) -> dict:
        symbol = str(symbol).upper().strip()
        self.book.ensure_securities([symbol])
        resolved = self.security_reference.resolve(symbol)
        with self.store.connect() as db:
            current = db.execute("SELECT * FROM security_master WHERE symbol=?", (symbol,)).fetchone()
            if not current:
                raise InputValidationError("SECURITY_NOT_FOUND", "Security not found.", "symbol")
            current = dict(current)
            exchange = resolved.get("exchange") or current.get("exchange") or "UNKNOWN"
            isin = resolved.get("isin") or current.get("isin")
            name = resolved.get("name") or current.get("name")
            lot_size = resolved.get("lot_size") if resolved.get("lot_size") is not None else current.get("lot_size")
            status = "RESOLVED" if isin else str(resolved.get("status") or "UNRESOLVED")
            db.execute(
                """
                UPDATE security_master
                SET exchange=?, isin=?, name=?, lot_size=?, master_data_source=?, master_data_status=?, resolved_at=datetime('now'), updated_at=datetime('now')
                WHERE symbol=?
                """,
                (exchange, isin, name, lot_size, resolved.get("source"), status, symbol),
            )
            row = dict(db.execute("SELECT * FROM security_master WHERE symbol=?", (symbol,)).fetchone())
        self._log("USER", "local", "SECURITY_MASTER", "SECURITY_AUTO_RESOLVED", f"Auto-resolved security master for {symbol}: {status}.", entity_type="SECURITY", entity_id=symbol, details={"result": resolved})
        return {"ok": True, "security": row, "resolution": resolved}

    def resolve_all_securities(self) -> dict:
        symbols = sorted(self.current_state().positions)
        results = [self.resolve_security(symbol) for symbol in symbols]
        return {"ok": True, "resolved": results, "provider": self.security_reference.health()}

    def confirm_settlement(self, event_id: int, note: str = "") -> dict:
        result = self.book.confirm_settlement(event_id, note=note)
        self._log("USER", "local", "SETTLEMENT", "SETTLEMENT_CONFIRMED", f"Confirmed settlement for transaction #{event_id}.", entity_type="TRANSACTION", entity_id=event_id, details={"note": note})
        return result

    def lock_nav(self, snapshot_date: str) -> dict:
        result = self.book.lock_nav(snapshot_date)
        self._log("USER", "local", "NAV", "NAV_LOCKED", f"Locked NAV for {snapshot_date}.", entity_type="NAV", entity_id=snapshot_date, details=result)
        return result

    def resolve_restatement(self, restatement_id: int) -> dict:
        with self.store.connect() as db:
            row = db.execute("SELECT affected_from_date FROM nav_restatements WHERE id=?", (int(restatement_id),)).fetchone()
        result = self.book.resolve_restatement(restatement_id)
        if row:
            with self.store.connect() as db:
                db.execute("UPDATE nav_controls SET status='RESTATED',updated_at=datetime('now') WHERE snapshot_date >= ? AND status='OFFICIAL'", (row["affected_from_date"],))
        result["nav_status"] = "RESTATED"
        self._log("USER", "local", "NAV", "NAV_RESTATEMENT_RESOLVED", f"Resolved NAV restatement #{restatement_id}.", entity_type="RESTATEMENT", entity_id=restatement_id, details=result)
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
