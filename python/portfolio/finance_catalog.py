"""Shared PostgreSQL finance-data catalog for admin-controlled ingestion.

The catalog is deliberately separate from user portfolio schemas. User routes only
read canonical rows from this catalog; provider calls are never made from them.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from html import unescape
from html.parser import HTMLParser
import time
import threading
from datetime import date, datetime, timezone
from typing import Any

from .postgres import AUTH_SCHEMA, _ensure_schema, _schema_connection

FINANCE_SCHEMA = "qport_finance"
REQUIRED_DOCUMENTS = (
    "FINANCIAL_STATEMENTS",
    "CASH_FLOW",
    "INCOME_STATEMENT",
    "DIVIDEND",
)
# Supported providers remain explicit for reconciliation/backfill.
PROVIDERS = ("tcbs", "cafef")
# Temporary worker scope: only CafeF is requested by normal worker runs.
WORKER_PROVIDERS = ("cafef",)
# Completed annual reports to retain/crawl for each listed equity.
FISCAL_YEAR_HISTORY = 10
# The external worker intentionally starts with the two main listed markets.
# UPCOM jobs stay queued until a later, explicit worker scope is enabled.
WORKER_CRAWL_EXCHANGES = ("HOSE", "HNX")

# Facts required by the deterministic FY valuation bridge.  These inputs are
# deliberately explicit: the value engine must never manufacture a number when
# a provider has not supplied it.
VALUE_ENGINE_REQUIRED_FACTS: tuple[tuple[str, str], ...] = (
    ("IS.PROFIT.NET", "net_income"),
    ("IS.PROFIT.OPERATING", "operating_profit"),
    ("CF.OPERATING.NET", "operating_cash_flow"),
    ("CF.OPERATING.DEPRECIATION", "depreciation_amortization"),
    ("CF.CAPEX", "capex"),
    ("BS.ASSETS.CASH_AND_EQUIVALENTS", "cash"),
    ("BS.DEBT.TOTAL", "total_debt"),
    ("IS.SHARES.OUTSTANDING", "shares_outstanding"),
)

# Defensive read-time predicate for legacy rows imported before filtering.
ACTIVE_EQUITY_SQL = (
    "is_active=1 "
    "AND exchange IN ('HOSE','HNX','UPCOM') "
    "AND company_name IS NOT NULL "
    "AND lower(trim(company_name)) NOT IN ('', 'nan', 'unknown', 'none', '-')"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _url_json(url: str, *, headers: dict[str, str] | None = None, timeout: float = 15, retries: int = 2) -> tuple[int, str]:
    """Fetch uncached provider data with bounded retry/backoff."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "QPort-FinanceData/1.0",
            "Accept": "application/json, text/plain, */*",
            "Cache-Control": "no-cache",
            **(headers or {}),
        },
    )
    last_error = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = int(response.status)
                body = response.read().decode("utf-8", errors="replace")
                if not body.strip():
                    raise RuntimeError("Provider returned an empty response")
                return status, body
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429} and exc.code < 500:
                raise
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            last_error = exc
        if attempt < retries:
            time.sleep(0.5 * (2 ** attempt))
    raise RuntimeError(f"provider request failed after {retries + 1} attempts: {last_error}")


def initialize_finance_schema() -> None:
    _ensure_schema(FINANCE_SCHEMA)
    with _schema_connection(FINANCE_SCHEMA) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS securities (
            symbol TEXT PRIMARY KEY,
            exchange TEXT NOT NULL DEFAULT 'UNKNOWN',
            company_name TEXT,
            industry TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_finance_securities_exchange
            ON securities(exchange, symbol);

        CREATE TABLE IF NOT EXISTS crawl_runs (
            id BIGSERIAL PRIMARY KEY,
            requested_by INTEGER,
            status TEXT NOT NULL,
            requested_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            total_symbols INTEGER NOT NULL DEFAULT 0,
            success_count INTEGER NOT NULL DEFAULT 0,
            failure_count INTEGER NOT NULL DEFAULT 0,
            error TEXT
        );

        CREATE TABLE IF NOT EXISTS crawl_queue (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            requested_by INTEGER,
            status TEXT NOT NULL CHECK(status IN ('QUEUED','RUNNING','COMPLETED','FAILED')),
            requested_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            error TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_finance_queue_active
            ON crawl_queue(symbol) WHERE status IN ('QUEUED','RUNNING');

        CREATE TABLE IF NOT EXISTS documents (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            provider TEXT NOT NULL CHECK(provider IN ('tcbs','cafef')),
            document_type TEXT NOT NULL,
            period_type TEXT NOT NULL CHECK(period_type IN ('FY','QUARTER')),
            fiscal_year INTEGER NOT NULL,
            fiscal_quarter INTEGER,
            period_end TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('SUCCESS','FAILED','PENDING')),
            source_url TEXT NOT NULL,
            payload TEXT,
            content_hash TEXT,
            fetched_at TEXT NOT NULL,
            error_code TEXT,
            error_message TEXT,
            crawl_run_id BIGINT,
            UNIQUE(symbol, provider, document_type, period_type, fiscal_year, fiscal_quarter)
        );
        CREATE INDEX IF NOT EXISTS idx_finance_documents_symbol
            ON documents(symbol, fiscal_year DESC, fiscal_quarter DESC);
        CREATE INDEX IF NOT EXISTS idx_finance_documents_status
            ON documents(status, provider);
        CREATE TABLE IF NOT EXISTS canonical_facts (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            statement_type TEXT NOT NULL,
            line_item_code TEXT NOT NULL,
            value NUMERIC NOT NULL,
            period_type TEXT NOT NULL,
            fiscal_year INTEGER NOT NULL,
            fiscal_quarter INTEGER,
            period_end TEXT NOT NULL,
            provider TEXT NOT NULL,
            source_document_id BIGINT,
            quality_status TEXT NOT NULL DEFAULT 'SINGLE_SOURCE',
            observed_at TEXT NOT NULL,
            UNIQUE(symbol, statement_type, line_item_code, period_type, fiscal_year, fiscal_quarter, provider)
        );
        CREATE INDEX IF NOT EXISTS idx_finance_canonical_symbol
            ON canonical_facts(symbol, line_item_code, fiscal_year DESC, fiscal_quarter DESC);
        CREATE TABLE IF NOT EXISTS parse_errors (
            id BIGSERIAL PRIMARY KEY,
            source_document_id BIGINT,
            symbol TEXT NOT NULL,
            provider TEXT NOT NULL,
            document_type TEXT NOT NULL,
            error_code TEXT NOT NULL,
            error_message TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            UNIQUE(source_document_id)
        );
        """)
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS finance_schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )
        migration = db.execute(
            "SELECT 1 FROM finance_schema_migrations WHERE name=?",
            ("documents_deduplicate_v1",),
        ).fetchone()
        if migration is None:
            print(
                "[finance-schema] duplicate-document migration started",
                flush=True,
            )
            db.execute(
                """
                CREATE TEMP TABLE finance_document_dedup_map
                ON COMMIT DROP AS
                SELECT id AS duplicate_id, keep_id
                FROM (
                    SELECT
                        id,
                        FIRST_VALUE(id) OVER (
                            PARTITION BY symbol, provider, document_type,
                                         period_type, fiscal_year,
                                         COALESCE(fiscal_quarter, 0)
                            ORDER BY
                                CASE status
                                    WHEN 'SUCCESS' THEN 0
                                    WHEN 'FAILED' THEN 1
                                    ELSE 2
                                END,
                                fetched_at DESC,
                                id DESC
                        ) AS keep_id,
                        ROW_NUMBER() OVER (
                            PARTITION BY symbol, provider, document_type,
                                         period_type, fiscal_year,
                                         COALESCE(fiscal_quarter, 0)
                            ORDER BY
                                CASE status
                                    WHEN 'SUCCESS' THEN 0
                                    WHEN 'FAILED' THEN 1
                                    ELSE 2
                                END,
                                fetched_at DESC,
                                id DESC
                        ) AS duplicate_rank
                    FROM documents
                ) AS ranked
                WHERE duplicate_rank > 1
                """
            )
            duplicate_count = db.execute(
                "SELECT COUNT(*) AS count FROM finance_document_dedup_map"
            ).fetchone()["count"]
            print(
                f"[finance-schema] duplicate-document migration found "
                f"{duplicate_count} duplicate rows",
                flush=True,
            )
            if int(duplicate_count or 0):
                db.execute(
                    """
                    UPDATE canonical_facts AS canonical
                    SET source_document_id=dedup.keep_id
                    FROM finance_document_dedup_map AS dedup
                    WHERE canonical.source_document_id=dedup.duplicate_id
                    """
                )
                db.execute(
                    """
                    DELETE FROM parse_errors AS duplicate_error
                    USING finance_document_dedup_map AS dedup
                    WHERE duplicate_error.source_document_id=dedup.duplicate_id
                      AND EXISTS (
                          SELECT 1
                          FROM parse_errors AS keeper_error
                          WHERE keeper_error.source_document_id=dedup.keep_id
                      )
                    """
                )
                db.execute(
                    """
                    UPDATE parse_errors AS parse_error
                    SET source_document_id=dedup.keep_id
                    FROM finance_document_dedup_map AS dedup
                    WHERE parse_error.source_document_id=dedup.duplicate_id
                    """
                )
                db.execute(
                    """
                    DELETE FROM documents AS duplicate_document
                    USING finance_document_dedup_map AS dedup
                    WHERE duplicate_document.id=dedup.duplicate_id
                    """
                )
            print(
                "[finance-schema] duplicate-document rows removed; "
                "creating logical-period unique index",
                flush=True,
            )
            db.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    uq_finance_documents_logical_period
                ON documents(
                    symbol, provider, document_type, period_type,
                    fiscal_year, (COALESCE(fiscal_quarter, 0))
                )
                """
            )
            db.execute(
                """
                INSERT INTO finance_schema_migrations(name, applied_at)
                VALUES(?,?)
                ON CONFLICT DO NOTHING
                """,
                ("documents_deduplicate_v1", _now()),
            )


def _ensure() -> None:
    initialize_finance_schema()


def upsert_security(symbol: str, exchange: str = "UNKNOWN", company_name: str | None = None, industry: str | None = None) -> None:
    _ensure()
    symbol = str(symbol).upper().strip()
    if not symbol:
        return
    with _schema_connection(FINANCE_SCHEMA) as db:
        db.execute(
            """INSERT INTO securities(symbol, exchange, company_name, industry, updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(symbol) DO UPDATE SET
               exchange=CASE WHEN excluded.exchange <> 'UNKNOWN' THEN excluded.exchange ELSE securities.exchange END,
               company_name=COALESCE(excluded.company_name,securities.company_name),
               industry=CASE WHEN excluded.industry IS NOT NULL AND excluded.industry <> 'UNKNOWN'
                             THEN excluded.industry ELSE securities.industry END,
               is_active=1,
               updated_at=excluded.updated_at""",
            (symbol, str(exchange or "UNKNOWN").upper(), company_name, industry, _now()),
        )


def list_securities(
    offset: int = 0,
    limit: int = 50,
    exchange: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> dict[str, Any]:
    """List active equities with SQL-derived crawl status before pagination."""
    _ensure()
    offset = max(0, int(offset))
    limit = min(200, max(1, int(limit)))
    exchange_value = str(exchange or "").upper().strip()
    status_value = str(status or "").upper().strip()
    search_value = str(q or "").strip()

    document_summary = """
        LEFT JOIN (
            SELECT
                symbol,
                COUNT(*) AS document_total,
                SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END) AS document_success,
                SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) AS document_failed,
                SUM(CASE WHEN status='PENDING' THEN 1 ELSE 0 END) AS document_pending
            FROM documents
            GROUP BY symbol
        ) AS d ON d.symbol = s.symbol
    """
    status_expression = """
        CASE
            WHEN COALESCE(d.document_total, 0) = 0 THEN 'NOT_CRAWLED'
            WHEN COALESCE(d.document_success, 0) > 0
                 AND COALESCE(d.document_failed, 0) = 0
                 AND COALESCE(d.document_pending, 0) = 0 THEN 'SUCCESS'
            WHEN COALESCE(d.document_success, 0) > 0
                 AND (COALESCE(d.document_failed, 0) > 0
                      OR COALESCE(d.document_pending, 0) > 0) THEN 'PARTIAL'
            WHEN COALESCE(d.document_failed, 0) > 0 THEN 'FAILED'
            ELSE 'PENDING'
        END
    """
    base_query = f"""
        SELECT
            s.symbol,
            s.exchange,
            s.company_name,
            s.industry,
            s.updated_at,
            COALESCE(d.document_total, 0) AS document_total,
            COALESCE(d.document_success, 0) AS document_success,
            COALESCE(d.document_failed, 0) AS document_failed,
            COALESCE(d.document_pending, 0) AS document_pending,
            {status_expression} AS crawl_status
        FROM securities AS s
        {document_summary}
        WHERE {ACTIVE_EQUITY_SQL}
    """
    params: list[Any] = []
    if exchange_value in {"HOSE", "HNX", "UPCOM"}:
        base_query += " AND s.exchange=?"
        params.append(exchange_value)
    if search_value:
        # Parameterized substring search for the public symbol or company name.
        # It composes with the existing exchange/status filters before paging.
        base_query += " AND (UPPER(s.symbol) LIKE ? OR UPPER(COALESCE(s.company_name, '')) LIKE ?)"
        needle = f"%{search_value.upper()}%"
        params.extend((needle, needle))

    status_conditions = {
        "SUCCESS": (
            "COALESCE(d.document_success, 0) > 0 "
            "AND COALESCE(d.document_failed, 0) = 0 "
            "AND COALESCE(d.document_pending, 0) = 0"
        ),
        "PARTIAL": (
            "COALESCE(d.document_success, 0) > 0 "
            "AND (COALESCE(d.document_failed, 0) > 0 "
            "OR COALESCE(d.document_pending, 0) > 0)"
        ),
        "FAILED": (
            "COALESCE(d.document_failed, 0) > 0 "
            "AND COALESCE(d.document_success, 0) = 0"
        ),
        "PENDING": (
            "COALESCE(d.document_total, 0) > 0 "
            "AND COALESCE(d.document_success, 0) = 0 "
            "AND COALESCE(d.document_failed, 0) = 0"
        ),
        "NOT_CRAWLED": "COALESCE(d.document_total, 0) = 0",
    }
    if status_value in status_conditions:
        base_query += f" AND {status_conditions[status_value]}"

    with _schema_connection(FINANCE_SCHEMA) as db:
        total = db.execute(
            f"SELECT COUNT(*) AS count FROM ({base_query}) AS filtered_securities",
            tuple(params),
        ).fetchone()["count"]
        rows = db.execute(
            f"{base_query} ORDER BY s.symbol LIMIT ? OFFSET ?",
            tuple(params) + (limit, offset),
        ).fetchall()

        symbols = [row["symbol"] for row in rows]
        documents = {}
        if symbols:
            placeholders = ",".join("?" for _ in symbols)
            docs = db.execute(
                f"SELECT symbol, provider, document_type, period_type, fiscal_year, fiscal_quarter, period_end, status, source_url, fetched_at, error_code, error_message FROM documents WHERE symbol IN ({placeholders}) ORDER BY symbol, provider, document_type, fiscal_year DESC, fiscal_quarter DESC",
                tuple(symbols),
            ).fetchall()
            for doc in docs:
                documents.setdefault(doc["symbol"], []).append(dict(doc))

    return {
        "items": [{**dict(row), "documents": documents.get(row["symbol"], [])} for row in rows],
        "total": int(total),
        "offset": offset,
        "limit": limit,
    }

def get_symbol_documents(symbol: str) -> dict[str, Any]:
    _ensure()
    symbol = str(symbol).upper().strip()
    with _schema_connection(FINANCE_SCHEMA) as db:
        rows = db.execute(
            "SELECT symbol, provider, document_type, period_type, fiscal_year, fiscal_quarter, period_end, status, source_url, payload, fetched_at, error_code, error_message FROM documents WHERE symbol=? ORDER BY fiscal_year DESC, fiscal_quarter DESC, provider, document_type",
            (symbol,),
        ).fetchall()
    return {"symbol": symbol, "documents": [dict(row) for row in rows]}


def _periods() -> list[tuple[str, int, int | None, str]]:
    """Return ten completed FYs plus completed quarters in the current year."""
    today = date.today()
    periods = [
        ("FY", year, None, f"{year}-12-31")
        for year in range(today.year - FISCAL_YEAR_HISTORY, today.year)
    ]
    quarter = ((today.month - 1) // 3)
    for q in range(1, quarter + 1):
        end_month = q * 3
        # Include only completed quarters.
        periods.append(("QUARTER", today.year, q, f"{today.year}-{end_month:02d}-{31 if end_month in (3, 12) else 30:02d}"))
    return periods



def ensure_required_documents(symbol: str) -> None:
    """Create auditable PENDING placeholders for every required period/provider."""
    symbol = str(symbol).upper().strip()
    if not symbol:
        return
    _ensure()
    periods = _periods()
    with _schema_connection(FINANCE_SCHEMA) as db:
        for period_type, year, quarter, period_end in periods:
            for document_type in REQUIRED_DOCUMENTS:
                if document_type == "DIVIDEND" and period_type != "FY":
                    continue
                for provider in WORKER_PROVIDERS:
                    if document_type == "DIVIDEND":
                        url = f"https://cafef.vn/du-lieu.ashx?symbol={symbol}"
                    else:
                        segment = "IncSta" if document_type == "INCOME_STATEMENT" else ("BSheet" if document_type == "FINANCIAL_STATEMENTS" else "CashFlow")
                        url = f"https://cafef.vn/du-lieu/bao-cao-tai-chinh/{symbol}/{segment}/{year}/{quarter or 4}/0/0/1/bao-cao-tai-chinh-{symbol.lower()}.chn"
                    db.execute(
                        """INSERT INTO documents(
                           symbol, provider, document_type, period_type, fiscal_year,
                           fiscal_quarter, period_end, status, source_url, fetched_at
                        ) VALUES(?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT (symbol, provider, document_type, period_type, fiscal_year, (COALESCE(fiscal_quarter, 0)))
                        DO NOTHING""",
                        (symbol, provider, document_type, period_type, year, quarter,
                         period_end, "PENDING", url, _now()),
                    )


class _CafeFTableParser(HTMLParser):
    """Extract simple label/value rows from CafeF financial HTML tables."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            value = unescape(" ".join("".join(self._cell).split()))
            self._row.append(value)
            self._cell = None
        elif tag == "tr" and self._row:
            self.rows.append(self._row)
            self._row = None


def _cafef_html_rows(payload: str) -> list[dict[str, Any]]:
    parser = _CafeFTableParser()
    parser.feed(payload)
    result: list[dict[str, Any]] = []
    for cells in parser.rows:
        if len(cells) < 2:
            continue
        numeric_values = [cell for cell in cells[1:] if _number(cell) is not None]
        if not numeric_values:
            continue
        # CafeF returns several periods in one row. The final numeric cell is
        # the period selected by the URL and is the safest value to canonicalize.
        row: dict[str, Any] = {"label": cells[0], "value": numeric_values[-1]}
        row["period_values"] = cells[1:]
        result.append(row)
    return result


def _payload_rows(payload: str | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return _cafef_html_rows(payload)
    if isinstance(value, list):
        return [dict(row) for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        for key in ("data", "content", "rows", "items", "result"):
            child = value.get(key)
            if isinstance(child, list):
                return [dict(row) for row in child if isinstance(row, dict)]
            if isinstance(child, dict):
                nested = _payload_rows(json.dumps(child))
                if nested:
                    return nested
        return [value]
    return []


def _number(value: Any) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        text = str(value).strip().replace("\u00a0", "").replace(" ", "")
        if "," in text and "." in text:
            # Treat the right-most separator as the decimal marker.
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            tail = text.rsplit(",", 1)[1]
            text = text.replace(",", "") if len(tail) == 3 else text.replace(",", ".")
        elif "." in text and text.count(".") == 1:
            head, tail = text.split(".", 1)
            # Vietnamese financial exports commonly use 1.234 for thousands.
            if len(tail) == 3 and len(head) <= 3:
                text = head + tail
        elif text.count(".") > 1:
            text = text.replace(".", "")
        return float(text)
    except (TypeError, ValueError):
        return None

def _token(value: Any) -> str:
    import unicodedata
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return "".join(char.lower() for char in text if char.isalnum())


def _value(row: dict[str, Any], *aliases: str) -> float | None:
    """Read provider rows in both column-oriented and label/value shapes."""
    if not isinstance(row, dict):
        return None
    normalized = {_token(key): value for key, value in row.items()}
    wanted = [_token(alias) for alias in aliases]
    # Direct field aliases (e.g. net_profit, outstanding_shares).
    for alias in wanted:
        for candidate, value in normalized.items():
            if candidate == alias or candidate.endswith(alias):
                parsed = _number(value)
                if parsed is not None:
                    return parsed
    # TCBS/CafeF often return {itemName/itemCode/label, value/amount}.
    label = " ".join(
        str(normalized.get(key, ""))
        for key in ("itemname", "itemcode", "label", "name", "title", "description", "namevn")
    )
    label_token = _token(label)
    if any(alias in label_token or label_token in alias for alias in wanted):
        for key in ("value", "amount", "numericvalue", "rawvalue", "current", "latest", "data"):
            parsed = _number(normalized.get(key))
            if parsed is not None:
                return parsed
        # Some responses expose the first numeric period as an arbitrary key.
        for value in normalized.values():
            parsed = _number(value)
            if parsed is not None:
                return parsed
    return None


def _canonicalize_document(symbol: str, provider: str, document_type: str, period_type: str, year: int, quarter: int | None, period_end: str, payload: str | None, source_document_id: int | None) -> None:
    rows = _payload_rows(payload)
    mappings = {
        "FINANCIAL_STATEMENTS": (
            ("BS.DEBT.TOTAL", ("total_debt", "debt", "borrowings", "total liabilities", "tong no", "no phai tra")),
            ("BS.ASSETS.CASH_AND_EQUIVALENTS", ("cash_and_cash_equivalents", "cash", "cash_equivalents", "cash and cash equivalents", "tien va tuong duong tien")),
            ("BS.LIABILITIES.SHORT_TERM_BORROWINGS", ("short_term_borrowings", "short_term_debt")),
            ("BS.LIABILITIES.LONG_TERM_BORROWINGS", ("long_term_borrowings", "long_term_debt")),
        ),
        "INCOME_STATEMENT": (
            ("IS.PROFIT.NET", ("net_profit", "net_profit_after_tax", "profit_after_tax", "net_income", "net profit after tax", "loi nhuan sau thue", "loi nhuan sau thue cua co dong cong ty me")),
            ("IS.PROFIT.OPERATING", ("operating_profit", "profit_from_operation", "operating income", "loi nhuan thuan tu hoat dong kinh doanh")),
            ("IS.SHARES.OUTSTANDING", ("outstanding_shares", "outstanding_share", "shares_outstanding", "shares", "shares outstanding", "so luong co phieu dang luu hanh")),
        ),
        "CASH_FLOW": (
            ("CF.OPERATING.DEPRECIATION", ("depreciation", "depreciation_amortization")),
            ("CF.CAPEX", ("capex", "purchase_of_fixed_assets", "fixed_asset_purchases")),
            ("CF.OPERATING.NET", ("operating_cash_flow", "net_cash_from_operating_activities")),
        ),
    }
    written = 0
    for code, aliases in mappings.get(document_type, ()):
        value = next((_value(row, *aliases) for row in rows if _value(row, *aliases) is not None), None)
        if value is None:
            continue
        with _schema_connection(FINANCE_SCHEMA) as db:
            db.execute(
                """INSERT INTO canonical_facts(
                   symbol, statement_type, line_item_code, value, period_type,
                   fiscal_year, fiscal_quarter, period_end, provider,
                   source_document_id, quality_status, observed_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(symbol, statement_type, line_item_code, period_type, fiscal_year, fiscal_quarter, provider)
                DO UPDATE SET value=excluded.value, source_document_id=excluded.source_document_id,
                    quality_status='SINGLE_SOURCE', observed_at=excluded.observed_at""",
                (symbol, "BALANCE_SHEET" if document_type == "FINANCIAL_STATEMENTS" else document_type,
                 code, value, period_type, year, quarter, period_end, provider,
                 source_document_id, "SINGLE_SOURCE", _now()),
            )
        written += 1
    if written == 0:
        with _schema_connection(FINANCE_SCHEMA) as db:
            db.execute(
                """INSERT INTO parse_errors(
                    source_document_id, symbol, provider, document_type,
                    error_code, error_message, observed_at
                ) VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(source_document_id) DO UPDATE SET
                    error_code=excluded.error_code,
                    error_message=excluded.error_message,
                    observed_at=excluded.observed_at""",
                (
                    source_document_id, symbol, provider, document_type,
                    "PAYLOAD_UNPARSEABLE" if rows else "PAYLOAD_EMPTY",
                    "Provider payload did not contain a supported canonical row shape."
                    if rows else "Provider payload contained no tabular rows.",
                    _now(),
                ),
            )

def _reconcile_dividend_document(symbol: str, provider: str, payload: str | None, source_document_id: int | None) -> None:
    rows = _payload_rows(payload)
    if not rows:
        return
    try:
        from .dividend_reconciliation import normalize_observation, persist_observations, reconcile_symbol
        observations = []
        for row in rows:
            title = str(row.get("title") or row.get("eventName") or row.get("event") or "")
            kind = str(row.get("dividend_type") or row.get("type") or "").upper()
            if "STOCK" in kind or "CỔ PHIẾU" in title.upper() or "CO PHIEU" in title.upper():
                kind = "STOCK_DIVIDEND"
            elif "CASH" in kind or "TIỀN" in title.upper() or "TIEN" in title.upper() or row.get("cash_per_share") is not None:
                kind = "CASH_DIVIDEND"
            else:
                continue
            event = {
                "symbol": symbol,
                "dividend_type": kind,
                "source_event_id": row.get("id") or row.get("eventId") or row.get("event_id"),
                "announcement_date": row.get("announcement_date") or row.get("announcementDate"),
                "ex_date": row.get("ex_date") or row.get("exDate"),
                "record_date": row.get("record_date") or row.get("recordDate"),
                "payment_date": row.get("payment_date") or row.get("paymentDate"),
                "cash_per_share": row.get("cash_per_share") or row.get("valuePerShare") or row.get("cash"),
                "stock_ratio": row.get("stock_ratio") or row.get("exerciseRatio") or row.get("ratio"),
                "raw_payload": row,
            }
            observations.append(normalize_observation(event, provider=provider, source_document_id=str(source_document_id or "")))
        if observations:
            persist_observations(observations)
            reconcile_symbol(symbol)
    except Exception:
        # Raw document persistence must remain successful even when a provider
        # payload needs a later parser revision or admin review.
        return


def get_canonical_facts(symbol: str) -> list[dict[str, Any]]:
    _ensure()
    with _schema_connection(FINANCE_SCHEMA) as db:
        rows = db.execute(
            """SELECT * FROM canonical_facts
               WHERE symbol=? AND quality_status NOT IN ('CONFLICT','QUARANTINED')
               ORDER BY fiscal_year DESC, fiscal_quarter DESC NULLS LAST""",
            (str(symbol).upper().strip(),),
        ).fetchall()
    return [dict(row) for row in rows]


def _materially_conflicting(rows: list[dict[str, Any]]) -> bool:
    values = [float(row["value"]) for row in rows if row.get("value") is not None]
    if len(values) < 2:
        return False
    baseline = values[0]
    return any(abs(value - baseline) > max(1.0, abs(baseline) * 0.001) for value in values[1:])


def valuation_readiness_audit(symbol: str, market_price: float | None = None) -> dict[str, Any]:
    """Audit whether one complete FY fact set can safely enter ValueEngine.

    Raw fetch status is intentionally not evidence of usability: a SUCCESS
    document with a parser error, a missing canonical fact, a period mismatch,
    or a material cross-source conflict blocks valuation.
    """
    _ensure()
    ticker = str(symbol).upper().strip()
    with _schema_connection(FINANCE_SCHEMA) as db:
        fact_rows = [
            dict(row) for row in db.execute(
                """SELECT symbol, statement_type, line_item_code, value,
                          period_type, fiscal_year, fiscal_quarter, period_end,
                          provider, source_document_id, quality_status, observed_at
                   FROM canonical_facts WHERE symbol=?
                   ORDER BY fiscal_year DESC, fiscal_quarter DESC NULLS LAST, provider ASC""",
                (ticker,),
            ).fetchall()
        ]
        document_rows = [
            dict(row) for row in db.execute(
                """SELECT id, provider, document_type, period_type, fiscal_year,
                          fiscal_quarter, period_end, status, fetched_at,
                          error_code, error_message
                   FROM documents WHERE symbol=?""",
                (ticker,),
            ).fetchall()
        ]
        parse_rows = [
            dict(row) for row in db.execute(
                """SELECT p.source_document_id, p.error_code, p.error_message,
                          d.provider, d.document_type, d.period_type,
                          d.fiscal_year, d.fiscal_quarter, d.period_end
                   FROM parse_errors p
                   JOIN documents d ON d.id=p.source_document_id
                   WHERE d.symbol=?""",
                (ticker,),
            ).fetchall()
        ]

    required_codes = [code for code, _ in VALUE_ENGINE_REQUIRED_FACTS]
    fact_periods = sorted(
        {
            int(row["fiscal_year"])
            for row in fact_rows
            if row.get("period_type") == "FY" and row.get("fiscal_quarter") is None
        },
        reverse=True,
    )
    selected_year = fact_periods[0] if fact_periods else None
    selected_facts: dict[str, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    relevant_parse_errors: list[dict[str, Any]] = []
    warnings: list[str] = []

    if selected_year is not None:
        period_facts = [
            row for row in fact_rows
            if row.get("period_type") == "FY"
            and row.get("fiscal_quarter") is None
            and int(row["fiscal_year"]) == selected_year
        ]
        for code in required_codes:
            candidates = [row for row in period_facts if row.get("line_item_code") == code and row.get("value") is not None]
            bad_quality = [row for row in candidates if row.get("quality_status") in {"CONFLICT", "QUARANTINED", "MISSING"}]
            if bad_quality or _materially_conflicting(candidates):
                conflicts.append({
                    "line_item_code": code,
                    "fiscal_year": selected_year,
                    "providers": sorted({str(row.get("provider") or "") for row in candidates}),
                })
                continue
            if candidates:
                selected_facts[code] = sorted(candidates, key=lambda row: str(row.get("provider") or ""))[0]
        relevant_parse_errors = [
            row for row in parse_rows
            if row.get("period_type") == "FY"
            and row.get("fiscal_quarter") is None
            and int(row["fiscal_year"]) == selected_year
        ]

    missing_codes = [code for code in required_codes if code not in selected_facts]
    reasons: list[str] = []
    if selected_year is None:
        reasons.append("FY_REQUIRED")
    if missing_codes:
        reasons.append("REQUIRED_FACTS_MISSING")
    if conflicts:
        reasons.append("CANONICAL_FACT_CONFLICT")
    if relevant_parse_errors:
        reasons.append("PARSE_ERROR_PRESENT")
    if market_price is not None and float(market_price) <= 0:
        reasons.append("MARKET_PRICE_MISSING")
    if selected_year is not None and not conflicts:
        single_source_codes = [
            code for code, fact in selected_facts.items()
            if fact.get("quality_status") == "SINGLE_SOURCE"
        ]
        if single_source_codes:
            warnings.append("SINGLE_SOURCE_FACTS:" + ",".join(single_source_codes))
    usable_document_ids = {
        int(row["id"]) for row in document_rows
        if row.get("status") == "SUCCESS"
        and int(row["id"]) not in {int(error["source_document_id"]) for error in parse_rows}
    }
    status = "READY" if not reasons else "BLOCKED"
    return {
        "symbol": ticker,
        "status": status,
        "selected_period": (
            {"period_type": "FY", "fiscal_year": selected_year, "fiscal_quarter": None}
            if selected_year is not None else None
        ),
        "required_facts": [
            {"line_item_code": code, "label": label, "available": code in selected_facts}
            for code, label in VALUE_ENGINE_REQUIRED_FACTS
        ],
        "missing": missing_codes,
        "conflicts": conflicts,
        "parse_errors": relevant_parse_errors,
        "warnings": warnings,
        "reasons": reasons,
        "document_summary": {
            "total": len(document_rows),
            "fetch_success": sum(1 for row in document_rows if row.get("status") == "SUCCESS"),
            "usable_success": len(usable_document_ids),
            "parse_error_count": len(parse_rows),
        },
        "selected_facts": selected_facts,
    }


def valuation_snapshot_from_catalog(symbol: str, market_price: float | None = None) -> dict[str, Any]:
    ticker = str(symbol).upper().strip()
    audit = valuation_readiness_audit(ticker, market_price)
    if audit["status"] != "READY":
        return {
            "ok": False,
            "code": "FINANCE_DATA_NOT_READY",
            "message": "contact admin",
            "symbol": ticker,
            "audit": audit,
        }
    latest = audit["selected_facts"]
    with _schema_connection(FINANCE_SCHEMA) as db:
        security = db.execute(
            "SELECT company_name, industry, exchange FROM securities WHERE symbol=?",
            (ticker,),
        ).fetchone()
    profile = [dict(security)] if security else []
    return {
        "ok": True,
        "symbol": ticker,
        "provider": "finance_catalog",
        "fetched_at": latest["IS.PROFIT.NET"]["observed_at"],
        "fiscal_year": latest["IS.PROFIT.NET"]["fiscal_year"],
        "fiscal_quarter": None,
        "period_end": latest["IS.PROFIT.NET"].get("period_end"),
        "income_statement": [{
            "net_profit": latest["IS.PROFIT.NET"]["value"],
            "operating_profit": latest["IS.PROFIT.OPERATING"]["value"],
        }],
        "balance_sheet": [{
            "total_debt": latest["BS.DEBT.TOTAL"]["value"],
            "cash": latest["BS.ASSETS.CASH_AND_EQUIVALENTS"]["value"],
        }],
        "cash_flow": [{
            "depreciation": latest["CF.OPERATING.DEPRECIATION"]["value"],
            "capex": latest["CF.CAPEX"]["value"],
            "operating_cash_flow": latest["CF.OPERATING.NET"]["value"],
        }],
        "ratios": [{"outstanding_shares": latest["IS.SHARES.OUTSTANDING"]["value"]}],
        "profile": profile,
        "prices": [{"close": market_price}],
        "audit": audit,
    }


def _save_document(symbol: str, provider: str, document_type: str, period_type: str, year: int, quarter: int | None, period_end: str, source_url: str, status: str, payload: str | None, error_code: str | None, error_message: str | None, run_id: int | None) -> None:
    body_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest() if payload else None
    # Commit the raw document first. Canonicalization uses a separate connection
    # only after this transaction is closed, avoiding nested transaction locks
    # and guaranteeing the source_document_id is visible to the normalizer.
    with _schema_connection(FINANCE_SCHEMA) as db:
        db.execute(
            """INSERT INTO documents(symbol,provider,document_type,period_type,fiscal_year,fiscal_quarter,period_end,status,source_url,payload,content_hash,fetched_at,error_code,error_message,crawl_run_id)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT (symbol, provider, document_type, period_type, fiscal_year, (COALESCE(fiscal_quarter, 0)))
               DO UPDATE SET status=excluded.status, source_url=excluded.source_url, payload=excluded.payload,
               content_hash=excluded.content_hash, fetched_at=excluded.fetched_at, error_code=excluded.error_code,
               error_message=excluded.error_message, crawl_run_id=excluded.crawl_run_id""",
            (symbol, provider, document_type, period_type, year, quarter, period_end, status, source_url, payload, body_hash, _now(), error_code, error_message, run_id),
        )
    if status != "SUCCESS":
        return
    with _schema_connection(FINANCE_SCHEMA) as db:
        row = db.execute(
            "SELECT id FROM documents WHERE symbol=? AND provider=? AND document_type=? AND period_type=? AND fiscal_year=? AND fiscal_quarter IS NOT DISTINCT FROM ?",
            (symbol, provider, document_type, period_type, year, quarter),
        ).fetchone()
    document_id = int(row["id"]) if row else None
    _canonicalize_document(symbol, provider, document_type, period_type, year, quarter, period_end, payload, document_id)
    if document_type == "DIVIDEND":
        _reconcile_dividend_document(symbol, provider, payload, document_id)

def _crawl_progress(symbol: str, message: str) -> None:
    print(f"[finance-crawl] symbol={symbol} {message}", flush=True)



def _tcbs_document_headers() -> dict[str, str]:
    """Build local-only TCBS request headers without logging credentials."""
    headers = {
        "Referer": "https://tcinvest.tcbs.com.vn/",
        "Origin": "https://tcinvest.tcbs.com.vn",
    }
    token = str(os.environ.get("TCBS_BEARER_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = (
            token if token.lower().startswith("bearer ") else f"Bearer {token}"
        )
    return headers

def _fetch_provider(symbol: str, provider: str, document_type: str, period_type: str, year: int, quarter: int | None, period_end: str, run_id: int | None) -> bool:
    if provider == "tcbs":
        if document_type == "DIVIDEND":
            url = f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/company/{symbol}/dividend-payment-histories?page=0&size=200"
        else:
            endpoint = {
                "FINANCIAL_STATEMENTS": "balancesheet",
                "INCOME_STATEMENT": "incomestatement",
                "CASH_FLOW": "cashflow",
            }.get(document_type, "incomestatement")
            yearly = "1" if period_type == "FY" else "0"
            url = f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/{endpoint}?yearly={yearly}&isAll=true"
        headers = _tcbs_document_headers()
    else:
        if document_type == "DIVIDEND":
            url = f"https://cafef.vn/du-lieu.ashx?symbol={symbol}"
        else:
            segment = "IncSta" if document_type == "INCOME_STATEMENT" else ("BSheet" if document_type == "FINANCIAL_STATEMENTS" else "CashFlow")
            q = quarter or 4
            url = f"https://cafef.vn/du-lieu/bao-cao-tai-chinh/{symbol}/{segment}/{year}/{q}/0/0/1/bao-cao-tai-chinh-{symbol.lower()}.chn"
        headers = {}
    period_label = f"{period_type}:{year}" + (f":Q{quarter}" if quarter else "")
    _crawl_progress(symbol, f"fetch provider={provider} document={document_type} period={period_label}")
    try:
        status, payload = _url_json(url, headers=headers)
        if status < 200 or status >= 300:
            raise RuntimeError(f"HTTP {status}")
        _save_document(symbol, provider, document_type, period_type, year, quarter, period_end, url, "SUCCESS", payload, None, None, run_id)
        _crawl_progress(symbol, f"success provider={provider} document={document_type} period={period_label}")
        return True
    except Exception as exc:
        if isinstance(exc, urllib.error.HTTPError):
            code = "PROVIDER_HTTP_ERROR"
            detail = f"HTTP {exc.code} {exc.reason or ''}".strip()
            status_label = str(exc.code)
        else:
            code = "PROVIDER_UNAVAILABLE"
            detail = str(exc)[:500]
            status_label = "unavailable"
        _save_document(
            symbol, provider, document_type, period_type, year, quarter,
            period_end, url, "FAILED", None, code, detail, run_id,
        )
        _crawl_progress(
            symbol,
            f"failed provider={provider} document={document_type} "
            f"period={period_label} code={code} status={status_label}",
        )
        return False


def claim_next_crawl_job(stale_after_seconds: int = 900) -> dict[str, Any] | None:
    """Claim one queued job that still has missing or incomplete documents."""
    _ensure()
    cutoff = datetime.now(timezone.utc).timestamp() - max(60, int(stale_after_seconds))
    cutoff_iso = datetime.fromtimestamp(cutoff, timezone.utc).isoformat()
    with _schema_connection(FINANCE_SCHEMA) as db:
        db.execute(
            "UPDATE crawl_queue SET status='QUEUED', started_at=NULL, error=NULL "
            "WHERE status='RUNNING' AND (started_at IS NULL OR started_at<?)",
            (cutoff_iso,),
        )
        db.execute(
            f"UPDATE crawl_queue SET status='FAILED', finished_at=?, "
            f"error='SECURITY_NOT_CRAWLABLE' WHERE status='QUEUED' "
            f"AND symbol NOT IN (SELECT symbol FROM securities WHERE {ACTIVE_EQUITY_SQL})",
            (_now(),),
        )
        while True:
            row = db.execute(
                """SELECT q.id, q.symbol, q.requested_by
                   FROM crawl_queue AS q
                   JOIN securities AS s ON s.symbol=q.symbol
                   WHERE q.status='QUEUED' AND s.exchange IN ('HOSE','HNX')
                   ORDER BY CASE s.exchange WHEN 'HOSE' THEN 0 WHEN 'HNX' THEN 1 ELSE 2 END,
                            q.id
                   LIMIT 1
                   FOR UPDATE OF q SKIP LOCKED"""
            ).fetchone()
            if row is None:
                return None
            if not _symbol_needs_crawl(db, row["symbol"]):
                db.execute(
                    "UPDATE crawl_queue SET status='COMPLETED', finished_at=?, "
                    "error='NO_MISSING_DOCUMENTS' "
                    "WHERE id=? AND status='QUEUED'",
                    (_now(), row["id"]),
                )
                _crawl_progress(
                    "queue",
                    f"skip queue_id={row['id']} symbol={row['symbol']} "
                    "reason=NO_MISSING_DOCUMENTS",
                )
                continue
            updated = db.execute(
                "UPDATE crawl_queue SET status='RUNNING', started_at=?, error=NULL "
                "WHERE id=? AND status='QUEUED'",
                (_now(), row["id"]),
            )
            if int(updated.rowcount or 0):
                return dict(row)



def finish_crawl_job(
    queue_id: int,
    *,
    status: str,
    error: str | None = None,
) -> None:
    """Persist the terminal state of a claimed local-worker job."""
    if status not in {"COMPLETED", "FAILED"}:
        raise ValueError("queue job status must be COMPLETED or FAILED")
    _ensure()
    with _schema_connection(FINANCE_SCHEMA) as db:
        db.execute(
            "UPDATE crawl_queue SET status=?, finished_at=?, error=? "
            "WHERE id=? AND status='RUNNING'",
            (status, _now(), error[:500] if error else None, queue_id),
        )


def enqueue_crawl_all(requested_by: int | None = None, exchange: str | None = None) -> dict[str, Any]:
    """Queue only active equities with missing or incomplete finance documents."""
    try:
        _validate_crawl_runtime()
    except RuntimeError as exc:
        return {
            "ok": False,
            "code": "CRAWL_RUNTIME_INVALID",
            "message": str(exc),
            "queued": 0,
            "eligible": 0,
            "already_queued": 0,
        }
    exchange_value = str(exchange or "").upper().strip()
    if exchange_value and exchange_value not in WORKER_CRAWL_EXCHANGES:
        return {
            "ok": False,
            "code": "CRAWL_EXCHANGE_UNSUPPORTED",
            "message": "External worker hiện chỉ crawl HOSE và HNX; UPCOM chưa thuộc scope.",
            "queued": 0,
            "eligible": 0,
            "already_queued": 0,
        }
    _ensure()
    with _schema_connection(FINANCE_SCHEMA) as db:
        if exchange_value:
            rows = db.execute(
                f"SELECT symbol FROM securities WHERE {ACTIVE_EQUITY_SQL} AND exchange=?",
                (exchange_value,),
            ).fetchall()
        else:
            rows = db.execute(
                f"SELECT symbol FROM securities WHERE {ACTIVE_EQUITY_SQL} "
                "AND exchange IN ('HOSE','HNX')"
            ).fetchall()
        symbols = [row["symbol"] for row in rows]
        required_keys = _current_required_document_keys()
        documents_by_symbol: dict[str, list[dict[str, Any]]] = {
            symbol: [] for symbol in symbols
        }
        if symbols:
            placeholders = ",".join("?" for _ in symbols)
            documents = db.execute(
                "SELECT symbol, provider, document_type, period_type, "
                "fiscal_year, fiscal_quarter, status "
                f"FROM documents WHERE symbol IN ({placeholders})",
                tuple(symbols),
            ).fetchall()
            for document in documents:
                documents_by_symbol[document["symbol"]].append(dict(document))

        crawl_symbols = [
            symbol for symbol in symbols
            if _has_missing_or_incomplete_documents(
                documents_by_symbol[symbol],
                required_keys,
            )
        ]
        existing_symbols: set[str] = set()
        if crawl_symbols:
            placeholders = ",".join("?" for _ in crawl_symbols)
            existing = db.execute(
                "SELECT symbol FROM crawl_queue "
                "WHERE status IN ('QUEUED','RUNNING') "
                f"AND symbol IN ({placeholders})",
                tuple(crawl_symbols),
            ).fetchall()
            existing_symbols = {row["symbol"] for row in existing}

        queued = 0
        for symbol in crawl_symbols:
            if symbol in existing_symbols:
                continue
            result = db.execute(
                """INSERT INTO crawl_queue(symbol, requested_by, status, requested_at)
                   VALUES(?,?,?,?)
                   ON CONFLICT DO NOTHING""",
                (symbol, requested_by, "QUEUED", _now()),
            )
            queued += int(result.rowcount or 0)

    eligible = len(crawl_symbols)
    already_queued = len(existing_symbols)
    skipped_complete = len(symbols) - eligible
    _crawl_progress(
        "queue",
        f"universe queue eligible={eligible} "
        f"already_queued={already_queued} queued={queued} "
        f"skipped_complete={skipped_complete}",
    )
    return {
        "ok": True,
        "queued": queued,
        "eligible": eligible,
        "already_queued": already_queued,
        "skipped_complete": skipped_complete,
        "message": (
            f"Đã xếp hàng {queued}/{eligible} mã cần crawl."
            + (
                f" {already_queued} mã đã có trạng thái QUEUED/RUNNING."
                if already_queued
                else ""
            )
            + (
                f" Bỏ qua {skipped_complete} mã đã đủ tài liệu."
                if skipped_complete
                else ""
            )
        ),
    }



def _validate_crawl_runtime() -> None:
    """Provider calls are allowed only in an explicitly named local worker."""
    runtime = str(os.environ.get("QPORT_FINANCE_RUNTIME") or "").strip().lower()
    if runtime not in {"local", "worker"}:
        raise RuntimeError(
            "CRAWL_RUNTIME_INVALID: set QPORT_FINANCE_RUNTIME=local (or worker) "
            "on the external crawler; Vercel is database-read-only"
        )
    if os.environ.get("VERCEL"):
        raise RuntimeError("CRAWL_RUNTIME_INVALID: provider crawling is disabled on Vercel")


def _should_fetch_document(status: str | None, *, retry_failed_only: bool) -> bool:
    """Return whether a document needs a provider request in this crawl."""
    normalized = str(status or "").upper()
    if normalized == "SUCCESS":
        return False
    if retry_failed_only:
        return normalized == "FAILED"
    return True


def _current_required_document_keys() -> set[tuple[str, str, str, int, int | None]]:
    periods = _periods()
    latest_fy = max((item[1] for item in periods if item[0] == "FY"), default=None)
    keys: set[tuple[str, str, str, int, int | None]] = set()
    for period_type, year, quarter, _period_end in periods:
        for document_type in REQUIRED_DOCUMENTS:
            if document_type == "DIVIDEND" and (period_type != "FY" or year != latest_fy):
                continue
            for provider in WORKER_PROVIDERS:
                keys.add((provider, document_type, period_type, year, quarter))
    return keys


def _has_missing_or_incomplete_documents(
    document_rows: list[dict[str, Any]],
    required_keys: set[tuple[str, str, str, int, int | None]] | None = None,
) -> bool:
    required = required_keys or _current_required_document_keys()
    existing = {
        (
            str(row["provider"]),
            str(row["document_type"]),
            str(row["period_type"]),
            int(row["fiscal_year"]),
            row["fiscal_quarter"],
        ): str(row["status"]).upper()
        for row in document_rows
    }
    return any(
        key not in existing
        or _should_fetch_document(existing[key], retry_failed_only=False)
        for key in required
    )


def _symbol_needs_crawl(db: Any, symbol: str) -> bool:
    rows = db.execute(
        "SELECT provider, document_type, period_type, fiscal_year, "
        "fiscal_quarter, status FROM documents WHERE symbol=?",
        (symbol,),
    ).fetchall()
    return _has_missing_or_incomplete_documents(
        [dict(row) for row in rows]
    )


def crawl_symbol(symbol: str, requested_by: int | None = None, *, retry_failed_only: bool = False) -> dict[str, Any]:
    _ensure()
    symbol = str(symbol).upper().strip()
    if not symbol:
        return {"ok": False, "code": "INVALID_SYMBOL"}
    try:
        _validate_crawl_runtime()
    except RuntimeError as exc:
        return {"ok": False, "code": "CRAWL_RUNTIME_INVALID", "message": str(exc)}
    if not _is_crawlable_security(symbol):
        return {
            "ok": False,
            "code": "SECURITY_NOT_CRAWLABLE",
            "message": "Symbol is not an active listed equity in the Finance universe.",
        }
    _crawl_progress(
        symbol,
        f"start providers={','.join(WORKER_PROVIDERS)} "
        f"retry_failed_only={retry_failed_only}",
    )
    ensure_required_documents(symbol)
    _crawl_progress(symbol, "required document placeholders ensured")
    with _schema_connection(FINANCE_SCHEMA) as db:
        row = db.execute("INSERT INTO crawl_runs(requested_by,status,requested_at,total_symbols) VALUES(?,?,?,1) RETURNING id", (requested_by, "RUNNING", _now())).fetchone()
        run_id = int(row["id"])
    results = []
    skipped_count = 0
    periods = _periods()
    latest_fy = max((item[1] for item in periods if item[0] == "FY"), default=None)
    for period_type, year, quarter, period_end in periods:
        for document_type in REQUIRED_DOCUMENTS:
            if document_type == "DIVIDEND" and (period_type != "FY" or year != latest_fy):
                continue
            for provider in WORKER_PROVIDERS:
                with _schema_connection(FINANCE_SCHEMA) as db:
                    existing = db.execute(
                        "SELECT status FROM documents WHERE symbol=? AND provider=? AND document_type=? "
                        "AND period_type=? AND fiscal_year=? "
                        "AND fiscal_quarter IS NOT DISTINCT FROM ?",
                        (symbol, provider, document_type, period_type, year, quarter),
                    ).fetchone()
                status = existing["status"] if existing else None
                if not _should_fetch_document(
                    status,
                    retry_failed_only=retry_failed_only,
                ):
                    skipped_count += 1
                    _crawl_progress(
                        symbol,
                        f"skip provider={provider} document={document_type} "
                        f"period={period_type}:{year}" + (f":Q{quarter}" if quarter else "")
                        + f" status={status or 'MISSING'}",
                    )
                    continue
                results.append(
                    _fetch_provider(
                        symbol, provider, document_type, period_type,
                        year, quarter, period_end, run_id,
                    )
                )
    success = sum(1 for item in results if item)
    failure = len(results) - success
    with _schema_connection(FINANCE_SCHEMA) as db:
        db.execute(
            "UPDATE crawl_runs SET status=?,finished_at=?,success_count=?,failure_count=? WHERE id=?",
            ("COMPLETED", _now(), success, failure, run_id),
        )
    _crawl_progress(
        symbol,
        f"completed run_id={run_id} fetched={len(results)} success={success} "
        f"failed={failure} skipped={skipped_count}",
    )
    return {
        "ok": True,
        "run_id": run_id,
        "symbol": symbol,
        "success_count": success,
        "failure_count": failure,
        "skipped_count": skipped_count,
    }


def finance_database_status() -> dict[str, Any]:
    """Return operational counts without exposing document payloads."""
    _ensure()
    with _schema_connection(FINANCE_SCHEMA) as db:
        securities = db.execute(
            "SELECT COUNT(*) AS count FROM securities"
        ).fetchone()["count"]
        documents = db.execute(
            "SELECT status, COUNT(*) AS count FROM documents GROUP BY status"
        ).fetchall()
        queue = db.execute(
            "SELECT status, COUNT(*) AS count FROM crawl_queue GROUP BY status"
        ).fetchall()
    return {
        "securities": int(securities or 0),
        "documents": {str(row["status"]): int(row["count"]) for row in documents},
        "queue": {str(row["status"]): int(row["count"]) for row in queue},
    }


def clear_finance_queue() -> dict[str, Any]:
    """Clear queue history after all workers have stopped."""
    _ensure()
    with _schema_connection(FINANCE_SCHEMA) as db:
        running = db.execute(
            "SELECT COUNT(*) AS count FROM crawl_queue WHERE status='RUNNING'"
        ).fetchone()["count"]
        if int(running or 0):
            raise RuntimeError("stop finance workers before clearing the queue")
        deleted = db.execute("DELETE FROM crawl_queue")
    return {"deleted_queue_rows": int(deleted.rowcount or 0)}


def clear_incomplete_finance_data() -> dict[str, Any]:
    """Remove only non-success documents and reset queue for an explicit rebuild."""
    _ensure()
    with _schema_connection(FINANCE_SCHEMA) as db:
        running = db.execute(
            "SELECT COUNT(*) AS count FROM crawl_queue WHERE status='RUNNING'"
        ).fetchone()["count"]
        if int(running or 0):
            raise RuntimeError("stop finance workers before clearing incomplete data")
        incomplete = db.execute(
            "SELECT COUNT(*) AS count FROM documents WHERE status <> 'SUCCESS'"
        ).fetchone()["count"]
        db.execute(
            """
            DELETE FROM parse_errors
            WHERE source_document_id IN (
                SELECT id FROM documents WHERE status <> 'SUCCESS'
            )
            """
        )
        deleted_documents = db.execute(
            "DELETE FROM documents WHERE status <> 'SUCCESS'"
        )
        queue_rows = db.execute(
            "SELECT COUNT(*) AS count FROM crawl_queue"
        ).fetchone()["count"]
        db.execute("DELETE FROM crawl_queue")
    return {
        "deleted_incomplete_documents": int(deleted_documents.rowcount or 0),
        "cleared_queue_rows": int(queue_rows or 0),
    }


def latest_documents_for_user(symbol: str) -> dict[str, Any]:
    result = get_symbol_documents(symbol)
    ready = [
        row for row in result["documents"]
        if str(row.get("status") or "").upper() == "SUCCESS"
    ]
    if not ready:
        return {"ok": False, "code": "FINANCE_DATA_MISSING", "message": "contact admin", "symbol": symbol}
    return {"ok": True, "documents": ready, "symbol": result["symbol"]}


def get_canonical_dividend_events(symbol: str) -> list[dict[str, Any]]:
    _ensure()
    # Reconciliation owns the canonical/conflict tables. Ensure they exist
    # before a read so a fresh deployment returns an empty catalog, not a 500.
    from .dividend_reconciliation import ensure_reconciliation_schema
    ensure_reconciliation_schema()
    ticker = str(symbol).upper().strip()
    with _schema_connection(FINANCE_SCHEMA) as db:
        rows = db.execute(
            """SELECT canonical_id AS event_key, symbol, dividend_type,
                      effective_event_date, cash_per_share, stock_ratio,
                      quality_status, evidence_json, last_seen_at
               FROM dividend_canonical
               WHERE symbol=? AND quality_status IN ('VERIFIED','SINGLE_SOURCE')
               ORDER BY effective_event_date DESC""",
            (ticker,),
        ).fetchall()
    return [dict(row) for row in rows]


def _universe_progress(message: str) -> None:
    print(f"[finance-universe] {message}", flush=True)


def _listing_call_with_heartbeat(label: str, callback: Any) -> Any:
    started = time.monotonic()
    stop = threading.Event()

    def heartbeat() -> None:
        while not stop.wait(10):
            elapsed = time.monotonic() - started
            _universe_progress(f"{label} still running ({elapsed:.0f}s)")

    monitor = threading.Thread(target=heartbeat, name="finance-universe-heartbeat", daemon=True)
    monitor.start()
    try:
        return callback()
    finally:
        stop.set()
        monitor.join(timeout=1)



def _normalize_exchange(value: str | None) -> str:
    """Map Vnstock exchange/group variants to the supported exchange filter."""
    token = _token(value)
    if token in {"hose", "hsx", "hoseindex"}:
        return "HOSE"
    if token in {"hnx", "hnxindex"}:
        return "HNX"
    if token in {"upcom", "upcomindex"}:
        return "UPCOM"
    return "UNKNOWN"


def _normalize_universe_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize Vnstock listing rows across provider schema variants."""
    raw = {str(key).strip().lower().replace("-", "_").replace(" ", "_"): value
           for key, value in dict(row).items()}

    def first(*keys: str) -> tuple[str | None, str | None]:
        for key in keys:
            value = raw.get(key)
            text = str(value).strip() if value is not None else ""
            if text and text.upper() not in {"-", "UNKNOWN", "NAN", "NONE"}:
                return text, key
        return None, None

    symbol, _ = first("symbol", "ticker", "code", "stock_code", "stockcode")
    exchange_raw, exchange_source = first(
        "exchange", "exchange_code", "exchangecode", "exchange_name",
        "exchangename", "listing_market", "listingmarket", "com_group_code",
        "comgroupcode", "group_code", "groupcode", "com_group", "floor_code",
        "floorcode", "floor", "market",
    )
    company_name, _ = first(
        "organ_name", "organname", "company_name", "companyname",
        "company_full_name", "companyfullname", "name", "company",
    )
    industry, industry_source = first(
        "industry", "industry_name", "industryname", "industry_level_1",
        "industrylevel1", "sector", "sector_name", "sectorname", "icb_name",
        "icbname", "icb_name1", "icbname1", "icb_name2", "icbname2",
        "icb_name3", "icbname3", "icb_name4", "icbname4",
    )
    exchange = _normalize_exchange(exchange_raw)
    return {
        "symbol": symbol.upper() if symbol else None,
        "exchange": exchange,
        "company_name": company_name,
        "industry": industry or "UNKNOWN",
        "exchange_raw": exchange_raw,
        "exchange_source": exchange_source,
        "industry_source": industry_source,
        "missing_exchange": exchange_raw is None,
        "unrecognized_exchange": exchange_raw is not None and exchange == "UNKNOWN",
        "missing_industry": industry is None,
    }



def _universe_quality(rows: list[dict[str, Any]], normalized_rows: list[dict[str, Any]]) -> dict[str, int]:
    symbols = [row["symbol"] for row in normalized_rows if row.get("symbol")]
    unique_symbols = set(symbols)
    return {
        "received": len(rows),
        "valid_symbols": len(unique_symbols),
        "duplicate_symbols": len(symbols) - len(unique_symbols),
        "missing_symbol": sum(1 for row in normalized_rows if not row.get("symbol")),
        "unknown_exchange": sum(1 for row in normalized_rows if row.get("exchange") == "UNKNOWN"),
        "missing_exchange": sum(1 for row in normalized_rows if row.get("missing_exchange")),
        "unrecognized_exchange": sum(1 for row in normalized_rows if row.get("unrecognized_exchange")),
        "missing_industry": sum(1 for row in normalized_rows if row.get("missing_industry")),
    }


def _merge_vnstock_universe_rows(
    exchange_rows: list[dict[str, Any]],
    industry_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join Vnstock's bulk exchange and ICB metadata by symbol.

    Vnstock all_symbols() intentionally discards exchange and industry columns.
    Retain the highest-level ICB classification (lowest numeric level) for the
    compact Finance Data universe table.
    """
    industries: dict[str, tuple[int, str]] = {}
    for row in industry_rows:
        normalized = _normalize_universe_row(row)
        symbol = normalized["symbol"]
        industry = normalized["industry"]
        if not symbol or industry == "UNKNOWN":
            continue
        raw_level = dict(row).get("icb_level", dict(row).get("level"))
        try:
            level = int(raw_level)
        except (TypeError, ValueError):
            level = 99
        existing = industries.get(symbol)
        if existing is None or level < existing[0]:
            industries[symbol] = (level, industry)

    merged: list[dict[str, Any]] = []
    seen_symbols: set[str] = set()
    for row in exchange_rows:
        item = dict(row)
        normalized = _normalize_universe_row(item)
        symbol = normalized["symbol"]
        if not symbol or symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        if symbol in industries:
            item["industry"] = industries[symbol][1]
            item["industry_source"] = "vnstock_icb"
        merged.append(item)
    return merged


def _filter_crawlable_equity_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Keep only ordinary listed equities eligible for financial-document crawling."""
    accepted: list[dict[str, Any]] = []
    rejected = {"non_stock": 0, "missing_symbol": 0, "invalid_exchange": 0, "missing_company_name": 0}
    for row in rows:
        raw = dict(row)
        normalized = _normalize_universe_row(raw)
        asset_type = str(raw.get("type") or raw.get("asset_type") or "").strip().upper()
        if asset_type != "STOCK":
            rejected["non_stock"] += 1
        elif not normalized["symbol"]:
            rejected["missing_symbol"] += 1
        elif normalized["exchange"] not in {"HOSE", "HNX", "UPCOM"}:
            rejected["invalid_exchange"] += 1
        elif not normalized["company_name"]:
            rejected["missing_company_name"] += 1
        else:
            accepted.append(raw)
    return accepted, rejected


def _deactivate_securities_not_in(symbols: list[str]) -> tuple[int, int]:
    """Hide stale instruments and cancel their queued crawl jobs after a refresh."""
    if not symbols:
        return 0, 0
    _ensure()
    placeholders = ",".join("?" for _ in symbols)
    now = _now()
    with _schema_connection(FINANCE_SCHEMA) as db:
        deactivated = db.execute(
            f"UPDATE securities SET is_active=0 WHERE is_active=1 "
            f"AND symbol NOT IN ({placeholders})",
            tuple(symbols),
        )
        cancelled = db.execute(
            f"UPDATE crawl_queue SET status='FAILED', finished_at=?, "
            f"error='UNIVERSE_FILTERED' WHERE status='QUEUED' "
            f"AND symbol NOT IN ({placeholders})",
            (now, *symbols),
        )
    return int(deactivated.rowcount or 0), int(cancelled.rowcount or 0)


def _is_crawlable_security(symbol: str) -> bool:
    _ensure()
    with _schema_connection(FINANCE_SCHEMA) as db:
        row = db.execute(
            f"SELECT 1 FROM securities WHERE symbol=? AND {ACTIVE_EQUITY_SQL}",
            (symbol,),
        ).fetchone()
    return row is not None


def sync_universe() -> dict[str, Any]:
    """Populate the universe from Vnstock's bulk exchange and ICB endpoints."""
    started = time.monotonic()
    _universe_progress("start runtime=local provider=vnstock-direct")
    try:
        _validate_crawl_runtime()
    except RuntimeError as exc:
        _universe_progress(f"rejected runtime: {exc}")
        return {"ok": False, "code": "CRAWL_RUNTIME_INVALID", "message": str(exc)}
    try:
        _universe_progress("loading vnstock.Listing for exchange and industry metadata")
        from vnstock import Listing  # type: ignore

        listing = Listing()
        _universe_progress("vnstock.Listing initialized")
        exchange_method = getattr(listing, "symbols_by_exchange", None)
        if not callable(exchange_method):
            raise RuntimeError("Installed Vnstock does not support symbols_by_exchange().")
        _universe_progress("calling Listing.symbols_by_exchange()")
        exchange_frame = _listing_call_with_heartbeat(
            "Listing.symbols_by_exchange()",
            exchange_method,
        )
        exchange_rows = (
            exchange_frame.to_dict("records")
            if hasattr(exchange_frame, "to_dict")
            else (exchange_frame or [])
        )
        if not exchange_rows:
            raise RuntimeError("Vnstock returned no exchange rows.")

        industry_rows: list[dict[str, Any]] = []
        industry_method = getattr(listing, "symbols_by_industries", None)
        if not callable(industry_method):
            _universe_progress(
                "Listing.symbols_by_industries() unavailable; keeping exchange/name metadata"
            )
        else:
            _universe_progress("calling Listing.symbols_by_industries()")
            try:
                industry_frame = _listing_call_with_heartbeat(
                    "Listing.symbols_by_industries()",
                    industry_method,
                )
                industry_rows = (
                    industry_frame.to_dict("records")
                    if hasattr(industry_frame, "to_dict")
                    else (industry_frame or [])
                )
                _universe_progress(
                    f"received {len(industry_rows)} ICB rows via Listing.symbols_by_industries()"
                )
            except Exception as exc:
                _universe_progress(
                    "Listing.symbols_by_industries() failed; "
                    f"continuing without industry metadata type={type(exc).__name__}"
                )

        merged_rows = _merge_vnstock_universe_rows(exchange_rows, industry_rows)
        rows, rejected = _filter_crawlable_equity_rows(merged_rows)
        _universe_progress(
            f"filtered crawlable equities={len(rows)}/{len(merged_rows)} "
            f"rejected_non_stock={rejected['non_stock']} "
            f"rejected_invalid_exchange={rejected['invalid_exchange']} "
            f"rejected_missing_name={rejected['missing_company_name']}"
        )
        columns = sorted({str(key) for row in rows[:100] for key in dict(row)})
        _universe_progress(
            f"received {len(rows)} symbol rows via Vnstock direct metadata APIs; "
            f"columns={json.dumps(columns, ensure_ascii=False)}"
        )
        count = 0
        normalized_rows = []
        checkpoint = max(1, len(rows) // 10) if rows else 1
        for row in rows:
            normalized = _normalize_universe_row(dict(row))
            symbol = normalized["symbol"]
            normalized_rows.append(normalized)
            if not symbol:
                continue
            upsert_security(
                symbol,
                normalized["exchange"],
                normalized["company_name"],
                normalized["industry"],
            )
            ensure_required_documents(symbol)
            count += 1
            if count == 1 or count % checkpoint == 0:
                _universe_progress(
                    f"persisted {count}/{len(rows)} symbols (latest={symbol})"
                )

        deactivated_count, cancelled_queue_count = _deactivate_securities_not_in(
            [row["symbol"] for row in normalized_rows if row.get("symbol")]
        )
        elapsed = time.monotonic() - started
        quality = _universe_quality(rows, normalized_rows)
        diagnostics = [
            {
                "symbol": row["symbol"],
                "exchange": row["exchange"],
                "exchange_raw": row["exchange_raw"],
                "exchange_source": row["exchange_source"],
                "industry_source": row["industry_source"],
            }
            for row in normalized_rows[:3]
        ]
        _universe_progress(
            f"completed count={count} deactivated={deactivated_count} "
            f"cancelled_queued={cancelled_queue_count} elapsed={elapsed:.1f}s"
        )
        _universe_progress(
            f"mapping_samples={json.dumps(diagnostics, ensure_ascii=False)}"
        )
        warnings = []
        if quality["unknown_exchange"]:
            warnings.append(f'{quality["unknown_exchange"]} mã chưa xác định sàn')
        if quality["unrecognized_exchange"]:
            warnings.append(
                f'{quality["unrecognized_exchange"]} mã có giá trị sàn không nhận diện được'
            )
        if quality["missing_industry"]:
            warnings.append(f'{quality["missing_industry"]} mã chưa có nhóm ngành')
        if quality["duplicate_symbols"]:
            warnings.append(f'{quality["duplicate_symbols"]} mã bị trùng')
        _universe_progress(
            "quality "
            f"valid={quality['valid_symbols']} "
            f"unknown_exchange={quality['unknown_exchange']} "
            f"missing_industry={quality['missing_industry']} "
            f"duplicates={quality['duplicate_symbols']}"
        )
        return {
            "ok": count > 0,
            "count": count,
            "provider": "vnstock",
            "quality": quality,
            "rejected": rejected,
            "deactivated_count": deactivated_count,
            "cancelled_queue_count": cancelled_queue_count,
            "warnings": warnings,
            "message": (
                f"Đã đồng bộ {count} mã từ Vnstock."
                + (f" Cảnh báo: {'; '.join(warnings)}." if warnings else "")
                if count else "Provider không trả danh sách mã."
            ),
        }
    except Exception as exc:
        elapsed = time.monotonic() - started
        _universe_progress(
            f"failed after {elapsed:.1f}s: {type(exc).__name__}: {exc}"
        )
        return {"ok": False, "code": "UNIVERSE_SYNC_FAILED", "message": str(exc)[:500]}

