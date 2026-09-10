"""Universe Canonical Coverage Audit & Summary Generator for QPort."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import re
from typing import Any

from portfolio.finance_catalog import _schema_connection, FINANCE_SCHEMA
from portfolio.financial_data.ssi_ingestion import parse_ssi_filename


def classify_history_depth(years_count: int) -> str:
    if years_count < 3:
        return "INSUFFICIENT"
    elif years_count in (3, 4):
        return "MINIMUM"
    elif years_count in (5, 6):
        return "GOOD"
    elif 7 <= years_count <= 10:
        return "STRONG"
    else:
        return "DEEP_HISTORY"


def determine_archetype(symbol: str) -> str:
    banks = {"ACB", "BID", "CTG", "HDB", "MBB", "MSN", "STB", "TCB", "TPB", "VCB", "VIB", "VPB", "EIB", "ABB", "AAS", "BAB", "BVB", "LPB", "NAB", "OCB", "PBK", "PGB", "SGB", "SSB", "VBB"}
    securities = {"VIX", "SSI", "VND", "HCM", "VCI", "SHS", "MBS", "FTS", "BSI", "CTS", "AGR", "ORS", "TCI", "VDS", "SBS", "IVS", "VIG"}
    if symbol in banks:
        return "BANK"
    if symbol in securities:
        return "SECURITIES"
    return "NORMAL_ENTERPRISE"


def run_canonical_coverage_audit(db_conn) -> dict[str, Any]:
    bctc_dir = Path("F:/DATA_BCTC")
    all_symbols = set()
    if bctc_dir.exists():
        for f in bctc_dir.glob("*.xlsx"):
            meta = parse_ssi_filename(f.name)
            if meta.is_valid and meta.symbol:
                all_symbols.add(meta.symbol)

    symbols_sorted = sorted(list(all_symbols)) if all_symbols else []

    # Fetch facts grouped by symbol, statement_type, fiscal_year
    facts_rows = db_conn.execute(
        """SELECT symbol, statement_type, line_item_code, fiscal_year, provider
           FROM canonical_facts
           WHERE provider = 'ssi'"""
    ).fetchall()

    symbol_data: dict[str, dict[str, Any]] = {}
    for sym in symbols_sorted:
        symbol_data[sym] = {
            "symbol": sym,
            "archetype": determine_archetype(sym),
            "bs_years": set(),
            "is_years": set(),
            "cf_years": set(),
            "canonical_fact_count": 0,
            "raw_fact_count": 0,
            "unmapped_count": 0,
            "conflicted_count": 0,
        }

    for r in facts_rows:
        sym = r["symbol"]
        if sym not in symbol_data:
            symbol_data[sym] = {
                "symbol": sym,
                "archetype": determine_archetype(sym),
                "bs_years": set(),
                "is_years": set(),
                "cf_years": set(),
                "canonical_fact_count": 0,
                "raw_fact_count": 0,
                "unmapped_count": 0,
                "conflicted_count": 0,
            }
        st = r["statement_type"]
        fy = r["fiscal_year"]
        symbol_data[sym]["canonical_fact_count"] += 1
        if fy:
            if st == "BALANCE_SHEET":
                symbol_data[sym]["bs_years"].add(fy)
            elif st == "INCOME_STATEMENT":
                symbol_data[sym]["is_years"].add(fy)
            elif st == "CASH_FLOW":
                symbol_data[sym]["cf_years"].add(fy)

    # Fetch raw observation counts per symbol
    raw_rows = db_conn.execute(
        """SELECT symbol, mapping_status, COUNT(*) as cnt
           FROM ssi_raw_financial_observations
           GROUP BY symbol, mapping_status"""
    ).fetchall()

    for r in raw_rows:
        sym = r["symbol"]
        if sym in symbol_data:
            cnt = r["cnt"]
            symbol_data[sym]["raw_fact_count"] += cnt
            if r["mapping_status"] == "UNMAPPED":
                symbol_data[sym]["unmapped_count"] += cnt

    records = []
    val_ready_count = 0
    val_partial_count = 0
    val_blocked_count = 0

    deep_hist_count = 0
    strong_hist_count = 0
    good_hist_count = 0
    min_hist_count = 0
    insufficient_hist_count = 0

    for sym, d in sorted(symbol_data.items()):
        bs_yrs = sorted(list(d["bs_years"]))
        is_yrs = sorted(list(d["is_years"]))
        cf_yrs = sorted(list(d["cf_years"]))

        bs_first = bs_yrs[0] if bs_yrs else None
        bs_last = bs_yrs[-1] if bs_yrs else None
        bs_count = len(bs_yrs)

        is_first = is_yrs[0] if is_yrs else None
        is_last = is_yrs[-1] if is_yrs else None
        is_count = len(is_yrs)

        cf_first = cf_yrs[0] if cf_yrs else None
        cf_last = cf_yrs[-1] if cf_yrs else None
        cf_count = len(cf_yrs)

        total_years = max(bs_count, is_count, cf_count)
        history_band = classify_history_depth(total_years)

        if history_band == "DEEP_HISTORY":
            deep_hist_count += 1
        elif history_band == "STRONG":
            strong_hist_count += 1
        elif history_band == "GOOD":
            good_hist_count += 1
        elif history_band == "MINIMUM":
            min_hist_count += 1
        else:
            insufficient_hist_count += 1

        raw_cnt = d["raw_fact_count"]
        mapped_cnt = d["canonical_fact_count"]
        coverage_pct = round((mapped_cnt / raw_cnt * 100.0), 2) if raw_cnt > 0 else 0.0

        val_ready = "READY" if (bs_count >= 3 and is_count >= 3) else ("PARTIAL" if total_years >= 1 else "BLOCKED")
        biz_ready = "READY" if (is_count >= 3 and bs_count >= 3) else ("PARTIAL" if total_years >= 1 else "BLOCKED")
        vt_ready = "READY" if (is_count >= 3 and cf_count >= 3) else ("PARTIAL" if total_years >= 1 else "INSUFFICIENT")

        if val_ready == "READY":
            val_ready_count += 1
        elif val_ready == "PARTIAL":
            val_partial_count += 1
        else:
            val_blocked_count += 1

        rec = {
            "symbol": sym,
            "archetype": d["archetype"],
            "balance_sheet_first_fy": bs_first or "",
            "balance_sheet_last_fy": bs_last or "",
            "balance_sheet_years": bs_count,
            "income_statement_first_fy": is_first or "",
            "income_statement_last_fy": is_last or "",
            "income_statement_years": is_count,
            "cash_flow_first_fy": cf_first or "",
            "cash_flow_last_fy": cf_last or "",
            "cash_flow_years": cf_count,
            "canonical_fact_count": mapped_cnt,
            "raw_fact_count": raw_cnt,
            "mapping_coverage_pct": coverage_pct,
            "unmapped_count": d["unmapped_count"],
            "conflicted_count": d["conflicted_count"],
            "valuation_core_ready": val_ready,
            "business_review_core_ready": biz_ready,
            "value_trap_core_ready": vt_ready,
            "history_band": history_band,
            "notes": "SSI Primary Source",
        }
        records.append(rec)

    # Write ssi-canonical-coverage.csv
    reports_dir = Path("docs/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    csv_path = reports_dir / "ssi-canonical-coverage.csv"

    fieldnames = [
        "symbol", "archetype", "balance_sheet_first_fy", "balance_sheet_last_fy", "balance_sheet_years",
        "income_statement_first_fy", "income_statement_last_fy", "income_statement_years",
        "cash_flow_first_fy", "cash_flow_last_fy", "cash_flow_years", "canonical_fact_count",
        "raw_fact_count", "mapping_coverage_pct", "unmapped_count", "conflicted_count",
        "valuation_core_ready", "business_review_core_ready", "value_trap_core_ready", "history_band", "notes"
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    summary_data = {
        "scanned_symbols_total": len(records),
        "valuation_core_ready": val_ready_count,
        "valuation_core_partial": val_partial_count,
        "valuation_core_blocked": val_blocked_count,
        "history_deep_gt_10y": deep_hist_count,
        "history_strong_7_10y": strong_hist_count,
        "history_good_5_6y": good_hist_count,
        "history_minimum_3_4y": min_hist_count,
        "history_insufficient_lt_3y": insufficient_hist_count,
        "primary_provider": "ssi",
        "secondary_providers": ["tcbs", "cafef"],
        "quarterly_data_required": False,
        "quarterly_data_used": False,
    }

    json_path = reports_dir / "ssi-canonical-coverage-summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)

    return summary_data


if __name__ == "__main__":
    os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "postgresql://qport:qport@127.0.0.1:5432/qport")
    with _schema_connection(FINANCE_SCHEMA) as conn:
        res = run_canonical_coverage_audit(conn)
        print("=== SSI CANONICAL COVERAGE AUDIT SUMMARY ===")
        print(json.dumps(res, indent=2))
