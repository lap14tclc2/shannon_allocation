"""
VSDC (Vietnam Securities Depository) ingestion — official corporate actions & share history.

Official source (public, no auth) per user-test.md. Provides:
  - Corporate-action announcements (cash dividend, stock dividend, bonus shares, rights issue)
  - Share-count registration history (for NON_ECONOMIC vs ECONOMIC share-change reconciliation)

VSDC requires a session-bound ``__VPToken`` anti-forgery token (from the <meta> tag)
on every POST plus a browser User-Agent. Dates are ``dd/mm/yyyy``; thousands use dots.
"""
from __future__ import annotations

import html as _html
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from .corporate_actions import (
    CorporateAction,
    _parse_stock_ratio,
)

BASE_URL = "https://vsdc.vn"
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) QPort/1.0"


class VsdcError(RuntimeError):
    pass


def _strip_diacritics(text: str) -> str:
    """Lowercase Vietnamese with diacritics stripped (robust label/keyword matching)."""
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _norm_key(text: str) -> str:
    return _strip_diacritics(text).replace(" ", "")


def _classify_vsdc(text: str) -> str:
    low = text.lower()
    n = _strip_diacritics(text)
    has_dividend = "cổ tức" in low or "co tuc" in n
    has_cash = (
        "tiền mặt" in low or "tien mat" in n
        or "bằng tiền" in low or "bang tien" in n
        or "cash" in low
    )
    has_stock = "cổ phiếu" in low or "co phieu" in n or "stock" in low
    if has_dividend and has_cash:
        return "CASH_DIVIDEND"
    if has_dividend and has_stock:
        return "STOCK_DIVIDEND"
    if ("thưởng" in low or "thuong" in n) and has_stock:
        return "BONUS_SHARE"
    if "quyền mua" in low or "quyen mua" in n or "rights" in low:
        return "RIGHTS_ISSUE"
    if ("phát hành" in low or "phat hanh" in n) and has_stock:
        return "STOCK_ISSUE"
    return "OTHER"


def _clean(value: Optional[str]) -> str:
    if value is None:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", _html.unescape(text)).strip()


def _parse_date(value: Optional[str]) -> Optional[str]:
    text = _clean(value)
    if not text:
        return None
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            return None
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except Exception:
        return None


def _parse_dt(value: Optional[str]) -> Optional[str]:
    text = _clean(value)
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})(?:\s*-\s*(\d{1,2}):(\d{2}))?", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hh = int(m.group(4) or 0)
        mm = int(m.group(5) or 0)
        try:
            return datetime(y, mo, d, hh, mm).isoformat()
        except ValueError:
            return None
    return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    text = _clean(value).replace(".", "").replace(",", "").replace(" ", "")
    if not text or not text.isdigit():
        return None
    return int(text)


def _parse_cash_vsdc(text: str) -> Optional[float]:
    """VSDC cash-per-share from prose like '01 cổ phiếu được nhận 1.000 đồng'."""
    n = text.lower().replace(".", "").replace(",", "")
    m = re.search(r"(?:nhận|được nhận|receive)\s+(\d+)\s*(?:đồng|vnd|đ)", n)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)\s*(?:đồng|vnd|đ)\s*/?\s*(?:cp|cổ phiếu|share)", n)
    if m:
        return float(m.group(1))
    return None


class VsdcClient:
    """Thin HTTP client for the public VSDC portal (session-bound __VPToken)."""

    def __init__(self, session: Optional[requests.Session] = None, timeout: float = 15.0) -> None:
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", DEFAULT_UA)
        self.timeout = timeout
        self._token: Optional[str] = None

    def _get_token(self) -> str:
        if self._token:
            return self._token
        resp = self.session.get(f"{BASE_URL}/vi/s-detail/1", timeout=self.timeout)
        resp.raise_for_status()
        m = re.search(r'<meta name="__VPToken" content="([^"]+)"', resp.text)
        self._token = m.group(1) if m else ""
        return self._token

    def _post(self, path: str, body: Dict[str, Any]) -> str:
        token = self._get_token()
        headers = {
            "__VPToken": token,
            "Content-Type": "application/json;charset=utf-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{BASE_URL}/",
        }
        resp = self.session.post(f"{BASE_URL}{path}", json=body, headers=headers, timeout=self.timeout)
        if resp.status_code == 400:
            raise VsdcError(f"VSDC POST {path} rejected (400) — token/session invalid")
        resp.raise_for_status()
        return resp.text

    # -- security lookup -----------------------------------------------------
    def search_security(self, symbol: str) -> Optional[int]:
        """Resolve a ticker to the VSDC security id via /isustocks/search."""
        html = self._post(
            "/isustocks/search",
            {"SearchKey": f"|{str(symbol).upper()}||||VI|||||", "CurrentPage": 1, "RecordOnPage": 10},
        )
        for m in re.finditer(r'href="(?:/vi)?/s-detail/(\d+)"[^>]*>\s*([A-Z0-9]+)\s*<', html):
            if m.group(2).upper() == str(symbol).upper():
                return int(m.group(1))
        m = re.search(r'href="(?:/vi)?/s-detail/(\d+)"', html)
        return int(m.group(1)) if m else None

    def get_security_detail(self, security_id: int) -> str:
        resp = self.session.get(f"{BASE_URL}/vi/s-detail/{security_id}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    # -- announcements -------------------------------------------------------
    def search_announcements(self, security_id: int, page: int = 1) -> List[Dict[str, Any]]:
        html = self._post(
            "/isuisser-tcdk/search",
            {"SearchKey": str(security_id), "CurrentPage": page, "RecordOnPage": 50},
        )
        out: List[Dict[str, Any]] = []
        for m in re.finditer(r'href="(?:/vi)?/ad/(\d+)"[^>]*>([^<]+)</a>', html):
            out.append({"id": int(m.group(1)), "title": _clean(m.group(2))})
        return out

    def search_rights(self, security_id: int, page: int = 1) -> List[Dict[str, Any]]:
        html = self._post(
            "/isuisser-thq/search",
            {"SearchKey": str(security_id), "CurrentPage": page, "RecordOnPage": 50},
        )
        out: List[Dict[str, Any]] = []
        for m in re.finditer(r'href="(?:/vi)?/ad/(\d+)"[^>]*>\s*([^<]+?)\s*<', html):
            out.append({"id": int(m.group(1)), "name": _clean(m.group(2))})
        return out

    def get_announcement(self, announcement_id: int) -> str:
        resp = self.session.get(f"{BASE_URL}/vi/ad/{announcement_id}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.text


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------
def parse_announcement(html: str, announcement_id: int) -> Dict[str, Any]:
    """Parse one VSDC announcement page into structured fields."""
    title = ""
    m = re.search(r'<h3[^>]*class="title-category"[^>]*>(.*?)</h3>', html, re.S)
    if m:
        title = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip()
    symbol = title.split(":", 1)[0].strip().upper() if ":" in title else None
    published = None
    pm = re.search(r'class="time-newstcph"[^>]*>(.*?)</div>', html, re.S)
    if pm:
        published = _parse_dt(pm.group(1))

    fields: Dict[str, str] = {}
    for row_m in re.finditer(
        r'<div class="col-md-4[^"]*item-info[^"]*">([^<]+)</div>\s*<div class="col-md-8[^"]*item-info[^"]*">(.*?)</div>',
        html,
        re.S,
    ):
        label = re.sub(r"\s+", " ", _html.unescape(row_m.group(1))).strip()
        label = re.sub(r"[:：\s]+$", "", label)
        value = _clean(row_m.group(2))
        if label:
            fields[_norm_key(label)] = value

    def _field(*keys: str) -> Optional[str]:
        for key in keys:
            norm = _norm_key(key)
            if norm in fields:
                return fields[norm] or None
        return None

    record_date = _parse_date(_field("Ngày đăng ký cuối cùng", "Ngày đăng ký cuối cùng", "ngay_dang_ky_cuoi_cung"))
    payment_date = _parse_date(_field("Ngày thanh toán", "Ngày thanh toán", "ngay_thanh_toan"))
    reason = _field("Lý do mục đích", "Ly do muc dich", "reason") or ""
    ratio_text = _field("Tỷ lệ thực hiện", "Ty le thuc hien", "ratio") or ""
    combos = " ".join([title, reason, ratio_text])

    action_type = _classify_vsdc(combos)
    cash_per_share = None
    stock_ratio = None
    if action_type == "CASH_DIVIDEND":
        cash_per_share = _parse_cash_vsdc(combos)
    elif action_type in ("STOCK_DIVIDEND", "BONUS_SHARE", "RIGHTS_ISSUE", "STOCK_ISSUE"):
        stock_ratio = _parse_stock_ratio(combos)
        if stock_ratio is not None and stock_ratio > 10:
            stock_ratio /= 100.0
    else:
        cash_per_share = _parse_cash_vsdc(combos)
        stock_ratio = _parse_stock_ratio(combos)
        if stock_ratio is not None and stock_ratio > 10:
            stock_ratio /= 100.0

    return {
        "announcement_id": announcement_id,
        "symbol": symbol,
        "title": title,
        "published_at": published,
        "announcement_date": _parse_date(published) if published else None,
        "record_date": record_date,
        "payment_date": payment_date,
        "reason": reason or None,
        "ratio_text": ratio_text or None,
        "action_type": action_type,
        "cash_per_share": cash_per_share,
        "stock_ratio": stock_ratio,
        "url": f"{BASE_URL}/vi/ad/{announcement_id}",
    }


def parse_share_registration_history(html: str, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """Parse the 'Thông tin đăng ký chứng khoán' table into ordered share-count deltas.

    Each row: (reason, quantity_delta, date). Quantity is the incremental change;
    reasons like 'Phát hành cổ phiếu để trả cổ tức' are NON_ECONOMIC; pure
    'Điều chỉnh số lượng chứng khoán' without a dividend reason is ECONOMIC_EVENT_CANDIDATE.
    """
    rows: List[Dict[str, Any]] = []
    table_m = re.search(r'id="Detail_TCPH_TTDKCK"(.*?)</table>', html, re.S)
    if not table_m:
        return rows
    for tr in re.finditer(r"<tr>(.*?)</tr>", table_m.group(1), re.S):
        tds = [td for td in re.findall(r"<td[^>]*>(.*?)</td>", tr.group(1), re.S)]
        if len(tds) < 5:
            continue
        reason = _clean(tds[2])
        quantity = _parse_int(tds[3])
        if quantity is None or reason in ("Tổng cộng:", ""):
            continue
        day = _parse_date(tds[5]) if len(tds) >= 6 else _parse_date(tds[4])
        rows.append({
            "symbol": symbol,
            "reason": reason,
            "quantity_delta": quantity,
            "date": day,
            "registration_round": _clean(tds[1]) or None,
        })
    return rows


# ---------------------------------------------------------------------------
# CorporateAction provider (protocol-compatible)
# ---------------------------------------------------------------------------
class VsdcCorporateActionProvider:
    """Corporate-action provider backed by the official VSDC public portal."""

    name = "vsdc"

    def __init__(self, client: Optional[VsdcClient] = None, max_announcements_per_security: int = 60) -> None:
        self._client = client or VsdcClient()
        self.max_announcements_per_security = max_announcements_per_security
        self._last_attempts: List[Dict[str, Any]] = []
        self._last_success_symbols: List[str] = []

    def health(self) -> dict:
        return {
            "provider": self.name,
            "status": "AVAILABLE" if self._last_success_symbols else "NOT_PROBED",
            "available": bool(self._last_success_symbols),
            "auth_mode": "NONE",
            "source": "https://vsdc.vn (official depository, public)",
            "last_success_symbols": list(self._last_success_symbols[-5:]),
            "last_attempts": list(self._last_attempts),
        }

    def events(self, symbols: list[str], start: str, end: str) -> list[CorporateAction]:
        """Discover VSDC corporate actions for the given symbols within [start, end]."""
        self._last_attempts = []
        self._last_success_symbols = []
        out: List[CorporateAction] = []
        seen: set[str] = set()
        for symbol in sorted({str(s).upper().strip() for s in symbols if s}):
            try:
                security_id = self._client.search_security(symbol)
                if security_id is None:
                    self._last_attempts.append({"symbol": symbol, "status": "ERROR", "error": "security_not_found"})
                    continue
                anns = self._client.search_announcements(security_id)[: self.max_announcements_per_security]
                rights = self._client.search_rights(security_id)[: self.max_announcements_per_security]
                ids = list(dict.fromkeys([a["id"] for a in anns] + [r["id"] for r in rights]))
                added = 0
                for ann_id in ids:
                    action = self._announcement_to_action(ann_id, start, end)
                    if action is None:
                        continue
                    if action.external_key in seen:
                        continue
                    seen.add(action.external_key)
                    out.append(action)
                    added += 1
                self._last_attempts.append({"symbol": symbol, "status": "SUCCESS" if added else "EMPTY", "count": added})
                if added:
                    self._last_success_symbols.append(symbol)
            except Exception as exc:
                self._last_attempts.append({"symbol": symbol, "status": "ERROR", "count": 0, "error": f"{type(exc).__name__}: {exc}"})
        return out

    def _announcement_to_action(self, announcement_id: int, start: str, end: str) -> Optional[CorporateAction]:
        html = self._client.get_announcement(announcement_id)
        parsed = parse_announcement(html, announcement_id)
        symbol = parsed["symbol"]
        if not symbol:
            return None
        anchor = parsed["record_date"] or parsed["payment_date"] or parsed["announcement_date"]
        if anchor is not None and (anchor < start or anchor > end):
            return None
        raw = {
            "id": announcement_id,
            "event_name": parsed["title"],
            "reason": parsed["reason"],
            "ratio_text": parsed["ratio_text"],
        }
        from .corporate_actions import _stable_event_key
        external_key = _stable_event_key(
            source=self.name, symbol=symbol, action_type=parsed["action_type"],
            event_name=parsed["title"],
            record_date=parsed["record_date"], ex_date=None,
            payment_date=parsed["payment_date"], announcement_date=parsed["announcement_date"],
            cash_per_share=parsed["cash_per_share"], stock_ratio=parsed["stock_ratio"],
            raw=raw,
        )
        return CorporateAction(
            external_key=external_key,
            symbol=symbol,
            action_type=parsed["action_type"],
            event_name=parsed["title"] or None,
            announcement_date=parsed["announcement_date"],
            ex_date=None,
            record_date=parsed["record_date"],
            payment_date=parsed["payment_date"],
            cash_per_share=parsed["cash_per_share"],
            stock_ratio=parsed["stock_ratio"],
            source=self.name,
            source_url=parsed["url"],
            confidence="PROVISIONAL",
            verification_status="UNVERIFIED",
            raw=raw,
        )


def default_corporate_action_provider():
    """VSDC-first corporate action provider with a resilient multi-source fallback.

    VSDC is the canonical official source; if a symbol fails there we fall back to
    the existing dividend-provider chain (VPS / FireAnt / CafeF / Vietcap + vnstock).
    """
    from .corporate_actions import VnstockCorporateActionProvider

    vsdc = VsdcCorporateActionProvider()

    class _VsdcFirstProvider:
        name = "vsdc_first"

        def health(self) -> dict:
            return {
                "provider": self.name,
                "vsdc": vsdc.health(),
                "fallback": VnstockCorporateActionProvider().health(),
            }

        def events(self, symbols, start, end):
            out = []
            seen = set()
            try:
                vsdc_actions = vsdc.events(symbols, start, end)
                for action in vsdc_actions:
                    if action.external_key not in seen:
                        out.append(action)
                        seen.add(action.external_key)
            except Exception:
                pass
            fallback = VnstockCorporateActionProvider()
            for symbol in sorted({str(s).upper().strip() for s in symbols if s}):
                try:
                    rows = fallback.events([symbol], start, end)
                except Exception:
                    continue
                for action in rows:
                    if action.external_key not in seen:
                        out.append(action)
                        seen.add(action.external_key)
            return out

    return _VsdcFirstProvider()