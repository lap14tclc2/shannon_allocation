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
import time
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
PROVIDERS = ("tcbs", "cafef")


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
               ON CONFLICT(symbol) DO UPDATE SET exchange=excluded.exchange,
               company_name=COALESCE(excluded.company_name,securities.company_name),
               industry=COALESCE(excluded.industry,securities.industry),
               updated_at=excluded.updated_at""",
            (symbol, str(exchange or "UNKNOWN").upper(), company_name, industry, _now()),
        )


def list_securities(offset: int = 0, limit: int = 50, exchange: str | None = None) -> dict[str, Any]:
    _ensure()
    offset = max(0, int(offset))
    limit = min(200, max(1, int(limit)))
    with _schema_connection(FINANCE_SCHEMA) as db:
        if exchange and exchange.upper() in {"HOSE", "HNX", "UPCOM"}:
            rows = db.execute(
                "SELECT symbol, exchange, company_name, industry, updated_at FROM securities WHERE is_active=1 AND exchange=? ORDER BY symbol LIMIT ? OFFSET ?",
                (exchange.upper(), limit, offset),
            ).fetchall()
            total = db.execute("SELECT COUNT(*) AS count FROM securities WHERE is_active=1 AND exchange=?", (exchange.upper(),)).fetchone()["count"]
        else:
            rows = db.execute(
                "SELECT symbol, exchange, company_name, industry, updated_at FROM securities WHERE is_active=1 ORDER BY symbol LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            total = db.execute("SELECT COUNT(*) AS count FROM securities WHERE is_active=1").fetchone()["count"]
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
    return {"items": [{**dict(row), "documents": documents.get(row["symbol"], [])} for row in rows], "total": int(total), "offset": offset, "limit": limit}


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
    today = date.today()
    periods = [("FY", year, None, f"{year}-12-31") for year in range(today.year - 4, today.year)]
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
                for provider in PROVIDERS:
                    if provider == "tcbs":
                        endpoint = {
                            "FINANCIAL_STATEMENTS": "balancesheet",
                            "INCOME_STATEMENT": "incomestatement",
                            "CASH_FLOW": "cashflow",
                            "DIVIDEND": "dividend-payment-histories",
                        }[document_type]
                        url = (
                            f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/{endpoint}"
                            if document_type != "DIVIDEND"
                            else f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/company/{symbol}/{endpoint}"
                        )
                    elif document_type == "DIVIDEND":
                        url = f"https://s.cafef.vn/du-lieu.ashx?symbol={symbol}"
                    else:
                        segment = "IncSta" if document_type == "INCOME_STATEMENT" else ("BalSheet" if document_type == "FINANCIAL_STATEMENTS" else "CashFlow")
                        url = f"https://s.cafef.vn/bao-cao-tai-chinh/{symbol}/{segment}/{year}/{quarter or 4}/0/0/bctc.chn"
                    db.execute(
                        """INSERT INTO documents(
                           symbol, provider, document_type, period_type, fiscal_year,
                           fiscal_quarter, period_end, status, source_url, fetched_at
                        ) VALUES(?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(symbol, provider, document_type, period_type, fiscal_year, fiscal_quarter)
                        DO NOTHING""",
                        (symbol, provider, document_type, period_type, year, quarter,
                         period_end, "PENDING", url, _now()),
                    )


def _payload_rows(payload: str | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return []
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


def valuation_snapshot_from_catalog(symbol: str, market_price: float | None = None) -> dict[str, Any]:
    ticker = str(symbol).upper().strip()
    facts = get_canonical_facts(ticker)
    if not facts:
        return {"ok": False, "code": "FINANCE_DATA_MISSING", "message": "contact admin", "symbol": ticker}
    # Reconcile same-period facts across providers before valuation. A
    # material disagreement is unavailable rather than silently selecting a
    # provider, while identical observations remain safely interchangeable.
    grouped: dict[tuple[str, int, int | None], list[dict[str, Any]]] = {}
    for fact in facts:
        key = (str(fact["line_item_code"]), int(fact["fiscal_year"]), fact.get("fiscal_quarter"))
        grouped.setdefault(key, []).append(fact)
    conflicts = []
    for key, rows in grouped.items():
        values = [float(row["value"]) for row in rows if row.get("value") is not None]
        if len(values) > 1:
            baseline = values[0]
            if any(abs(value - baseline) > max(1.0, abs(baseline) * 0.001) for value in values[1:]):
                conflicts.append({"line_item_code": key[0], "fiscal_year": key[1], "fiscal_quarter": key[2]})
    if conflicts:
        return {
            "ok": False,
            "code": "FINANCE_DATA_CONFLICT",
            "message": "contact admin",
            "symbol": ticker,
            "conflicts": conflicts,
        }
    latest = {}
    for fact in facts:
        latest.setdefault(fact["line_item_code"], fact)
    missing = []
    if latest.get("IS.PROFIT.NET") is None:
        missing.append("net_income")
    if latest.get("IS.SHARES.OUTSTANDING") is None:
        missing.append("shares_outstanding")
    if market_price is None or float(market_price) <= 0:
        missing.append("market_price")
    if missing:
        return {"ok": False, "code": "FINANCE_DATA_INCOMPLETE", "message": "contact admin", "symbol": ticker, "missing": missing}
    with _schema_connection(FINANCE_SCHEMA) as db:
        security = db.execute(
            "SELECT company_name, industry, exchange FROM securities WHERE symbol=?",
            (ticker,),
        ).fetchone()
    profile = [dict(security)] if security else []
    return {
        "ok": True, "symbol": ticker, "provider": "finance_catalog",
        "fetched_at": latest["IS.PROFIT.NET"]["observed_at"],
        "fiscal_year": latest["IS.PROFIT.NET"]["fiscal_year"],
        "fiscal_quarter": latest["IS.PROFIT.NET"].get("fiscal_quarter"),
        "period_end": latest["IS.PROFIT.NET"].get("period_end"),
        "income_statement": [{"net_profit": latest["IS.PROFIT.NET"]["value"], "operating_profit": latest.get("IS.PROFIT.OPERATING", {}).get("value")}],
        "balance_sheet": [{"total_debt": latest.get("BS.DEBT.TOTAL", {}).get("value"), "cash": latest.get("BS.ASSETS.CASH_AND_EQUIVALENTS", {}).get("value")}],
        "cash_flow": [{"depreciation": latest.get("CF.OPERATING.DEPRECIATION", {}).get("value"), "capex": latest.get("CF.CAPEX", {}).get("value"), "operating_cash_flow": latest.get("CF.OPERATING.NET", {}).get("value")}],
        "ratios": [{"outstanding_shares": latest["IS.SHARES.OUTSTANDING"]["value"]}],
        "profile": profile, "prices": [{"close": market_price}],
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
               ON CONFLICT(symbol,provider,document_type,period_type,fiscal_year,fiscal_quarter)
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
        headers = {"Referer": "https://tcinvest.tcbs.com.vn/", "Origin": "https://tcinvest.tcbs.com.vn"}
    else:
        if document_type == "DIVIDEND":
            url = f"https://s.cafef.vn/du-lieu.ashx?symbol={symbol}"
        else:
            segment = "IncSta" if document_type == "INCOME_STATEMENT" else ("BalSheet" if document_type == "FINANCIAL_STATEMENTS" else "CashFlow")
            q = quarter or 4
            url = f"https://s.cafef.vn/bao-cao-tai-chinh/{symbol}/{segment}/{year}/{q}/0/0/bctc.chn"
        headers = {}
    try:
        status, payload = _url_json(url, headers=headers)
        if status < 200 or status >= 300:
            raise RuntimeError(f"HTTP {status}")
        _save_document(symbol, provider, document_type, period_type, year, quarter, period_end, url, "SUCCESS", payload, None, None, run_id)
        return True
    except Exception as exc:
        code = "PROVIDER_HTTP_ERROR" if isinstance(exc, urllib.error.HTTPError) else "PROVIDER_UNAVAILABLE"
        _save_document(symbol, provider, document_type, period_type, year, quarter, period_end, url, "FAILED", None, code, str(exc)[:500], run_id)
        return False


def enqueue_crawl_all(requested_by: int | None = None, exchange: str | None = None) -> dict[str, Any]:
    """Queue all active securities for an external worker; never crawls in request time."""
    try:
        _validate_crawl_runtime()
    except RuntimeError as exc:
        return {"ok": False, "code": "CRAWL_RUNTIME_INVALID", "message": str(exc), "queued": 0}
    _ensure()
    with _schema_connection(FINANCE_SCHEMA) as db:
        if exchange and exchange.upper() in {"HOSE", "HNX", "UPCOM"}:
            rows = db.execute("SELECT symbol FROM securities WHERE is_active=1 AND exchange=?", (exchange.upper(),)).fetchall()
        else:
            rows = db.execute("SELECT symbol FROM securities WHERE is_active=1").fetchall()
        queued = 0
        for row in rows:
            result = db.execute(
                """INSERT INTO crawl_queue(symbol, requested_by, status, requested_at)
                   VALUES(?,?,?,?)
                   ON CONFLICT DO NOTHING""",
                (row["symbol"], requested_by, "QUEUED", _now()),
            )
            queued += int(result.rowcount or 0)
    return {"ok": True, "queued": queued, "message": f"Đã xếp hàng {queued} mã cho external worker."}



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


def crawl_symbol(symbol: str, requested_by: int | None = None, *, retry_failed_only: bool = False) -> dict[str, Any]:
    _ensure()
    symbol = str(symbol).upper().strip()
    if not symbol:
        return {"ok": False, "code": "INVALID_SYMBOL"}
    try:
        _validate_crawl_runtime()
    except RuntimeError as exc:
        return {"ok": False, "code": "CRAWL_RUNTIME_INVALID", "message": str(exc)}
    ensure_required_documents(symbol)
    with _schema_connection(FINANCE_SCHEMA) as db:
        row = db.execute("INSERT INTO crawl_runs(requested_by,status,requested_at,total_symbols) VALUES(?,?,?,1) RETURNING id", (requested_by, "RUNNING", _now())).fetchone()
        run_id = int(row["id"])
    results = []
    periods = _periods()
    latest_fy = max((item[1] for item in periods if item[0] == "FY"), default=None)
    for period_type, year, quarter, period_end in periods:
        for document_type in REQUIRED_DOCUMENTS:
            if document_type == "DIVIDEND" and (period_type != "FY" or year != latest_fy):
                continue
            for provider in PROVIDERS:
                if retry_failed_only:
                    with _schema_connection(FINANCE_SCHEMA) as db:
                        existing = db.execute("SELECT status FROM documents WHERE symbol=? AND provider=? AND document_type=? AND period_type=? AND fiscal_year=? AND fiscal_quarter IS NOT DISTINCT FROM ?", (symbol, provider, document_type, period_type, year, quarter)).fetchone()
                    if existing and existing["status"] == "SUCCESS":
                        continue
                results.append(_fetch_provider(symbol, provider, document_type, period_type, year, quarter, period_end, run_id))
    success = sum(1 for item in results if item)
    with _schema_connection(FINANCE_SCHEMA) as db:
        db.execute("UPDATE crawl_runs SET status=?,finished_at=?,success_count=?,failure_count=? WHERE id=?", ("COMPLETED" if success else "FAILED", _now(), success, len(results)-success, run_id))
    return {"ok": bool(success), "run_id": run_id, "symbol": symbol, "success_count": success, "failure_count": len(results)-success}


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


def sync_universe() -> dict[str, Any]:
    """Populate the exchange universe from Vnstock on an external worker.

    Vercel remains read-only unless explicitly opted in, preventing serverless
    provider calls and filesystem/runtime failures.
    """
    try:
        _validate_crawl_runtime()
    except RuntimeError as exc:
        return {"ok": False, "code": "CRAWL_RUNTIME_INVALID", "message": str(exc)}
    try:
        from vnstock import Listing  # type: ignore
        listing = Listing()
        frame = None
        for method_name in ("all_symbols", "symbols_by_exchange"):
            method = getattr(listing, method_name, None)
            if not callable(method):
                continue
            try:
                frame = method()
                break
            except TypeError:
                frame = method(exchange="ALL")
                break
        rows = frame.to_dict("records") if hasattr(frame, "to_dict") else (frame or [])
        count = 0
        for row in rows:
            lowered = {str(k).lower().strip(): v for k, v in dict(row).items()}
            symbol = next((lowered.get(k) for k in ("symbol", "ticker", "code") if lowered.get(k)), None)
            exchange = next((lowered.get(k) for k in ("exchange", "floor", "com_group_code", "market") if lowered.get(k)), "UNKNOWN")
            name = next((lowered.get(k) for k in ("organ_name", "company_name", "name") if lowered.get(k)), None)
            industry = next((lowered.get(k) for k in ("industry", "industry_name", "icb_name3") if lowered.get(k)), None)
            if symbol:
                upsert_security(str(symbol), str(exchange), str(name) if name else None, str(industry) if industry else None)
                ensure_required_documents(str(symbol))
                count += 1
        return {"ok": count > 0, "count": count, "message": f"Đã đồng bộ {count} mã." if count else "Provider không trả danh sách mã."}
    except Exception as exc:
        return {"ok": False, "code": "UNIVERSE_SYNC_FAILED", "message": str(exc)[:500]}
