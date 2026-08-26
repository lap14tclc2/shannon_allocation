from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from io import StringIO
from typing import Any
from urllib.request import Request, urlopen

import pandas as pd


CAFEF_REPORTS = {
    "income_statement": ("incsta", "ket-qua-hoat-dong-kinh-doanh-.chn"),
    "balance_sheet": ("bsheet", "can-doi-ke-toan-.chn"),
    "cash_flow": ("cashflow", "luu-chuyen-tien-te-.chn"),
}


def _plain(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    return re.sub(r"[^a-z0-9]+", " ", "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()).strip()


def _number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = re.sub(r"[^0-9,().-]", "", str(value)).strip()
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").replace(".", "").replace(",", ".")
    try:
        parsed = float(text)
        return -parsed if negative else parsed
    except ValueError:
        return None


def _latest_table(html: str) -> tuple[pd.DataFrame, int]:
    tables = [frame for frame in pd.read_html(StringIO(html)) if frame.shape[0] >= 5 and frame.shape[1] >= 2]
    if not tables:
        raise RuntimeError("CafeF did not return a financial statement table")
    frame = max(tables, key=lambda item: item.shape[0])
    usable = []
    for column in range(1, frame.shape[1]):
        if frame.iloc[:, column].map(_number).notna().any():
            usable.append(column)
    if not usable:
        raise RuntimeError("CafeF financial statement has no numeric period")
    return frame, usable[-1]


def _find(frame: pd.DataFrame, column: int, *labels: str) -> float | None:
    wanted = [_plain(label) for label in labels]
    for _, row in frame.iterrows():
        label = _plain(row.iloc[0])
        if any(term in label for term in wanted):
            value = _number(row.iloc[column])
            if value is not None:
                return value
    return None


def _get(session: Any, url: str) -> str:
    headers = {
        "Accept": "text/html,application/xhtml+xml",
        "User-Agent": "Mozilla/5.0 Chrome/151 QPort/1.0",
        "Referer": "https://cafef.vn/du-lieu.chn",
    }
    if session is not None:
        response = session.get(url, headers=headers, timeout=25)
        response.raise_for_status()
        return response.text
    with urlopen(Request(url, headers=headers), timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")


def cafef_valuation_snapshot(symbol: str, *, session: Any = None) -> dict:
    ticker = str(symbol or "").upper().strip()
    if not re.fullmatch(r"[A-Z0-9]{3,10}", ticker):
        raise RuntimeError("Invalid symbol")
    client = session
    year = datetime.now(timezone.utc).year
    frames: dict[str, tuple[pd.DataFrame, int]] = {}
    source_urls: list[str] = []
    for name, (report_type, slug) in CAFEF_REPORTS.items():
        url = f"https://s.cafef.vn/bao-cao-tai-chinh/{ticker}/{report_type}/{year}/0/0/0/0/{slug}"
        frames[name] = _latest_table(_get(client, url))
        source_urls.append(url)

    overview_url = f"https://s.cafef.vn/hose/{ticker}-qport.chn"
    overview = _get(client, overview_url)
    source_urls.append(overview_url)
    meta = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', overview, re.IGNORECASE)
    description = meta.group(1) if meta else ""
    price_match = re.search(r"Giá cổ phiếu[^:]*:\s*([0-9.,]+)\s*VNĐ", description, re.IGNORECASE)
    cap_match = re.search(r"Vốn hóa tt:\s*([0-9.,]+)\s*tỷ", description, re.IGNORECASE)
    price = _number(price_match.group(1)) if price_match else None
    market_cap_billion = _number(cap_match.group(1)) if cap_match else None
    shares = market_cap_billion * 1_000_000_000 / price if market_cap_billion and price else None

    income_frame, income_col = frames["income_statement"]
    balance_frame, balance_col = frames["balance_sheet"]
    cash_frame, cash_col = frames["cash_flow"]
    net_income = _find(income_frame, income_col, "lợi nhuận sau thuế công ty mẹ", "lợi nhuận sau thuế thu nhập doanh nghiệp")
    equity = _find(balance_frame, balance_col, "i vốn chủ sở hữu", "d vốn chủ sở hữu")
    eps = net_income / shares if net_income is not None and shares else None
    bvps = equity / shares if equity is not None and shares else None

    return {
        "status": "success",
        "symbol": ticker,
        "provider": "cafef_public",
        "api_variant": "annual_html_statements",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source_urls": source_urls,
        "profile": [{"outstanding_shares": shares, "sector": "Chưa phân loại (CafeF)"}],
        "income_statement": [{"year_report": year - 1, "net_profit": net_income}],
        "balance_sheet": [{
            "year_report": year - 1,
            "cash_and_cash_equivalents": _find(balance_frame, balance_col, "tiền và các khoản tương đương tiền"),
            "short_term_investments": _find(balance_frame, balance_col, "các khoản đầu tư tài chính ngắn hạn"),
            "short_term_borrowings": _find(balance_frame, balance_col, "vay và nợ thuê tài chính ngắn hạn"),
            "long_term_borrowings": _find(balance_frame, balance_col, "vay và nợ thuê tài chính dài hạn"),
            "equity": equity,
        }],
        "cash_flow": [{
            "year_report": year - 1,
            "depreciation": _find(cash_frame, cash_col, "khấu hao tscđ và bđsđt"),
            "operating_cash_flow": _find(cash_frame, cash_col, "lưu chuyển tiền thuần từ hoạt động kinh doanh"),
            "capex": _find(cash_frame, cash_col, "tiền chi để mua sắm xây dựng tscđ"),
        }],
        "ratios": [{"year_report": year - 1, "eps": eps, "bvps": bvps, "outstanding_shares": shares}],
        "prices": [{"close": price}],
    }
