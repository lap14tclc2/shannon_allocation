from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any

# P0 audit (2026-08-29): the prev_hash chain can branch when two concurrent
# appends both read the same tail record_hash before either commits. All writers
# must serialize on this lock so each new record chains to the real tail.
_append_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_postgres(db) -> bool:
    return hasattr(db, "schema")


def _acquire_append_serialization(db) -> None:
    """Serialize appends across threads AND processes.

    SQLite: ``BEGIN IMMEDIATE`` takes a write lock before the tail read, so a
    concurrent append blocks until the current transaction commits and then reads
    the true tail hash. PostgreSQL: ``pg_advisory_xact_lock`` serializes appends
    inside the current transaction (held until commit).
    """
    if _is_postgres(db):
        db.execute("SELECT pg_advisory_xact_lock(9790101)")
    else:
        db.execute("BEGIN IMMEDIATE")


def ensure_activity_schema(store) -> None:
    with store.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                occurred_at TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                category TEXT NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id TEXT,
                status TEXT NOT NULL,
                summary TEXT NOT NULL,
                details_json TEXT NOT NULL DEFAULT '{}',
                source TEXT NOT NULL DEFAULT 'QPORT',
                idempotency_key TEXT,
                prev_hash TEXT,
                record_hash TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_activity_log_occurred_at ON activity_log(occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_activity_log_category ON activity_log(category, occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_activity_log_action ON activity_log(action, occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_activity_log_actor ON activity_log(actor_type, actor_id, occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_activity_log_status ON activity_log(status, occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_activity_log_category_status ON activity_log(category, status, occurred_at DESC);
            """
        )
        # Migrate pre-existing logs that predate the idempotency column.
        try:
            cols = {r["name"] for r in db.execute("PRAGMA table_info(activity_log)").fetchall()}
            if "idempotency_key" not in cols:
                db.execute("ALTER TABLE activity_log ADD COLUMN idempotency_key TEXT")
        except Exception:
            pass
        db.executescript(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_activity_log_idempotency
                ON activity_log(idempotency_key) WHERE idempotency_key IS NOT NULL;
            """
        )


def _canonical_payload(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def append_activity(
    store,
    *,
    actor_type: str,
    actor_id: str,
    category: str,
    action: str,
    summary: str,
    status: str = "SUCCESS",
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    details: dict[str, Any] | None = None,
    source: str = "QPORT",
    idempotency_key: str | None = None,
) -> int:
    """Append one tamper-evident activity record.

    The table has no update/delete API. Each row hashes the previous row hash plus
    its own canonical payload so accidental/manual mutations can be detected by
    ``verify_activity_chain``.

    ``idempotency_key`` (optional) makes the append idempotent: when a row with
    the same key already exists, the existing id is returned and nothing is
    appended. This guarantees audit-only operations (e.g. repeated AI exports of
    the same schema/day) never grow the log.
    """
    ensure_activity_schema(store)
    occurred_at = _now()
    actor_type = str(actor_type or "SYSTEM").upper()[:20]
    actor_id = str(actor_id or "qport")[:100]
    category = str(category or "SYSTEM").upper()[:50]
    action = str(action or "UNKNOWN").upper()[:100]
    status = str(status or "SUCCESS").upper()[:20]
    summary = str(summary or action)[:1000]
    source = str(source or "QPORT")[:50]
    idempotency_key = str(idempotency_key).strip()[:200] if idempotency_key else None
    details_json = json.dumps(details or {}, ensure_ascii=False, sort_keys=True, default=str)

    with _append_lock:
        with store.connect() as db:
            _acquire_append_serialization(db)
            if idempotency_key:
                existing = db.execute(
                    "SELECT id FROM activity_log WHERE idempotency_key=? ORDER BY id LIMIT 1",
                    (idempotency_key,),
                ).fetchone()
                if existing:
                    return int(existing["id"])
            previous = db.execute("SELECT record_hash FROM activity_log ORDER BY id DESC LIMIT 1").fetchone()
            prev_hash = previous["record_hash"] if previous else None
            payload = {
                "occurred_at": occurred_at,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "category": category,
                "action": action,
                "entity_type": entity_type,
                "entity_id": None if entity_id is None else str(entity_id),
                "status": status,
                "summary": summary,
                "details_json": details_json,
                "source": source,
                "prev_hash": prev_hash,
            }
            digest = hashlib.sha256(((prev_hash or "") + _canonical_payload(payload)).encode("utf-8")).hexdigest()
            cur = db.execute(
                """
                INSERT INTO activity_log(
                    occurred_at,actor_type,actor_id,category,action,entity_type,entity_id,
                    status,summary,details_json,source,idempotency_key,prev_hash,record_hash
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    occurred_at, actor_type, actor_id, category, action, entity_type,
                    None if entity_id is None else str(entity_id), status, summary,
                    details_json, source, idempotency_key, prev_hash, digest,
                ),
            )
            return int(cur.lastrowid)


def list_activity(store, *, limit: int = 500, category: str | None = None) -> list[dict]:
    ensure_activity_schema(store)
    limit = max(1, min(int(limit or 500), 5000))
    with store.connect() as db:
        if category:
            rows = db.execute(
                "SELECT * FROM activity_log WHERE category=? ORDER BY id DESC LIMIT ?",
                (str(category).upper(), limit),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["details"] = json.loads(item.pop("details_json") or "{}")
        except Exception:
            item["details"] = {}
            item.pop("details_json", None)
        out.append(item)
    return out


def list_activity_page(
    store,
    *,
    page: int = 1,
    page_size: int = 50,
    category: str | None = None,
    actor_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> tuple[list[dict], int]:
    """Fetch a bounded page using SQL predicates; never materialize the full log."""
    ensure_activity_schema(store)
    page = max(1, int(page))
    page_size = max(1, min(int(page_size or 50), 200))
    clauses = []
    params: list[Any] = []
    if category and category.upper() != "ALL":
        clauses.append("category=?"); params.append(category.upper())
    if actor_type and actor_type.upper() != "ALL":
        clauses.append("actor_type=?"); params.append(actor_type.upper())
    if status and status.upper() != "ALL":
        clauses.append("status=?"); params.append(status.upper())
    if q:
        needle = f"%{str(q).strip().lower()}%"
        clauses.append("(LOWER(action) LIKE ? OR LOWER(summary) LIKE ? OR LOWER(entity_type) LIKE ? OR LOWER(entity_id) LIKE ? OR LOWER(actor_id) LIKE ?)")
        params.extend([needle] * 5)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with store.connect() as db:
        total_row = db.execute(f"SELECT COUNT(*) AS count FROM activity_log{where}", tuple(params)).fetchone()
        rows = db.execute(
            f"SELECT * FROM activity_log{where} ORDER BY occurred_at DESC, id DESC LIMIT ? OFFSET ?",
            tuple(params + [page_size, (page - 1) * page_size]),
        ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["details"] = json.loads(item.pop("details_json") or "{}")
        except Exception:
            item["details"] = {}
            item.pop("details_json", None)
        out.append(item)
    return out, int(total_row["count"] if total_row else 0)


def verify_activity_chain(store) -> dict:
    ensure_activity_schema(store)
    with store.connect() as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM activity_log ORDER BY id").fetchall()]
    previous_hash = None
    for row in rows:
        payload = {
            "occurred_at": row["occurred_at"],
            "actor_type": row["actor_type"],
            "actor_id": row["actor_id"],
            "category": row["category"],
            "action": row["action"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "status": row["status"],
            "summary": row["summary"],
            "details_json": row["details_json"],
            "source": row["source"],
            "prev_hash": row["prev_hash"],
        }
        expected = hashlib.sha256(((previous_hash or "") + _canonical_payload(payload)).encode("utf-8")).hexdigest()
        if row["prev_hash"] != previous_hash or row["record_hash"] != expected:
            return {
                "status": "BROKEN",
                "records": len(rows),
                "first_bad_id": row["id"],
                "first_bad": trace_row(row),
                "previous_good_id": rows[rows.index(row) - 1]["id"] if rows.index(row) > 0 else None,
            }
        previous_hash = row["record_hash"]
    return {"status": "VERIFIED", "records": len(rows), "first_bad_id": None, "head_hash": previous_hash}


def trace_row(row: dict) -> dict:
    """Project one activity row to the audit trace fields requested in review."""
    return {
        "event_id": row.get("id"),
        "occurred_at": row.get("occurred_at"),
        "event_type": row.get("action"),
        "category": row.get("category"),
        "actor_type": row.get("actor_type"),
        "actor_id": row.get("actor_id"),
        "entity_type": row.get("entity_type"),
        "entity_id": row.get("entity_id"),
        "status": row.get("status"),
        "source": row.get("source"),
        "idempotency_key": row.get("idempotency_key"),
        "previous_hash": row.get("prev_hash"),
        "current_hash": row.get("record_hash"),
    }


def trace_activity_chain(store, *, from_id: int, limit: int = 10) -> dict:
    """Return a bounded trace of activity rows starting at ``from_id``.

    This is the diagnostic the reviewer requested: inspect ``event_id``,
    ``event_type``, ``created_at``/``occurred_at``, ``source``,
    ``idempotency_key``, ``previous_hash`` and ``current_hash`` around the
    first broken record so the corruption can be confirmed and, after operator
    confirmation, repaired with ``repair_activity_chain``.
    """
    ensure_activity_schema(store)
    from_id = int(from_id)
    limit = max(1, min(int(limit or 10), 200))
    with store.connect() as db:
        rows = [dict(r) for r in db.execute(
            "SELECT * FROM activity_log WHERE id >= ? ORDER BY id LIMIT ?",
            (from_id, limit),
        ).fetchall()]
    return {
        "from_id": from_id,
        "rows": [trace_row(r) for r in rows],
        "integrity": verify_activity_chain(store),
    }


def repair_activity_chain(store, *, checkpoint_id: int | None = None) -> dict:
    """Rebase the tamper-evident chain after an operator-confirmed break.

    The audit log is append-only; the chain can still be corrupted by a legacy
    concurrent append that shared a ``prev_hash``, or by an external DBA edit.
    This tool recomputes ``prev_hash``/``record_hash`` for the whole log (or from
    an optional checkpoint row id) from the current canonical payloads.

    It is an explicit, operator-invoked recovery: it never rewrites the audit
    content itself, only the integrity hashes that proved tamper-evidence.
    """
    ensure_activity_schema(store)
    with store.connect() as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM activity_log ORDER BY id").fetchall()]
    if not rows:
        return {"status": "VERIFIED", "records": 0, "first_bad_id": None}
    if checkpoint_id is not None:
        checkpoint_id = int(checkpoint_id)
        rows = [r for r in rows if r["id"] >= checkpoint_id]
        if not rows:
            raise ValueError("CHECKPOINT_NOT_FOUND: no activity rows at or after the requested id.")
        previous_hash = None
        with store.connect() as db:
            before = db.execute(
                "SELECT record_hash FROM activity_log WHERE id < ? ORDER BY id DESC LIMIT 1",
                (checkpoint_id,),
            ).fetchone()
            previous_hash = before["record_hash"] if before else None
    else:
        previous_hash = None
    with store.connect() as db:
        for row in rows:
            payload = {
                "occurred_at": row["occurred_at"],
                "actor_type": row["actor_type"],
                "actor_id": row["actor_id"],
                "category": row["category"],
                "action": row["action"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "status": row["status"],
                "summary": row["summary"],
                "details_json": row["details_json"],
                "source": row["source"],
                "prev_hash": previous_hash,
            }
            digest = hashlib.sha256(((previous_hash or "") + _canonical_payload(payload)).encode("utf-8")).hexdigest()
            db.execute(
                "UPDATE activity_log SET prev_hash=?, record_hash=? WHERE id=?",
                (previous_hash, digest, row["id"]),
            )
            previous_hash = digest
    return verify_activity_chain(store)
