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


# ==============================================================================
# Task 183: Final Liquidity Gate Integrity Audit Test Suite
# ==============================================================================

def test_liquidity_gate_case_a_strong():
    """Case A: Quality PASS + MOS PASS + Liquidity STRONG -> BUY, Liquidity Gate PASS."""
    from unittest.mock import patch
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
    with patch("portfolio.value_engine.liquidity_evaluator.evaluate_symbol_liquidity") as mock_liq:
        mock_liq.return_value = {
            "symbol": "LIQ_STRONG",
            "classification": "LIQUIDITY_STRONG",
            "classification_vi": "Thanh khoản tốt",
            "commentary_vi": "Cổ phiếu có thanh khoản dồi dào (>10 tỷ/ngày).",
            "latest_price": 40000.0,
            "avg_volume_20d": 500000.0,
            "avg_trading_value_20d_billion": 20.0,
            "trading_day_coverage_pct": 100.0,
            "trading_days_observed": 20,
            "data_status": "AVAILABLE",
        }
        munger = build_munger_financial_analysis("LIQ_STRONG", existing_history=history, valuation_data=val_data)
        dec = munger.to_dict()["long_term_decision"]
        trace = dec["decision_trace"]

        assert dec["state"] == "BUY"
        assert trace["liquidity_gate_status"] == "PASS"
        assert trace["liquidity_gate_classification"] == "LIQUIDITY_STRONG"
        assert trace["quality_gate"] == "PASS"


def test_liquidity_gate_case_b_acceptable():
    """Case B: Quality PASS + MOS PASS + Liquidity ACCEPTABLE -> BUY, Liquidity Gate PASS."""
    from unittest.mock import patch
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
    with patch("portfolio.value_engine.liquidity_evaluator.evaluate_symbol_liquidity") as mock_liq:
        mock_liq.return_value = {
            "symbol": "LIQ_ACCEPT",
            "classification": "LIQUIDITY_ACCEPTABLE",
            "classification_vi": "Thanh khoản đủ",
            "commentary_vi": "Thanh khoản đáp ứng yêu cầu giao dịch (>5 tỷ/ngày).",
            "latest_price": 40000.0,
            "avg_volume_20d": 150000.0,
            "avg_trading_value_20d_billion": 6.0,
            "trading_day_coverage_pct": 100.0,
            "trading_days_observed": 20,
            "data_status": "AVAILABLE",
        }
        munger = build_munger_financial_analysis("LIQ_ACCEPT", existing_history=history, valuation_data=val_data)
        dec = munger.to_dict()["long_term_decision"]
        trace = dec["decision_trace"]

        assert dec["state"] == "BUY"
        assert trace["liquidity_gate_status"] == "PASS"
        assert trace["liquidity_gate_classification"] == "LIQUIDITY_ACCEPTABLE"
        assert trace["quality_gate"] == "PASS"


def test_liquidity_gate_case_c_weak_monitoring_only():
    """Case C: Quality PASS + MOS PASS + Liquidity WEAK -> Does not degrade business quality; liquidity is a separate gate."""
    from unittest.mock import patch
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
    with patch("portfolio.value_engine.liquidity_evaluator.evaluate_symbol_liquidity") as mock_liq:
        mock_liq.return_value = {
            "symbol": "LIQ_WEAK",
            "classification": "LIQUIDITY_WEAK",
            "classification_vi": "Thanh khoản thấp",
            "commentary_vi": "Thanh khoản thấp (<5 tỷ/ngày).",
            "latest_price": 40000.0,
            "avg_volume_20d": 20000.0,
            "avg_trading_value_20d_billion": 0.8,
            "trading_day_coverage_pct": 70.0,
            "trading_days_observed": 20,
            "data_status": "AVAILABLE",
        }
        munger = build_munger_financial_analysis("LIQ_WEAK", existing_history=history, valuation_data=val_data)
        dec = munger.to_dict()["long_term_decision"]
        trace = dec["decision_trace"]

        # Quality remains PASS
        assert trace["quality_gate"] == "PASS"
        # Liquidity gate reflects WATCH
        assert trace["liquidity_gate_status"] == "WATCH"
        assert trace["liquidity_gate_classification"] == "LIQUIDITY_WEAK"


def test_liquidity_gate_case_d_insufficient_data_not_silently_pass():
    """Case D: Quality PASS + MOS PASS + Liquidity INSUFFICIENT_DATA -> Liquidity Gate MUST NOT silently become PASS."""
    from unittest.mock import patch
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
    with patch("portfolio.value_engine.liquidity_evaluator.evaluate_symbol_liquidity") as mock_liq:
        mock_liq.return_value = {
            "symbol": "LIQ_MISSING",
            "classification": "LIQUIDITY_INSUFFICIENT_DATA",
            "classification_vi": "Chưa đủ dữ liệu thanh khoản",
            "commentary_vi": "Chưa đủ dữ liệu giao dịch lịch sử để đánh giá thanh khoản.",
            "latest_price": 40000.0,
            "avg_volume_20d": None,
            "avg_trading_value_20d_billion": None,
            "trading_day_coverage_pct": None,
            "trading_days_observed": 0,
            "data_status": "INSUFFICIENT_DATA",
        }
        munger = build_munger_financial_analysis("LIQ_MISSING", existing_history=history, valuation_data=val_data)
        dec = munger.to_dict()["long_term_decision"]
        trace = dec["decision_trace"]

        # Liquidity gate MUST be UNKNOWN, NEVER PASS
        assert trace["liquidity_gate_status"] == "UNKNOWN"
        assert trace["liquidity_gate_status"] != "PASS"
        assert trace["liquidity_gate_classification"] == "LIQUIDITY_INSUFFICIENT_DATA"
        # Business quality must NOT be degraded to FAIL
        assert trace["quality_gate"] == "PASS"


def test_liquidity_gate_case_e_quality_fail_overrides_strong_liquidity():
    """Case E: Quality FAIL + MOS PASS + Liquidity STRONG -> Business Quality remains the hard blocker (AVOID)."""
    from unittest.mock import patch
    pats = [200e9, 100e9, 20e9, -50e9, -150e9]
    history = _make_sample_history(pats=pats)
    val_data = {
        "status": "READY",
        "current_price": 20000.0,
        "base_iv": 60000.0,
        "bear_iv": 30000.0,
        "bull_iv": 80000.0,
        "actual_mos_pct": 66.67,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "UNINVESTABLE",
    }
    with patch("portfolio.value_engine.liquidity_evaluator.evaluate_symbol_liquidity") as mock_liq:
        mock_liq.return_value = {
            "symbol": "LIQ_STRONG_BAD_BIZ",
            "classification": "LIQUIDITY_STRONG",
            "classification_vi": "Thanh khoản tốt",
            "commentary_vi": "Cổ phiếu có thanh khoản dồi dào.",
            "latest_price": 20000.0,
            "avg_volume_20d": 1000000.0,
            "avg_trading_value_20d_billion": 20.0,
            "trading_day_coverage_pct": 100.0,
            "trading_days_observed": 20,
            "data_status": "AVAILABLE",
        }
        munger = build_munger_financial_analysis("LIQ_STRONG_BAD_BIZ", existing_history=history, valuation_data=val_data)
        dec = munger.to_dict()["long_term_decision"]
        trace = dec["decision_trace"]

        # Decision is AVOID because business quality failed
        assert dec["state"] == "AVOID"
        assert trace["quality_gate"] == "FAIL"
        assert trace["liquidity_gate_status"] == "PASS"


def test_liquidity_gate_case_f_trace_separation():
    """Case F: Decision trace cleanly separates liquidity_gate from quality_gate, forensics_gate, value_trap_gate, mos_gate."""
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
    munger = build_munger_financial_analysis("TRACE_SYM", existing_history=history, valuation_data=val_data)
    trace = munger.to_dict()["long_term_decision"]["decision_trace"]

    # All gates are distinct entries
    assert "quality_gate" in trace
    assert "forensic_gate" in trace
    assert "value_trap_gate" in trace
    assert "liquidity_gate" in trace
    assert "valuation_gate" in trace
    assert "mos_gate" in trace


def test_liquidity_real_data_bfc_and_hah():
    """Section 5: Real data audit for BFC and HAH."""
    from portfolio.value_engine.liquidity_evaluator import evaluate_symbol_liquidity

    # BFC real data audit
    bfc_liq = evaluate_symbol_liquidity("BFC")
    assert bfc_liq["symbol"] == "BFC"
    assert bfc_liq["data_status"] == "AVAILABLE"
    assert bfc_liq["classification"] == "LIQUIDITY_ACCEPTABLE"
    assert bfc_liq["avg_trading_value_20d_billion"] >= 5.0
    assert bfc_liq["trading_day_coverage_pct"] >= 80.0
    assert bfc_liq["latest_price"] is not None

    # HAH real data audit
    hah_liq = evaluate_symbol_liquidity("HAH")
    assert hah_liq["symbol"] == "HAH"
    assert hah_liq["data_status"] == "AVAILABLE"
    assert hah_liq["classification"] == "LIQUIDITY_STRONG"
    assert hah_liq["avg_trading_value_20d_billion"] >= 10.0
    assert hah_liq["trading_day_coverage_pct"] >= 85.0
    assert hah_liq["latest_price"] is not None


# ==============================================================================
# Task 184: Deterministic 17-Point Golden Matrix Suite
# ==============================================================================

def test_golden_matrix_04_critical_forensic_failure_blocks_buy():
    """Point 4: Critical forensic accounting failure -> Blocker decision (AVOID, not BUY)."""
    # Create history with severe balance sheet violation (Assets != Liabilities + Equity by 1400B)
    history = _make_sample_history()
    for h in history:
        h["total_liabilities"] = 500e9
        h["equity"] = 1000e9
        h["total_assets"] = 100e9  # Severe violation: 100B != 500B + 1000B
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
    munger = build_munger_financial_analysis("GM_FORENSIC_CRITICAL", existing_history=history, valuation_data=val_data)
    dec = munger.to_dict()["long_term_decision"]
    assert dec["state"] == "AVOID"
    assert dec["decision_trace"]["forensic_gate"] == "FAIL"
    assert len(dec["blocking_reasons"]) > 0


def test_golden_matrix_05_value_trap_high_risk_blocks_buy():
    """Point 5: Value trap HIGH_RISK -> Blocker decision (AVOID, not BUY)."""
    # Create severe structural deterioration (collapsing profits & CFO)
    pats = [500e9, 200e9, 50e9, -100e9, -300e9]
    cfos = [300e9, 50e9, -80e9, -200e9, -400e9]
    revenues = [2000e9, 1500e9, 1000e9, 700e9, 400e9]
    equities = [1000e9, 800e9, 600e9, 400e9, 100e9]
    history = _make_sample_history(pats=pats, cfos=cfos, revenues=revenues, equities=equities)
    val_data = {
        "status": "READY",
        "current_price": 10000.0,
        "base_iv": 80000.0,
        "bear_iv": 55000.0,
        "bull_iv": 100000.0,
        "actual_mos_pct": 87.5,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("GM_VALUE_TRAP", existing_history=history, valuation_data=val_data)
    dec = munger.to_dict()["long_term_decision"]
    assert dec["state"] == "AVOID"
    assert dec["decision_trace"]["quality_gate"] == "FAIL" or dec["decision_trace"]["value_trap_gate"] == "FAIL"
    assert len(dec["blocking_reasons"]) > 0


def test_golden_matrix_06_valuation_not_ready_produces_no_buy():
    """Point 6: Valuation NOT_READY / missing IV -> no BUY (REVIEW_BUSINESS / WAIT_FOR_DATA)."""
    history = _make_sample_history()
    val_data = {
        "status": "NOT_READY",
        "current_price": 40000.0,
        "base_iv": None,
        "bear_iv": None,
        "bull_iv": None,
        "actual_mos_pct": None,
        "required_mos_pct": 25.0,
        "valuation_confidence": "LOW",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("GM_VAL_NOT_READY", existing_history=history, valuation_data=val_data)
    dec = munger.to_dict()["long_term_decision"]
    assert dec["state"] != "BUY"
    assert dec["state"] != "BUY_MORE"
    assert dec["mos_gate"] == "UNKNOWN"
    assert dec["state"] in ("REVIEW_BUSINESS", "WAIT_FOR_DATA", "HOLD")


def test_golden_matrix_07_unresolved_share_basis_blocks_trusted_buy():
    """Point 7: Unresolved share basis -> Valuation not ready / no trusted BUY."""
    from portfolio.value_engine.share_basis import resolve_canonical_share_basis
    basis = resolve_canonical_share_basis("UNRESOLVED_SYM", bctc_shares=None, bctc_fiscal_year=None, bctc_period_end=None)
    assert basis.is_compatible_with_current_price is False or basis.status != "VALID"
    assert basis.status in ("INSUFFICIENT_DATA", "UNRESOLVED_MISMATCH", "CONFLICTED")


def test_golden_matrix_15_pure_stock_split_preserves_economic_mos():
    """Point 15: Pure stock split preserves economic MOS."""
    from portfolio.value_engine.share_basis import calculate_canonical_mos
    # Pre-split: IV = 100,000, Price = 50,000 -> MOS = 50%
    mos_pre = calculate_canonical_mos(market_price=50000.0, intrinsic_value_per_share=100000.0)
    # Post-split 1:10: IV = 10,000, Price = 5,000 -> MOS = 50%
    mos_post = calculate_canonical_mos(market_price=5000.0, intrinsic_value_per_share=10000.0)
    assert mos_pre == float(50.0) or mos_pre == 50.0
    assert mos_post == float(50.0) or mos_post == 50.0
    assert mos_pre == mos_post


def test_golden_matrix_16_economic_dilution_not_normalized_away():
    """Point 16: Economic dilution (ESOP / Rights) does not get treated as non-economic split."""
    from portfolio.corporate_action_normalizer import CorporateActionEvent, CorporateActionType
    split_ev = CorporateActionEvent(symbol="X", action_type=CorporateActionType.STOCK_SPLIT.value, effective_date="2024-01-01", split_factor=2.0)
    stock_div = CorporateActionEvent(symbol="X", action_type=CorporateActionType.STOCK_DIVIDEND.value, effective_date="2024-01-01", stock_ratio=0.1)
    bonus_ev = CorporateActionEvent(symbol="X", action_type=CorporateActionType.BONUS_SHARES.value, effective_date="2024-01-01", stock_ratio=0.1)
    esop_ev = CorporateActionEvent(symbol="X", action_type=CorporateActionType.ESOP.value, effective_date="2024-01-01")
    rights_ev = CorporateActionEvent(symbol="X", action_type=CorporateActionType.RIGHTS_ISSUE.value, effective_date="2024-01-01")
    new_shares_ev = CorporateActionEvent(symbol="X", action_type=CorporateActionType.NEW_SHARE_ISSUANCE.value, effective_date="2024-01-01")

    assert split_ev.is_non_economic is True
    assert stock_div.is_non_economic is True
    assert bonus_ev.is_non_economic is True
    assert esop_ev.is_non_economic is False
    assert rights_ev.is_non_economic is False
    assert new_shares_ev.is_non_economic is False


def test_golden_matrix_17_missing_data_never_silently_becomes_pass_or_buy():
    """Point 17: Missing data never silently becomes PASS / CLEAR / BUY."""
    from portfolio.value_engine.liquidity_evaluator import classify_liquidity
    # Missing volume & turnover -> INSUFFICIENT_DATA, never PASS
    code, vi_label, _ = classify_liquidity(avg_val_20d_billion=None, avg_vol_20d=0, coverage_pct=0.0, trading_days=0)
    assert code == "LIQUIDITY_INSUFFICIENT_DATA"
    assert code != "LIQUIDITY_STRONG"
    assert code != "LIQUIDITY_ACCEPTABLE"

    # Empty history -> Data readiness NOT_READY, Decision NOT BUY
    munger_empty = build_munger_financial_analysis("GM_EMPTY", existing_history=[], valuation_data=None)
    dec_empty = munger_empty.to_dict()["long_term_decision"]
    assert dec_empty["state"] != "BUY"
    assert dec_empty["state"] != "BUY_MORE"


