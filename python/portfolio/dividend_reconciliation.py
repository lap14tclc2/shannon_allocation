"""Normalize -> reconcile -> conflict pipeline for provider dividend observations.

This module is deliberately separate from the user-facing cache. A crawler can
persist raw provider observations, reconcile them into canonical events, and
leave disagreements open for an admin to resolve without mutating history.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any

from .postgres import _ensure_schema, _schema_connection

SCHEMA = "qport_finance"
SUPPORTED_TYPES = {"CASH_DIVIDEND", "STOCK_DIVIDEND"}
PROVIDER_PRIORITY = {"tcbs": 0, "cafef": 1, "vps": 2, "vps_events": 2}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)[:10]


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def _payload_hash(value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def ensure_reconciliation_schema() -> None:
    _ensure_schema(SCHEMA)
    with _schema_connection(SCHEMA) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS dividend_observations (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            provider TEXT NOT NULL,
            source_document_id TEXT,
            provider_event_id TEXT,
            dividend_type TEXT NOT NULL CHECK(dividend_type IN ('CASH_DIVIDEND','STOCK_DIVIDEND')),
            announcement_date TEXT,
            ex_date TEXT,
            record_date TEXT,
            payment_date TEXT,
            cash_per_share DOUBLE PRECISION,
            stock_ratio DOUBLE PRECISION,
            raw_payload TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            parser_version TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'NORMALIZED' CHECK(status IN ('NORMALIZED','REJECTED')),
            UNIQUE(symbol, provider, source_document_id, provider_event_id, dividend_type, content_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_dividend_observations_symbol
            ON dividend_observations(symbol, dividend_type, ex_date, record_date);

        CREATE TABLE IF NOT EXISTS dividend_canonical (
            canonical_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            dividend_type TEXT NOT NULL,
            effective_event_date TEXT NOT NULL,
            cash_per_share DOUBLE PRECISION,
            stock_ratio DOUBLE PRECISION,
            chosen_observation_id BIGINT,
            quality_status TEXT NOT NULL CHECK(quality_status IN ('VERIFIED','SINGLE_SOURCE','CONFLICT')),
            evidence_json TEXT NOT NULL DEFAULT '[]',
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_dividend_canonical_event
            ON dividend_canonical(symbol, dividend_type, effective_event_date);

        CREATE TABLE IF NOT EXISTS dividend_conflicts (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            conflict_key TEXT NOT NULL UNIQUE,
            conflict_type TEXT NOT NULL,
            observation_ids_json TEXT NOT NULL,
            details_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN','RESOLVED')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_dividend_conflicts_open
            ON dividend_conflicts(symbol, status, updated_at DESC);
        """)


def normalize_observation(
    event: dict[str, Any],
    *,
    provider: str,
    source_document_id: str | None = None,
    parser_version: str = "dividend-normalizer-v1",
) -> dict[str, Any]:
    """Convert one provider event to a stable, auditable observation."""
    symbol = str(event.get("symbol") or "").strip().upper()
    dividend_type = str(event.get("dividend_type") or "").strip().upper()
    if not symbol or not dividend_type:
        raise ValueError("symbol and dividend_type are required")
    if dividend_type not in SUPPORTED_TYPES:
        raise ValueError(f"unsupported dividend_type: {dividend_type}")
    payload = event.get("raw_payload", event)
    return {
        "symbol": symbol,
        "provider": str(provider or "unknown").strip().lower(),
        "source_document_id": source_document_id,
        "provider_event_id": event.get("source_event_id") or event.get("provider_event_id"),
        "dividend_type": dividend_type,
        "announcement_date": _date(event.get("announcement_date")),
        "ex_date": _date(event.get("ex_date")),
        "record_date": _date(event.get("record_date")),
        "payment_date": _date(event.get("payment_date")),
        "cash_per_share": _number(event.get("cash_per_share")),
        "stock_ratio": _number(event.get("stock_ratio")),
        "raw_payload": payload,
        "content_hash": _payload_hash(payload),
        "parser_version": parser_version,
        "observed_at": _now(),
        "status": "NORMALIZED",
    }


def persist_observations(observations: list[dict[str, Any]]) -> list[int]:
    ensure_reconciliation_schema()
    ids: list[int] = []
    with _schema_connection(SCHEMA) as db:
        for item in observations:
            normalized = item if "content_hash" in item else normalize_observation(item, provider=item.get("provider", "unknown"))
            row = db.execute("""
                INSERT INTO dividend_observations(
                    symbol,provider,source_document_id,provider_event_id,dividend_type,
                    announcement_date,ex_date,record_date,payment_date,cash_per_share,
                    stock_ratio,raw_payload,content_hash,parser_version,observed_at,status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(symbol,provider,source_document_id,provider_event_id,dividend_type,content_hash)
                DO UPDATE SET observed_at=EXCLUDED.observed_at
                RETURNING id
            """, (
                normalized["symbol"], normalized["provider"], normalized.get("source_document_id"),
                normalized.get("provider_event_id"), normalized["dividend_type"],
                normalized.get("announcement_date"), normalized.get("ex_date"),
                normalized.get("record_date"), normalized.get("payment_date"),
                normalized.get("cash_per_share"), normalized.get("stock_ratio"),
                json.dumps(normalized.get("raw_payload"), ensure_ascii=False, default=str),
                normalized["content_hash"], normalized["parser_version"],
                normalized["observed_at"], normalized.get("status", "NORMALIZED"),
            )).fetchone()
            if row:
                ids.append(int(row["id"]))
    return ids


def _effective(row: dict[str, Any]) -> str:
    return str(row.get("ex_date") or row.get("record_date") or row.get("payment_date") or row.get("announcement_date") or "9999-12-31")


def _close(a: str, b: str) -> bool:
    try:
        return abs((date.fromisoformat(a[:10]) - date.fromisoformat(b[:10])).days) <= 2
    except (TypeError, ValueError):
        return a == b


def _same_economics(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if a["dividend_type"] != b["dividend_type"]:
        return False
    if a["dividend_type"] == "CASH_DIVIDEND":
        av, bv = a.get("cash_per_share"), b.get("cash_per_share")
        return av is None or bv is None or abs(float(av) - float(bv)) <= max(1.0, abs(float(av)) * 0.001)
    av, bv = a.get("stock_ratio"), b.get("stock_ratio")
    return av is None or bv is None or abs(float(av) - float(bv)) <= 1e-6


def _canonical_id(symbol: str, kind: str, effective: str) -> str:
    return hashlib.sha256(f"{symbol}|{kind}|{effective}".encode()).hexdigest()[:32]


def reconcile_symbol(symbol: str) -> dict[str, Any]:
    ensure_reconciliation_schema()
    symbol = str(symbol).upper().strip()
    with _schema_connection(SCHEMA) as db:
        rows = [dict(row) for row in db.execute(
            "SELECT * FROM dividend_observations WHERE symbol=? AND status='NORMALIZED' ORDER BY id",
            (symbol,),
        ).fetchall()]
        groups: list[list[dict[str, Any]]] = []
        for row in rows:
            target = next((group for group in groups if _close(_effective(group[0]), _effective(row))), None)
            if target is None:
                groups.append([row])
            else:
                target.append(row)
        canonical_count = 0
        conflict_count = 0
        now = _now()
        for group in groups:
            kind = group[0]["dividend_type"]
            effective = min(_effective(item) for item in group)
            sources = sorted({str(item["provider"]) for item in group})
            # A date family with materially different economics is an explicit conflict.
            family = [item for item in rows if item["dividend_type"] == kind and _close(_effective(item), effective)]
            family_values = {round(float(item["cash_per_share"]), 6) for item in family if item.get("cash_per_share") is not None} if kind == "CASH_DIVIDEND" else {round(float(item["stock_ratio"]), 8) for item in family if item.get("stock_ratio") is not None}
            conflict = len(family_values) > 1
            chosen = sorted(group, key=lambda item: PROVIDER_PRIORITY.get(item["provider"], 99))[0]
            quality = "CONFLICT" if conflict else ("VERIFIED" if len(sources) > 1 else "SINGLE_SOURCE")
            cid = _canonical_id(symbol, kind, effective)
            evidence = [{"id": item["id"], "provider": item["provider"], "source_document_id": item["source_document_id"], "value": item.get("cash_per_share") if kind == "CASH_DIVIDEND" else item.get("stock_ratio")} for item in group]
            db.execute("""
                INSERT INTO dividend_canonical(canonical_id,symbol,dividend_type,effective_event_date,cash_per_share,stock_ratio,chosen_observation_id,quality_status,evidence_json,first_seen_at,last_seen_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(canonical_id) DO UPDATE SET
                    cash_per_share=excluded.cash_per_share, stock_ratio=excluded.stock_ratio,
                    chosen_observation_id=excluded.chosen_observation_id, quality_status=excluded.quality_status,
                    evidence_json=excluded.evidence_json, last_seen_at=excluded.last_seen_at
            """, (cid, symbol, kind, effective, chosen.get("cash_per_share"), chosen.get("stock_ratio"), chosen["id"], quality, json.dumps(evidence), now, now))
            canonical_count += 1
            if conflict:
                key = f"{symbol}|{kind}|{effective}"
                db.execute("""
                    INSERT INTO dividend_conflicts(symbol, conflict_key, conflict_type, observation_ids_json, details_json, status, created_at, updated_at)
                    VALUES(?,?,?,?,?,'OPEN',?,?)
                    ON CONFLICT(conflict_key) DO UPDATE SET observation_ids_json=excluded.observation_ids_json, details_json=excluded.details_json, status='OPEN', updated_at=excluded.updated_at
                """, (symbol, key, "ECONOMIC_VALUE_MISMATCH", json.dumps([item["id"] for item in family]), json.dumps({"values": sorted(family_values), "providers": sorted({item["provider"] for item in family})}), now, now))
                conflict_count += 1
        return {"symbol": symbol, "canonical_count": canonical_count, "open_conflicts": conflict_count}


def reconcile_all(symbols: list[str]) -> list[dict[str, Any]]:
    return [reconcile_symbol(symbol) for symbol in symbols]
