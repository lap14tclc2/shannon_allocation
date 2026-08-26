#!/usr/bin/env python3
"""Validated, transactional sync of finance data from local PostgreSQL to Vercel PostgreSQL."""
from __future__ import annotations

import argparse
import hashlib
import os
import sys

import psycopg
from psycopg.rows import dict_row

SCHEMA = "qport_finance"
MAX_ROWS = 250_000


def validate_url(name: str, value: str) -> str:
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


def fingerprint(row: dict) -> str:
    fields = ("symbol", "provider", "document_type", "period_type", "fiscal_year",
              "fiscal_quarter", "period_end", "status", "source_url", "payload",
              "content_hash", "fetched_at", "error_code", "error_message")
    raw = "\x1f".join(str(row.get(key) or "") for key in fields)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def fetch_source(conn):
    if not schema_exists(conn):
        raise RuntimeError("Source database has no qport_finance schema")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f'SELECT symbol, exchange, company_name, industry, is_active, updated_at FROM "{SCHEMA}".securities ORDER BY symbol')
        securities = list(cur.fetchall())
        cur.execute(f'''SELECT symbol, provider, document_type, period_type, fiscal_year,
            fiscal_quarter, period_end, status, source_url, payload, content_hash,
            fetched_at, error_code, error_message, crawl_run_id
            FROM "{SCHEMA}".documents ORDER BY symbol, provider, document_type, fiscal_year, fiscal_quarter''')
        documents = list(cur.fetchmany(MAX_ROWS + 1))
    if len(documents) > MAX_ROWS:
        raise RuntimeError(f"Source contains more than {MAX_ROWS} documents; split the sync")
    return securities, documents


def validate_rows(securities, documents) -> None:
    symbols = {str(row["symbol"]).upper() for row in securities}
    if not symbols:
        raise RuntimeError("Source universe is empty")
    for row in documents:
        symbol = str(row["symbol"]).upper()
        if symbol not in symbols:
            raise RuntimeError(f"Document references unknown symbol: {symbol}")
        if row["provider"] not in {"tcbs", "cafef"}:
            raise RuntimeError(f"Invalid provider: {row['provider']}")
        if row["status"] not in {"SUCCESS", "FAILED", "PENDING"}:
            raise RuntimeError(f"Invalid status: {row['status']}")
        if row["status"] == "SUCCESS" and not row["payload"]:
            raise RuntimeError(f"Successful document has empty payload: {symbol}")
        if row["content_hash"] and row["payload"]:
            expected = hashlib.sha256(str(row["payload"]).encode("utf-8")).hexdigest()
            if expected != row["content_hash"]:
                raise RuntimeError(f"Checksum mismatch: {symbol}/{row['provider']}")


def sync(source_url: str, target_url: str, dry_run: bool) -> dict:
    if source_url == target_url:
        raise RuntimeError("Source and target DATABASE_URL must be different")
    with psycopg.connect(source_url) as source:
        securities, documents = fetch_source(source)
    validate_rows(securities, documents)
    digest = hashlib.sha256("".join(fingerprint(row) for row in documents).encode()).hexdigest()
    if dry_run:
        return {"ok": True, "dry_run": True, "securities": len(securities), "documents": len(documents), "digest": digest}
    with psycopg.connect(target_url) as target:
        ensure_target_schema(target)
        with target.cursor() as cur:
            for row in securities:
                cur.execute(f'''INSERT INTO "{SCHEMA}".securities
                    (symbol, exchange, company_name, industry, is_active, updated_at)
                    VALUES(%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(symbol) DO UPDATE SET exchange=EXCLUDED.exchange,
                    company_name=COALESCE(EXCLUDED.company_name, "{SCHEMA}".securities.company_name),
                    industry=COALESCE(EXCLUDED.industry, "{SCHEMA}".securities.industry),
                    is_active=EXCLUDED.is_active, updated_at=EXCLUDED.updated_at''',
                    tuple(row[key] for key in ("symbol", "exchange", "company_name", "industry", "is_active", "updated_at")))
            for row in documents:
                cur.execute(f'''INSERT INTO "{SCHEMA}".documents
                    (symbol, provider, document_type, period_type, fiscal_year,
                     fiscal_quarter, period_end, status, source_url, payload,
                     content_hash, fetched_at, error_code, error_message, crawl_run_id)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(symbol, provider, document_type, period_type,
                                fiscal_year, fiscal_quarter)
                    DO UPDATE SET status=EXCLUDED.status, source_url=EXCLUDED.source_url,
                    payload=EXCLUDED.payload, content_hash=EXCLUDED.content_hash,
                    fetched_at=EXCLUDED.fetched_at, error_code=EXCLUDED.error_code,
                    error_message=EXCLUDED.error_message, crawl_run_id=EXCLUDED.crawl_run_id
                    WHERE EXCLUDED.fetched_at >= "{SCHEMA}".documents.fetched_at''',
                    tuple(row[key] for key in ("symbol", "provider", "document_type", "period_type",
                    "fiscal_year", "fiscal_quarter", "period_end", "status", "source_url",
                    "payload", "content_hash", "fetched_at", "error_code", "error_message", "crawl_run_id")))
        target.commit()
    return {"ok": True, "dry_run": False, "securities": len(securities), "documents": len(documents), "digest": digest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-url", default=os.getenv("QPORT_LOCAL_DATABASE_URL"))
    parser.add_argument("--target-url", default=os.getenv("QPORT_VERCEL_DATABASE_URL"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        print(sync(validate_url("source-url", args.source_url), validate_url("target-url", args.target_url), args.dry_run))
    except Exception as exc:
        print(f"SYNC_FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
