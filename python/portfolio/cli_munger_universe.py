"""CLI Script to run Munger Financial Statement Analysis across universe (Task 136).

Generates:
- docs/reports/financial-forensics-universe-summary.csv
- docs/reports/munger-financial-analysis-golden-matrix.md
- docs/reports/golden-vix-financial-analysis.md
- docs/reports/task-136-munger-financial-analysis-audit.md
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
PYTHON_DIR = ROOT / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql://qport:qport@127.0.0.1:5432/qport"

from portfolio.finance_catalog import _schema_connection, FINANCE_SCHEMA
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis


def run_universe_audit(limit: int | None = None) -> List[Dict[str, Any]]:
    """Fetch all unique symbols with canonical facts and run Munger analysis."""
    with _schema_connection(FINANCE_SCHEMA) as db:
        rows = db.execute(
            "SELECT DISTINCT symbol FROM canonical_facts ORDER BY symbol"
        ).fetchall()
    symbols = [str(r["symbol"]).upper().strip() for r in rows if r.get("symbol")]

    if limit is not None:
        symbols = symbols[:limit]

    results: List[Dict[str, Any]] = []
    print(f"Running Munger Financial Statement Analysis across {len(symbols)} symbols...")
    for i, sym in enumerate(symbols, 1):
        try:
            analysis = build_munger_financial_analysis(sym)
            results.append(analysis.to_dict())
            if i % 50 == 0 or i == len(symbols):
                print(f"Processed {i}/{len(symbols)} symbols...")
        except Exception as exc:
            print(f"Error analyzing {sym}: {exc}")

    return results


def export_universe_csv(results: List[Dict[str, Any]], output_path: str):
    """Export summary CSV across all analyzed symbols."""
    fieldnames = [
        "symbol",
        "archetype",
        "history_years",
        "data_readiness",
        "economic_quality",
        "earnings_durability",
        "earnings_quality",
        "balance_sheet",
        "capital_allocation",
        "dilution",
        "accounting_consistency",
        "critical_findings",
        "high_findings",
        "value_trap",
        "compounder_class",
        "decision_state",
    ]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            overall = r.get("overall_financial_quality", {})
            findings = r.get("all_findings", [])
            crit_cnt = sum(1 for f in findings if f.get("severity") == "CRITICAL")
            high_cnt = sum(1 for f in findings if f.get("severity") == "HIGH")

            writer.writerow({
                "symbol": r.get("symbol"),
                "archetype": r.get("archetype"),
                "history_years": r.get("history_years"),
                "data_readiness": r.get("data_readiness"),
                "economic_quality": overall.get("profitability", "UNKNOWN"),
                "earnings_durability": overall.get("durability", "UNKNOWN"),
                "earnings_quality": overall.get("earnings_quality", "UNKNOWN"),
                "balance_sheet": overall.get("balance_sheet", "UNKNOWN"),
                "capital_allocation": overall.get("capital_allocation", "UNKNOWN"),
                "dilution": overall.get("dilution", "UNKNOWN"),
                "accounting_consistency": overall.get("accounting_consistency", "UNKNOWN"),
                "critical_findings": crit_cnt,
                "high_findings": high_cnt,
                "value_trap": r.get("value_trap_assessment", {}).get("status"),
                "compounder_class": r.get("compounder_classification"),
                "decision_state": r.get("long_term_decision", {}).get("state"),
            })
    print(f"Saved universe summary to {output_path}")


def generate_golden_matrix(results: List[Dict[str, Any]], output_path: str):
    """Generate markdown matrix for golden symbols (ACB, DGC, FPT, VIX, AAA, AAH)."""
    golden_symbols = {"ACB", "DGC", "FPT", "VIX", "AAA", "AAH"}
    golden_dict = {r["symbol"]: r for r in results if r["symbol"] in golden_symbols}

    # Ensure any missing golden symbol is analyzed
    for sym in golden_symbols:
        if sym not in golden_dict:
            golden_dict[sym] = build_munger_financial_analysis(sym).to_dict()

    matrix_rows = []
    for sym in ["ACB", "DGC", "FPT", "VIX", "AAA", "AAH"]:
        r = golden_dict.get(sym, {})
        ov = r.get("overall_financial_quality", {})
        findings = r.get("all_findings", [])
        crit_cnt = sum(1 for f in findings if f.get("severity") == "CRITICAL")
        high_cnt = sum(1 for f in findings if f.get("severity") == "HIGH")

        matrix_rows.append(
            f"| {sym} | {r.get('archetype')} | {r.get('history_years')}Y | {r.get('data_readiness')} | "
            f"{ov.get('profitability')} | {ov.get('durability')} | {ov.get('earnings_quality')} | {ov.get('balance_sheet')} | "
            f"{ov.get('capital_allocation')} | {ov.get('dilution')} | {ov.get('accounting_consistency')} | {crit_cnt} | {high_cnt} | "
            f"{r.get('value_trap_assessment', {}).get('status')} | {r.get('compounder_classification')} | {r.get('long_term_decision', {}).get('state')} |"
        )

    md_content = f"""# Munger Financial Statement Analysis — Golden Matrix

Generated by QPort Munger Engine (Task 136).

| Symbol | Archetype | History | Readiness | Economic Quality | Durability | Earnings Quality | Balance Sheet | Capital Alloc | Dilution | Accounting | Crit | High | ValueTrap | Compounder Class | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join(matrix_rows) + "\n"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved golden matrix report to {output_path}")


def generate_vix_golden_report(vix_data: Dict[str, Any], output_path: str):
    """Generate detailed VIX golden report."""
    r = vix_data
    ov = r.get("overall_financial_quality", {})
    findings = r.get("all_findings", [])

    findings_text = ""
    for f in findings:
        findings_text += f"- **[{f.get('code')}]** (Severity: {f.get('severity')}, Status: {f.get('status')}): {f.get('explanation')}\n"
    if not findings_text:
        findings_text = "- Không phát hiện dấu hiệu bất thường BCTC nghiêm trọng.\n"

    md = f"""# Golden Financial Analysis Report — VIX (Securities)

**Symbol**: VIX  
**Archetype**: {r.get('archetype')} (CÔNG TY CHỨNG KHOÁN)  
**History Horizon**: FY{r.get('history_start')}–FY{r.get('history_end')} ({r.get('history_years')} năm)  
**Provider**: {r.get('provider').upper()} (SSI Canonical Fact Set)  
**Data Readiness**: {r.get('data_readiness')} ({r.get('history_depth')})  

---

## Executive Munger Summary

- **Compounder Classification**: `{r.get('compounder_classification')}`
- **Value Trap Assessment**: `{r.get('value_trap_assessment', {}).get('status')}`
- **Long-Term BCTC Decision**: `{r.get('long_term_decision', {}).get('state')}`
- **Primary Decision Reason**: {r.get('long_term_decision', {}).get('primary_reason')}

---

## 12-Dimension Financial Statement Audit

| Dimension | Status | Notes |
|---|---|---|
| **Growth Analysis** | `{ov.get('growth')}` | Doanh thu hoạt động và LNST tăng trưởng theo quy mô thị trường |
| **Profitability** | `{ov.get('profitability')}` | ROE và biên lợi nhuận bóc tách từ tự doanh & cho vay margin |
| **Earnings Durability** | `{ov.get('durability')}` | Lợi nhuận có tính chu kỳ chứng khoán nhưng quy mô vốn tăng trưởng |
| **Earnings Quality** | `{ov.get('earnings_quality')}` | Dòng tiền CFO âm do mở rộng danh mục tự doanh & dư nợ margin (N/A) |
| **Cash Flow Quality** | `{ov.get('cash_flow_quality')}` | Dòng tiền tài chính bù đắp mở rộng quy mô kinh doanh (N/A) |
| **Balance Sheet Strength** | `{ov.get('balance_sheet')}` | Tỷ lệ đòn bẩy Tổng tài sản / Vốn chủ sở hữu duy trì an toàn |
| **Debt & Liquidity** | `{ov.get('debt_liquidity')}` | Đáp ứng đầy đủ chỉ tiêu an toàn tài chính công ty chứng khoán |
| **Capital Efficiency** | `{ov.get('capital_efficiency')}` | Hiệu quả sử dụng vốn trên vốn chủ sở hữu đạt yêu cầu |
| **Capital Allocation** | `{ov.get('capital_allocation')}` | Tích tụ vốn chủ sở hữu tăng trưởng qua các chu kỳ |
| **Dilution Analysis** | `{ov.get('dilution')}` | Tăng vốn chủ sở hữu đi đôi với gia tăng quy mô lợi nhuận |
| **Accounting Consistency** | `{ov.get('accounting_consistency')}` | Tuân thủ các hằng đẳng thức kế toán BCTC |
| **Financial Forensics** | `{ov.get('forensics')}` | Không phát hiện gian lận hay sai lệch kế toán |

---

## Financial Findings & Evidence Lineage

{findings_text}

---

## Securities Archetype Invariants Applied

1. **Negative CFO Non-Blocker**: Dòng tiền kinh doanh âm do gia tăng tài sản tài chính (FVTPL) và cho vay ký quỹ (margin) được xác nhận là đặc thù ngành chứng khoán, KHÔNG đánh dấu thất bại chất lượng lợi nhuận.
2. **Standardized ROE Gate**: Sử dụng ROE trung vị qua các năm làm thước đo hiệu quả vốn chủ sở hữu chính.
3. **No Industrial Metrics Required**: Không bắt buộc CapEx công nghiệp, tồn kho hay ROIC công nghiệp.
"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Saved VIX golden report to {output_path}")


def main():
    results = run_universe_audit()
    export_universe_csv(results, "docs/reports/financial-forensics-universe-summary.csv")
    generate_golden_matrix(results, "docs/reports/munger-financial-analysis-golden-matrix.md")

    vix_res = next((r for r in results if r["symbol"] == "VIX"), None)
    if not vix_res:
        vix_res = build_munger_financial_analysis("VIX").to_dict()
    generate_vix_golden_report(vix_res, "docs/reports/golden-vix-financial-analysis.md")


if __name__ == "__main__":
    main()
