from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone

from .dividends import (
    DividendEvent,
    DividendLookupError,
    DividendProvider,
    TICKER_RE,
    _event_sort_key,
    _signature,
    default_dividend_providers,
)

VIETNAM_PAR_VALUE_VND = 10_000.0
EVENT_DATE_TOLERANCE_DAYS = 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _loads(value, fallback):
    try:
        return json.loads(value) if value not in (None, "") else fallback
    except Exception:
        return fallback


def _event_key(event: DividendEvent) -> str:
    payload = _json(_signature(event))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _row_dates(row: dict) -> set[str]:
    return {
        str(value)
        for value in (
            row.get("effective_event_date"),
            row.get("announcement_date"),
            row.get("ex_date"),
            row.get("record_date"),
            row.get("payment_date"),
        )
        if value
    }


def _date_distance_days(a, b) -> int | None:
    if not a or not b:
        return None
    try:
        return abs((date.fromisoformat(str(a)[:10]) - date.fromisoformat(str(b)[:10])).days)
    except (TypeError, ValueError):
        return None


def _dates_close(a, b, tolerance: int = EVENT_DATE_TOLERANCE_DAYS) -> bool:
    distance = _date_distance_days(a, b)
    return distance is not None and distance <= tolerance


def _economic_value_matches(a: dict, b: dict) -> bool:
    if a.get("dividend_type") == "CASH_DIVIDEND":
        av, bv = a.get("cash_per_share"), b.get("cash_per_share")
        if av not in (None, "") and bv not in (None, ""):
            return abs(float(av) - float(bv)) <= max(1.0, abs(float(av)) * 0.001)
    if a.get("dividend_type") == "STOCK_DIVIDEND":
        av, bv = a.get("stock_ratio"), b.get("stock_ratio")
        if av not in (None, "") and bv not in (None, ""):
            return abs(float(av) - float(bv)) <= 1e-6
    return True


def _same_dividend_family(a: dict, b: dict) -> bool:
    """Match two components to the same corporate-action family.

    Provider feeds disagree on which date is the event date and can differ by a
    day because one reports ex-date while another reports record-date. Exact
    source IDs therefore cannot be the identity of a dividend event.
    """
    if str(a.get("symbol") or "").upper() != str(b.get("symbol") or "").upper():
        return False

    source_id_a, source_id_b = a.get("source_event_id"), b.get("source_event_id")
    if source_id_a and source_id_b and source_id_a == source_id_b and a.get("source") == b.get("source"):
        return True

    dates_a, dates_b = _row_dates(a), _row_dates(b)
    if dates_a & dates_b:
        return True

    # Same semantic dates are strong evidence even if timezone/provider
    # normalization shifts the date by one or two days.
    for field in ("ex_date", "record_date", "payment_date"):
        if _dates_close(a.get(field), b.get(field)):
            return True

    # Providers often expose record-date as their effective date while another
    # provider exposes ex-date. Keep this fallback deliberately tight.
    if _dates_close(a.get("effective_event_date"), b.get("effective_event_date")):
        return True

    return False


def _same_economic_event(a: dict, b: dict) -> bool:
    """Provider-independent identity for one cash or stock dividend component."""
    if str(a.get("symbol") or "").upper() != str(b.get("symbol") or "").upper():
        return False
    if a.get("dividend_type") != b.get("dividend_type"):
        return False
    if not _economic_value_matches(a, b):
        return False
    return _same_dividend_family(a, b)


def _evidence_stub(row: dict) -> dict:
    return {
        key: row.get(key)
        for key in (
            "source", "source_event_id", "title", "effective_event_date",
            "announcement_date", "ex_date", "record_date", "payment_date",
            "cash_per_share", "stock_ratio", "source_url",
        )
        if row.get(key) not in (None, "")
    }


def _merge_cached_row(primary: dict, other: dict) -> dict:
    merged = dict(primary)
    for key in (
        "title", "announcement_date", "ex_date", "record_date", "payment_date",
        "cash_per_share", "stock_ratio", "stock_ratio_percent", "source_url",
    ):
        if merged.get(key) in (None, "", 0) and other.get(key) not in (None, ""):
            merged[key] = other[key]

    evidence = list(merged.get("evidence") or [])
    for item in list(other.get("evidence") or []) + [_evidence_stub(other)]:
        if item and item not in evidence:
            evidence.append(item)
    merged["evidence"] = evidence
    merged["cross_source_match"] = bool(
        merged.get("cross_source_match")
        or other.get("cross_source_match")
        or primary.get("source") != other.get("source")
    )
    merged["duplicate_sources"] = sorted({
        str(source)
        for source in (
            primary.get("source"),
            other.get("source"),
            *(item.get("source") for item in evidence if isinstance(item, dict)),
        )
        if source
    })
    return merged


def _suppress_cash_percent_stock_artifacts(rows: list[dict]) -> list[dict]:
    """Remove a common schema-tolerant parser artifact.

    Some generic provider rows expose the cash rate in a field called ``ratio``.
    A combined announcement such as "7% cash + 13% stock" can therefore produce
    stock rows 7% and 13%. When a stock ratio equals cash-per-share/par-value and
    the same event family also contains another distinct stock ratio, the matching
    cash-percent stock row is treated as an artifact.
    """
    cash_rows = [row for row in rows if row.get("dividend_type") == "CASH_DIVIDEND"]
    stock_rows = [row for row in rows if row.get("dividend_type") == "STOCK_DIVIDEND"]
    suppressed_ids: set[int] = set()

    for stock in stock_rows:
        stock_ratio = stock.get("stock_ratio")
        if stock_ratio in (None, ""):
            continue
        stock_ratio = float(stock_ratio)
        for cash in cash_rows:
            cash_per_share = cash.get("cash_per_share")
            if cash_per_share in (None, "") or not _same_dividend_family(stock, cash):
                continue
            cash_ratio = float(cash_per_share) / VIETNAM_PAR_VALUE_VND
            if abs(stock_ratio - cash_ratio) > 1e-6:
                continue

            # Do not suppress a genuine only-stock component. Require another
            # distinct stock ratio in the same family, e.g. real 13% beside the
            # spurious 7% derived from a 700 VND cash dividend.
            distinct_sibling = any(
                sibling is not stock
                and sibling.get("stock_ratio") not in (None, "")
                and abs(float(sibling.get("stock_ratio")) - stock_ratio) > 1e-6
                and _same_dividend_family(stock, sibling)
                for sibling in stock_rows
            )
            if not distinct_sibling:
                continue

            same_native_event = bool(
                stock.get("source") == cash.get("source")
                and stock.get("source_event_id")
                and stock.get("source_event_id") == cash.get("source_event_id")
            )
            same_title = bool(stock.get("title") and stock.get("title") == cash.get("title"))
            if same_native_event or same_title or stock.get("source") == cash.get("source"):
                suppressed_ids.add(id(stock))
                break

    return [row for row in rows if id(row) not in suppressed_ids]


def ensure_dividend_schema(store) -> None:
    """Create the provider-cache schema inside the existing QPort SQLite DB."""
    with store.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS dividend_events (
                event_key TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                dividend_type TEXT NOT NULL,
                effective_event_date TEXT NOT NULL,
                source TEXT NOT NULL,
                source_event_id TEXT,
                title TEXT,
                announcement_date TEXT,
                ex_date TEXT,
                record_date TEXT,
                payment_date TEXT,
                cash_per_share REAL,
                stock_ratio REAL,
                source_url TEXT,
                evidence_json TEXT NOT NULL DEFAULT '[]',
                cross_source_match INTEGER NOT NULL DEFAULT 0,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_dividend_events_symbol_date
                ON dividend_events(symbol, effective_event_date DESC, dividend_type);

            CREATE TABLE IF NOT EXISTS dividend_fetch_state (
                symbol TEXT PRIMARY KEY,
                fetched_at TEXT NOT NULL,
                lookback_start TEXT NOT NULL,
                lookahead_end TEXT NOT NULL,
                provider_strategy TEXT NOT NULL,
                source_counts_json TEXT NOT NULL DEFAULT '{}',
                errors_json TEXT NOT NULL DEFAULT '[]',
                provider_attempts_json TEXT NOT NULL DEFAULT '[]'
            );
            """
        )
        db.execute(
            "DELETE FROM dividend_events WHERE symbol = '' OR dividend_type NOT IN ('CASH_DIVIDEND','STOCK_DIVIDEND')"
        )


class SqliteDividendService:
    """DB-first dividend history with canonical provider-independent events."""

    def __init__(
        self,
        store,
        providers: list[DividendProvider] | None = None,
        *,
        stop_on_first_data: bool | None = None,
    ) -> None:
        using_defaults = providers is None
        self.store = store
        self.providers = providers or default_dividend_providers()
        # Normal QPort refreshes stop after the first usable provider. Historical
        # cache rows are still event-level canonicalized so older multi-source
        # data cannot leak duplicate rows into the UI.
        self.stop_on_first_data = True if using_defaults else (
            False if stop_on_first_data is None else bool(stop_on_first_data)
        )
        self.single_source_runtime = using_defaults
        ensure_dividend_schema(store)

    @property
    def provider_strategy(self) -> str:
        return "FIRST_PROVIDER_WITH_USABLE_DIVIDEND" if self.stop_on_first_data else "AGGREGATE_EVIDENCE"

    def health(self) -> dict:
        return {
            "provider": "sqlite_cached_canonical_dividend",
            "strategy": "SQLITE_FIRST_PROVIDER_ON_CACHE_MISS",
            "provider_strategy": self.provider_strategy,
            "provider_order": [p.name for p in self.providers],
            "deduplication": "CANONICAL_EVENT_FAMILY_PLUS_PARSER_ARTIFACT_SUPPRESSION",
            "providers": [p.health() for p in self.providers],
            "persistence": "SQLITE",
        }

    def _validate_symbol(self, symbol: str) -> str:
        symbol = str(symbol or "").upper().strip()
        if not TICKER_RE.fullmatch(symbol):
            raise DividendLookupError("Ticker must contain 2-10 uppercase letters/digits.")
        return symbol

    def _fetch_state(self, symbol: str) -> dict | None:
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM dividend_fetch_state WHERE symbol = ?", (symbol,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["source_counts"] = _loads(item.pop("source_counts_json", "{}"), {})
        item["errors"] = _loads(item.pop("errors_json", "[]"), [])
        item["provider_attempts"] = _loads(item.pop("provider_attempts_json", "[]"), [])
        return item

    def _cached_events(self, symbol: str) -> list[dict]:
        with self.store.connect() as db:
            rows = db.execute(
                """
                SELECT * FROM dividend_events
                WHERE symbol = ?
                ORDER BY effective_event_date DESC,
                         CASE dividend_type WHEN 'CASH_DIVIDEND' THEN 0 ELSE 1 END,
                         source_event_id DESC
                """,
                (symbol,),
            ).fetchall()
        out: list[dict] = []
        for row in rows:
            item = dict(row)
            item["cross_source_match"] = bool(item.get("cross_source_match"))
            item["evidence"] = _loads(item.pop("evidence_json", "[]"), [])
            item["stock_ratio_percent"] = (
                float(item["stock_ratio"]) * 100.0 if item.get("stock_ratio") is not None else None
            )
            out.append(item)

        if not out:
            return out

        # First remove a known parser artifact, then merge provider rows by the
        # economics of the event rather than by provider-native IDs.
        out = _suppress_cash_percent_stock_artifacts(out)
        priority = {p.name: i for i, p in enumerate(self.providers)}
        canonical: list[dict] = []
        for row in out:
            duplicate_index = next((
                i for i, current in enumerate(canonical)
                if _same_economic_event(current, row)
            ), None)
            if duplicate_index is None:
                row = dict(row)
                row["duplicate_sources"] = [row.get("source")] if row.get("source") else []
                canonical.append(row)
            else:
                current = canonical[duplicate_index]
                current_priority = priority.get(current.get("source"), 999)
                row_priority = priority.get(row.get("source"), 999)
                if row_priority < current_priority:
                    canonical[duplicate_index] = _merge_cached_row(row, current)
                else:
                    canonical[duplicate_index] = _merge_cached_row(current, row)

        canonical.sort(
            key=lambda row: (
                row.get("effective_event_date") or "0000-00-00",
                1 if row.get("dividend_type") == "CASH_DIVIDEND" else 0,
                row.get("source_event_id") or "",
            ),
            reverse=True,
        )
        return canonical

    def _write_fetch_state(
        self,
        symbol: str,
        *,
        start: str,
        end: str,
        counts: dict,
        errors: list,
        attempts: list,
    ) -> str:
        fetched_at = _now()
        with self.store.connect() as db:
            db.execute(
                """
                INSERT INTO dividend_fetch_state(
                    symbol,fetched_at,lookback_start,lookahead_end,provider_strategy,
                    source_counts_json,errors_json,provider_attempts_json
                ) VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(symbol) DO UPDATE SET
                    fetched_at=excluded.fetched_at,
                    lookback_start=excluded.lookback_start,
                    lookahead_end=excluded.lookahead_end,
                    provider_strategy=excluded.provider_strategy,
                    source_counts_json=excluded.source_counts_json,
                    errors_json=excluded.errors_json,
                    provider_attempts_json=excluded.provider_attempts_json
                """,
                (
                    symbol, fetched_at, start, end, self.provider_strategy,
                    _json(counts), _json(errors), _json(attempts),
                ),
            )
        return fetched_at

    def _persist_events(self, canonical: dict[tuple, DividendEvent], evidence: dict[tuple, list[DividendEvent]]) -> None:
        if not canonical:
            return
        now = _now()
        with self.store.connect() as db:
            for sig, event in canonical.items():
                evidence_rows = [item.as_dict() for item in evidence.get(sig, [])]
                effective = _event_sort_key(event)[0]
                db.execute(
                    """
                    INSERT INTO dividend_events(
                        event_key,symbol,dividend_type,effective_event_date,source,
                        source_event_id,title,announcement_date,ex_date,record_date,
                        payment_date,cash_per_share,stock_ratio,source_url,evidence_json,
                        cross_source_match,first_seen_at,last_seen_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(event_key) DO UPDATE SET
                        source=excluded.source,
                        source_event_id=excluded.source_event_id,
                        title=COALESCE(excluded.title,dividend_events.title),
                        announcement_date=COALESCE(excluded.announcement_date,dividend_events.announcement_date),
                        ex_date=COALESCE(excluded.ex_date,dividend_events.ex_date),
                        record_date=COALESCE(excluded.record_date,dividend_events.record_date),
                        payment_date=COALESCE(excluded.payment_date,dividend_events.payment_date),
                        cash_per_share=COALESCE(excluded.cash_per_share,dividend_events.cash_per_share),
                        stock_ratio=COALESCE(excluded.stock_ratio,dividend_events.stock_ratio),
                        source_url=COALESCE(excluded.source_url,dividend_events.source_url),
                        evidence_json=excluded.evidence_json,
                        cross_source_match=excluded.cross_source_match,
                        last_seen_at=excluded.last_seen_at
                    """,
                    (
                        _event_key(event), event.symbol, event.dividend_type, effective,
                        event.source, event.source_event_id, event.title, event.announcement_date,
                        event.ex_date, event.record_date, event.payment_date, event.cash_per_share,
                        event.stock_ratio, event.source_url, _json(evidence_rows),
                        1 if len({item.source for item in evidence.get(sig, [])}) > 1 else 0,
                        now, now,
                    ),
                )

    def _fetch_from_providers(self, symbol: str, start: str, end: str) -> dict:
        events: list[DividendEvent] = []
        errors: list[dict] = []
        counts: dict[str, int] = {}
        attempts: list[dict] = []
        for provider in self.providers:
            try:
                rows = provider.events(symbol, start, end)
                counts[provider.name] = len(rows)
                events.extend(rows)
                attempts.append({
                    "provider": provider.name,
                    "status": "SUCCESS" if rows else "EMPTY",
                    "count": len(rows),
                })
                if rows and self.stop_on_first_data:
                    break
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                errors.append({"provider": provider.name, "error": error})
                attempts.append({
                    "provider": provider.name,
                    "status": "ERROR",
                    "count": 0,
                    "error": error,
                })

        canonical: dict[tuple, DividendEvent] = {}
        evidence: dict[tuple, list[DividendEvent]] = {}
        priority = {p.name: i for i, p in enumerate(self.providers)}
        for event in events:
            sig = _signature(event)
            evidence.setdefault(sig, []).append(event)
            current = canonical.get(sig)
            if current is None or priority.get(event.source, 999) < priority.get(current.source, 999):
                canonical[sig] = event

        # A successful normal refresh replaces stale multi-provider cache rows.
        # Provider failures never destroy the last good cache.
        if canonical and self.single_source_runtime:
            with self.store.connect() as db:
                db.execute("DELETE FROM dividend_events WHERE symbol = ?", (symbol,))
        self._persist_events(canonical, evidence)
        fetched_at = self._write_fetch_state(
            symbol,
            start=start,
            end=end,
            counts=counts,
            errors=errors,
            attempts=attempts,
        )
        return {
            "source_counts": counts,
            "errors": errors,
            "provider_attempts": attempts,
            "fetched_at": fetched_at,
        }

    def _response(self, symbol: str, *, origin: str, state: dict | None, start: str, end: str) -> dict:
        events = self._cached_events(symbol)
        source_counts = (state or {}).get("source_counts") or {}
        errors = (state or {}).get("errors") or []
        attempts = (state or {}).get("provider_attempts") or []
        latest_date = events[0]["effective_event_date"] if events else None
        latest_components = [
            row for row in events
            if row["effective_event_date"] == latest_date
        ] if latest_date else []
        canonical_sources = sorted({row.get("source") for row in events if row.get("source")})
        canonical_source = canonical_sources[0] if len(canonical_sources) == 1 else (
            "MIXED_FALLBACK_CANONICAL" if canonical_sources else None
        )
        return {
            "ok": True,
            "symbol": symbol,
            "found": bool(events),
            "latest": latest_components[0] if latest_components else None,
            "latest_components": latest_components,
            "latest_event_date": latest_date,
            "events": events,
            "event_count": len(events),
            "canonical_source": canonical_source,
            "canonical_sources": canonical_sources,
            "deduplication_policy": "CANONICAL_EVENT_FAMILY_PLUS_PARSER_ARTIFACT_SUPPRESSION",
            "source_counts": source_counts,
            "errors": errors,
            "provider_attempts": attempts,
            "provider_strategy": self.provider_strategy,
            "lookback_start": (state or {}).get("lookback_start") or start,
            "lookahead_end": (state or {}).get("lookahead_end") or end,
            "retrieved_at": _now(),
            "cached_at": (state or {}).get("fetched_at"),
            "data_origin": origin,
            "cache_hit": origin == "SQLITE_CACHE",
            "persistence": "SQLITE",
            "read_only": True,
        }

    def history(
        self,
        symbol: str,
        *,
        force_refresh: bool = False,
        years_back: int = 20,
        years_forward: int = 2,
    ) -> dict:
        symbol = self._validate_symbol(symbol)
        today = date.today()
        start = (today - timedelta(days=366 * max(1, int(years_back)))).isoformat()
        end = (today + timedelta(days=366 * max(0, int(years_forward)))).isoformat()
        state = self._fetch_state(symbol)
        if state is not None and not force_refresh:
            return self._response(
                symbol, origin="SQLITE_CACHE", state=state, start=start, end=end,
            )

        self._fetch_from_providers(symbol, start, end)
        state = self._fetch_state(symbol)
        return self._response(
            symbol, origin="PROVIDER_REFRESH", state=state, start=start, end=end,
        )

    def latest(self, symbol: str, *, force_refresh: bool = False) -> dict:
        return self.history(symbol, force_refresh=force_refresh)
