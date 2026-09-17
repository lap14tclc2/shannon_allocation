"""Golden Business Quality & Normalized Earning Power Matrix Test Suite (TASK-185).

Verifies the economic correctness of the QPort Munger Business Quality engine:
A. Strong normalized earnings, stable profitability, healthy cash economics -> QUALITY PASS
B. Reported PAT strong, normalized earning power weak -> Peak flag & CV volatility preserved, not blindly PASS
C. Peak earnings with high current ROE -> is_peak_earnings flag preserved in monitoring signals
D. Temporary CFO/PAT divergence without structural deterioration -> WATCH / monitoring signal, not automatic FAIL
E. Persistent cash conversion deterioration across multiple years -> Forensic quality concern
F. Historical receivables warning with recent 3Y normalized -> Historical WATCH, not structural FAIL
G. Cheap valuation with weak business economics -> Quality blocker dominates, decision is AVOID (not BUY)
H. Excellent business with MOS FAIL -> Quality PASS, candidate remains true, decision is WAIT_FOR_MOS
I. BANK archetype -> No industrial working capital / CFO / capex false blocker
J. SECURITIES archetype -> No industrial CFO cash conversion false blocker
K. Missing normalized earnings evidence (<3Y history) -> INSUFFICIENT / UNKNOWN, not PASS
L. Real economic dilution (ESOP, Rights) -> Remains visible as economic event
M. Pure stock split -> Preserves per-share economic MOS without distortion
"""

import os
import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://qport:qport@127.0.0.1:5432/qport")

from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_models import CompounderClassification, DimensionStatus
from portfolio.corporate_action_normalizer import CorporateActionEvent, CorporateActionType
from portfolio.value_engine.share_basis import calculate_canonical_mos


def _make_history(pats, revenues=None, cfos=None, equities=None, debts=None, receivables=None, inventories=None):
    n = len(pats)
    if revenues is None:
        revenues = [1000e9 + i * 150e9 for i in range(n)]
    if cfos is None:
        cfos = [p * 1.05 for p in pats]
    if equities is None:
        equities = [1000e9 + i * 120e9 for i in range(n)]
    if debts is None:
        debts = [200e9 for _ in range(n)]
    if receivables is None:
        receivables = [r * 0.10 for r in revenues]
    if inventories is None:
        inventories = [r * 0.10 for r in revenues]

    return [
        {
            "fiscal_year": 2020 + i,
            "revenue": revenues[i],
            "net_profit": pats[i],
            "operating_cash_flow": cfos[i],
            "equity": equities[i],
            "total_debt": debts[i],
            "total_liabilities": debts[i] + revenues[i] * 0.1,
            "receivables": receivables[i],
            "inventory": inventories[i],
            "total_assets": equities[i] + debts[i] + revenues[i] * 0.1,
        }
        for i in range(n)
    ]


def test_scenario_a_strong_normalized_earnings_quality_pass():
    """Scenario A: Strong normalized earnings, stable profitability, healthy cash conversion -> QUALITY PASS."""
    pats = [200e9, 230e9, 260e9, 300e9, 350e9]
    history = _make_history(pats=pats)
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
    munger = build_munger_financial_analysis("SYM_A", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    trace = m_dict["long_term_decision"]["decision_trace"]
    assert trace["quality_gate"] == "PASS"
    assert m_dict["compounder_classification"] == CompounderClassification.COMPOUNDER.value
    assert m_dict["normalized_earning_power"]["earnings_volatility"] < 0.35
    assert m_dict["normalized_earning_power"]["is_peak_earnings"] is False
    assert trace["final_decision"] == "BUY"


def test_scenario_b_reported_strong_normalized_weak_preserves_volatility():
    """Scenario B: Reported PAT strong but volatile / normalized earning power much lower -> Volatility CV tracked."""
    # Erratic earnings: 50B, 300B, 80B, 400B, 420B
    pats = [50e9, 300e9, 80e9, 400e9, 420e9]
    history = _make_history(pats=pats)
    val_data = {
        "status": "READY",
        "current_price": 40000.0,
        "base_iv": 80000.0,
        "bear_iv": 55000.0,
        "bull_iv": 100000.0,
        "actual_mos_pct": 50.0,
        "required_mos_pct": 30.0,
        "valuation_confidence": "MEDIUM",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("SYM_B", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    norm_ep = m_dict["normalized_earning_power"]
    assert norm_ep["earnings_volatility"] >= 0.35
    assert m_dict["compounder_classification"] != CompounderClassification.COMPOUNDER.value
    # Monitoring signals must include volatility warning
    dec = m_dict["long_term_decision"]
    assert any("biến động LNST" in r for r in dec["monitoring_signals"])


def test_scenario_c_peak_earnings_flagged():
    """Scenario C: Peak earnings with recent spike >= 1.5x 5Y normalized PAT -> is_peak_earnings flag True."""
    # Historical ~100B, sudden peak 500B
    pats = [80e9, 90e9, 100e9, 110e9, 500e9]
    history = _make_history(pats=pats)
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
    munger = build_munger_financial_analysis("SYM_C", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    norm_ep = m_dict["normalized_earning_power"]
    assert norm_ep["is_peak_earnings"] is True
    dec = m_dict["long_term_decision"]
    assert any("cao hơn mức chuẩn hóa" in r or "chu kỳ" in r for r in dec["monitoring_signals"])


def test_scenario_d_temporary_cfo_pat_divergence_is_watch_not_fail():
    """Scenario D: Single-year CFO/PAT dip due to working capital growth is WATCH, not hard FAIL."""
    # Year 5 CFO dips to 50B on 300B PAT due to inventory buildup for orders
    pats = [200e9, 220e9, 250e9, 280e9, 300e9]
    cfos = [210e9, 230e9, 260e9, 290e9, 80e9]  # 4 years healthy, 1 year temporary dip
    history = _make_history(pats=pats, cfos=cfos)
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
    munger = build_munger_financial_analysis("SYM_D", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    trace = m_dict["long_term_decision"]["decision_trace"]
    # Not an automatic hard blocker
    assert len(trace["hard_blockers"]) == 0
    assert trace["final_decision"] == "BUY"


def test_scenario_e_persistent_weak_cfo_generates_forensic_concern():
    """Scenario E: Persistent multi-year CFO/PAT << 0.5x generates forensic warning/concern and blocks BUY."""
    pats = [200e9, 220e9, 250e9, 280e9, 300e9]
    cfos = [30e9, 40e9, 50e9, 60e9, 70e9]  # Persistently ~20% of PAT
    history = _make_history(pats=pats, cfos=cfos)
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
    munger = build_munger_financial_analysis("SYM_E", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    dec = m_dict["long_term_decision"]
    # Severe persistent cash divergence is an accounting/forensic concern
    assert dec["state"] == "AVOID"
    assert len(dec["blocking_reasons"]) > 0


def test_scenario_f_historical_receivables_warning_recent_normalized():
    """Scenario F: 10Y receivables warning with recent 3Y normalized is historical WATCH, not structural FAIL."""
    revenues = [500e9, 600e9, 800e9, 1200e9, 1500e9]
    # Fast initial growth (50 -> 150) but recent 3Y normalized (150 -> 160 -> 170 on 800 -> 1200 -> 1500 rev)
    receivables = [50e9, 100e9, 150e9, 160e9, 170e9]
    pats = [100e9, 120e9, 160e9, 240e9, 300e9]
    history = _make_history(pats=pats, revenues=revenues, receivables=receivables)
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
    munger = build_munger_financial_analysis("SYM_F", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    trace = m_dict["long_term_decision"]["decision_trace"]
    assert len(trace["hard_blockers"]) == 0
    assert trace["final_decision"] in ("BUY", "CONDITIONAL_BUY")


def test_scenario_g_cheap_valuation_with_weak_business_is_avoid():
    """Scenario G: Cheap valuation (80% MOS) with deteriorating/negative earnings remains AVOID."""
    pats = [200e9, 100e9, 0e9, -100e9, -250e9]
    history = _make_history(pats=pats)
    val_data = {
        "status": "READY",
        "current_price": 10000.0,
        "base_iv": 50000.0,
        "bear_iv": 30000.0,
        "bull_iv": 70000.0,
        "actual_mos_pct": 80.0,  # Deep MOS
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "UNINVESTABLE",
    }
    munger = build_munger_financial_analysis("SYM_G", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    dec = m_dict["long_term_decision"]
    assert dec["state"] == "AVOID"
    assert dec["state"] != "BUY"
    assert len(dec["blocking_reasons"]) > 0


def test_scenario_h_excellent_business_with_mos_fail_is_wait_for_mos():
    """Scenario H: Excellent business with MOS FAIL -> Quality PASS, Decision WAIT_FOR_MOS (Candidate eligible)."""
    pats = [200e9, 230e9, 270e9, 320e9, 380e9]
    history = _make_history(pats=pats)
    val_data = {
        "status": "READY",
        "current_price": 90000.0,
        "base_iv": 100000.0,
        "bear_iv": 75000.0,
        "bull_iv": 130000.0,
        "actual_mos_pct": 10.0,  # < required 25%
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("SYM_H", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    trace = m_dict["long_term_decision"]["decision_trace"]
    assert trace["quality_gate"] == "PASS"
    assert trace["mos_gate"] == "FAIL"
    assert trace["final_decision"] == "WAIT_FOR_MOS"


def test_scenario_i_bank_archetype_bypasses_industrial_rules():
    """Scenario I: BANK archetype does not require industrial working capital or inventory."""
    pats = [1000e9, 1200e9, 1500e9, 1800e9, 2200e9]
    equities = [10000e9, 11500e9, 13500e9, 16000e9, 19000e9]
    # Bank history has NO inventory, NO industrial CFO
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
        "required_mos_pct": 20.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }
    munger = build_munger_financial_analysis("ACB", existing_history=bank_history, valuation_data=val_data)
    m_dict = munger.to_dict()

    assert m_dict["archetype"] == "BANK"
    trace = m_dict["long_term_decision"]["decision_trace"]
    assert trace["quality_gate"] == "PASS"
    assert len(trace["hard_blockers"]) == 0


def test_scenario_j_securities_archetype_bypasses_industrial_cfo():
    """Scenario J: SECURITIES archetype does not require industrial CFO / capex cash conversion."""
    pats = [300e9, 450e9, 350e9, 600e9, 800e9]
    equities = [3000e9, 3500e9, 4000e9, 5000e9, 6500e9]
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
    munger = build_munger_financial_analysis("SSI", existing_history=sec_history, valuation_data=val_data)
    m_dict = munger.to_dict()

    assert m_dict["archetype"] == "SECURITIES"
    trace = m_dict["long_term_decision"]["decision_trace"]
    assert trace["quality_gate"] == "PASS"
    assert len(trace["hard_blockers"]) == 0


def test_scenario_k_missing_normalized_earnings_is_insufficient():
    """Scenario K: Missing history (<3Y) -> data_readiness INSUFFICIENT, does not blindly PASS."""
    pats = [100e9, 120e9]  # only 2 years
    history = _make_history(pats=pats)
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
    munger = build_munger_financial_analysis("SYM_K", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    assert m_dict["data_readiness"] == "INSUFFICIENT"
    assert m_dict["compounder_classification"] == CompounderClassification.INSUFFICIENT_DATA.value
    dec = m_dict["long_term_decision"]
    assert dec["state"] != "BUY"


def test_scenario_l_economic_dilution_remains_visible():
    """Scenario L: Real economic dilution (ESOP, rights issue) is classified as economic (is_non_economic = False)."""
    esop = CorporateActionEvent(symbol="XYZ", action_type=CorporateActionType.ESOP.value, effective_date="2024-01-01")
    rights = CorporateActionEvent(symbol="XYZ", action_type=CorporateActionType.RIGHTS_ISSUE.value, effective_date="2024-01-01")
    new_shares = CorporateActionEvent(symbol="XYZ", action_type=CorporateActionType.NEW_SHARE_ISSUANCE.value, effective_date="2024-01-01")

    assert esop.is_non_economic is False
    assert rights.is_non_economic is False
    assert new_shares.is_non_economic is False


def test_scenario_m_pure_split_preserves_economic_mos():
    """Scenario M: Pure stock split preserves economic MOS exactly."""
    # Pre-split: Price 50,000, IV 100,000 -> MOS = 50%
    mos_pre = calculate_canonical_mos(market_price=50000.0, intrinsic_value_per_share=100000.0)
    # Post-split 1:2: Price 25,000, IV 50,000 -> MOS = 50%
    mos_post = calculate_canonical_mos(market_price=25000.0, intrinsic_value_per_share=50000.0)

    assert float(mos_pre) == 50.0
    assert float(mos_post) == 50.0
    assert mos_pre == mos_post
