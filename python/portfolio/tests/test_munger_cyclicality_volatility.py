"""Munger Cyclicality & Earnings Volatility Integrity Test Suite (TASK-186).

Verifies the distinction between:
1. Durable Compounder (COMPOUNDER)
2. High-Quality Cyclical Business (CYCLICAL_QUALITY)
3. Structurally Deteriorating Business (DETERIORATING_BUSINESS / WEAK_BUSINESS)

Covers 10 deterministic golden scenarios (A through J):
A. CV < 35%, stable earnings -> COMPOUNDER eligible
B. CV >= 35%, strong normalized earnings -> NOT COMPOUNDER (routed to CYCLICAL_QUALITY)
C. CV >= 35%, strong normalized earnings, no structural deterioration -> CYCLICAL_QUALITY is QUALITY_PASS
D. Peak earnings with healthy normalized earnings -> Monitoring signal, not automatic FAIL
E. Peak earnings with weak normalized earnings -> Flagged in monitoring and normalized earning power
F. Very high volatility with structural deterioration -> Blocker decision AVOID dominates
G. Excellent business with MOS FAIL -> Quality PASS preserved independently from valuation
H. BANK archetype with high earnings volatility -> Bypasses industrial working capital/CFO
I. SECURITIES archetype with high earnings volatility -> Bypasses industrial CFO/capex
J. 5Y vs 10Y normalized earnings divergence -> Traceable in normalized_earning_power
"""

import os
import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://qport:qport@127.0.0.1:5432/qport")

from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_models import CompounderClassification, DeteriorationClassification


def _make_cyclical_history(pats, revenues=None, cfos=None, equities=None, debts=None):
    n = len(pats)
    if revenues is None:
        revenues = [1000e9 + i * 150e9 for i in range(n)]
    if cfos is None:
        cfos = [p * 1.05 for p in pats]
    if equities is None:
        equities = [1000e9 + i * 120e9 for i in range(n)]
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
            "total_liabilities": debts[i] + revenues[i] * 0.1,
            "receivables": revenues[i] * 0.10,
            "inventory": revenues[i] * 0.10,
            "total_assets": equities[i] + debts[i] + revenues[i] * 0.1,
        }
        for i in range(n)
    ]


def test_scenario_a_low_volatility_compounder_eligible():
    """Scenario A: CV < 35%, stable earnings growth, no loss years -> COMPOUNDER eligible."""
    pats = [200e9, 230e9, 260e9, 300e9, 350e9]
    history = _make_cyclical_history(pats=pats)
    val_data = {
        "status": "READY",
        "current_price": 40000.0,
        "base_iv": 80000.0,
        "bear_iv": 55000.0,
        "bull_iv": 100000.0,
        "actual_mos_pct": 50.0,
        "required_mos_pct": 20.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("SYM_A_COMP", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    assert m_dict["normalized_earning_power"]["earnings_volatility"] < 0.35
    assert m_dict["compounder_classification"] == CompounderClassification.COMPOUNDER.value
    assert m_dict["long_term_decision"]["decision_trace"]["quality_gate"] == "PASS"


def test_scenario_b_high_volatility_prevents_compounder():
    """Scenario B: CV >= 35%, strong average earnings -> Strictly NOT COMPOUNDER (routed to CYCLICAL_QUALITY)."""
    # Volatile earnings: 100B -> 400B -> 150B -> 500B -> 450B (High return, but fluctuating)
    pats = [100e9, 400e9, 150e9, 500e9, 450e9]
    history = _make_cyclical_history(pats=pats)
    val_data = {
        "status": "READY",
        "current_price": 40000.0,
        "base_iv": 80000.0,
        "bear_iv": 55000.0,
        "bull_iv": 100000.0,
        "actual_mos_pct": 50.0,
        "required_mos_pct": 25.0,
        "valuation_confidence": "MEDIUM",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("SYM_B_VOL", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    assert m_dict["normalized_earning_power"]["earnings_volatility"] >= 0.35
    assert m_dict["compounder_classification"] != CompounderClassification.COMPOUNDER.value
    assert m_dict["compounder_classification"] == CompounderClassification.CYCLICAL_QUALITY.value


def test_scenario_c_cyclical_quality_remains_quality_pass():
    """Scenario C: CYCLICAL_QUALITY with healthy balance sheet and no fraud is QUALITY_PASS."""
    pats = [150e9, 350e9, 180e9, 450e9, 400e9]
    history = _make_cyclical_history(pats=pats)
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
    munger = build_munger_financial_analysis("SYM_C_CYC_PASS", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    trace = m_dict["long_term_decision"]["decision_trace"]
    assert m_dict["compounder_classification"] == CompounderClassification.CYCLICAL_QUALITY.value
    assert trace["quality_gate"] == "PASS"
    assert trace["final_decision"] == "BUY"


def test_scenario_d_peak_earnings_is_monitoring_not_automatic_fail():
    """Scenario D: Peak earnings (reported >= 1.5x 5Y norm) is a monitoring signal, not an automatic hard blocker."""
    # Historical baseline 200B-270B (ROE > 18%), recent year peaks at 1000B (>= 1.5x 5Y norm)
    pats = [200e9, 220e9, 250e9, 270e9, 1000e9]
    history = _make_cyclical_history(pats=pats)
    val_data = {
        "status": "READY",
        "current_price": 40000.0,
        "base_iv": 80000.0,
        "bear_iv": 55000.0,
        "bull_iv": 100000.0,
        "actual_mos_pct": 50.0,
        "required_mos_pct": 30.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("SYM_D_PEAK", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    norm_ep = m_dict["normalized_earning_power"]
    assert norm_ep["is_peak_earnings"] is True
    dec = m_dict["long_term_decision"]
    assert len(dec["decision_trace"]["hard_blockers"]) == 0
    assert any("cao hơn mức chuẩn hóa" in r or "chu kỳ" in r for r in dec["monitoring_signals"])


def test_scenario_e_peak_earnings_with_weak_normalized_tracked():
    """Scenario E: Peak earnings with low historical average is tracked in normalized_earning_power."""
    pats = [20e9, 30e9, 25e9, 40e9, 200e9]
    history = _make_cyclical_history(pats=pats)
    val_data = {
        "status": "READY",
        "current_price": 20000.0,
        "base_iv": 30000.0,
        "bear_iv": 18000.0,
        "bull_iv": 40000.0,
        "actual_mos_pct": 33.33,
        "required_mos_pct": 25.0,
        "valuation_confidence": "MEDIUM",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("SYM_E_WEAK_NORM", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    norm_ep = m_dict["normalized_earning_power"]
    assert norm_ep["is_peak_earnings"] is True
    assert norm_ep["normalized_pat_5y"] < 100e9


def test_scenario_f_high_volatility_with_structural_decay_blocks_buy():
    """Scenario F: High volatility accompanying structural deterioration produces AVOID blocker."""
    # Deteriorating business with losses and collapsing equity
    pats = [300e9, 100e9, -50e9, -200e9, -400e9]
    history = _make_cyclical_history(pats=pats)
    val_data = {
        "status": "READY",
        "current_price": 5000.0,
        "base_iv": 30000.0,
        "bear_iv": 15000.0,
        "bull_iv": 40000.0,
        "actual_mos_pct": 83.33,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "UNINVESTABLE",
    }
    munger = build_munger_financial_analysis("SYM_F_STRUCTURAL", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    dec = m_dict["long_term_decision"]
    assert dec["state"] == "AVOID"
    assert dec["state"] != "BUY"
    assert len(dec["blocking_reasons"]) > 0


def test_scenario_g_excellent_business_mos_fail_preserves_quality_pass():
    """Scenario G: High quality cyclical business with MOS FAIL preserves Quality PASS (WAIT_FOR_MOS)."""
    pats = [200e9, 450e9, 250e9, 500e9, 550e9]
    history = _make_cyclical_history(pats=pats)
    val_data = {
        "status": "READY",
        "current_price": 95000.0,
        "base_iv": 100000.0,
        "bear_iv": 70000.0,
        "bull_iv": 130000.0,
        "actual_mos_pct": 5.0,  # < required 25%
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("SYM_G_EXPENSIVE", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    trace = m_dict["long_term_decision"]["decision_trace"]
    assert trace["quality_gate"] == "PASS"
    assert trace["mos_gate"] == "FAIL"
    assert trace["final_decision"] == "WAIT_FOR_MOS"


def test_scenario_h_bank_high_volatility_no_industrial_cfo_blocker():
    """Scenario H: BANK with earnings volatility evaluates correctly without industrial CFO false failure."""
    pats = [1000e9, 2500e9, 1200e9, 3200e9, 3500e9]
    equities = [10000e9, 12000e9, 13500e9, 16000e9, 19000e9]
    bank_history = [
        {
            "fiscal_year": 2020 + i,
            "net_profit": pats[i],
            "equity": equities[i],
            "total_assets": equities[i] * 8.0,
            "total_debt": equities[i] * 7.0,
        }
        for i in range(len(pats))
    ]
    val_data = {
        "status": "READY",
        "current_price": 20000.0,
        "base_iv": 30000.0,
        "bear_iv": 22000.0,
        "bull_iv": 40000.0,
        "actual_mos_pct": 33.33,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("TCB", existing_history=bank_history, valuation_data=val_data)
    m_dict = munger.to_dict()

    assert m_dict["archetype"] == "BANK"
    assert m_dict["compounder_classification"] == CompounderClassification.CYCLICAL_QUALITY.value
    trace = m_dict["long_term_decision"]["decision_trace"]
    assert trace["quality_gate"] == "PASS"
    assert len(trace["hard_blockers"]) == 0


def test_scenario_i_securities_high_volatility_no_industrial_cfo_blocker():
    """Scenario I: SECURITIES with high earnings volatility evaluates without industrial cash conversion penalty."""
    pats = [200e9, 800e9, 300e9, 1200e9, 1100e9]
    equities = [3000e9, 3600e9, 4000e9, 5000e9, 6000e9]
    sec_history = [
        {
            "fiscal_year": 2020 + i,
            "net_profit": pats[i],
            "equity": equities[i],
            "total_assets": equities[i] * 2.5,
            "total_debt": equities[i] * 1.5,
        }
        for i in range(len(pats))
    ]
    val_data = {
        "status": "READY",
        "current_price": 15000.0,
        "base_iv": 25000.0,
        "bear_iv": 18000.0,
        "bull_iv": 35000.0,
        "actual_mos_pct": 40.0,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("VIX", existing_history=sec_history, valuation_data=val_data)
    m_dict = munger.to_dict()

    assert m_dict["archetype"] == "SECURITIES"
    assert m_dict["compounder_classification"] == CompounderClassification.CYCLICAL_QUALITY.value
    trace = m_dict["long_term_decision"]["decision_trace"]
    assert trace["quality_gate"] == "PASS"
    assert len(trace["hard_blockers"]) == 0


def test_scenario_j_5y_vs_10y_normalized_earnings_divergence_traceable():
    """Scenario J: 5Y vs 10Y normalized earnings divergence is clearly exposed and traceable."""
    # 10 years of earnings with massive cycle growth in the last 5 years
    pats_10y = [50e9, 60e9, 70e9, 80e9, 90e9, 200e9, 350e9, 300e9, 400e9, 450e9]
    history = [
        {
            "fiscal_year": 2015 + i,
            "revenue": 500e9 + i * 150e9,
            "net_profit": pats_10y[i],
            "operating_cash_flow": pats_10y[i] * 1.05,
            "equity": 500e9 + i * 100e9,
            "total_debt": 100e9,
            "total_liabilities": 200e9,
            "receivables": 100e9,
            "inventory": 100e9,
            "total_assets": 700e9 + i * 100e9,
        }
        for i in range(10)
    ]
    val_data = {
        "status": "READY",
        "current_price": 30000.0,
        "base_iv": 60000.0,
        "bear_iv": 45000.0,
        "bull_iv": 80000.0,
        "actual_mos_pct": 50.0,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("SYM_J_DIVERGENCE", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    norm_ep = m_dict["normalized_earning_power"]
    assert norm_ep["normalized_pat_5y"] > norm_ep["normalized_pat_10y"]
    assert norm_ep["normalized_pat_5y"] == sum(pats_10y[-5:]) / 5.0
    assert norm_ep["normalized_pat_10y"] == sum(pats_10y) / 10.0
    assert "explanation" in norm_ep
