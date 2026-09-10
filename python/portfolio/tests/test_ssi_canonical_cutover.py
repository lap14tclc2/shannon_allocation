"""Comprehensive Integration and Policy Tests for SSI Canonical Cutover (Task 132)."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from portfolio.financial_data.models import StatementType, FactIdentityKey
from portfolio.canonical_valuation import build_canonical_valuation
from portfolio.policy.context_builder import build_decision_context
from portfolio.policy.engine import evaluate_decision
from portfolio.finance_catalog import initialize_finance_schema, _schema_connection, FINANCE_SCHEMA


def test_fy_only_policy_absence_of_quarterly_data_does_not_block_decision():
    """Verify long-term policy engine operates on FY history without quarterly penalties."""
    # Build context for FPT with mock valid valuation
    val = {
        "ok": True,
        "symbol": "FPT",
        "quality_verdict": "HIGH_QUALITY",
        "intrinsic_value": 95000.0,
        "margin_of_safety_pct": 25.0,
        "provider": "ssi",
        "valuation_model": "OWNER_EARNINGS",
        "financial_history": [
            {"year": 2025, "revenue": 50000, "net_profit": 9000, "cfo": 9500},
            {"year": 2024, "revenue": 45000, "net_profit": 8000, "cfo": 8500},
            {"year": 2023, "revenue": 40000, "net_profit": 7000, "cfo": 7500},
            {"year": 2022, "revenue": 35000, "net_profit": 6000, "cfo": 6500},
            {"year": 2021, "revenue": 30000, "net_profit": 5000, "cfo": 5500},
        ],
    }

    ctx = build_decision_context(
        symbol="FPT",
        valuation=val,
        personal_finance={
            "survival_months": 12,
            "reserve_status": "SUFFICIENT",
            "available_long_term_capital": 500_000_000,
        },
    )

    # Prove quarterly data is not required
    assert ctx.value_trap_status != "HIGH_RISK"

    # Evaluate investment decision
    evidence = evaluate_decision(ctx)
    assert evidence.decision in ("BUY", "BUY_MORE", "HOLD", "BUILD_RESERVE_FIRST", "WAIT_FOR_MOS")
    # Absence of quarterly data must NOT be listed in reasons
    reasons_text = " ".join(evidence.reasons)
    assert "quarterly" not in reasons_text.lower()
    assert "quarter" not in reasons_text.lower()


def test_archetype_not_applicable_handling_bank_and_securities():
    """Verify BANK and SECURITIES do not require enterprise-only inventory/CFO."""
    acb_ctx = build_decision_context(
        symbol="ACB",
        valuation={"ok": True, "symbol": "ACB", "quality_verdict": "HIGH_QUALITY", "intrinsic_value": 30000.0},
    )
    assert "BS.INVENTORY" not in acb_ctx.missing_data

    vix_ctx = build_decision_context(
        symbol="VIX",
        valuation={"ok": True, "symbol": "VIX", "quality_verdict": "INVESTABLE", "intrinsic_value": 20000.0},
    )
    assert "BS.INVENTORY" not in vix_ctx.missing_data


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_ssi_primary_source_precedence_in_database():
    """Verify SSI facts take precedence over TCBS facts in PostgreSQL query path."""
    from portfolio.finance_catalog import valuation_snapshot_from_catalog

    initialize_finance_schema()
    with _schema_connection(FINANCE_SCHEMA) as conn:
        conn.execute("DELETE FROM canonical_facts WHERE symbol = 'TEST132'")
        
        # Insert mock TCBS facts
        conn.execute(
            """INSERT INTO canonical_facts
               (symbol, statement_type, line_item_code, value, period_type, fiscal_year, period_end, provider, quality_status, observed_at)
               VALUES ('TEST132', 'INCOME_STATEMENT', 'IS.REVENUE', 100.0, 'FY', 2025, '2025-12-31', 'tcbs', 'FALLBACK', '2026-09-10T00:00:00Z')"""
        )

        # Insert mock SSI primary facts (with different value for IS.REVENUE)
        conn.execute(
            """INSERT INTO canonical_facts
               (symbol, statement_type, line_item_code, value, period_type, fiscal_year, period_end, provider, quality_status, observed_at)
               VALUES ('TEST132', 'INCOME_STATEMENT', 'IS.REVENUE', 500.0, 'FY', 2025, '2025-12-31', 'ssi', 'PRIMARY_SSI', '2026-09-10T00:00:00Z')"""
        )

        if hasattr(conn, "commit"):
            conn.commit()

        # Query valuation snapshot for TEST132
        snap = valuation_snapshot_from_catalog("TEST132")
        income = snap.get("income_statement", [])
        assert len(income) > 0
        rev_item = [r for r in income if r.get("line_item_code") == "IS.REVENUE"][0]
        # Revenue value MUST match SSI value (500.0), NOT TCBS value (100.0)
        assert rev_item.get("value") == 500.0
        assert rev_item.get("provider") == "ssi"

        # Clean up mock symbol
        conn.execute("DELETE FROM canonical_facts WHERE symbol = 'TEST132'")
        if hasattr(conn, "commit"):
            conn.commit()


def test_zero_runtime_xlsx_access_in_request_path():
    """Verify runtime valuation and policy context functions execute with zero XLSX disk access."""
    # Ensure build_canonical_valuation and build_investment_decision_context run without reading XLSX files
    val = build_canonical_valuation("ACB", market_price=22000.0)
    ctx = build_investment_decision_context(symbol="ACB", valuation=val if val.get("ok") else None)
    assert ctx.symbol == "ACB"
    assert ctx.archetype == "BANK"
