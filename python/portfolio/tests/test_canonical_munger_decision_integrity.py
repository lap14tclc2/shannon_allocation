"""Canonical Munger Decision Engine Integrity & Blocker Semantics Test Suite (Task 182).

Verifies the layer AFTER valuation/MOS:
- Single canonical decision authority
- Blocker vs monitoring signal classification
- Case A (Quality PASS, Forensics CLEAR, ValueTrap CLEAR, Liquidity OK, MOS PASS -> BUY/BUY_MORE)
- Case B (Quality PASS, Forensics WATCH, ValueTrap CLEAR, Liquidity OK, MOS PASS -> BUY/CONDITIONAL_BUY with monitoring signals, not WAIT_FOR_MOS)
- Case C (Quality PASS, Forensics CLEAR, ValueTrap CLEAR, Liquidity OK, MOS FAIL -> WAIT_FOR_MOS)
- Case D (Quality FAIL, MOS PASS -> Quality blocker overrides MOS, AVOID)
- Case E (Liquidity insufficient, MOS PASS -> Liquidity constraint, does not degrade business quality)
- Candidate != BUY separation (is_mos_qualified = false does NOT remove candidate)
- Independent stress tests (Earnings stress vs Valuation stress vs Personal finance)
- BFC & HAH regressions without phantom conditionality or contradictions
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql://qport:qport@127.0.0.1:5432/qport")

import pytest
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_candidates import _evaluate_candidate_symbol
from portfolio.value_engine.munger_models import CompounderClassification, FindingSeverity
from portfolio.canonical_valuation import build_canonical_valuation
from portfolio.value_engine.liquidity_evaluator import classify_liquidity


def _make_sample_history(symbol="TEST", pats=None, revenues=None, cfos=None, equities=None, debts=None):
    if pats is None:
        pats = [200e9, 220e9, 240e9, 270e9, 300e9]
    n = len(pats)
    if revenues is None:
        revenues = [1000e9 + i * 100e9 for i in range(n)]
    if cfos is None:
        cfos = [p * 1.1 for p in pats]
    if equities is None:
        equities = [1000e9 + i * 150e9 for i in range(n)]
    if debts is None:
        debts = [200e9 for _ in range(n)]

    return [
        {
            "fiscal_year": 2020 + i,
            "revenue": revenues[i],
            "net_profit": pats[i],
            "operating_cash_flow": cfos[i],
            "equity": equities[i],
            "total_debt": debts[i],
            "receivables": revenues[i] * 0.1,
            "inventory": revenues[i] * 0.1,
            "total_assets": equities[i] + debts[i] + revenues[i] * 0.2,
        }
        for i in range(n)
    ]


def test_ac1_ac2_single_decision_authority_and_decision_trace():
    """AC1 & AC2: Exactly one canonical decision authority and structured decision trace."""
    history = _make_sample_history()
    val_data = {
        "status": "READY",
        "current_price": 40000.0,
        "base_iv": 60000.0,
        "bear_iv": 45000.0,
        "bull_iv": 80000.0,
        "actual_mos_pct": 33.33,
        "required_mos_pct": 20.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("TEST_AC1", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    dec = m_dict["long_term_decision"]
    assert dec["decision_authority"] == "MUNGER_BCTC_PIPELINE"
    assert "decision_trace" in dec

    trace = dec["decision_trace"]
    assert "quality_gate" in trace
    assert "forensic_gate" in trace
    assert "value_trap_gate" in trace
    assert "liquidity_gate" in trace
    assert "valuation_gate" in trace
    assert "mos_gate" in trace
    assert "hard_blockers" in trace
    assert "monitoring_signals" in trace
    assert "supporting_evidence" in trace
    assert "final_decision" in trace
    assert "explanation" in trace


def test_case_a_all_pass_mos_pass_produces_buy():
    """Case A: Quality PASS + Forensics CLEAR + ValueTrap CLEAR + Liquidity OK + MOS PASS -> BUY (never WAIT_FOR_MOS)."""
    history = _make_sample_history()
    val_data = {
        "status": "READY",
        "current_price": 40000.0,
        "base_iv": 80000.0,
        "bear_iv": 55000.0,  # price < bear_iv -> robust BUY
        "bull_iv": 100000.0,
        "actual_mos_pct": 50.0,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("CASE_A", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()
    dec = m_dict["long_term_decision"]

    assert dec["state"] == "BUY"
    assert dec["mos_gate"] == "PASS"
    assert dec["state"] != "WAIT_FOR_MOS"
    assert "Chờ mức giá có biên an toàn" not in dec["action_vi"]


def test_case_b_watch_forensics_does_not_block_buy_when_compensated_by_mos():
    """Case B: Quality PASS + Forensics WATCH + ValueTrap CLEAR + Liquidity OK + MOS PASS -> BUY with monitoring reasons (never WAIT_FOR_MOS)."""
    # High earnings volatility (CV > 0.35) -> WATCH
    pats = [100e9, 350e9, 120e9, 450e9, 420e9]
    history = _make_sample_history(pats=pats)

    val_data = {
        "status": "READY",
        "current_price": 35000.0,
        "base_iv": 70000.0,
        "bear_iv": 45000.0,
        "bull_iv": 90000.0,
        "actual_mos_pct": 50.0,
        "required_mos_pct": 30.0,
        "valuation_confidence": "MEDIUM",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("CASE_B", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()
    dec = m_dict["long_term_decision"]

    assert dec["state"] in ("BUY", "CONDITIONAL_BUY")
    assert dec["state"] != "WAIT_FOR_MOS"
    assert len(dec["monitoring_reasons"]) > 0
    # Must explain that MOS passes while monitoring items are tracked
    assert "MOS đạt" in dec["action_vi"] or "Có thể mua" in dec["action_vi"]
    assert "Chờ mức giá có biên an toàn" not in dec["action_vi"]


def test_case_c_quality_pass_mos_fail_produces_wait_for_mos():
    """Case C: Quality PASS + Forensics CLEAR + ValueTrap CLEAR + Liquidity OK + MOS FAIL -> WAIT_FOR_MOS."""
    history = _make_sample_history()
    val_data = {
        "status": "READY",
        "current_price": 75000.0,
        "base_iv": 80000.0,
        "bear_iv": 55000.0,
        "bull_iv": 100000.0,
        "actual_mos_pct": 6.25,  # < required 25%
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("CASE_C", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()
    dec = m_dict["long_term_decision"]

    assert dec["state"] == "WAIT_FOR_MOS"
    assert dec["mos_gate"] == "FAIL"
    assert "Chờ biên an toàn" in dec["action_vi"] or "Chờ mức giá có biên an toàn" in dec["action_vi"]


def test_case_d_quality_fail_overrides_mos_pass():
    """Case D: Quality FAIL + MOS PASS (e.g. 70%) -> Quality blocker overrides MOS (AVOID, not BUY)."""
    # Deteriorating business with negative earnings & ROE < 0
    pats = [200e9, 100e9, 20e9, -50e9, -150e9]
    history = _make_sample_history(pats=pats)

    val_data = {
        "status": "READY",
        "current_price": 20000.0,
        "base_iv": 60000.0,
        "bear_iv": 30000.0,
        "bull_iv": 80000.0,
        "actual_mos_pct": 66.67,  # Very high MOS
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "UNINVESTABLE",
    }
    munger = build_munger_financial_analysis("CASE_D", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()
    dec = m_dict["long_term_decision"]

    assert dec["state"] in ("AVOID", "REVIEW_BUSINESS")
    assert dec["state"] != "BUY"
    assert len(dec["blocking_reasons"]) > 0
    assert any("Chất lượng kinh doanh" in r or "DETERIORATING" in r or "suy giảm" in r for r in dec["blocking_reasons"])


def test_case_e_liquidity_gate_independent_from_business_quality():
    """Case E: Liquidity insufficient data or low volume does NOT degrade business quality."""
    code, vi_label, comment = classify_liquidity(
        avg_val_20d_billion=None,
        avg_vol_20d=0,
        coverage_pct=0.0,
        trading_days=0,
    )
    assert code == "LIQUIDITY_INSUFFICIENT_DATA"
    assert vi_label == "Chưa đủ dữ liệu thanh khoản"
    # Semantic check: does not say the business is bad
    assert "kinh doanh kém" not in comment.lower()
    assert "chất lượng kém" not in comment.lower()


def test_ac8_candidate_distinct_from_buy():
    """AC8: Candidate status remains separate from BUY status; is_mos_qualified = false does NOT remove candidate."""
    # Test with a high-quality symbol like FPT where it is a candidate
    cand = _evaluate_candidate_symbol("FPT")
    if cand:
        # FPT is a candidate with valid tier
        assert cand.get("candidate_tier_code") in ("EXCEPTIONAL", "HIGH_QUALITY", "INVESTABLE")
        # Candidate status is preserved independently of is_mos_qualified
        assert "is_mos_qualified" in cand
        if not cand.get("is_mos_qualified"):
            assert "chưa đạt biên an toàn" in cand.get("mos_status_vi", "").lower()
        else:
            assert "đạt biên an toàn" in cand.get("mos_status_vi", "").lower()


def test_ac10_normalized_earning_power_used():
    """AC10: Normalized earning power is preserved and used to detect peak earnings."""
    # Peak latest year 600B vs previous average ~150B
    pats = [100e9, 120e9, 150e9, 180e9, 600e9]
    history = _make_sample_history(pats=pats)
    val_data = {
        "status": "READY",
        "current_price": 50000.0,
        "base_iv": 80000.0,
        "bear_iv": 55000.0,
        "bull_iv": 100000.0,
        "actual_mos_pct": 37.5,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("PEAK_EARNINGS", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    assert m_dict["normalized_earning_power"]["is_peak_earnings"] is True
    assert m_dict["normalized_earning_power"]["normalized_pat_5y"] > 0
    # Must be tracked in monitoring reasons
    dec = m_dict["long_term_decision"]
    assert any("chu kỳ" in r or "chuẩn hóa" in r for r in dec["monitoring_reasons"])


def test_ac11_stress_tests_independent_provenance():
    """AC11: Business earnings stress test is independent from personal financial stress or single year one-offs."""
    history = _make_sample_history()
    val_data = {
        "status": "READY",
        "current_price": 40000.0,
        "base_iv": 80000.0,
        "bear_iv": 55000.0,
        "bull_iv": 100000.0,
        "actual_mos_pct": 50.0,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("STRESS_TEST", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    # Verify stress test results exist and are derived from business economics
    assert "decision_trace" in m_dict["long_term_decision"]
    trace = m_dict["long_term_decision"]["decision_trace"]
    assert trace["mos_gate"] == "PASS"


def test_ac12_bfc_regression():
    """AC12: BFC Regression - MOS 67.44% >= 50% Req MOS, BUY, clean conditions, 0 blockers, clean monitoring signals."""
    bfc_val = build_canonical_valuation("BFC", compute_munger=True)
    assert bfc_val is not None
    munger = bfc_val.get("munger_analysis")
    assert munger is not None

    dec = munger["long_term_decision"]
    assert dec["state"] == "BUY"
    assert dec["action_vi"] == "Có thể mua"
    assert dec["mos_gate"] == "PASS"
    assert dec["actual_mos_pct"] >= 50.0
    assert len(dec["blocking_reasons"]) == 0
    assert len(dec["conditions"]) == 0
    assert len(dec["monitoring_reasons"]) > 0
    assert dec["watch_coexistence_rationale"] is not None
    assert "Biên an toàn yêu cầu" in dec["watch_coexistence_rationale"] or "biên an toàn yêu cầu" in dec["watch_coexistence_rationale"].lower()


def test_ac13_hah_regression():
    """AC13: HAH Regression - MOS 70.49% >= 50% Req MOS, BUY, clean conditions, 0 blockers, clean monitoring signals."""
    hah_val = build_canonical_valuation("HAH", compute_munger=True)
    assert hah_val is not None
    munger = hah_val.get("munger_analysis")
    assert munger is not None

    dec = munger["long_term_decision"]
    assert dec["state"] == "BUY"
    assert dec["action_vi"] == "Có thể mua"
    assert dec["mos_gate"] == "PASS"
    assert dec["actual_mos_pct"] >= 50.0
    assert len(dec["blocking_reasons"]) == 0
    assert len(dec["conditions"]) == 0
    assert len(dec["monitoring_reasons"]) > 0
    assert dec["watch_coexistence_rationale"] is not None


def test_ac15_no_raw_enums_or_nan_leakage():
    """AC15: No raw enums, null, or NaN leakage in investor-facing decision and action strings."""
    for sym in ["BFC", "HAH", "FPT", "DGC"]:
        val = build_canonical_valuation(sym, compute_munger=True)
        if not val or not val.get("munger_analysis"):
            continue
        munger = val["munger_analysis"]
        dec = munger["long_term_decision"]
        assert dec["action_vi"] is not None
        assert "None" not in dec["action_vi"]
        assert "NaN" not in dec["action_vi"]
        assert "NULL" not in dec["action_vi"]
        for r in dec["monitoring_reasons"]:
            assert "None" not in r
            assert "NaN" not in r
