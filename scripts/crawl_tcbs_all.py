#!/usr/bin/env python3
"""
TCBS Financial Data Crawler with Flexible Period Filtering.

Modes:
1. 'all': Lấy toàn bộ lịch sử BCTC từ kỳ đầu tiên đến nay.
2. 'latest': Chỉ lấy 1 kỳ mới nhất (Quý mới nhất & Năm mới nhất).
3. 'range': Lấy trong khoảng thời gian (VD: from_year=2020, to_year=2026, hoặc from_quarter, to_quarter).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from curl_cffi import requests

TOKEN = (
    "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhdXRoZW5fc2VydmljZSIsImV4cCI6MTc4Nzg4MTA1NCwianRpIjoiIiwiaWF0IjoxNzg3ODM3ODU0LCJzdWIiOiIxMDAwMDAxOTk3NSIsImN1c3RvZHlJRCI6IjEwNUM4MDA4NzgiLCJ0Y2JzSWQiOiIxMDAwMDAxOTk3NSIsImVtYWlsIjoiaG9uYXoxNDBAZ21haWwuY29tIiwicm9sZXMiOlsiY3VzdG9tZXIiXSwic2NvcGVzIjpbImFsbDphbGwiLCJzb2NrZXQ6YWxsIl0sInN0ZXB1cF9leHAiOjAsInNvdHBfc2lnbiI6IiIsImNsaWVudF9rZXkiOiJsU0tpWlRUbjNiQzhyRWZDWjRlZzhnc3FRYlhWN0ZUNCIsInNlc3Npb25JRCI6ImU0YzdkZTQ2LWY0MzItNDIzMC1hOGQ4LTc1NDVlZWZmNzE5ZiIsImFjY291bnRfc3RhdHVzIjoiMSIsIm90cCI6IiIsIm90cFR5cGUiOiIiLCJvdHBTb3VyY2UiOiJUQ0lOVkVTVCIsIm90cFNlc3Npb25JZCI6IiIsImFjY291bnRUeXBlIjoiUFJJTUFSWSIsInByaW1hcnlTdWIiOiIiLCJwcmltYXJ5Q3VzdG9keUlEIjoiIiwiZW5vdHBfc2lnbiI6IiIsInNxYV9zaWduIjoiIiwiZW5fb3RwIjoiIiwiZW5PVFBUeXBlIjoiIiwiY2FTdGF0dXMiOiJJR05PUkUiLCJjdXNUeXBlIjoiSU5ESVZJRFVBTCIsInRlbmFudCI6InRjYnMiLCJ0Y2JzUm9sZXMiOm51bGx9.EtmzGt1468xfZvsakIcgLERgT8hPkU6kmihVfue7u-qZMP2JWSSK2c8DypZBw7sPQlRnZbAwmDJQv4u14dKmoddMs1ViUYuUiwY51b48_IW0aq0-sEeWs4J6oZ0JhvdwvYskwo38jUy43BpN4XB3Vs--ikuc5ghnby2Gf46a_3R1PrGdHCwZoNnuN0SjBbvaquksyV7gPKNIdFhuW8jUbNMarZR3NH2Meb8ZxYLEZifbgSY-Y9axB9EwbulUw4BO2xy5xpDiwu7QW47yaBL_8VHCjdc-siHAbr4fAASFcvrw8nMEhY2XXMEf-2YDUTNReKqZAgsDVX4J1b2b529WOA"
)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://tcinvest.tcbs.com.vn",
    "Referer": "https://tcinvest.tcbs.com.vn/",
}

OUT_DIR = Path("docs/crawled")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def filter_period_records(
    records: List[Dict[str, Any]],
    mode: str = "all",
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Lọc danh sách các kỳ tài chính theo mode:
    - 'all': giữ nguyên toàn bộ.
    - 'latest': chỉ lấy 1 bản ghi mới nhất.
    - 'range': lọc theo khoảng [from_year, to_year].
    """
    if not records or not isinstance(records, list):
        return records

    if mode == "latest":
        return [records[0]]

    if mode == "range":
        filtered = []
        for r in records:
            yr = r.get("year")
            if yr is None:
                continue
            if from_year is not None and yr < from_year:
                continue
            if to_year is not None and yr > to_year:
                continue
            filtered.append(r)
        return filtered

    return records


def crawl_symbol(
    symbol: str,
    session: Optional[requests.Session] = None,
    mode: str = "all",
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    save_to_disk: bool = True,
    force_refetch: bool = False,
) -> Dict[str, Any]:
    """
    Crawl báo cáo tài chính của 1 mã cổ phiếu từ TCBS với các tùy chọn:
    
    :param symbol: Mã cổ phiếu (VD: 'FPT', 'MWG')
    :param session: requests.Session của curl_cffi (nếu không có sẽ tự khởi tạo)
    :param mode: 'all' (toàn bộ lịch sử), 'latest' (kỳ mới nhất), 'range' (theo khoảng năm)
    :param from_year: Năm bắt đầu (dùng khi mode='range')
    :param to_year: Năm kết thúc (dùng khi mode='range')
    :param save_to_disk: Có lưu file JSON vào docs/crawled/{symbol}.json hay không
    :param force_refetch: Bắt buộc tải lại dù file đã tồn tại trên đĩa
    :return: Dictionary chứa dữ liệu BCTC đã lọc
    """
    symbol = symbol.upper().strip()
    out_file = OUT_DIR / f"{symbol}.json"

    # Nếu file đã tồn tại trên đĩa và không bắt buộc tải mới, đọc từ đĩa và filter
    if out_file.exists() and not force_refetch and out_file.stat().st_size > 500:
        try:
            with open(out_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            data_map = cached.get("data", {})
            filtered_data = {}
            for k, records in data_map.items():
                filtered_data[k] = filter_period_records(records, mode=mode, from_year=from_year, to_year=to_year)
            return {
                "symbol": symbol,
                "source": "tcbs_cached",
                "mode": mode,
                "data": filtered_data,
            }
        except Exception:
            pass

    endpoints = {
        "incomestatement_quarter": f"https://apiextaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/incomestatement?yearly=0&isAll=true",
        "balancesheet_quarter": f"https://apiextaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/balancesheet?yearly=0&isAll=true",
        "cashflow_quarter": f"https://apiextaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/cashflow?yearly=0&isAll=true",
        "incomestatement_year": f"https://apiextaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/incomestatement?yearly=1&isAll=true",
        "balancesheet_year": f"https://apiextaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/balancesheet?yearly=1&isAll=true",
        "cashflow_year": f"https://apiextaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/cashflow?yearly=1&isAll=true",
    }

    local_session = session or requests.Session(impersonate="chrome120")
    raw_data = {}
    total_records = 0

    for key, url in endpoints.items():
        retries = 0
        while retries <= 3:
            try:
                resp = local_session.get(url, headers=HEADERS, timeout=12)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        raw_data[key] = data
                        total_records += len(data)
                    elif isinstance(data, dict):
                        raw_data[key] = data
                        total_records += 1
                    break
                elif resp.status_code in (404, 400):
                    raw_data[key] = []
                    break
                elif resp.status_code == 429:
                    retries += 1
                    sleep_time = 2.0 * retries + random.uniform(0.5, 1.5)
                    time.sleep(sleep_time)
                else:
                    retries += 1
                    time.sleep(1.0)
            except Exception:
                retries += 1
                time.sleep(1.5)

    # Lưu bản đầy đủ (all) vào docs/crawled/{symbol}.json nếu yêu cầu
    if save_to_disk and total_records > 0:
        full_payload = {
            "symbol": symbol,
            "source": "tcbs",
            "crawled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data": raw_data,
        }
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(full_payload, f, ensure_ascii=False, indent=2)

    # Trả về kết quả theo filter mode yêu cầu
    filtered_data = {}
    for k, records in raw_data.items():
        filtered_data[k] = filter_period_records(records, mode=mode, from_year=from_year, to_year=to_year)

    return {
        "symbol": symbol,
        "source": "tcbs",
        "mode": mode,
        "from_year": from_year,
        "to_year": to_year,
        "data": filtered_data,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="TCBS Flexible Period Financial Crawler")
    parser.add_argument("--symbol", "-s", type=str, default="FPT", help="Mã cổ phiếu cần lấy (VD: FPT)")
    parser.add_argument(
        "--mode",
        "-m",
        choices=["all", "latest", "range"],
        default="all",
        help="Chế độ lấy dữ liệu: all (tất cả), latest (kỳ mới nhất), range (khoảng năm)",
    )
    parser.add_argument("--from-year", type=int, default=None, help="Năm bắt đầu (cho mode=range)")
    parser.add_argument("--to-year", type=int, default=None, help="Năm kết thúc (cho mode=range)")
    parser.add_argument("--force", action="store_true", help="Bắt buộc cào mới từ API không dùng cache")

    args = parser.parse_args()

    print(f"============================================================")
    print(f"🚀 Running TCBS Crawler: symbol={args.symbol}, mode={args.mode}")
    if args.mode == "range":
        print(f"📅 Khoảng năm: {args.from_year} -> {args.to_year}")
    print(f"============================================================")

    res = crawl_symbol(
        symbol=args.symbol,
        mode=args.mode,
        from_year=args.from_year,
        to_year=args.to_year,
        force_refetch=args.force,
    )

    d = res.get("data", {})
    is_q = d.get("incomestatement_quarter", [])
    is_y = d.get("incomestatement_year", [])

    print(f"📊 Kết quả cho mã {args.symbol}:")
    print(f"   - Số quý thu được: {len(is_q)}")
    if is_q:
        print(f"     + Quý mới nhất: {is_q[0].get('year')} Q{is_q[0].get('quarter')}")
        print(f"     + Quý cũ nhất: {is_q[-1].get('year')} Q{is_q[-1].get('quarter')}")
    print(f"   - Số năm thu được: {len(is_y)}")
    if is_y:
        print(f"     + Năm mới nhất: {is_y[0].get('year')}")
        print(f"     + Năm cũ nhất: {is_y[-1].get('year')}")
    print(f"============================================================")


if __name__ == "__main__":
    main()
