"""Test suite for Munger Financial Statement Analysis Engine (Task 136)."""

from __future__ import annotations

import os
import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = ROOT / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql://qport:qport@127.0.0.1:5432/qport"

from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_forensics import (
    run_accounting_consistency_checks,
    run_earnings_quality_forensics,
    run_inventory_forensics,
    run_receivables_forensics,
)
from portfolio.value_engine.munger_history_builder import classify_history_depth
from portfolio.policy.models import InvestmentDecisionContext
from portfolio.policy.engine import evaluate_decision


def test_history_depth_classification():
    assert classify_history_depth(2) == "INSUFFICIENT_HISTORY"
    assert classify_history_depth(4) == "LIMITED"
    assert classify_history_depth(6) == "USABLE"
    assert classify_history_depth(8) == "STRONG"
    assert classify_history_depth(12) == "DEEP_HISTORY"


def test_vix_securities_munger_analysis():
    analysis = build_munger_financial_analysis("VIX")
    assert analysis.symbol == "VIX"
    assert analysis.archetype == "SECURITIES"
    assert analysis.history_years >= 5
    assert analysis.data_readiness == "READY"
    assert analysis.earnings_quality.status == "NOT_APPLICABLE"
    assert analysis.value_trap_assessment["status"] == "CLEAR"
    assert analysis.long_term_decision["state"] == "WAIT_FOR_MOS"


def test_acb_bank_munger_analysis():
    analysis = build_munger_financial_analysis("ACB")
    assert analysis.symbol == "ACB"
    assert analysis.archetype == "BANK"
    assert analysis.history_years >= 5
    assert analysis.data_readiness == "READY"
    assert analysis.earnings_quality.status == "NOT_APPLICABLE"
    assert analysis.value_trap_assessment["status"] == "CLEAR"
    assert analysis.long_term_decision["state"] == "WAIT_FOR_MOS"


def test_fpt_dgc_normal_enterprise_analysis():
    for sym in ["FPT", "DGC"]:
        analysis = build_munger_financial_analysis(sym)
        assert analysis.symbol == sym
        assert analysis.archetype == "NORMAL_ENTERPRISE"
        assert analysis.history_years >= 5
        assert analysis.data_readiness == "READY"
        assert analysis.long_term_decision["state"] in ("BUY", "WAIT_FOR_MOS", "AVOID")


def test_qualitative_unknown_does_not_block_bctc_decision():
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_price=100.0,
        base_iv=150.0,
        required_mos=20.0,
        actual_mos=33.3,
        model_status="VALID",
        valuation_confidence="HIGH",
        accounting_reliability="PASS",
        financial_strength="PASS",
        business_review_status="REVIEW_BUSINESS",  # Qualitative UNKNOWN
        circle_of_competence="UNKNOWN",
        moat_assessment="UNKNOWN",
        management_integrity="UNKNOWN",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=1000.0,
        data_readiness={"financial_core": "READY", "valuation": "READY", "value_trap": "READY"},
    )

    ev = evaluate_decision(ctx)
    assert ev.decision == "BUY"
    assert "BUSINESS_REVIEW_INCOMPLETE" not in ev.blocking_reasons


def test_forensics_non_applicable_archetypes():
    dummy_history = {"years": [2021, 2022, 2023, 2024], "by_year": {}}
    
    eq_bank = run_earnings_quality_forensics(dummy_history, archetype="BANK")
    assert eq_bank.status == "NOT_APPLICABLE"

    rec_bank = run_receivables_forensics(dummy_history, archetype="BANK")
    assert rec_bank.status == "NOT_APPLICABLE"

    inv_bank = run_inventory_forensics(dummy_history, archetype="BANK")
    assert inv_bank.status == "NOT_APPLICABLE"
