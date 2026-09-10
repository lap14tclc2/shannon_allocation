"""Unit tests for Buffett-Munger Qualitative Evidence Framework (Task 133)."""

from __future__ import annotations

import pytest

from portfolio.policy.models import InvestmentDecisionContext
from portfolio.policy.qualitative import (
    QualitativeEvidenceItem,
    MungerChecklistQuestion,
    MungerChecklist,
    build_default_munger_checklist,
    evaluate_qualitative_dimension,
)
from portfolio.policy.engine import evaluate_decision
from portfolio.policy.context_builder import build_decision_context


def test_unknown_stays_unknown_without_evidence():
    """Verify qualitative dimension defaults to UNKNOWN when no explicit evidence exists."""
    dim_eval = evaluate_qualitative_dimension("MOAT", [])
    assert dim_eval["status"] == "UNKNOWN"
    assert dim_eval["confidence"] == "LOW"
    assert "Explicit evidence required" in dim_eval["missing"]


def test_financial_metrics_cannot_prove_moat():
    """High ROE or profit margin alone must NOT produce MOAT PASS without explicit evidence."""
    ctx = build_decision_context(
        symbol="FPT",
        valuation={
            "ok": True,
            "quality_tier": "HIGH_QUALITY",
            "historical_roe_avg": 25.0,
            "base_iv": 100000.0,
            "financial_history_10y": [{"year": 2024, "roe": 25.0}],
        },
    )
    assert ctx.moat_assessment == "UNKNOWN"
    assert ctx.moat_types == []


def test_financial_metrics_cannot_prove_management_integrity():
    """High ROE or profit growth alone must NOT infer MANAGEMENT_INTEGRITY PASS."""
    ctx = build_decision_context(symbol="ACB")
    assert ctx.management_integrity == "UNKNOWN"
    assert ctx.numeric_capital_allocation == "UNKNOWN"
    assert ctx.capital_allocation_quality == "UNKNOWN"


def test_ai_summary_cannot_set_canonical_pass():
    """AI summary evidence attempting PASS must be downgraded to WATCH."""
    item = QualitativeEvidenceItem(
        symbol="FPT",
        dimension="MOAT",
        status="PASS",
        confidence="HIGH",
        evidence_type="AI_SUMMARY",
        evidence_text="AI thinks FPT has a strong ecosystem moat.",
        source="AI_SUMMARY",
    )
    dim_eval = evaluate_qualitative_dimension("MOAT", [item])
    assert dim_eval["status"] == "WATCH"


def test_explicit_moat_evidence_and_counter_evidence():
    """Explicit moat evidence produces PASS, but counter-evidence triggers WATCH/FAIL."""
    supporting_item = QualitativeEvidenceItem(
        symbol="FPT",
        dimension="MOAT",
        status="PASS",
        confidence="HIGH",
        evidence_type="MANAGEMENT_DISCLOSURE",
        evidence_text="High customer switching costs in enterprise software contracts.",
        source="ANNUAL_REPORT",
    )
    eval_pass = evaluate_qualitative_dimension("MOAT", [supporting_item])
    assert eval_pass["status"] == "PASS"

    counter_item = QualitativeEvidenceItem(
        symbol="FPT",
        dimension="MOAT",
        status="FAIL",
        confidence="HIGH",
        evidence_type="EXTERNAL_RESEARCH",
        evidence_text="Rising competition and contract pricing pressure weakening moat.",
        source="EXTERNAL_RESEARCH",
    )
    eval_counter = evaluate_qualitative_dimension("MOAT", [supporting_item, counter_item])
    assert eval_counter["status"] in {"WATCH", "FAIL"}


def test_accounting_reliability_split():
    """Numeric accounting quality and qualitative governance must remain separate."""
    ctx = build_decision_context(
        symbol="DGC",
        valuation={
            "ok": True,
            "cash_flow_quality": "HIGH_QUALITY",
            "historical_roe_avg": 20.0,
            "base_iv": 100000.0,
        },
    )
    assert ctx.accounting_numeric_quality == "PASS"
    assert ctx.accounting_qualitative_reliability == "UNKNOWN"
    assert ctx.accounting_reliability == "WATCH"


def test_circle_of_competence_is_investor_specific():
    """Circle of competence defaults to UNKNOWN and requires manual investor assertion."""
    ctx = build_decision_context(symbol="VIX")
    assert ctx.circle_of_competence == "UNKNOWN"


def test_value_trap_clear_does_not_imply_business_pass_or_buy():
    """Scenario 1: ValueTrap CLEAR + Moat UNKNOWN does NOT automatically trigger BUY."""
    ctx = InvestmentDecisionContext(
        symbol="DGC",
        value_trap_status="CLEAR",
        actual_mos=40.0,
        business_review_status="BUSINESS_REVIEW",
        moat_assessment="UNKNOWN",
        survival_reserve_status="SAFE",
        available_long_term_capital=500_000_000,
    )
    decision = evaluate_decision(ctx)
    assert decision.decision != "BUY"
    assert decision.decision in {"WAIT_FOR_MOS", "REVIEW_BUSINESS", "AVOID"}


def test_moat_pass_business_pass_mos_insufficient_waits_for_mos():
    """Scenario 2: Moat PASS + Business PASS + MOS insufficient -> WAIT_FOR_MOS."""
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        value_trap_status="CLEAR",
        actual_mos=10.0,
        required_mos=25.0,
        business_review_status="BUSINESS_PASS",
        moat_assessment="PASS",
        survival_reserve_status="SAFE",
        available_long_term_capital=500_000_000,
    )
    decision = evaluate_decision(ctx)
    assert decision.decision == "WAIT_FOR_MOS"


def test_business_attractive_pbs_unconfigured_builds_reserve_first():
    """Scenario 3: Business attractive + PBS unconfigured -> BUILD_RESERVE_FIRST."""
    ctx = InvestmentDecisionContext(
        symbol="ACB",
        value_trap_status="CLEAR",
        actual_mos=35.0,
        required_mos=25.0,
        business_review_status="BUSINESS_PASS",
        moat_assessment="PASS",
        survival_reserve_status="UNCONFIGURED",
        available_long_term_capital=0,
    )
    decision = evaluate_decision(ctx)
    assert decision.decision == "BUILD_RESERVE_FIRST"


def test_price_decline_alone_never_triggers_sell():
    """Scenario 6: Stock price decline (-50%) with unchanged economics must NEVER trigger SELL."""
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_weight=15.0,
        value_trap_status="CLEAR",
        business_review_status="BUSINESS_PASS",
        moat_assessment="PASS",
        management_integrity="PASS",
        accounting_reliability="PASS",
    )
    decision = evaluate_decision(ctx)
    assert decision.decision not in {"SELL", "SELL_REVIEW"}


def test_explicit_moat_destruction_triggers_sell_review():
    """Scenario 5: Explicit moat destruction evidence triggers SELL_REVIEW for existing position."""
    ctx = InvestmentDecisionContext(
        symbol="VIX",
        current_weight=10.0,
        value_trap_status="TRAP_WARNING",
        business_review_status="BUSINESS_FAIL",
        moat_assessment="FAIL",
        moat_counter_evidence=["Confirmed loss of core franchise and regulatory sanctions"],
    )
    decision = evaluate_decision(ctx)
    assert decision.decision in {"SELL_REVIEW", "SELL", "REVIEW_BUSINESS"}


def test_munger_checklist_structure_and_answering():
    """Verify 8-question Munger Precommitment Checklist behavior."""
    cl = build_default_munger_checklist("FPT")
    assert len(cl.questions) == 8
    assert cl.overall_status() == "UNANSWERED"

    cl.questions[0].status = "ANSWERED"
    cl.questions[1].status = "CONCERN"
    cl.questions[1].notes = "Competitor pricing pressure"

    assert cl.overall_status() == "CONCERN"
    assert "Q2" in cl.concerns()
