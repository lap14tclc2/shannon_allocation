"""Generate Buffett-Munger Qualitative Evidence Audit Report (Task 133)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from portfolio.canonical_valuation import build_canonical_valuation
from portfolio.policy.context_builder import build_decision_context
from portfolio.policy.engine import evaluate_decision
from portfolio.policy.qualitative import build_default_munger_checklist, evaluate_qualitative_dimension
from portfolio.finance_catalog import _schema_connection, FINANCE_SCHEMA


GOLDEN_SYMBOLS = ["ACB", "DGC", "FPT", "VIX"]


def generate_qualitative_evidence_audit_report(db_conn) -> str:
    md_lines = [
        "# Buffett-Munger Qualitative Evidence Audit Report",
        "",
        "**Generated Date**: 2026-09-10  ",
        "**Framework**: Quantitative / Qualitative Evidence Separation & Falsification Discipline  ",
        "**Principle**: Financial statement numbers alone must NEVER fabricate qualitative PASS dimensions.  ",
        "",
        "---",
        "",
    ]

    for sym in GOLDEN_SYMBOLS:
        val = None

        ctx = build_decision_context(
            symbol=sym,
            valuation=val if isinstance(val, dict) and val.get("ok") else None,
            personal_finance={
                "survival_reserve_status": "SAFE",
                "available_long_term_capital": 500_000_000,
            },
        )
        decision_evidence = evaluate_decision(ctx)
        munger_cl = build_default_munger_checklist(sym)

        archetype = "BANK" if sym in {"ACB"} else ("SECURITIES" if sym in {"VIX"} else "NORMAL_ENTERPRISE")

        md_lines.append(f"## {sym} — Archetype: {archetype}")
        md_lines.append("")

        # 1. Understandability
        md_lines.append("### 1. UNDERSTANDABILITY / CIRCLE OF COMPETENCE")
        md_lines.append(f"- **Status**: `{ctx.circle_of_competence}`")
        md_lines.append(f"- **Source**: `MANUAL_USER_REVIEW` (Default: UNKNOWN until investor asserts competence)")
        md_lines.append(f"- **Supporting Evidence**: Explicit business model description required.")
        md_lines.append(f"- **Missing**: Investor circle of competence confirmation.")
        md_lines.append("")

        # 2. Moat
        md_lines.append("### 2. MOAT & FALSIFICATION")
        md_lines.append(f"- **Status**: `{ctx.moat_assessment}`")
        md_lines.append(f"- **Moat Types**: {', '.join(ctx.moat_types) if ctx.moat_types else 'None (Explicit evidence required)'}")
        md_lines.append(f"- **Supporting Evidence**: {', '.join(ctx.moat_supporting_evidence) if ctx.moat_supporting_evidence else 'None (Financial metrics alone cannot prove moat)'}")
        md_lines.append(f"- **Counter Evidence (Falsification)**: {', '.join(ctx.moat_counter_evidence) if ctx.moat_counter_evidence else 'None observed'}")
        md_lines.append(f"- **Missing**: Explicit competitive advantage evidence (e.g. cost curve, switching costs, scale economics).")
        md_lines.append("")

        # 3. Management / Capital Allocation Split
        md_lines.append("### 3. MANAGEMENT & CAPITAL ALLOCATION SPLIT")
        md_lines.append(f"- **Numeric Capital Allocation**: `{ctx.numeric_capital_allocation}` (Derived from ROIC / retained earnings returns)")
        md_lines.append(f"- **Management Integrity (Qualitative)**: `{ctx.management_integrity}` (Default: UNKNOWN)")
        md_lines.append(f"- **Aggregate Capital Allocation Quality**: `{ctx.capital_allocation_quality}`")
        md_lines.append(f"- **Missing**: Qualitative governance / management integrity disclosure.")
        md_lines.append("")

        # 4. Accounting Reliability Split
        md_lines.append("### 4. ACCOUNTING RELIABILITY SPLIT")
        md_lines.append(f"- **Numeric Quality**: `{ctx.accounting_numeric_quality}` (CFO / cash conversion audit)")
        md_lines.append(f"- **Qualitative Governance**: `{ctx.accounting_qualitative_reliability}` (Auditor qualification & related-party disclosure)")
        md_lines.append(f"- **Aggregate Reliability**: `{ctx.accounting_reliability}`")
        md_lines.append("")

        # 5. Munger Precommitment Checklist
        md_lines.append("### 5. MUNGER PRECOMMITMENT CHECKLIST")
        md_lines.append(f"- **Checklist Status**: `{ctx.munger_checklist_status}`")
        md_lines.append("- **Questions Overview**:")
        for q in munger_cl.questions:
            md_lines.append(f"  - [{q.question_id}] {q.question_text}: `{q.status}`")
        md_lines.append(f"- **Concerns**: {', '.join(ctx.munger_checklist_concerns) if ctx.munger_checklist_concerns else 'None'}")
        md_lines.append("")

        # 6. Decision Impact
        md_lines.append("### 6. DECISION IMPACT")
        md_lines.append(f"- **Decision**: `{decision_evidence.decision}`")
        md_lines.append(f"- **Confidence**: `{decision_evidence.confidence}`")
        md_lines.append(f"- **Summary**: {decision_evidence.summary}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    report_content = "\n".join(md_lines)
    out_path = Path("docs/reports/buffett-munger-qualitative-evidence-audit.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    return str(out_path)


if __name__ == "__main__":
    path = generate_qualitative_evidence_audit_report(None)
    print(f"Generated qualitative evidence audit report at: {path}")

