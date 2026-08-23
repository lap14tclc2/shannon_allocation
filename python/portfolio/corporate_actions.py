from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any, Protocol


@dataclass
class CorporateAction:
    external_key: str
    symbol: str
    action_type: str
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
    if value is None or value == "":
        return None
    text = str(value).strip()
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except Exception:
        return None


def _classify(text: str) -> str:
    low = text.lower()
    if "cổ tức" in low and ("tiền" in low or "cash" in low):
        return "CASH_DIVIDEND"
    if "cổ tức" in low and ("cổ phiếu" in low or "stock" in low):
        return "STOCK_DIVIDEND"
    if "thưởng" in low and "cổ phiếu" in low:
        return "BONUS_SHARE"
    if "quyền mua" in low or "rights" in low:
        return "RIGHTS_ISSUE"
    if "phát hành" in low and "cổ phiếu" in low:
        return "STOCK_ISSUE"
    return "OTHER"


def _parse_stock_ratio(text: str) -> float | None:
    low = text.lower().replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)", low)
    if match:
        existing = float(match.group(1))
        received = float(match.group(2))
        if existing > 0:
            return received / existing
    match = re.search(r"(?:tỷ lệ|ty le|ratio)?\s*(\d+(?:\.\d+)?)\s*%", low)
    if match:
        pct = float(match.group(1))
        if 0 < pct <= 1000:
            return pct / 100.0
    return None


def _parse_cash_per_share(text: str) -> float | None:
    normalized = text.lower().replace(".", "").replace(",", "")
    patterns = [
        r"(\d+)\s*(?:đồng|vnd)\s*/\s*(?:cp|cổ phiếu|share)",
        r"(?:cash|tiền mặt)[^\d]{0,20}(\d+)\s*(?:đồng|vnd)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return float(match.group(1))
    return None


def normalize_event_row(row: dict, default_symbol: str | None = None, source: str = "vnstock_data") -> CorporateAction | None:
    """Normalize an unknown provider row without assuming a fixed vendor schema.

    Vnstock explicitly recommends inspecting the runtime schema. We therefore
    preserve the complete raw row, use aliases only for common fields, and mark
    the result PROVISIONAL unless authoritative verification is later attached.
    """
    raw = {str(k): (v.item() if hasattr(v, "item") else v) for k, v in row.items()}
    symbol = str(_value(raw, ("symbol", "ticker", "code", "stock_code")) or default_symbol or "").upper().strip()
    if not symbol:
        return None
    text = _text(raw)
    action_type = _classify(text)
    record_date = _date_value(_value(raw, ("record_date", "last_registration_date", "registration_date", "ngay_dang_ky_cuoi_cung")))
    ex_date = _date_value(_value(raw, ("ex_date", "ex_right_date", "ngay_giao_dich_khong_huong_quyen")))
    payment_date = _date_value(_value(raw, ("payment_date", "pay_date", "execution_date", "ngay_thanh_toan")))
    announcement_date = _date_value(_value(raw, ("announcement_date", "publish_date", "date", "event_date")))
    cash = _value(raw, ("cash_per_share", "dividend_value", "cash_dividend"))
    ratio = _value(raw, ("stock_ratio", "ratio", "dividend_ratio"))
    try:
        cash_per_share = float(cash) if cash not in (None, "") else _parse_cash_per_share(text)
    except Exception:
        cash_per_share = _parse_cash_per_share(text)
    try:
        stock_ratio = float(ratio) if ratio not in (None, "") else _parse_stock_ratio(text)
        if stock_ratio is not None and stock_ratio > 10:
            stock_ratio /= 100.0
    except Exception:
        stock_ratio = _parse_stock_ratio(text)
    key_material = json.dumps(raw, ensure_ascii=False, sort_keys=True, default=str)
    external_key = f"{source}:{symbol}:{hashlib.sha256(key_material.encode('utf-8')).hexdigest()[:24]}"
    source_url = _value(raw, ("url", "source_url", "link"))
    return CorporateAction(
        external_key=external_key,
        symbol=symbol,
        action_type=action_type,
        announcement_date=announcement_date,
        ex_date=ex_date,
        record_date=record_date,
        payment_date=payment_date,
        cash_per_share=cash_per_share,
        stock_ratio=stock_ratio,
        source=source,
        source_url=str(source_url) if source_url else None,
        confidence="PROVISIONAL",
        verification_status="UNVERIFIED",
        raw=raw,
    )


class VnstockCorporateActionProvider:
    name = "vnstock_data"

    def __init__(self) -> None:
        self._error: str | None = None
        try:
            from vnstock_data import Reference  # type: ignore
            self._Reference = Reference
        except Exception as exc:
            self._Reference = None
            self._error = str(exc)

    def health(self) -> dict:
        return {
            "provider": self.name,
            "available": self._Reference is not None,
            "error": self._error,
            "mode": "raw-first runtime-schema normalization",
        }

    def events(self, symbols: list[str], start: str, end: str) -> list[CorporateAction]:
        if self._Reference is None:
            raise RuntimeError("vnstock_data is not installed. Install python/requirements-vnstock.txt.")
        ref = self._Reference()
        rows: list[dict] = []
        # Prefer the market calendar because it fetches all dividend/share-issue
        # events in one call. Fall back to per-company events when unavailable.
        try:
            frame = ref.events.calendar(start=start, end=end, event_type="dividend")
            rows = frame.to_dict("records") if hasattr(frame, "to_dict") else []
        except Exception:
            for symbol in symbols:
                try:
                    frame = ref.company(symbol).events()
                    for row in (frame.to_dict("records") if hasattr(frame, "to_dict") else []):
                        row = dict(row)
                        row.setdefault("symbol", symbol)
                        rows.append(row)
                except Exception:
                    continue
        wanted = {s.upper() for s in symbols}
        out = []
        for row in rows:
            action = normalize_event_row(dict(row), source=self.name)
            if action and action.symbol in wanted:
                out.append(action)
        return out


def default_window(days_back: int = 370, days_forward: int = 370) -> tuple[str, str]:
    today = date.today()
    return (today - timedelta(days=days_back)).isoformat(), (today + timedelta(days=days_forward)).isoformat()


def action_as_dict(action: CorporateAction) -> dict:
    return asdict(action)
