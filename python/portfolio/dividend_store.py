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


def ensure_dividend_schema(store) -> None:
    """Create the provider-cache schema inside the existing QPort SQLite DB.

    QPort already stores ledger, prices, snapshots and operational controls in
    SQLite. These tables close the remaining persistence gap for provider-backed
    dividend information. A fetch-state row is kept even when a provider returns
    zero events so normal dashboard reads do not repeatedly call the network.
    """
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
        # Defensive cleanup for any partially-written legacy/cache rows. The
        # unique event_key prevents duplicate canonical events going forward.
        db.execute(
            "DELETE FROM dividend_events WHERE symbol = '' OR dividend_type NOT IN ('CASH_DIVIDEND','STOCK_DIVIDEND')"
        )


class SqliteDividendService:
    """DB-first dividend history with provider fallback.

    Normal reads are SQLite-only once a symbol has a fetch-state row. Providers
    are contacted only on a cache miss or when ``force_refresh=True``. Manual
    refresh therefore remains available without making every dashboard render a
    network operation.
    """

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
        self.stop_on_first_data = using_defaults if stop_on_first_data is None else bool(stop_on_first_data)
        ensure_dividend_schema(store)

    @property
    def provider_strategy(self) -> str:
        return "FIRST_PROVIDER_WITH_USABLE_DIVIDEND" if self.stop_on_first_data else "AGGREGATE_EVIDENCE"

    def health(self) -> dict:
        return {
            "provider": "sqlite_cached_multi_source_dividend",
            "strategy": "SQLITE_FIRST_PROVIDER_ON_CACHE_MISS",
            "provider_strategy": self.provider_strategy,
            "provider_order": [p.name for p in self.providers],
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
            row = db.execute(
                "SELECT * FROM dividend_fetch_state WHERE symbol = ?",
                (symbol,),
            ).fetchone()
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
        return out

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
                    symbol,
                    fetched_at,
                    start,
                    end,
                    self.provider_strategy,
                    _json(counts),
                    _json(errors),
                    _json(attempts),
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
                        _event_key(event),
                        event.symbol,
                        event.dividend_type,
                        effective,
                        event.source,
                        event.source_event_id,
                        event.title,
                        event.announcement_date,
                        event.ex_date,
                        event.record_date,
                        event.payment_date,
                        event.cash_per_share,
                        event.stock_ratio,
                        event.source_url,
                        _json(evidence_rows),
                        1 if len({item.source for item in evidence.get(sig, [])}) > 1 else 0,
                        now,
                        now,
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
                attempts.append({"provider": provider.name, "status": "ERROR", "count": 0, "error": error})

        canonical: dict[tuple, DividendEvent] = {}
        evidence: dict[tuple, list[DividendEvent]] = {}
        priority = {p.name: i for i, p in enumerate(self.providers)}
        for event in events:
            sig = _signature(event)
            evidence.setdefault(sig, []).append(event)
            current = canonical.get(sig)
            if current is None or priority.get(event.source, 999) < priority.get(current.source, 999):
                canonical[sig] = event
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
        latest_components = [row for row in events if row["effective_event_date"] == latest_date] if latest_date else []
        return {
            "ok": True,
            "symbol": symbol,
            "found": bool(events),
            "latest": latest_components[0] if latest_components else None,
            "latest_components": latest_components,
            "latest_event_date": latest_date,
            "events": events,
            "event_count": len(events),
            "source_counts": source_counts,
            "errors": errors,
            "provider_attempts": attempts,
            "provider_strategy": (state or {}).get("provider_strategy") or self.provider_strategy,
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
            return self._response(symbol, origin="SQLITE_CACHE", state=state, start=start, end=end)

        self._fetch_from_providers(symbol, start, end)
        state = self._fetch_state(symbol)
        return self._response(symbol, origin="PROVIDER_REFRESH", state=state, start=start, end=end)

    def latest(self, symbol: str, *, force_refresh: bool = False) -> dict:
        return self.history(symbol, force_refresh=force_refresh)
