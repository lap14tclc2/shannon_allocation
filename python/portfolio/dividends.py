from __future__ import annotations

import html
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Protocol

import requests

TICKER_RE = re.compile(r"^[A-Z0-9]{2,10}$")


class DividendLookupError(RuntimeError):
    pass


@dataclass(frozen=True)
class DividendEvent:
    symbol: str
    dividend_type: str  # CASH_DIVIDEND | STOCK_DIVIDEND
    source: str
    source_event_id: str | None = None
    title: str | None = None
    announcement_date: str | None = None
    ex_date: str | None = None
    record_date: str | None = None
    payment_date: str | None = None
    cash_per_share: float | None = None
    stock_ratio: float | None = None
    source_url: str | None = None
    raw: dict[str, Any] | None = None

    def as_dict(self) -> dict:
        row = asdict(self)
        row["stock_ratio_percent"] = self.stock_ratio * 100.0 if self.stock_ratio is not None else None
        return row


class DividendProvider(Protocol):
    name: str

    def events(self, symbol: str, start: str, end: str) -> list[DividendEvent]: ...
    def health(self) -> dict: ...


def _norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _value_ci(row: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    values = {_norm_key(k): v for k, v in row.items()}
    for alias in aliases:
        value = values.get(_norm_key(alias))
        if value not in (None, ""):
            return value
    return None


def _iso_date(value: Any) -> str | None:
    if value in (None, ""):
        return None

    if isinstance(value, (int, float)):
        number = float(value)
        if number > 10_000_000_000:
            number /= 1000.0
        if number > 1_000_000_000:
            try:
                return datetime.fromtimestamp(number, tz=timezone.utc).date().isoformat()
            except Exception:
                return None

    text = str(value).strip()
    if not text:
        return None

    dotnet = re.search(r"/Date\((\d+)", text)
    if dotnet:
        return _iso_date(int(dotnet.group(1)))

    iso_match = re.search(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", text)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))).isoformat()
        except ValueError:
            pass

    vn_match = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b", text)
    if vn_match:
        try:
            return date(int(vn_match.group(3)), int(vn_match.group(2)), int(vn_match.group(1))).isoformat()
        except ValueError:
            pass

    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except Exception:
        return None


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, str):
            cleaned = value.strip().replace(" ", "")
            if "," in cleaned and "." not in cleaned:
                cleaned = cleaned.replace(",", ".")
            return float(cleaned)
        return float(value)
    except Exception:
        return None


def _ratio(value: Any) -> float | None:
    number = _float(value)
    if number is None or number <= 0:
        return None
    if 1 < number <= 100:
        return number / 100.0
    return number


def _cash_from_title(title: str | None) -> float | None:
    if not title:
        return None
    normalized = title.lower().replace(".", "").replace(",", "")
    for pattern in (
        r"(\d+)\s*(?:đồng|vnd|đ)\s*/?\s*(?:cp|cổ phiếu|share)",
        r"(?:cổ tức|co tuc|cash)[^\d]{0,60}(\d+)\s*(?:đồng|vnd|đ)",
        r"\((\d+)\s*(?:đ|đồng|vnd)\s*/?\s*cp\)",
    ):
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _stock_ratio_from_title(title: str | None) -> float | None:
    if not title:
        return None
    text = title.lower().replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)", text)
    if match:
        old = float(match.group(1))
        new = float(match.group(2))
        return new / old if old > 0 else None
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if match:
        return float(match.group(1)) / 100.0
    return None


def _contains_dividend(text: str | None) -> bool:
    low = str(text or "").lower()
    return "cổ tức" in low or "co tuc" in low or "dividend" in low


def _contains_stock_dividend(title: str | None) -> bool:
    text = str(title or "").lower()
    return _contains_dividend(text) and (
        "cổ phiếu" in text or "co phieu" in text or "stock" in text
    )


def _row_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for value in row.values():
        if isinstance(value, (str, int, float)):
            parts.append(str(value))
    return " ".join(parts)


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _generic_dividend_event(
    raw: dict[str, Any],
    *,
    symbol: str,
    source: str,
    source_url: str,
    start: str,
    end: str,
) -> DividendEvent | None:
    text = _row_text(raw)
    if not _contains_dividend(text):
        return None

    row_symbol = str(
        _value_ci(raw, ("symbol", "ticker", "code", "stock_code", "stockCode"))
        or symbol
    ).upper().strip()
    if row_symbol != symbol:
        return None

    title_value = _value_ci(
        raw,
        (
            "eventTitleVi", "eventTitle", "event_name", "eventName",
            "title", "name", "description", "content", "purpose", "reason",
        ),
    )
    title = str(title_value).strip() if title_value not in (None, "") else text.strip() or None

    cash_direct = _value_ci(
        raw,
        ("cashPerShare", "cash_per_share", "valuePerShare", "dividendValue", "cashDividend"),
    )
    ratio_direct = _value_ci(
        raw,
        ("exerciseRatio", "stockRatio", "stock_ratio", "dividendRatio", "ratio"),
    )

    low = str(title or text).lower()
    stock_words = any(token in low for token in ("cổ phiếu", "co phieu", "stock"))
    cash_words = any(token in low for token in ("tiền", "tien", "cash", "đồng", " vnd", "đ/cp"))

    if stock_words:
        dtype = "STOCK_DIVIDEND"
    elif cash_words or cash_direct not in (None, ""):
        dtype = "CASH_DIVIDEND"
    else:
        return None

    record_date = _iso_date(
        _value_ci(
            raw,
            (
                "recordDate", "lastRegistrationDate", "last_registration_date",
                "registrationDeadline", "ngay_dang_ky_cuoi_cung",
            ),
        )
    )
    ex_date = _iso_date(
        _value_ci(
            raw,
            (
                "exrightDate", "exRightDate", "exDate", "registrationDate",
                "ex_right_date", "ngay_giao_dich_khong_huong_quyen",
            ),
        )
    )
    payment_date = _iso_date(
        _value_ci(
            raw,
            ("payoutDate", "paymentDate", "executionDate", "payDate", "execution_date"),
        )
    )
    announcement_date = _iso_date(
        _value_ci(
            raw,
            ("publicDate", "publishDate", "announcementDate", "eventDate", "date", "createdDate"),
        )
    )

    event_date = record_date or ex_date or announcement_date or payment_date
    if not event_date:
        return None
    if not (start <= event_date <= end):
        return None

    cash_per_share = None
    stock_ratio = None
    if dtype == "CASH_DIVIDEND":
        cash_per_share = _float(cash_direct)
        if cash_per_share is None or cash_per_share <= 0:
            cash_per_share = _cash_from_title(title)
    else:
        stock_ratio = _ratio(ratio_direct)
        if stock_ratio is None:
            stock_ratio = _stock_ratio_from_title(title)

    native_id = _value_ci(
        raw,
        ("eventID", "eventId", "event_id", "id", "eventCode", "event_code", "newsId"),
    )

    return DividendEvent(
        symbol=symbol,
        dividend_type=dtype,
        source=source,
        source_event_id=str(native_id) if native_id not in (None, "") else None,
        title=title,
        announcement_date=announcement_date,
        ex_date=ex_date,
        record_date=record_date,
        payment_date=payment_date,
        cash_per_share=cash_per_share,
        stock_ratio=stock_ratio,
        source_url=source_url,
        raw=dict(raw),
    )


def _dedupe(events: list[DividendEvent]) -> list[DividendEvent]:
    seen: set[tuple] = set()
    out: list[DividendEvent] = []
    for event in events:
        key = (
            event.source_event_id,
            event.dividend_type,
            event.record_date,
            event.ex_date,
            event.payment_date,
            round(event.cash_per_share or 0.0, 4),
            round(event.stock_ratio or 0.0, 8),
            event.title,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(event)
    return out


class VpsDividendProvider:
    """Public VPS company-events endpoint with schema-tolerant normalization."""

    name = "vps_events"
    endpoint_template = "https://histdatafeed.vps.com.vn/company/events/{symbol}"

    def __init__(self, session=None, timeout: float = 20.0) -> None:
        self.session = session or requests
        self.timeout = float(timeout)

    def health(self) -> dict:
        return {
            "provider": self.name,
            "available": True,
            "transport": "DIRECT_HTTPS_JSON",
            "auth_required": False,
            "contract": "SCHEMA_TOLERANT",
        }

    def events(self, symbol: str, start: str, end: str) -> list[DividendEvent]:
        url = self.endpoint_template.format(symbol=symbol)
        response = self.session.get(
            url,
            headers={
                "Accept": "application/json,text/plain,*/*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) QPort/1.0",
                "Referer": "https://vps.com.vn/",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        out: list[DividendEvent] = []
        for raw in _walk_dicts(payload):
            event = _generic_dividend_event(
                raw,
                symbol=symbol,
                source=self.name,
                source_url=url,
                start=start,
                end=end,
            )
            if event is not None:
                out.append(event)
        return _dedupe(out)


class FireAntPublicContentProvider:
    """Best-effort FireAnt public website/BFF fallback from the symbol page."""

    name = "fireant_public"
    endpoint_template = "https://fireant.vn/top-symbols/content/symbols/{symbol}"

    def __init__(self, session=None, timeout: float = 20.0) -> None:
        self.session = session or requests
        self.timeout = float(timeout)

    def health(self) -> dict:
        return {
            "provider": self.name,
            "available": True,
            "transport": "PUBLIC_WEB_BFF",
            "auth_required": False,
            "contract": "BEST_EFFORT",
        }

    def events(self, symbol: str, start: str, end: str) -> list[DividendEvent]:
        url = self.endpoint_template.format(symbol=symbol)
        response = self.session.get(
            url,
            headers={
                "Accept": "application/json,text/html,*/*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36",
                "Referer": f"https://fireant.vn/ma-chung-khoan/{symbol}",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

        try:
            payload = response.json()
        except Exception:
            payload = None

        out: list[DividendEvent] = []
        if payload is not None:
            for raw in _walk_dicts(payload):
                event = _generic_dividend_event(
                    raw,
                    symbol=symbol,
                    source=self.name,
                    source_url=url,
                    start=start,
                    end=end,
                )
                if event is not None:
                    out.append(event)
            return _dedupe(out)

        text = html.unescape(re.sub(r"<[^>]+>", " ", getattr(response, "text", "") or ""))
        text = re.sub(r"\s+", " ", text).strip()
        if not _contains_dividend(text):
            return []

        snippets = re.findall(
            r"[^.!?]{0,180}(?:cổ tức|co tuc|dividend)[^.!?]{0,220}",
            text,
            flags=re.IGNORECASE,
        )
        for index, snippet in enumerate(snippets):
            event_date = _iso_date(snippet)
            if not event_date or not (start <= event_date <= end):
                continue
            low = snippet.lower()
            if any(token in low for token in ("cổ phiếu", "co phieu", "stock")):
                dtype = "STOCK_DIVIDEND"
            elif any(token in low for token in ("tiền", "tien", "cash", "đồng", "vnd", "đ/cp")):
                dtype = "CASH_DIVIDEND"
            else:
                continue
            out.append(
                DividendEvent(
                    symbol=symbol,
                    dividend_type=dtype,
                    source=self.name,
                    source_event_id=f"html-{index}-{event_date}",
                    title=snippet.strip(),
                    announcement_date=event_date,
                    cash_per_share=_cash_from_title(snippet) if dtype == "CASH_DIVIDEND" else None,
                    stock_ratio=_stock_ratio_from_title(snippet) if dtype == "STOCK_DIVIDEND" else None,
                    source_url=url,
                    raw={"snippet": snippet.strip()},
                )
            )
        return _dedupe(out)


class VietcapDividendProvider:
    """Direct Vietcap IQ feed kept as a later fallback after observed HTTP 403."""

    name = "vci_iq"
    endpoint = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/events"

    def __init__(self, session=None, timeout: float = 20.0) -> None:
        self.session = session or requests
        self.timeout = float(timeout)

    def health(self) -> dict:
        return {
            "provider": self.name,
            "available": True,
            "transport": "DIRECT_HTTPS_JSON",
            "auth_required": "UNKNOWN_OR_PROVIDER_BLOCKED",
            "priority": "FALLBACK_ONLY",
        }

    def events(self, symbol: str, start: str, end: str) -> list[DividendEvent]:
        response = self.session.get(
            self.endpoint,
            params={"ticker": symbol, "pageSize": 200, "page": 0},
            headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0 QPort/1.0"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        content = ((payload or {}).get("data") or {}).get("content") or []
        out: list[DividendEvent] = []
        for raw in content:
            if not isinstance(raw, dict):
                continue
            event_symbol = str(raw.get("ticker") or symbol).upper().strip()
            if event_symbol != symbol:
                continue
            title = str(raw.get("eventTitleVi") or raw.get("eventTitleEn") or "").strip() or None
            code = str(raw.get("eventCode") or "").upper().strip()
            if code == "DIV":
                dtype = "CASH_DIVIDEND"
            elif code == "ISS" and _contains_stock_dividend(title):
                dtype = "STOCK_DIVIDEND"
            else:
                continue
            record_date = _iso_date(raw.get("recordDate"))
            ex_date = _iso_date(raw.get("exrightDate"))
            payment_date = _iso_date(raw.get("payoutDate"))
            announcement_date = _iso_date(raw.get("publicDate"))
            event_date = record_date or ex_date or announcement_date or payment_date
            if event_date and not (start <= event_date <= end):
                continue
            cash = _float(raw.get("valuePerShare")) if dtype == "CASH_DIVIDEND" else None
            if dtype == "CASH_DIVIDEND" and (cash is None or cash <= 0):
                cash = _cash_from_title(title)
            stock_ratio = _ratio(raw.get("exerciseRatio")) if dtype == "STOCK_DIVIDEND" else None
            if dtype == "STOCK_DIVIDEND" and stock_ratio is None:
                stock_ratio = _stock_ratio_from_title(title)
            out.append(
                DividendEvent(
                    symbol=symbol,
                    dividend_type=dtype,
                    source=self.name,
                    source_event_id=str(raw.get("id")) if raw.get("id") not in (None, "") else None,
                    title=title,
                    announcement_date=announcement_date,
                    ex_date=ex_date,
                    record_date=record_date,
                    payment_date=payment_date,
                    cash_per_share=cash,
                    stock_ratio=stock_ratio,
                    source_url=self.endpoint,
                    raw=dict(raw),
                )
            )
        return out


class FireAntDividendProvider:
    """FireAnt OAuth Events API kept as a later fallback/cross-check."""

    name = "fireant"
    endpoint = "https://api.fireant.vn/events/search"

    def __init__(self, session=None, timeout: float = 20.0) -> None:
        self.session = session or requests
        self.timeout = float(timeout)

    def health(self) -> dict:
        return {
            "provider": self.name,
            "available": True,
            "transport": "DIRECT_HTTPS_JSON",
            "auth_required": True,
            "priority": "FALLBACK_ONLY",
        }

    def events(self, symbol: str, start: str, end: str) -> list[DividendEvent]:
        response = self.session.get(
            self.endpoint,
            params={
                "symbol": symbol,
                "type": 0,
                "orderBy": 2,
                "startDate": f"{start}T00:00:00Z",
                "endDate": f"{end}T23:59:59Z",
                "offset": 0,
                "limit": 200,
            },
            headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0 QPort/1.0"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload if isinstance(payload, list) else ((payload or {}).get("data") or [])
        if isinstance(rows, dict):
            rows = rows.get("content") or rows.get("items") or []
        out: list[DividendEvent] = []
        for raw in rows if isinstance(rows, list) else []:
            if not isinstance(raw, dict):
                continue
            event_symbol = str(raw.get("symbol") or symbol).upper().strip()
            if event_symbol != symbol:
                continue
            event_type = int(raw.get("type") or 0)
            if event_type == 1:
                dtype = "CASH_DIVIDEND"
            elif event_type == 2:
                dtype = "STOCK_DIVIDEND"
            else:
                continue
            title = str(raw.get("title") or raw.get("name") or "").strip() or None
            out.append(
                DividendEvent(
                    symbol=symbol,
                    dividend_type=dtype,
                    source=self.name,
                    source_event_id=str(raw.get("eventID")) if raw.get("eventID") not in (None, "") else None,
                    title=title,
                    ex_date=_iso_date(raw.get("registrationDate")),
                    record_date=_iso_date(raw.get("recordDate")),
                    payment_date=_iso_date(raw.get("executionDate")),
                    cash_per_share=_cash_from_title(title) if dtype == "CASH_DIVIDEND" else None,
                    stock_ratio=_stock_ratio_from_title(title) if dtype == "STOCK_DIVIDEND" else None,
                    source_url=self.endpoint,
                    raw=dict(raw),
                )
            )
        return out


def _event_sort_key(event: DividendEvent) -> tuple[str, str, str]:
    effective = event.record_date or event.ex_date or event.announcement_date or event.payment_date or "0000-00-00"
    return (effective, event.announcement_date or "0000-00-00", event.source_event_id or "")


def _signature(event: DividendEvent) -> tuple:
    return (
        event.symbol,
        event.dividend_type,
        event.record_date,
        event.ex_date,
        event.payment_date,
        round(event.cash_per_share or 0.0, 4),
        round(event.stock_ratio or 0.0, 8),
    )


class LatestDividendService:
    """Read-only latest-dividend lookup with ordered provider failover."""

    def __init__(
        self,
        providers: list[DividendProvider] | None = None,
        *,
        stop_on_first_data: bool | None = None,
    ) -> None:
        using_defaults = providers is None
        self.providers = providers or [
            VpsDividendProvider(),
            FireAntPublicContentProvider(),
            VietcapDividendProvider(),
            FireAntDividendProvider(),
        ]
        self.stop_on_first_data = using_defaults if stop_on_first_data is None else bool(stop_on_first_data)

    def health(self) -> dict:
        return {
            "provider": "multi_source_dividend",
            "strategy": "FIRST_PROVIDER_WITH_USABLE_DIVIDEND" if self.stop_on_first_data else "AGGREGATE_EVIDENCE",
            "provider_order": [p.name for p in self.providers],
            "providers": [p.health() for p in self.providers],
        }

    def latest(self, symbol: str, *, years_back: int = 5, years_forward: int = 2) -> dict:
        symbol = str(symbol or "").upper().strip()
        if not TICKER_RE.fullmatch(symbol):
            raise DividendLookupError("Ticker must contain 2-10 uppercase letters/digits.")

        today = date.today()
        start = (today - timedelta(days=366 * max(1, int(years_back)))).isoformat()
        end = (today + timedelta(days=366 * max(0, int(years_forward)))).isoformat()
        events: list[DividendEvent] = []
        errors: list[dict] = []
        source_counts: dict[str, int] = {}
        provider_attempts: list[dict] = []

        for provider in self.providers:
            try:
                rows = provider.events(symbol, start, end)
                source_counts[provider.name] = len(rows)
                events.extend(rows)
                provider_attempts.append(
                    {"provider": provider.name, "status": "SUCCESS" if rows else "EMPTY", "count": len(rows)}
                )
                if rows and self.stop_on_first_data:
                    break
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                errors.append({"provider": provider.name, "error": error})
                provider_attempts.append({"provider": provider.name, "status": "ERROR", "count": 0, "error": error})

        base = {
            "ok": True,
            "symbol": symbol,
            "source_counts": source_counts,
            "errors": errors,
            "provider_attempts": provider_attempts,
            "provider_strategy": "FIRST_PROVIDER_WITH_USABLE_DIVIDEND" if self.stop_on_first_data else "AGGREGATE_EVIDENCE",
            "lookback_start": start,
            "lookahead_end": end,
            "read_only": True,
        }

        if not events:
            return {**base, "found": False, "latest": None}

        canonical: dict[tuple, DividendEvent] = {}
        evidence: dict[tuple, list[DividendEvent]] = {}
        provider_priority = {p.name: i for i, p in enumerate(self.providers)}
        for event in events:
            sig = _signature(event)
            evidence.setdefault(sig, []).append(event)
            current = canonical.get(sig)
            if current is None or provider_priority.get(event.source, 999) < provider_priority.get(current.source, 999):
                canonical[sig] = event

        latest = max(canonical.values(), key=_event_sort_key)
        sig = _signature(latest)
        latest_payload = latest.as_dict()
        latest_payload["evidence"] = [item.as_dict() for item in evidence.get(sig, [])]
        latest_payload["cross_source_match"] = len({item.source for item in evidence.get(sig, [])}) > 1
        latest_payload["effective_event_date"] = _event_sort_key(latest)[0]

        return {
            **base,
            "found": True,
            "latest": latest_payload,
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
