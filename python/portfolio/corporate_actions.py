from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any, Protocol

from .vnstock_isolated import run_vnstock_task, vnstock_runtime_health


@dataclass
class CorporateAction:
    external_key: str
    symbol: str
    action_type: str
    event_name: str | None = None
    announcement_date: str | None = None
    ex_date: str | None = None
    record_date: str | None = None
    payment_date: str | None = None
    cash_per_share: float | None = None
    stock_ratio: float | None = None
    source: str = "manual"
    source_url: str | None = None
    confidence: str = "PROVISIONAL"
    verification_status: str = "UNVERIFIED"
    raw: dict[str, Any] | None = None


class CorporateActionProvider(Protocol):
    name: str
    def events(self, symbols: list[str], start: str, end: str) -> list[CorporateAction]: ...
    def health(self) -> dict: ...


def _text(row: dict) -> str:
    return " ".join(str(v) for v in row.values() if v is not None).strip()


def _value(row: dict, aliases: tuple[str, ...]):
    lowered = {str(k).lower().strip(): v for k, v in row.items()}
    for alias in aliases:
        if alias in lowered and lowered[alias] not in (None, ""):
            return lowered[alias]
    return None


def _date_value(value) -> str | None:
    if value is None or value == "": return None
    text = str(value).strip()
    if "T" in text: text = text.split("T", 1)[0]
    try: return date.fromisoformat(text[:10]).isoformat()
    except Exception: return None


def _classify(text: str) -> str:
    low = text.lower()
    if "cổ tức" in low and ("tiền" in low or "cash" in low): return "CASH_DIVIDEND"
    if "cổ tức" in low and ("cổ phiếu" in low or "stock" in low): return "STOCK_DIVIDEND"
    if "thưởng" in low and "cổ phiếu" in low: return "BONUS_SHARE"
    if "quyền mua" in low or "rights" in low: return "RIGHTS_ISSUE"
    if "phát hành" in low and "cổ phiếu" in low: return "STOCK_ISSUE"
    return "OTHER"


def _parse_stock_ratio(text: str) -> float | None:
    low = text.lower().replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)", low)
    if match:
        existing, received = float(match.group(1)), float(match.group(2))
        return received / existing if existing > 0 else None
    match = re.search(r"(?:tỷ lệ|ty le|ratio)?\s*(\d+(?:\.\d+)?)\s*%", low)
    if match:
        pct = float(match.group(1)); return pct / 100.0 if 0 < pct <= 1000 else None
    return None


def _parse_cash_per_share(text: str) -> float | None:
    normalized = text.lower().replace(".", "").replace(",", "")
    for pattern in (
        r"(\d+)\s*(?:đồng|vnd)\s*/\s*(?:cp|cổ phiếu|share)",
        r"(?:cash|tiền mặt)[^\d]{0,20}(\d+)\s*(?:đồng|vnd)",
    ):
        match = re.search(pattern, normalized)
        if match: return float(match.group(1))
    return None


def _stable_event_key(*, source: str, symbol: str, action_type: str, event_name: str | None, record_date: str | None,
                      ex_date: str | None, payment_date: str | None, announcement_date: str | None,
                      cash_per_share: float | None, stock_ratio: float | None, raw: dict) -> str:
    native_id = _value(raw, ("event_id", "eventid", "id", "event_code", "eventcode", "news_id"))
    if native_id not in (None, ""):
        return f"{source}:{symbol}:id:{str(native_id).strip()}"
    material = {
        "symbol": symbol,
        "action_type": action_type,
        "event_name": re.sub(r"\s+", " ", str(event_name or "").strip().lower()),
        "record_date": record_date,
        "ex_date": ex_date,
        "payment_date": payment_date,
        "announcement_date": announcement_date,
        "cash_per_share": round(float(cash_per_share), 6) if cash_per_share is not None else None,
        "stock_ratio": round(float(stock_ratio), 10) if stock_ratio is not None else None,
    }
    digest = hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    return f"{source}:{symbol}:event:{digest}"


def normalize_event_row(row: dict, default_symbol: str | None = None, source: str = "vnstock") -> CorporateAction | None:
    raw = {str(k): (v.item() if hasattr(v, "item") else v) for k, v in row.items()}
    symbol = str(_value(raw, ("symbol", "ticker", "code", "stock_code")) or default_symbol or "").upper().strip()
    if not symbol: return None
    text = _text(raw)
    action_type = _classify(text)
    event_name_value = _value(raw, ("event_name", "event_title", "title", "name", "description", "purpose", "reason"))
    event_name = str(event_name_value).strip() if event_name_value not in (None, "") else None
    record_date = _date_value(_value(raw, ("record_date", "last_registration_date", "registration_date", "ngay_dang_ky_cuoi_cung")))
    ex_date = _date_value(_value(raw, ("ex_date", "ex_right_date", "ngay_giao_dich_khong_huong_quyen")))
    payment_date = _date_value(_value(raw, ("payment_date", "pay_date", "execution_date", "ngay_thanh_toan")))
    announcement_date = _date_value(_value(raw, ("announcement_date", "publish_date", "date", "event_date")))
    cash = _value(raw, ("cash_per_share", "dividend_value", "cash_dividend"))
    ratio = _value(raw, ("stock_ratio", "ratio", "dividend_ratio"))
    try: cash_per_share = float(cash) if cash not in (None, "") else _parse_cash_per_share(text)
    except Exception: cash_per_share = _parse_cash_per_share(text)
    try:
        stock_ratio = float(ratio) if ratio not in (None, "") else _parse_stock_ratio(text)
        if stock_ratio is not None and stock_ratio > 10: stock_ratio /= 100.0
    except Exception: stock_ratio = _parse_stock_ratio(text)
    source_url = _value(raw, ("url", "source_url", "link"))
    external_key = _stable_event_key(
        source=source, symbol=symbol, action_type=action_type, event_name=event_name,
        record_date=record_date, ex_date=ex_date, payment_date=payment_date,
        announcement_date=announcement_date, cash_per_share=cash_per_share,
        stock_ratio=stock_ratio, raw=raw,
    )
    return CorporateAction(
        external_key=external_key, symbol=symbol, action_type=action_type, event_name=event_name,
        announcement_date=announcement_date, ex_date=ex_date, record_date=record_date,
        payment_date=payment_date, cash_per_share=cash_per_share, stock_ratio=stock_ratio,
        source=source, source_url=str(source_url) if source_url else None,
        confidence="PROVISIONAL", verification_status="UNVERIFIED", raw=raw,
    )


def _records(frame) -> list[dict]:
    if frame is None: return []
    if hasattr(frame, "to_dict"):
        try: return [dict(row) for row in frame.to_dict("records")]
        except Exception: return []
    if isinstance(frame, list): return [dict(row) for row in frame if isinstance(row, dict)]
    return []


class VnstockCorporateActionProvider:
    """Vnstock corporate-action discovery through an isolated worker runtime."""

    def __init__(self, reference_factory=None, provider_name: str | None = None) -> None:
        self._Reference = reference_factory
        self.name = provider_name or "vnstock"
        self._error: str | None = None
        self._api_variant = "injected" if reference_factory is not None else "external_worker"
        self._isolated = reference_factory is None

    def health(self) -> dict:
        if self._isolated:
            probe = vnstock_runtime_health("reference")
            self.name = str(probe.get("provider") or self.name)
            self._api_variant = str(probe.get("api_variant") or self._api_variant)
            self._error = probe.get("error")
            return {
                "provider": self.name,
                "available": bool(probe.get("available")),
                "error": self._error,
                "api_variant": self._api_variant,
                "isolation": "EXTERNAL_PYTHON_SUBPROCESS",
                "worker_python": probe.get("worker_python"),
                "python_version": probe.get("python_version"),
                "capability": "REFERENCE_EVENTS",
                "mode": "raw-first stable-event normalization",
            }
        return {
            "provider": self.name, "available": self._Reference is not None,
            "error": self._error, "api_variant": self._api_variant,
            "isolation": "INJECTED_DIRECT", "capability": "REFERENCE_EVENTS",
            "mode": "raw-first stable-event normalization",
        }

    @staticmethod
    def _company_events(ref, symbol: str) -> list[dict]:
        company = getattr(ref, "company", None)
        if company is None: return []
        events_method = getattr(company, "events", None)
        if callable(events_method):
            for call in (lambda: events_method(symbol=symbol), lambda: events_method(symbol)):
                try:
                    rows = _records(call())
                    if rows: return rows
                except Exception: pass
        if callable(company):
            try:
                obj = company(symbol); method = getattr(obj, "events", None)
                if callable(method): return _records(method())
            except Exception: pass
        return []

    @staticmethod
    def _calendar_events(ref, start: str, end: str) -> list[dict]:
        events_obj = getattr(ref, "events", None)
        calendar = getattr(events_obj, "calendar", None) if events_obj is not None else None
        if not callable(calendar): return []
        try: return _records(calendar(start=start, end=end, event_type="dividend"))
        except Exception: return []

    def events(self, symbols: list[str], start: str, end: str) -> list[CorporateAction]:
        wanted = {str(s).upper() for s in symbols}
        provider_name = self.name
        if self._isolated:
            result = run_vnstock_task("events", {"symbols": sorted(wanted), "start": start, "end": end})
            rows = result.get("data") or []
            provider_name = str(result.get("provider") or self.name)
            self.name = provider_name
            self._api_variant = str(result.get("api_variant") or self._api_variant)
        else:
            ref = self._Reference()
            rows = self._calendar_events(ref, start, end)
            if not rows:
                rows = []
                for symbol in sorted(wanted):
                    for row in self._company_events(ref, symbol):
                        item = dict(row); item.setdefault("symbol", symbol); rows.append(item)
        out: list[CorporateAction] = []
        seen: set[str] = set()
        for row in rows:
            default_symbol = str(row.get("symbol") or "").upper() or None
            action = normalize_event_row(dict(row), default_symbol=default_symbol, source=provider_name)
            if action and action.symbol in wanted and action.external_key not in seen:
                out.append(action); seen.add(action.external_key)
        return out


def default_window(days_back: int = 370, days_forward: int = 370) -> tuple[str, str]:
    today = date.today()
    return (today - timedelta(days=days_back)).isoformat(), (today + timedelta(days=days_forward)).isoformat()


def action_as_dict(action: CorporateAction) -> dict:
    return asdict(action)
