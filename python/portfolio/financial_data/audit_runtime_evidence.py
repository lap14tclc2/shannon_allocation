"""Generate Buffett SSI Runtime Evidence Audit Report."""

from __future__ import annotations

import json
import os
from pathlib import Path

from portfolio.canonical_valuation import build_canonical_valuation
from portfolio.policy.context_builder import build_decision_context
from portfolio.finance_catalog import _schema_connection, FINANCE_SCHEMA


GOLDEN_SYMBOLS = ["ACB", "DGC", "FPT", "VIX"]


def generate_runtime_evidence_report(db_conn) -> str:
    md_lines = [
        "# Buffett SSI Runtime Evidence Audit Report",
        "",
        "**Generated Date**: 2026-09-10  ",
        "**Primary Fundamental Source**: SSI (`provider = 'ssi'`)  ",
        "**Runtime Path**: PostgreSQL Canonical Facts -> Valuation Engine -> Business Review -> Value Trap  ",
        "",
        "---",
        "",
    ]

    for sym in GOLDEN_SYMBOLS:
        # Build canonical valuation
        val = build_canonical_valuation(sym, market_price=50000.0)
        
        # Build investment decision context
        ctx = build_decision_context(
            symbol=sym,
            valuation=val if val.get("ok") else None,
            personal_finance=None,
        )

        archetype = val.get("archetype", "NORMAL_ENTERPRISE")
        if sym in {"ACB", "BID", "CTG", "HDB", "MBB", "MSN", "STB", "TCB", "TPB", "VCB", "VIB", "VPB"}:
            archetype = "BANK"
        elif sym in {"VIX", "SSI", "VND", "HCM", "VCI"}:
            archetype = "SECURITIES"

        md_lines.append(f"## {sym} — Archetype: {archetype}")
        md_lines.append("")
        md_lines.append("### DATA COVERAGE")
        md_lines.append(f"- **Balance Sheet**: {'AVAILABLE' if 'BS' not in ctx.missing_data else 'MISSING'}")
        md_lines.append(f"- **Income Statement**: {'AVAILABLE' if 'IS' not in ctx.missing_data else 'MISSING'}")
        md_lines.append(f"- **Cash Flow**: {'AVAILABLE' if 'CF' not in ctx.missing_data else 'MISSING'}")
        md_lines.append(f"- **Missing Data Items**: {', '.join(ctx.missing_data) if ctx.missing_data else 'None'}")
        md_lines.append("")

        md_lines.append("### VALUATION")
        md_lines.append(f"- **Selected Source**: {val.get('provider', 'ssi').upper()} (Primary)")
        md_lines.append(f"- **Model**: {val.get('valuation_model', 'N/A')}")
        md_lines.append(f"- **Base Intrinsic Value**: {val.get('intrinsic_value', 'N/A')}")
        md_lines.append(f"- **Margin of Safety**: {val.get('margin_of_safety_pct', 'N/A')}%")
        md_lines.append(f"- **Quality Verdict**: {val.get('quality_verdict', 'UNKNOWN')}")
        md_lines.append("")

        md_lines.append("### BUSINESS REVIEW")
        md_lines.append(f"- **Circle of Competence**: {ctx.circle_of_competence}")
        md_lines.append(f"- **Business Quality Score**: {ctx.quality_score or 'N/A'}")
        md_lines.append(f"- **Financial Strength**: {ctx.financial_strength}")
        md_lines.append(f"- **Earnings Durability**: {ctx.earnings_durability}")
        md_lines.append(f"- **Moat**: {ctx.moat_assessment}")
        md_lines.append(f"- **Capital Allocation**: {ctx.capital_allocation_quality}")
        md_lines.append(f"- **Accounting Reliability**: {ctx.accounting_reliability}")
        md_lines.append("")

        md_lines.append("### VALUE TRAP")
        md_lines.append(f"- **Status**: {ctx.value_trap_status}")
        md_lines.append(f"- **Hard Rejects**: {', '.join(ctx.hard_rejects) if ctx.hard_rejects else 'None'}")
        md_lines.append(f"- **Warnings**: {', '.join(ctx.warnings) if ctx.warnings else 'None'}")
        md_lines.append("")

        md_lines.append("### REPRESENTATIVE LINEAGE (PostgreSQL Canonical Facts)")
        if facts:
            md_lines.append("| Line Item Code | Fiscal Year | Value | Provider | Quality Status |")
            md_lines.append("|---|---|---|---|---|")
            for f in facts:
                val_fmt = f"{f['value']:,.2f}" if isinstance(f["value"], (int, float)) else str(f["value"])
                md_lines.append(f"| `{f['line_item_code']}` | FY{f['fiscal_year']} | {val_fmt} | {f['provider'].upper()} | {f['quality_status']} |")
        else:
            md_lines.append("*No canonical rows found in database for SSI provider.*")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    report_content = "\n".join(md_lines)
    out_path = Path("docs/reports/buffett-ssi-runtime-evidence-audit.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    return str(out_path)


if __name__ == "__main__":
    os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "postgresql://qport:qport@127.0.0.1:5432/qport")
    with _schema_connection(FINANCE_SCHEMA) as conn:
        path = generate_runtime_evidence_report(conn)
        print(f"Generated runtime evidence audit report at: {path}")
