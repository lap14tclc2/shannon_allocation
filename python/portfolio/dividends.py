from __future__ import annotations

import hashlib
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
    dividend_type: str
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
        n = float(value)
        if n > 10_000_000_000:
            n /= 1000.0
        if n > 1_000_000_000:
            try:
                return datetime.fromtimestamp(n, tz=timezone.utc).date().isoformat()
            except Exception:
                return None
    text = str(value).strip()
    if not text:
        return None
    dotnet = re.search(r"/Date\((\d+)", text)
    if dotnet:
        return _iso_date(int(dotnet.group(1)))
    ymd = re.search(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", text)
    if ymd:
        try:
            return date(int(ymd.group(1)), int(ymd.group(2)), int(ymd.group(3))).isoformat()
        except ValueError:
            pass
    dmy = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b", text)
    if dmy:
        try:
            return date(int(dmy.group(3)), int(dmy.group(2)), int(dmy.group(1))).isoformat()
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
            text = value.strip().replace(" ", "")
            if "," in text and "." not in text:
                text = text.replace(",", ".")
            return float(text)
        return float(value)
    except Exception:
        return None


def _vendor_ratio(value: Any) -> float | None:
    n = _float(value)
    if n is None or n <= 0:
        return None
    if 1 < n <= 100:
        return n / 100.0
    return n


def _cash_from_title(title: str | None) -> float | None:
    if not title:
        return None
    text = title.lower().replace(".", "").replace(",", "")
    for pattern in (
        r"(\d+)\s*(?:đồng|vnd|đ)\s*/?\s*(?:cp|cổ phiếu|share)",
        r"(?:cổ tức|co tuc|cash)[^\d]{0,80}(\d+)\s*(?:đồng|vnd|đ)",
        r"\((\d+)\s*(?:đ|đồng|vnd)\s*/?\s*cp\)",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _stock_ratio_from_title(title: str | None) -> float | None:
    if not title:
        return None
    text = title.lower().replace(",", ".")
    # Prefer ratios that occur near stock/dividend wording. CafeF commonly uses 100:13.
    matches = list(re.finditer(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)", text))
    if matches:
        match = matches[-1]
        old, new = float(match.group(1)), float(match.group(2))
        return new / old if old > 0 else None
    percent = re.search(r"(?:cổ phiếu|co phieu|stock|tỷ lệ|ty le)[^\d]{0,30}(\d+(?:\.\d+)?)\s*%", text)
    if percent:
        return float(percent.group(1)) / 100.0
    generic = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if generic:
        return float(generic.group(1)) / 100.0
    return None


def _contains_dividend(text: str | None) -> bool:
    low = str(text or "").lower()
    return "cổ tức" in low or "co tuc" in low or "dividend" in low


def _row_text(row: dict[str, Any]) -> str:
    return " ".join(str(v) for v in row.values() if isinstance(v, (str, int, float)))


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _components_from_text(
    *, symbol: str, source: str, source_url: str, source_event_id: str | None,
    title: str, announcement_date: str | None, ex_date: str | None,
    record_date: str | None, payment_date: str | None,
    cash_direct: Any = None, ratio_direct: Any = None, raw: dict[str, Any] | None = None,
) -> list[DividendEvent]:
    low = title.lower()
    has_stock = any(token in low for token in ("cổ phiếu", "co phieu", "stock", "thưởng cp"))
    has_cash = any(token in low for token in ("bằng tiền", "tiền mặt", "tien mat", "cash", "đồng/cp", "đ/cp", " vnd")) or cash_direct not in (None, "")
    cash = _float(cash_direct)
    if cash is None or cash <= 0:
        cash = _cash_from_title(title)
    ratio = _vendor_ratio(ratio_direct)
    if ratio is None:
        ratio = _stock_ratio_from_title(title)
    out: list[DividendEvent] = []
    if has_cash or cash is not None:
        out.append(DividendEvent(
            symbol=symbol, dividend_type="CASH_DIVIDEND", source=source,
            source_event_id=source_event_id, title=title, announcement_date=announcement_date,
            ex_date=ex_date, record_date=record_date, payment_date=payment_date,
            cash_per_share=cash, source_url=source_url, raw=dict(raw or {}),
        ))
    if has_stock:
        out.append(DividendEvent(
            symbol=symbol, dividend_type="STOCK_DIVIDEND", source=source,
            source_event_id=source_event_id, title=title, announcement_date=announcement_date,
            ex_date=ex_date, record_date=record_date, payment_date=payment_date,
            stock_ratio=ratio, source_url=source_url, raw=dict(raw or {}),
        ))
    return out


def _generic_dividend_events(raw: dict[str, Any], *, symbol: str, source: str, source_url: str, start: str, end: str) -> list[DividendEvent]:
    text = _row_text(raw)
    if not _contains_dividend(text):
        return []
    row_symbol = str(_value_ci(raw, ("symbol", "ticker", "code", "stock_code", "stockCode")) or symbol).upper().strip()
    if row_symbol != symbol:
        return []
    title_value = _value_ci(raw, (
        "eventTitleVi", "eventTitle", "event_name", "eventName", "title", "name",
        "description", "content", "purpose", "reason",
    ))
    title = str(title_value).strip() if title_value not in (None, "") else text.strip()
    record_date = _iso_date(_value_ci(raw, ("recordDate", "lastRegistrationDate", "last_registration_date", "registrationDeadline", "ngay_dang_ky_cuoi_cung")))
    ex_date = _iso_date(_value_ci(raw, ("exrightDate", "exRightDate", "exDate", "registrationDate", "ex_right_date", "ngay_giao_dich_khong_huong_quyen")))
    payment_date = _iso_date(_value_ci(raw, ("payoutDate", "paymentDate", "executionDate", "payDate", "execution_date")))
    announcement_date = _iso_date(_value_ci(raw, ("publicDate", "publishDate", "announcementDate", "eventDate", "date", "createdDate")))
    event_date = record_date or ex_date or announcement_date or payment_date
    if not event_date or not (start <= event_date <= end):
        return []
    native_id = _value_ci(raw, ("eventID", "eventId", "event_id", "id", "eventCode", "event_code", "newsId"))
    return _components_from_text(
        symbol=symbol, source=source, source_url=source_url,
        source_event_id=str(native_id) if native_id not in (None, "") else None,
        title=title, announcement_date=announcement_date, ex_date=ex_date,
        record_date=record_date, payment_date=payment_date,
        cash_direct=_value_ci(raw, ("cashPerShare", "cash_per_share", "valuePerShare", "dividendValue", "cashDividend")),
        ratio_direct=_value_ci(raw, ("exerciseRatio", "stockRatio", "stock_ratio", "dividendRatio", "ratio")),
        raw=raw,
    )


def _dedupe(events: list[DividendEvent]) -> list[DividendEvent]:
    seen: set[tuple] = set()
    out: list[DividendEvent] = []
    for event in events:
        key = (
            event.source_event_id, event.dividend_type, event.record_date, event.ex_date,
            event.payment_date, round(event.cash_per_share or 0.0, 4),
            round(event.stock_ratio or 0.0, 8), event.title,
        )
        if key not in seen:
            seen.add(key)
            out.append(event)
    return out


class VpsDividendProvider:
    name = "vps_events"
    endpoint_template = "https://histdatafeed.vps.com.vn/company/events/{symbol}"

    def __init__(self, session=None, timeout: float = 20.0) -> None:
        self.session, self.timeout = session or requests, float(timeout)

    def health(self) -> dict:
        return {"provider":self.name,"available":True,"transport":"DIRECT_HTTPS_JSON","auth_required":False,"contract":"SCHEMA_TOLERANT"}

    def events(self, symbol: str, start: str, end: str) -> list[DividendEvent]:
        url = self.endpoint_template.format(symbol=symbol)
        response = self.session.get(url, headers={"Accept":"application/json,text/plain,*/*","User-Agent":"Mozilla/5.0 QPort/1.0","Referer":"https://vps.com.vn/"}, timeout=self.timeout)
        response.raise_for_status()
        out: list[DividendEvent] = []
        for raw in _walk_dicts(response.json()):
            out.extend(_generic_dividend_events(raw, symbol=symbol, source=self.name, source_url=url, start=start, end=end))
        return _dedupe(out)


class FireAntPublicContentProvider:
    name = "fireant_public"
    endpoint_template = "https://fireant.vn/top-symbols/content/symbols/{symbol}"

    def __init__(self, session=None, timeout: float = 20.0) -> None:
        self.session, self.timeout = session or requests, float(timeout)

    def health(self) -> dict:
        return {"provider":self.name,"available":True,"transport":"PUBLIC_WEB_BFF","auth_required":False,"contract":"BEST_EFFORT"}

    def events(self, symbol: str, start: str, end: str) -> list[DividendEvent]:
        url = self.endpoint_template.format(symbol=symbol)
        response = self.session.get(url, headers={"Accept":"application/json,text/html,*/*","User-Agent":"Mozilla/5.0 Chrome/151 QPort/1.0","Referer":f"https://fireant.vn/ma-chung-khoan/{symbol}"}, timeout=self.timeout)
        response.raise_for_status()
        try:
            payload = response.json()
        except Exception:
            payload = None
        out: list[DividendEvent] = []
        if payload is not None:
            for raw in _walk_dicts(payload):
                out.extend(_generic_dividend_events(raw, symbol=symbol, source=self.name, source_url=url, start=start, end=end))
            return _dedupe(out)
        raw_html = getattr(response, "text", "") or ""
        candidates = [html.unescape(re.sub(r"\s+", " ", x)).strip() for x in re.findall(r">([^<>]*(?:cổ tức|co tuc|dividend)[^<>]*)<", raw_html, re.I)]
        for index, title in enumerate(candidates):
            event_date = _iso_date(title)
            if not event_date or not (start <= event_date <= end):
                continue
            out.extend(_components_from_text(
                symbol=symbol, source=self.name, source_url=url, source_event_id=f"html-{index}-{event_date}",
                title=title, announcement_date=event_date, ex_date=None, record_date=None, payment_date=None,
                raw={"snippet":title},
            ))
        return _dedupe(out)


class CafeFDividendProvider:
    name = "cafef_public"
    endpoint_template = "https://cafef.vn/du-lieu/tin-doanh-nghiep/{symbol}/event.chn"

    def __init__(self, session=None, timeout: float = 20.0) -> None:
        self.session, self.timeout = session or requests, float(timeout)

    def health(self) -> dict:
        return {"provider":self.name,"available":True,"transport":"PUBLIC_HTML","auth_required":False,"contract":"TEXT_EVENT_PARSER"}

    @staticmethod
    def _gdkhq_date(text: str) -> str | None:
        match = re.search(r"(\d{1,2}[./-]\d{1,2}[./-]20\d{2})\s*,?\s*ngày\s+GDKHQ", text, re.I)
        return _iso_date(match.group(1)) if match else None

    def events(self, symbol: str, start: str, end: str) -> list[DividendEvent]:
        url = self.endpoint_template.format(symbol=symbol.lower())
        response = self.session.get(url, headers={"Accept":"text/html,application/xhtml+xml","User-Agent":"Mozilla/5.0 Chrome/151 QPort/1.0","Referer":"https://cafef.vn/du-lieu.chn"}, timeout=self.timeout)
        response.raise_for_status()
        raw_html = getattr(response, "text", "") or ""
        candidates = [html.unescape(re.sub(r"\s+", " ", x)).strip() for x in re.findall(r">([^<>]*(?:cổ tức|co tuc|dividend)[^<>]*)<", raw_html, re.I)]
        out: list[DividendEvent] = []
        for title in candidates:
            ex_date = self._gdkhq_date(title)
            date_candidates = re.findall(r"\d{1,2}[./-]\d{1,2}[./-]20\d{2}", title)
            announcement_date = _iso_date(date_candidates[0]) if date_candidates and not ex_date else None
            effective = ex_date or announcement_date
            if not effective or not (start <= effective <= end):
                continue
            digest = hashlib.sha256(f"{symbol}|{effective}|{title}".encode("utf-8")).hexdigest()[:20]
            out.extend(_components_from_text(
                symbol=symbol, source=self.name, source_url=url, source_event_id=digest,
                title=title, announcement_date=announcement_date, ex_date=ex_date,
                record_date=None, payment_date=None, raw={"snippet":title},
            ))
        return _dedupe(out)


class VietcapDividendProvider:
    name = "vci_iq"
    endpoint = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/events"

    def __init__(self, session=None, timeout: float = 20.0) -> None:
        self.session, self.timeout = session or requests, float(timeout)

    def health(self) -> dict:
        return {"provider":self.name,"available":True,"transport":"DIRECT_HTTPS_JSON","auth_required":"UNKNOWN_OR_PROVIDER_BLOCKED","priority":"LATE_FALLBACK"}

    def events(self, symbol: str, start: str, end: str) -> list[DividendEvent]:
        response = self.session.get(self.endpoint, params={"ticker":symbol,"pageSize":200,"page":0}, headers={"Accept":"application/json","User-Agent":"Mozilla/5.0 QPort/1.0"}, timeout=self.timeout)
        response.raise_for_status()
        rows = ((response.json() or {}).get("data") or {}).get("content") or []
        out: list[DividendEvent] = []
        for raw in rows:
            if not isinstance(raw, dict) or str(raw.get("ticker") or symbol).upper().strip() != symbol:
                continue
            title = str(raw.get("eventTitleVi") or raw.get("eventTitleEn") or "").strip()
            code = str(raw.get("eventCode") or "").upper().strip()
            if code not in {"DIV", "ISS"}:
                continue
            record_date, ex_date = _iso_date(raw.get("recordDate")), _iso_date(raw.get("exrightDate"))
            payment_date, announcement_date = _iso_date(raw.get("payoutDate")), _iso_date(raw.get("publicDate"))
            effective = record_date or ex_date or announcement_date or payment_date
            if effective and not (start <= effective <= end):
                continue
            if code == "DIV":
                # DIV is a cash component even if the title is terse.
                out.append(DividendEvent(
                    symbol=symbol, dividend_type="CASH_DIVIDEND", source=self.name,
                    source_event_id=str(raw.get("id")) if raw.get("id") not in (None, "") else None,
                    title=title or None, announcement_date=announcement_date, ex_date=ex_date,
                    record_date=record_date, payment_date=payment_date,
                    cash_per_share=_float(raw.get("valuePerShare")) or _cash_from_title(title),
                    source_url=self.endpoint, raw=dict(raw),
                ))
            if code == "ISS" and any(token in title.lower() for token in ("cổ tức", "co tuc", "dividend")):
                out.append(DividendEvent(
                    symbol=symbol, dividend_type="STOCK_DIVIDEND", source=self.name,
                    source_event_id=str(raw.get("id")) if raw.get("id") not in (None, "") else None,
                    title=title or None, announcement_date=announcement_date, ex_date=ex_date,
                    record_date=record_date, payment_date=payment_date,
                    stock_ratio=_vendor_ratio(raw.get("exerciseRatio")) or _stock_ratio_from_title(title),
                    source_url=self.endpoint, raw=dict(raw),
                ))
        return _dedupe(out)


class FireAntDividendProvider:
    name = "fireant"
    endpoint = "https://api.fireant.vn/events/search"

    def __init__(self, session=None, timeout: float = 20.0) -> None:
        self.session, self.timeout = session or requests, float(timeout)

    def health(self) -> dict:
        return {"provider":self.name,"available":True,"transport":"DIRECT_HTTPS_JSON","auth_required":True,"priority":"LATE_FALLBACK"}

    def events(self, symbol: str, start: str, end: str) -> list[DividendEvent]:
        response = self.session.get(self.endpoint, params={"symbol":symbol,"type":0,"orderBy":2,"startDate":f"{start}T00:00:00Z","endDate":f"{end}T23:59:59Z","offset":0,"limit":200}, headers={"Accept":"application/json","User-Agent":"Mozilla/5.0 QPort/1.0"}, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        rows = payload if isinstance(payload, list) else ((payload or {}).get("data") or [])
        if isinstance(rows, dict):
            rows = rows.get("content") or rows.get("items") or []
        out: list[DividendEvent] = []
        for raw in rows if isinstance(rows, list) else []:
            if not isinstance(raw, dict) or str(raw.get("symbol") or symbol).upper().strip() != symbol:
                continue
            event_type = int(raw.get("type") or 0)
            if event_type not in {1, 2}:
                continue
            title = str(raw.get("title") or raw.get("name") or "").strip()
            dtype = "CASH_DIVIDEND" if event_type == 1 else "STOCK_DIVIDEND"
            out.append(DividendEvent(
                symbol=symbol, dividend_type=dtype, source=self.name,
                source_event_id=str(raw.get("eventID")) if raw.get("eventID") not in (None, "") else None,
                title=title or None, ex_date=_iso_date(raw.get("registrationDate")),
                record_date=_iso_date(raw.get("recordDate")), payment_date=_iso_date(raw.get("executionDate")),
                cash_per_share=_cash_from_title(title) if dtype == "CASH_DIVIDEND" else None,
                stock_ratio=_stock_ratio_from_title(title) if dtype == "STOCK_DIVIDEND" else None,
                source_url=self.endpoint, raw=dict(raw),
            ))
        return _dedupe(out)


def default_dividend_providers() -> list[DividendProvider]:
    # Public/no-auth sources first. The two providers observed returning 403/401
    # in QPort runtime are deliberately late fallbacks.
    return [VpsDividendProvider(), CafeFDividendProvider(), FireAntPublicContentProvider(), VietcapDividendProvider(), FireAntDividendProvider()]


def _event_sort_key(event: DividendEvent) -> tuple[str, str, str]:
    effective = event.record_date or event.ex_date or event.announcement_date or event.payment_date or "0000-00-00"
    return (effective, event.announcement_date or "0000-00-00", event.source_event_id or "")


def _signature(event: DividendEvent) -> tuple:
    return (event.symbol, event.dividend_type, event.record_date, event.ex_date, event.payment_date, round(event.cash_per_share or 0.0,4), round(event.stock_ratio or 0.0,8))


class LatestDividendService:
    def __init__(self, providers: list[DividendProvider] | None = None, *, stop_on_first_data: bool | None = None) -> None:
        using_defaults = providers is None
        self.providers = providers or default_dividend_providers()
        self.stop_on_first_data = using_defaults if stop_on_first_data is None else bool(stop_on_first_data)

    def health(self) -> dict:
        return {"provider":"multi_source_dividend","strategy":"FIRST_PROVIDER_WITH_USABLE_DIVIDEND" if self.stop_on_first_data else "AGGREGATE_EVIDENCE","provider_order":[p.name for p in self.providers],"providers":[p.health() for p in self.providers]}

    def latest(self, symbol: str, *, years_back: int = 5, years_forward: int = 2) -> dict:
        symbol = str(symbol or "").upper().strip()
        if not TICKER_RE.fullmatch(symbol):
            raise DividendLookupError("Ticker must contain 2-10 uppercase letters/digits.")
        today = date.today()
        start = (today - timedelta(days=366 * max(1,int(years_back)))).isoformat()
        end = (today + timedelta(days=366 * max(0,int(years_forward)))).isoformat()
        events: list[DividendEvent] = []
        errors: list[dict] = []
        counts: dict[str,int] = {}
        attempts: list[dict] = []
        for provider in self.providers:
            try:
                rows = provider.events(symbol,start,end)
                counts[provider.name] = len(rows); events.extend(rows)
                attempts.append({"provider":provider.name,"status":"SUCCESS" if rows else "EMPTY","count":len(rows)})
                if rows and self.stop_on_first_data:
                    break
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                errors.append({"provider":provider.name,"error":error})
                attempts.append({"provider":provider.name,"status":"ERROR","count":0,"error":error})
        base = {"ok":True,"symbol":symbol,"source_counts":counts,"errors":errors,"provider_attempts":attempts,"provider_strategy":"FIRST_PROVIDER_WITH_USABLE_DIVIDEND" if self.stop_on_first_data else "AGGREGATE_EVIDENCE","lookback_start":start,"lookahead_end":end,"read_only":True}
        if not events:
            return {**base,"found":False,"latest":None,"latest_components":[]}
        canonical: dict[tuple,DividendEvent] = {}
        evidence: dict[tuple,list[DividendEvent]] = {}
        priority = {p.name:i for i,p in enumerate(self.providers)}
        for event in events:
            sig = _signature(event); evidence.setdefault(sig,[]).append(event)
            current = canonical.get(sig)
            if current is None or priority.get(event.source,999) < priority.get(current.source,999):
                canonical[sig] = event
        latest_date = max(_event_sort_key(event)[0] for event in canonical.values())
        latest_events = [event for event in canonical.values() if _event_sort_key(event)[0] == latest_date]
        latest_events.sort(key=lambda event: (0 if event.dividend_type == "CASH_DIVIDEND" else 1, event.source_event_id or ""))
        components = []
        for event in latest_events:
            sig = _signature(event); payload = event.as_dict()
            payload["evidence"] = [item.as_dict() for item in evidence.get(sig,[])]
            payload["cross_source_match"] = len({item.source for item in evidence.get(sig,[])}) > 1
            payload["effective_event_date"] = latest_date
            components.append(payload)
        return {**base,"found":True,"latest":components[0],"latest_components":components,"latest_event_date":latest_date,"retrieved_at":datetime.now(timezone.utc).isoformat(timespec="seconds")}
