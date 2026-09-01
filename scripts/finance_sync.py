#!/usr/bin/env python3
"""Validated, transactional sync of the complete qport_finance catalog.

The local worker crawls and reconciles provider data. This script copies the
validated catalog to the Vercel/Neon PostgreSQL database. It never calls a
provider and never exposes database credentials to browser code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any

import psycopg
from psycopg.rows import dict_row

SCHEMA = "qport_finance"
MAX_ROWS_PER_TABLE = 1_500_000
PROVIDERS = {"tcbs", "cafef"}
DOCUMENT_STATUSES = {"SUCCESS", "FAILED", "PENDING", "NOT_AVAILABLE"}
QUALITY_STATUSES = {"SINGLE_SOURCE", "VERIFIED", "CONFLICT", "QUARANTINED"}
TABLE_COLUMNS = {
    "crawl_runs": ("id", "requested_by", "status", "requested_at", "started_at", "finished_at", "total_symbols", "success_count", "failure_count", "error"),
    "crawl_queue": ("id", "symbol", "requested_by", "status", "requested_at", "started_at", "finished_at", "error"),
    "securities": ("symbol", "exchange", "company_name", "industry", "is_active", "updated_at"),
    "documents": ("id", "symbol", "provider", "document_type", "period_type", "fiscal_year", "fiscal_quarter", "period_end", "status", "source_url", "payload", "content_hash", "fetched_at", "error_code", "error_message", "crawl_run_id"),
    "canonical_facts": ("id", "symbol", "statement_type", "line_item_code", "value", "period_type", "fiscal_year", "fiscal_quarter", "period_end", "provider", "source_document_id", "quality_status", "observed_at"),
    "parse_errors": ("id", "source_document_id", "symbol", "provider", "document_type", "error_code", "error_message", "observed_at"),
    "dividend_observations": ("id", "symbol", "provider", "source_document_id", "provider_event_id", "dividend_type", "announcement_date", "ex_date", "record_date", "payment_date", "cash_per_share", "stock_ratio", "raw_payload", "content_hash", "parser_version", "observed_at", "status"),
    "dividend_canonical": ("canonical_id", "symbol", "dividend_type", "effective_event_date", "cash_per_share", "stock_ratio", "chosen_observation_id", "quality_status", "evidence_json", "first_seen_at", "last_seen_at"),
    "dividend_conflicts": ("id", "symbol", "conflict_key", "conflict_type", "observation_ids_json", "details_json", "status", "created_at", "updated_at"),
}
TABLE_ORDER = (
    "crawl_runs",
    "crawl_queue",
    "securities",
    "documents",
    "canonical_facts",
    "parse_errors",
    "dividend_observations",
    "dividend_canonical",
    "dividend_conflicts",
)
ID_TABLES = set(TABLE_COLUMNS) - {"securities", "dividend_canonical"}


def validate_url(name: str, value: str | None) -> str:
    value = str(value or "").strip()
    if not value.startswith(("postgresql://", "postgres://")):
        raise ValueError(f"{name} must be a PostgreSQL connection string")
    return value.replace("postgres://", "postgresql://", 1)


def schema_exists(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name=%s", (SCHEMA,))
        return cur.fetchone() is not None


def ensure_target_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
        cur.execute(f'''CREATE TABLE IF NOT EXISTS "{SCHEMA}".crawl_runs (
            id BIGSERIAL PRIMARY KEY, requested_by BIGINT, status TEXT NOT NULL,
            requested_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
            total_symbols INTEGER NOT NULL DEFAULT 0, success_count INTEGER NOT NULL DEFAULT 0,
            failure_count INTEGER NOT NULL DEFAULT 0, error TEXT)''')
        cur.execute(f'''CREATE TABLE IF NOT EXISTS "{SCHEMA}".crawl_queue (
            id BIGSERIAL PRIMARY KEY, symbol TEXT NOT NULL, requested_by BIGINT,
            status TEXT NOT NULL, requested_at TEXT NOT NULL, started_at TEXT,
            finished_at TEXT, error TEXT)''')
        cur.execute(f'''CREATE TABLE IF NOT EXISTS "{SCHEMA}".securities (
            symbol TEXT PRIMARY KEY, exchange TEXT NOT NULL DEFAULT 'UNKNOWN',
            company_name TEXT, industry TEXT, is_active INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL)''')
        cur.execute(f'''CREATE TABLE IF NOT EXISTS "{SCHEMA}".documents (
            id BIGSERIAL PRIMARY KEY, symbol TEXT NOT NULL, provider TEXT NOT NULL,
            document_type TEXT NOT NULL, period_type TEXT NOT NULL,
            fiscal_year INTEGER NOT NULL, fiscal_quarter INTEGER,
            period_end TEXT NOT NULL, status TEXT NOT NULL, source_url TEXT NOT NULL,
            payload TEXT, content_hash TEXT, fetched_at TEXT NOT NULL,
            error_code TEXT, error_message TEXT, crawl_run_id BIGINT,
            UNIQUE(symbol, provider, document_type, period_type, fiscal_year, fiscal_quarter))''')
        cur.execute(f'''CREATE TABLE IF NOT EXISTS "{SCHEMA}".canonical_facts (
            id BIGSERIAL PRIMARY KEY, symbol TEXT NOT NULL, statement_type TEXT NOT NULL,
            line_item_code TEXT NOT NULL, value NUMERIC NOT NULL, period_type TEXT NOT NULL,
            fiscal_year INTEGER NOT NULL, fiscal_quarter INTEGER, period_end TEXT NOT NULL,
            provider TEXT NOT NULL, source_document_id BIGINT, quality_status TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            UNIQUE(symbol, statement_type, line_item_code, period_type, fiscal_year, fiscal_quarter, provider))''')
        cur.execute(f'''CREATE TABLE IF NOT EXISTS "{SCHEMA}".parse_errors (
            id BIGSERIAL PRIMARY KEY, source_document_id BIGINT, symbol TEXT NOT NULL,
            provider TEXT NOT NULL, document_type TEXT NOT NULL, error_code TEXT NOT NULL,
            error_message TEXT NOT NULL, observed_at TEXT NOT NULL)''')
        cur.execute(f'''CREATE TABLE IF NOT EXISTS "{SCHEMA}".dividend_observations (
            id BIGSERIAL PRIMARY KEY, symbol TEXT NOT NULL, provider TEXT NOT NULL,
            source_document_id TEXT, provider_event_id TEXT, dividend_type TEXT NOT NULL,
            announcement_date TEXT, ex_date TEXT, record_date TEXT, payment_date TEXT,
            cash_per_share DOUBLE PRECISION, stock_ratio DOUBLE PRECISION,
            raw_payload TEXT NOT NULL, content_hash TEXT NOT NULL,
            parser_version TEXT NOT NULL, observed_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'NORMALIZED')''')
        cur.execute(f'''CREATE TABLE IF NOT EXISTS "{SCHEMA}".dividend_canonical (
            canonical_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, dividend_type TEXT NOT NULL,
            effective_event_date TEXT NOT NULL, cash_per_share DOUBLE PRECISION,
            stock_ratio DOUBLE PRECISION, chosen_observation_id BIGINT,
            quality_status TEXT NOT NULL, evidence_json TEXT NOT NULL DEFAULT '[]',
            first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL)''')
        cur.execute(f'''CREATE TABLE IF NOT EXISTS "{SCHEMA}".dividend_conflicts (
            id BIGSERIAL PRIMARY KEY, symbol TEXT NOT NULL, conflict_key TEXT NOT NULL UNIQUE,
            conflict_type TEXT NOT NULL, observation_ids_json TEXT NOT NULL,
            details_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')
    conn.commit()


def fingerprint(row: dict[str, Any], columns: tuple[str, ...]) -> str:
    raw = "\x1f".join(str(row.get(key) or "") for key in columns)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def fetch_source(conn) -> dict[str, list[dict[str, Any]]]:
    if not schema_exists(conn):
        raise RuntimeError("Source database has no qport_finance schema")
    result: dict[str, list[dict[str, Any]]] = {}
    with conn.cursor(row_factory=dict_row) as cur:
        for table in TABLE_ORDER:
            columns = ", ".join(f'"{column}"' for column in TABLE_COLUMNS[table])
            order = '"symbol"' if table == "securities" else '"id"'
            if table == "dividend_canonical":
                order = '"canonical_id"'
            cur.execute(f'SELECT {columns} FROM "{SCHEMA}"."{table}" ORDER BY {order}')
            rows = list(cur.fetchmany(MAX_ROWS_PER_TABLE + 1))
            if len(rows) > MAX_ROWS_PER_TABLE:
                raise RuntimeError(f"Source contains more than {MAX_ROWS_PER_TABLE} rows in {table}")
            result[table] = rows
    return result


def validate_rows(data: dict[str, list[dict[str, Any]]]) -> None:
    symbols = {str(row["symbol"]).upper() for row in data["securities"]}
    if not symbols:
        raise RuntimeError("Source universe is empty")
    document_ids = {int(row["id"]) for row in data["documents"]}
    observation_ids = {int(row["id"]) for row in data["dividend_observations"]}
    for row in data["documents"]:
        symbol = str(row["symbol"]).upper()
        if symbol not in symbols:
            raise RuntimeError(f"Document references unknown symbol: {symbol}")
        if row["provider"] not in PROVIDERS:
            raise RuntimeError(f"Invalid document provider: {row['provider']}")
        if row["status"] not in DOCUMENT_STATUSES:
            raise RuntimeError(f"Invalid document status: {row['status']}")
        if row["status"] == "SUCCESS" and not row["payload"]:
            raise RuntimeError(f"Successful document has empty payload: {symbol}")
        if row["content_hash"] and row["payload"]:
            expected = hashlib.sha256(str(row["payload"]).encode("utf-8")).hexdigest()
            if expected != row["content_hash"]:
                raise RuntimeError(f"Document checksum mismatch: {symbol}/{row['provider']}")
    for row in data["canonical_facts"]:
        if str(row["symbol"]).upper() not in symbols:
            raise RuntimeError(f"Canonical fact references unknown symbol: {row['symbol']}")
        if row["provider"] not in PROVIDERS:
            raise RuntimeError(f"Invalid canonical provider: {row['provider']}")
        if row["quality_status"] not in QUALITY_STATUSES:
            raise RuntimeError(f"Invalid canonical quality status: {row['quality_status']}")
        if row["source_document_id"] is not None and int(row["source_document_id"]) not in document_ids:
            raise RuntimeError(f"Canonical fact references unknown document: {row['source_document_id']}")
    for row in data["parse_errors"]:
        if row["provider"] not in PROVIDERS:
            raise RuntimeError(f"Invalid parse-error provider: {row['provider']}")
    for row in data["dividend_observations"]:
        if str(row["symbol"]).upper() not in symbols:
            raise RuntimeError(f"Dividend observation references unknown symbol: {row['symbol']}")
        if row["provider"] not in PROVIDERS:
            raise RuntimeError(f"Invalid dividend provider: {row['provider']}")
        if row["status"] not in {"NORMALIZED", "REJECTED"}:
            raise RuntimeError(f"Invalid dividend observation status: {row['status']}")
        if row["raw_payload"] is None:
            raise RuntimeError(f"Dividend observation has no raw payload: {row['id']}")
        raw = row["raw_payload"]
        try:
            parsed_raw = json.loads(raw) if isinstance(raw, str) else raw
            expected_json = hashlib.sha256(json.dumps(parsed_raw, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        except Exception:
            expected_json = None
        expected_raw = hashlib.sha256(str(raw).encode("utf-8")).hexdigest()
        if row["content_hash"] not in (expected_json, expected_raw):
            raise RuntimeError(f"Dividend observation checksum mismatch: {row['id']}")
    for row in data["dividend_canonical"]:
        if row["quality_status"] not in QUALITY_STATUSES:
            raise RuntimeError(f"Invalid dividend canonical quality: {row['quality_status']}")
        if row["chosen_observation_id"] is not None and int(row["chosen_observation_id"]) not in observation_ids:
            raise RuntimeError(f"Canonical dividend references unknown observation: {row['chosen_observation_id']}")
    for row in data["dividend_conflicts"]:
        if row["status"] not in {"OPEN", "RESOLVED"}:
            raise RuntimeError(f"Invalid dividend conflict status: {row['status']}")


def _upsert_table(cur, table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    columns = TABLE_COLUMNS[table]
    quoted = ", ".join(f'"{column}"' for column in columns)
    key = '"symbol"' if table == "securities" else '"canonical_id"' if table == "dividend_canonical" else '"id"'
    updates = ", ".join(f'"{column}"=EXCLUDED."{column}"' for column in columns if column not in {"id", "symbol", "canonical_id"})
    
    batch_size = 2000
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        val_placeholders = []
        params = []
        for row in chunk:
            val_placeholders.append("(" + ", ".join(["%s"] * len(columns)) + ")")
            params.extend(None if (table == "documents" and column == "payload") else row.get(column) for column in columns)
        
        sql = f'''INSERT INTO "{SCHEMA}"."{table}" ({quoted}) VALUES {", ".join(val_placeholders)}
                  ON CONFLICT ({key}) DO UPDATE SET {updates}'''
        cur.execute(sql, params)


def _reset_sequences(cur) -> None:
    for table in sorted(ID_TABLES):
        cur.execute(
            f'''SELECT setval(pg_get_serial_sequence(%s, 'id'),
                       COALESCE((SELECT MAX(id) FROM "{SCHEMA}"."{table}"), 1), true)''',
            (f"{SCHEMA}.{table}",),
        )


def sync(source_url: str, target_url: str, dry_run: bool) -> dict[str, Any]:
    source_url = validate_url("source-url", source_url)
    target_url = validate_url("target-url", target_url)
    if source_url == target_url:
        raise RuntimeError("Source and target DATABASE_URL must be different")
    with psycopg.connect(source_url) as source:
        data = fetch_source(source)
    validate_rows(data)
    digest = hashlib.sha256(
        "".join(fingerprint(row, TABLE_COLUMNS[table]) for table in TABLE_ORDER for row in data[table]).encode("utf-8")
    ).hexdigest()
    counts = {table: len(rows) for table, rows in data.items()}
    if dry_run:
        return {"ok": True, "dry_run": True, "counts": counts, "digest": digest}
    with psycopg.connect(target_url) as target:
        ensure_target_schema(target)
        with target.cursor() as cur:
            for table in TABLE_ORDER:
                _upsert_table(cur, table, data[table])
            _reset_sequences(cur)
        target.commit()
    return {"ok": True, "dry_run": False, "counts": counts, "digest": digest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-url", default=os.getenv("QPORT_LOCAL_DATABASE_URL"))
    parser.add_argument("--target-url", default=os.getenv("QPORT_VERCEL_DATABASE_URL"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        result = sync(args.source_url, args.target_url, args.dry_run)
        print(result)
    except Exception as exc:
        print(f"SYNC_FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
