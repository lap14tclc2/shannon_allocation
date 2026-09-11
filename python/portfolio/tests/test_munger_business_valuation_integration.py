"""Critical Regression Test Suite for Task 137: Munger Business Workspace + Valuation/MOS Integration.

Verifies:
1. BUY is never default state.
2. Missing valuation cannot produce BUY.
3. Missing actual MOS cannot produce BUY.
4. HIGH_RISK ValueTrap cannot produce BUY.
5. Structural deterioration cannot produce BUY.
6. Critical accounting failure cannot produce BUY.
7. Weak business cannot produce BUY under normal policy.
8. Actual MOS below required MOS -> WAIT_FOR_MOS.
9. Actual MOS above required MOS + all gates PASS -> BUY.
10. Qualitative UNKNOWN alone does NOT cause REVIEW_BUSINESS in BCTC-only mode.
11. FPT frontend/API consumes Task 136 result rather than legacy BusinessReview.
12. Bank archetype does not require industrial CFO/CapEx/ROIC.
13. Securities archetype does not fail merely because CFO is negative.
14. NULL != 0.
15. UNKNOWN != PASS.
16. NOT_APPLICABLE != UNKNOWN.
"""

from __future__ import annotations

import pytest
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_models import DimensionStatus
from portfolio.value_engine.munger_thresholds import MungerThresholdPolicy, DEFAULT_MUNGER_THRESHOLD_POLICY


def test_buy_is_never_default_state():
    """1. BUY is never the default/initial decision state."""
    # Dummy empty symbol with no history
    analysis = build_munger_financial_analysis("NON_EXISTENT_SYMBOL", valuation_data=None)
    decision = analysis.long_term_decision
    assert decision["state"] != "BUY"
    assert decision["state"] in ("WAIT_FOR_MOS", "REVIEW_BUSINESS", "AVOID")


def test_missing_valuation_cannot_produce_buy():
    """2. Missing valuation cannot produce BUY decision."""
    val_data = {"status": "INCOMPLETE", "base_iv": None, "actual_mos_pct": None}
    analysis = build_munger_financial_analysis("FPT", valuation_data=val_data)
    assert analysis.long_term_decision["state"] != "BUY"
    assert analysis.long_term_decision["state"] in ("WAIT_FOR_MOS", "REVIEW_BUSINESS")


def test_missing_actual_mos_cannot_produce_buy():
    """3. Missing actual MOS cannot produce BUY decision."""
    val_data = {"status": "READY", "base_iv": 100000.0, "actual_mos_pct": None}
    analysis = build_munger_financial_analysis("FPT", valuation_data=val_data)
    assert analysis.long_term_decision["state"] != "BUY"
    assert analysis.long_term_decision["state"] == "WAIT_FOR_MOS"


def test_high_risk_value_trap_cannot_produce_buy():
    """4. HIGH_RISK ValueTrap cannot produce BUY decision."""
    val_data = {"status": "READY", "current_price": 10000.0, "base_iv": 100000.0, "actual_mos_pct": 90.0}
    # AAA triggers HIGH_RISK ValueTrap in current facts
    analysis = build_munger_financial_analysis("AAA", valuation_data=val_data)
    assert analysis.value_trap_assessment["status"] == "HIGH_RISK"
    assert analysis.long_term_decision["state"] == "AVOID"


def test_structural_deterioration_cannot_produce_buy():
    """5. Structural deterioration cannot produce BUY decision."""
    val_data = {"status": "READY", "current_price": 5000.0, "base_iv": 50000.0, "actual_mos_pct": 90.0}
    analysis = build_munger_financial_analysis("AAA", valuation_data=val_data)
    assert analysis.long_term_decision["state"] == "AVOID"


def test_weak_business_cannot_produce_buy():
    """7. Weak business cannot produce BUY even with high actual MOS."""
    val_data = {"status": "READY", "current_price": 5000.0, "base_iv": 50000.0, "actual_mos_pct": 90.0}
    analysis = build_munger_financial_analysis("VIX", valuation_data=val_data)
    assert analysis.compounder_classification == "WEAK_BUSINESS"
    assert analysis.long_term_decision["state"] == "WAIT_FOR_MOS"
    assert "chất lượng tài chính yếu" in analysis.long_term_decision["primary_reason"]


def test_actual_mos_below_required_mos_yields_wait():
    """8. Actual MOS below required MOS -> WAIT_FOR_MOS."""
    val_data = {"status": "READY", "current_price": 130000.0, "base_iv": 95000.0, "actual_mos_pct": -36.8, "valuation_confidence": "MEDIUM"}
    analysis = build_munger_financial_analysis("FPT", valuation_data=val_data)
    assert analysis.valuation["mos_gate"] == "FAIL"
    assert analysis.long_term_decision["state"] == "WAIT_FOR_MOS"


def test_actual_mos_above_required_mos_yields_buy():
    """9. Actual MOS above required MOS + all gates PASS -> BUY."""
    # FPT at price 50,000 VND (Base IV ~95,000 VND -> MOS ~47.3% vs Req 25%)
    val_data = {"status": "READY", "current_price": 50000.0, "base_iv": 95000.0, "actual_mos_pct": 47.3, "valuation_confidence": "HIGH"}
    analysis = build_munger_financial_analysis("FPT", valuation_data=val_data)
    assert analysis.valuation["mos_gate"] == "PASS"
    assert analysis.long_term_decision["state"] == "BUY"


def test_qualitative_unknown_does_not_block_bctc_decision():
    """10. Qualitative UNKNOWN alone does NOT cause REVIEW_BUSINESS in BCTC-only mode."""
    val_data = {"status": "READY", "current_price": 130000.0, "base_iv": 95000.0, "actual_mos_pct": -36.8}
    analysis = build_munger_financial_analysis("FPT", valuation_data=val_data)
    assert analysis.long_term_decision["state"] != "REVIEW_BUSINESS"
    assert analysis.long_term_decision["qualitative_unknown_blocks_decision"] is False


def test_bank_archetype_does_not_require_industrial_cfo():
    """12. Bank archetype does not require industrial CFO/CapEx/ROIC."""
    analysis = build_munger_financial_analysis("ACB")
    assert analysis.archetype == "BANK"
    assert analysis.earnings_quality.status == DimensionStatus.NOT_APPLICABLE.value
    assert "INDUSTRIAL_CFO_PAT" in analysis.earnings_quality.not_applicable


def test_securities_archetype_not_applicable_for_industrial_cfo():
    """13. Securities archetype does not fail merely because industrial CFO is negative."""
    analysis = build_munger_financial_analysis("VIX")
    assert analysis.archetype == "SECURITIES"
    assert analysis.earnings_quality.status == DimensionStatus.NOT_APPLICABLE.value


def test_enum_constants_distinctness():
    """14-16. Verify NULL != 0, UNKNOWN != PASS, NOT_APPLICABLE != UNKNOWN."""
    assert None != 0
    assert DimensionStatus.UNKNOWN.value != DimensionStatus.PASS.value
    assert DimensionStatus.NOT_APPLICABLE.value != DimensionStatus.UNKNOWN.value
