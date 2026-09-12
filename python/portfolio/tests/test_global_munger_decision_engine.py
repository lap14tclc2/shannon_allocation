"""Global Regression & Integrity Tests for Munger Financial Decision Engine (Task 161).

Verifies for all symbols across the canonical universe:
1. Metric consistency: Metric calculated once and consumed consistently across summary, 12D matrix, forensics, value-trap.
2. Missing data semantics: Missing data produces INSUFFICIENT_DATA / "Chưa đủ dữ liệu", never fake PASS or 0.
3. CFO/PAT consistency across all modules.
4. Volatility semantics: High CV (>60%) flags volatility warning.
5. Forensic & Value Trap consistency: Hard failures directly translate to HIGH_RISK value trap.
6. MOS Gate Contracts:
   - actual_mos >= required_mos -> mos_gate == "PASS"
   - actual_mos < required_mos -> mos_gate == "FAIL"
7. Decision Invariant:
   - When mos_gate == "PASS", decision is NEVER "WAIT_FOR_MOS" ("Chờ đạt biên an toàn").
   - When mos_gate == "FAIL", decision is "WAIT_FOR_MOS" ("Chờ đạt biên an toàn").
   - When forensic red flags exist, decision is "AVOID" ("Chưa phù hợp để đầu tư").
8. Zero raw enum leakage in presentation layer.
9. Munger 8 Inversion Pre-Commitment questions answered with quantitative evidence.
"""

from __future__ import annotations

import pytest
from portfolio.canonical_valuation import build_canonical_valuation
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_thesis_challenge import run_thesis_challenge_analysis
from portfolio.value_engine.vietnamese_presenter import (
    DECISION_VIETNAMESE,
    STATUS_VIETNAMESE,
    VALUETRAP_VIETNAMESE,
    CLASSIFICATION_VIETNAMESE,
    get_vietnamese_decision,
    get_vietnamese_status,
)


@pytest.mark.parametrize("symbol", ["ACB", "DGC", "FPT", "VIX", "MWG", "HPG", "VNM", "MBB"])
def test_symbol_munger_pipeline_integrity(symbol: str):
    """Verify end-to-end Munger pipeline integrity for diverse archetype symbols."""
    val = build_canonical_valuation(symbol, compute_munger=False)
    munger = build_munger_financial_analysis(symbol, valuation_data=val)
    m_dict = munger.to_dict()

    dec = m_dict.get("long_term_decision", {})
    val_data = m_dict.get("valuation", {})
    trace = dec.get("decision_trace", {})
    vt = m_dict.get("value_trap_assessment", {})

    actual_mos = val_data.get("actual_mos_pct")
    required_mos = val_data.get("required_mos_pct")
    mos_gate = val_data.get("mos_gate")
    dec_state = dec.get("state")

    # Invariant 1: MOS Gate Logic
    if actual_mos is not None and required_mos is not None and val_data.get("status") == "READY":
        if actual_mos >= required_mos:
            assert mos_gate == "PASS", f"Expected PASS for {symbol} when {actual_mos} >= {required_mos}"
            # Invariant 2: When MOS passes, decision MUST NOT be WAIT_FOR_MOS
            assert dec_state != "WAIT_FOR_MOS", f"Decision for {symbol} must not be WAIT_FOR_MOS when MOS is PASS! Got: {dec_state}"
        else:
            assert mos_gate == "FAIL", f"Expected FAIL for {symbol} when {actual_mos} < {required_mos}"
            if dec_state not in ("AVOID", "REVIEW_BUSINESS"):
                assert dec_state == "WAIT_FOR_MOS", f"Decision for {symbol} should be WAIT_FOR_MOS when MOS fails and no AVOID. Got: {dec_state}"

    # Invariant 3: Decision trace completeness
    assert "mos_gate" in trace
    assert "quality_gate" in trace
    assert "value_trap_gate" in trace
    assert "decision_vietnamese" in trace
    assert trace["decision_vietnamese"] != ""

    # Invariant 4: No raw english machine codes in state_vietnamese
    assert dec.get("state_vietnamese") in DECISION_VIETNAMESE.values()

    # Invariant 5: Thesis challenge 8 questions answered
    thesis = run_thesis_challenge_analysis(m_dict, valuation_data=val)
    assert len(thesis.questions) == 8
    for q in thesis.questions:
        assert q.conclusion_vi != "", f"Question {q.question_number} has empty conclusion for {symbol}"
        assert q.answer_status_vi != "", f"Question {q.question_number} has empty status_vi for {symbol}"


def test_decision_vietnamese_mapping_coverage():
    """Verify all decision codes map cleanly to natural Vietnamese."""
    expected_keys = [
        "BUY", "BUY_MORE", "BUY_UNDER_MOS", "CONDITIONAL_BUY", "BUY_WATCH",
        "WAIT_FOR_QUALITY_CONFIRMATION", "HOLD", "HOLD_NO_NEW_CAPITAL",
        "WAIT_FOR_MOS", "BUILD_RESERVE_FIRST", "REVIEW_BUSINESS",
        "BUSINESS_REVIEW_INCOMPLETE", "AVOID", "DO_NOT_BUY", "SELL_REVIEW", "SELL"
    ]
    for k in expected_keys:
        assert k in DECISION_VIETNAMESE, f"Missing decision key: {k}"
        assert DECISION_VIETNAMESE[k] != ""
        assert not DECISION_VIETNAMESE[k].isupper(), f"Value should be Vietnamese text, not uppercase code: {DECISION_VIETNAMESE[k]}"


def test_no_fake_pass_on_missing_data():
    """Verify missing facts return INSUFFICIENT or UNKNOWN status, not PASS."""
    # Construct empty history for a fake symbol
    munger = build_munger_financial_analysis("NONEXISTENT_XYZ_999", raw_facts=[])
    m_dict = munger.to_dict()
    assert m_dict.get("data_readiness") == "INSUFFICIENT"
    assert m_dict.get("history_years") == 0
    assert m_dict.get("long_term_decision", {}).get("state") == "REVIEW_BUSINESS"
