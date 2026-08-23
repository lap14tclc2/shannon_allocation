from __future__ import annotations

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


def _iso_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
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
        return float(value)
    except Exception:
        return None


def _ratio(value: Any) -> float | None:
    number = _float(value)
    if number is None or number <= 0:
        return None
    # Vendor feeds normally expose 0.15 for 15%. Be defensive for feeds using 15.
    if 1 < number <= 100:
        return number / 100.0
    return number


def _cash_from_title(title: str | None) -> float | None:
    if not title:
        return None
    normalized = title.lower().replace(".", "").replace(",", "")
    for pattern in (
        r"(\d+)\s*(?:đồng|vnd)\s*/\s*(?:cp|cổ phiếu|share)",
        r"(?:cổ tức|co tuc|cash)[^\d]{0,40}(\d+)\s*(?:đồng|vnd)",
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


def _contains_stock_dividend(title: str | None) -> bool:
    text = str(title or "").lower()
    return ("cổ tức" in text or "co tuc" in text or "dividend" in text) and (
        "cổ phiếu" in text or "co phieu" in text or "stock" in text
    )


class VietcapDividendProvider:
    """Direct Vietcap IQ corporate-action feed; no vnstock package is required."""

    name = "vci_iq"
    endpoint = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/events"

    def __init__(self, session=None, timeout: float = 20.0) -> None:
        self.session = session or requests
        self.timeout = float(timeout)

    def health(self) -> dict:
        return {"provider": self.name, "available": True, "transport": "DIRECT_HTTPS_JSON", "auth_required": False}

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
    """FireAnt documented Events API used as an independent fallback/cross-check."""

    name = "fireant"
    endpoint = "https://api.fireant.vn/events/search"

    def __init__(self, session=None, timeout: float = 20.0) -> None:
        self.session = session or requests
        self.timeout = float(timeout)

    def health(self) -> dict:
        return {"provider": self.name, "available": True, "transport": "DIRECT_HTTPS_JSON", "auth_required": False}

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
            # FireAnt API documents record/registration/execution dates but not payout values.
            # Parse the human title when it contains the amount/ratio; otherwise keep it unknown.
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
    # "Latest dividend" is keyed by entitlement/record date first. This keeps a
    # later payment of an old entitlement from outranking a newer dividend event.
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
    """Read-only latest-dividend lookup with direct HTTP providers.

    Provider order is deliberate: Vietcap normally contains amount/ratio detail;
    FireAnt is an independent documented event source and fallback. A lookup never
    changes holdings/cash and never posts an event to the QPort ledger.
    """

    def __init__(self, providers: list[DividendProvider] | None = None) -> None:
        self.providers = providers or [VietcapDividendProvider(), FireAntDividendProvider()]

    def health(self) -> dict:
        return {"provider": "multi_source_dividend", "providers": [p.health() for p in self.providers]}

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
        for provider in self.providers:
            try:
                rows = provider.events(symbol, start, end)
                source_counts[provider.name] = len(rows)
                events.extend(rows)
            except Exception as exc:
                errors.append({"provider": provider.name, "error": f"{type(exc).__name__}: {exc}"})

        if not events:
            return {
                "ok": True,
                "found": False,
                "symbol": symbol,
                "latest": None,
                "source_counts": source_counts,
                "errors": errors,
                "lookback_start": start,
                "lookahead_end": end,
                "read_only": True,
            }

        # Keep all provider evidence but deduplicate equivalent business events for ranking.
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
            "ok": True,
            "found": True,
            "symbol": symbol,
            "latest": latest_payload,
            "source_counts": source_counts,
            "errors": errors,
            "lookback_start": start,
            "lookahead_end": end,
            "read_only": True,
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
