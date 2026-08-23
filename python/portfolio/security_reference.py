from __future__ import annotations

import re
from typing import Any

ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


def _records(frame) -> list[dict]:
    if frame is None:
        return []
    if hasattr(frame, "to_dict"):
        try:
            return [dict(row) for row in frame.to_dict("records")]
        except Exception:
            pass
    if isinstance(frame, dict):
        return [dict(frame)]
    if isinstance(frame, list):
        return [dict(row) for row in frame if isinstance(row, dict)]
    return []


def _find_value(row: dict[str, Any], aliases: tuple[str, ...]):
    lowered = {str(k).lower().strip(): v for k, v in row.items()}
    for alias in aliases:
        if alias in lowered and lowered[alias] not in (None, ""):
            return lowered[alias]
    return None


def _find_isin(row: dict[str, Any]) -> str | None:
    aliases = ("isin", "isin_code", "isincode", "security_isin", "securities_isin")
    direct = _find_value(row, aliases)
    candidates = [direct] if direct not in (None, "") else []
    candidates.extend(v for v in row.values() if isinstance(v, str) and len(v.strip()) == 12)
    for value in candidates:
        text = str(value or "").upper().strip()
        if ISIN_RE.fullmatch(text):
            return text
    return None


class VnstockSecurityReferenceProvider:
    """Resolve security master attributes without inventing identifiers.

    ISIN is assigned by the market infrastructure and is not mathematically
    derivable from a ticker. This provider inspects Vnstock Reference runtime
    data and returns UNRESOLVED when the source does not expose a valid ISIN.
    """

    def __init__(self, reference_factory=None, provider_name: str | None = None) -> None:
        self._Reference = reference_factory
        self.name = provider_name or "vnstock"
        self._error: str | None = None
        self._variant = "injected" if reference_factory else None
        if reference_factory:
            return
        community_error = None
        try:
            from vnstock import Reference  # type: ignore
            self._Reference = Reference
            self.name = "vnstock"
            self._variant = "community_v4"
            return
        except Exception as exc:
            community_error = str(exc)
        try:
            from vnstock_data import Reference  # type: ignore
            self._Reference = Reference
            self.name = "vnstock_data"
            self._variant = "sponsor"
            return
        except Exception as exc:
            self._Reference = None
            self._variant = "unavailable"
            self._error = f"vnstock: {community_error}; vnstock_data: {exc}"

    def health(self) -> dict:
        return {"provider": self.name, "available": self._Reference is not None, "api_variant": self._variant, "error": self._error}

    @staticmethod
    def _company_info(ref, symbol: str) -> list[dict]:
        company = getattr(ref, "company", None)
        if company is None:
            return []
        if callable(company):
            try:
                obj = company(symbol)
                info = getattr(obj, "info", None)
                if callable(info):
                    rows = _records(info())
                    if rows:
                        return rows
            except Exception:
                pass
        info = getattr(company, "info", None)
        if callable(info):
            for call in (lambda: info(symbol=symbol), lambda: info(symbol)):
                try:
                    rows = _records(call())
                    if rows:
                        return rows
                except Exception:
                    pass
        return []

    def resolve(self, symbol: str) -> dict:
        symbol = str(symbol).upper().strip()
        if self._Reference is None:
            return {"symbol": symbol, "status": "PROVIDER_UNAVAILABLE", "source": self.name, "error": self._error}
        try:
            ref = self._Reference()
            rows = self._company_info(ref, symbol)
        except Exception as exc:
            return {"symbol": symbol, "status": "ERROR", "source": self.name, "error": str(exc)}
        if not rows:
            return {"symbol": symbol, "status": "UNRESOLVED", "source": self.name, "reason": "No company reference row returned."}
        row = rows[0]
        isin = _find_isin(row)
        exchange = _find_value(row, ("exchange", "exchange_code", "floor", "market", "com_group_code"))
        name = _find_value(row, ("organ_name", "company_name", "name", "short_name"))
        lot_size = _find_value(row, ("lot_size", "trading_lot", "board_lot"))
        try:
            lot_size = float(lot_size) if lot_size not in (None, "") else None
        except Exception:
            lot_size = None
        return {
            "symbol": symbol,
            "status": "RESOLVED" if isin else "PARTIAL",
            "source": self.name,
            "isin": isin,
            "exchange": str(exchange).upper().strip() if exchange not in (None, "") else None,
            "name": str(name).strip() if name not in (None, "") else None,
            "lot_size": lot_size,
            "available_fields": sorted(str(k) for k in row.keys()),
        }
