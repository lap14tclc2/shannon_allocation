from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
                prev_hash TEXT,
                record_hash TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_activity_log_occurred_at ON activity_log(occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_activity_log_category ON activity_log(category, occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_activity_log_action ON activity_log(action, occurred_at DESC);
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
) -> int:
    """Append one tamper-evident activity record.

    The table has no update/delete API. Each row hashes the previous row hash plus
    its own canonical payload so accidental/manual mutations can be detected by
    ``verify_activity_chain``.
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
    details_json = json.dumps(details or {}, ensure_ascii=False, sort_keys=True, default=str)
    with store.connect() as db:
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
                status,summary,details_json,source,prev_hash,record_hash
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                occurred_at, actor_type, actor_id, category, action, entity_type,
                None if entity_id is None else str(entity_id), status, summary,
                details_json, source, prev_hash, digest,
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
            return {"status": "BROKEN", "records": len(rows), "first_bad_id": row["id"]}
        previous_hash = row["record_hash"]
    return {"status": "VERIFIED", "records": len(rows), "first_bad_id": None, "head_hash": previous_hash}
