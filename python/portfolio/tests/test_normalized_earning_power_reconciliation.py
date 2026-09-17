"""Task 187: Normalized Earning Power & Cyclical Classification Reconciliation Test Suite.

Comprehensive deterministic test coverage for:
- Scenario A: Same input -> identical 5Y/10Y normalized PAT (deterministic mathematical invariance)
- Scenario B: Peak earnings -> normalization does not extrapolate peak
- Scenario C: High CV (>= 35%) -> is_compounder is strictly False
- Scenario D: High CV alone -> does not produce false classification if fundamentals fail
- Scenario E: Genuine cyclical evidence + high CV -> CYCLICAL_QUALITY
- Scenario F: High CV + structural deterioration -> DETERIORATING_BUSINESS / quality FAIL
- Scenario G: Stable high-quality business (CV < 35%) -> COMPOUNDER
- Scenario H: 5Y vs 10Y divergence preserved in audit trace
- Scenario I: Missing annual data -> INSUFFICIENT_DATA, never silently safe
- Scenario J: Bank archetype -> no industrial CFO/PAT false blocker
- Scenario K: Securities archetype -> no industrial CFO/PAT false blocker
- Scenario L: FPT secular growth regression & classification trace
- Scenario M: BFC fertilizer cyclical regression
- Scenario N: HAH container shipping cyclical regression
- Scenario O: ACB bank regression
- Scenario P: TCB bank regression
- Scenario Q: TPB bank regression
- Scenario R: TLG consumer/stationery regression
- Scenario S: CONDITIONAL_BUY canonical decision model consistency
"""

import pytest
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_history_builder import build_financial_history_from_facts
from portfolio.value_engine.munger_models import (
    CompounderClassification,
    DeteriorationClassification,
    DimensionStatus,
)


def _make_historical_facts(
    symbol: str,
    pat_by_year: dict[int, float],
    revenue_by_year: dict[int, float] | None = None,
    equity_by_year: dict[int, float] | None = None,
    cfo_by_year: dict[int, float] | None = None,
    debt_by_year: dict[int, float] | None = None,
) -> list[dict]:
    """Helper to synthesize canonical facts for unit testing."""
    facts = []
    for y, pat in pat_by_year.items():
        facts.append({
            "symbol": symbol,
            "statement_type": "INCOME_STATEMENT",
            "line_item_code": "IS.PROFIT.NET",
            "period_type": "FY",
            "fiscal_year": y,
            "provider": "ssi",
            "value": pat,
            "quality_status": "SINGLE_SOURCE",
            "observed_at": f"{y}-12-31",
        })
        rev = revenue_by_year.get(y, pat * 5.0) if revenue_by_year else pat * 5.0
        facts.append({
            "symbol": symbol,
            "statement_type": "INCOME_STATEMENT",
            "line_item_code": "IS.REVENUE",
            "period_type": "FY",
            "fiscal_year": y,
            "provider": "ssi",
            "value": rev,
            "quality_status": "SINGLE_SOURCE",
            "observed_at": f"{y}-12-31",
        })
        eq = equity_by_year.get(y, pat * 4.0) if equity_by_year else pat * 4.0
        facts.append({
            "symbol": symbol,
            "statement_type": "BALANCE_SHEET",
            "line_item_code": "BS.EQUITY.TOTAL",
            "period_type": "FY",
            "fiscal_year": y,
            "provider": "ssi",
            "value": eq,
            "quality_status": "SINGLE_SOURCE",
            "observed_at": f"{y}-12-31",
        })
        cfo = cfo_by_year.get(y, pat * 1.1) if cfo_by_year else pat * 1.1
        facts.append({
            "symbol": symbol,
            "statement_type": "CASH_FLOW",
            "line_item_code": "CF.OPERATING.NET",
            "period_type": "FY",
            "fiscal_year": y,
            "provider": "ssi",
            "value": cfo,
            "quality_status": "SINGLE_SOURCE",
            "observed_at": f"{y}-12-31",
        })
        debt = debt_by_year.get(y, pat * 0.5) if debt_by_year else pat * 0.5
        facts.append({
            "symbol": symbol,
            "statement_type": "BALANCE_SHEET",
            "line_item_code": "BS.DEBT.TOTAL",
            "period_type": "FY",
            "fiscal_year": y,
            "provider": "ssi",
            "value": debt,
            "quality_status": "SINGLE_SOURCE",
            "observed_at": f"{y}-12-31",
        })
    return facts


# =========================================================================
# Scenario A: Deterministic Invariance (Same facts -> exact same norm PAT)
# =========================================================================
def test_scenario_a_deterministic_invariance():
    pats = {
        2016: 100e9, 2017: 120e9, 2018: 140e9, 2019: 160e9, 2020: 180e9,
        2021: 200e9, 2022: 220e9, 2023: 240e9, 2024: 260e9, 2025: 280e9,
    }
    facts = _make_historical_facts("DETERMINISTIC_TEST", pats)
    res1 = build_munger_financial_analysis("DETERMINISTIC_TEST", raw_facts=facts)
    res2 = build_munger_financial_analysis("DETERMINISTIC_TEST", raw_facts=facts)

    norm1 = res1.normalized_earning_power
    norm2 = res2.normalized_earning_power

    expected_5y = sum([200e9, 220e9, 240e9, 260e9, 280e9]) / 5.0
    expected_10y = sum(pats.values()) / 10.0

    assert norm1["normalized_pat_5y"] == expected_5y
    assert norm1["normalized_pat_10y"] == expected_10y
    assert norm1["normalized_pat_5y"] == norm2["normalized_pat_5y"]
    assert norm1["normalized_pat_10y"] == norm2["normalized_pat_10y"]


# =========================================================================
# Scenario B: Peak earnings -> Normalization does not extrapolate peak
# =========================================================================
def test_scenario_b_peak_earnings_not_extrapolated():
    # 5Y history with huge peak in year 5
    pats = {
        2021: 100e9, 2022: 120e9, 2023: 110e9, 2024: 130e9, 2025: 600e9,  # peak year
    }
    facts = _make_historical_facts("PEAK_TEST", pats)
    res = build_munger_financial_analysis("PEAK_TEST", raw_facts=facts)
    norm = res.normalized_earning_power

    assert norm["is_peak_earnings"] is True
    # 5Y normalized is 212B, reported latest is 600B
    assert norm["normalized_pat_5y"] == sum(pats.values()) / 5.0
    assert norm["normalized_pat_5y"] < norm["reported_latest"] * 0.5


# =========================================================================
# Scenario C: High CV (>= 35%) -> is_compounder is strictly False
# =========================================================================
def test_scenario_c_high_cv_blocks_compounder():
    pats = {
        2021: 100e9, 2022: 300e9, 2023: 80e9, 2024: 250e9, 2025: 400e9,
    }
    facts = _make_historical_facts("HIGH_CV_TEST", pats)
    res = build_munger_financial_analysis("HIGH_CV_TEST", raw_facts=facts)
    norm = res.normalized_earning_power

    assert norm["earnings_volatility"] >= 0.35
    assert res.compounder_classification != CompounderClassification.COMPOUNDER.value


# =========================================================================
# Scenario D: High CV alone does not produce CYCLICAL_QUALITY if fundamentals fail
# =========================================================================
def test_scenario_d_high_cv_with_insolvency_is_not_cyclical_quality():
    pats = {
        2021: 100e9, 2022: 300e9, 2023: -50e9, 2024: 250e9, 2025: 400e9,
    }
    # Extreme debt causing solvency failure
    debts = {y: 5000e9 for y in pats}
    equities = {y: 100e9 for y in pats}
    facts = _make_historical_facts("DISTRESSED_TEST", pats, equity_by_year=equities, debt_by_year=debts)
    res = build_munger_financial_analysis("DISTRESSED_TEST", raw_facts=facts)

    assert res.long_term_decision["decision_trace"]["quality_gate"] in ("FAIL", "WATCH")
    assert res.compounder_classification in (
        CompounderClassification.DETERIORATING_BUSINESS.value,
        CompounderClassification.WEAK_BUSINESS.value,
        CompounderClassification.AVERAGE_BUSINESS.value,
    )


# =========================================================================
# Scenario E: Genuine cyclical evidence + high CV -> CYCLICAL_QUALITY
# =========================================================================
def test_scenario_e_genuine_cyclical_is_cyclical_quality():
    pats = {
        2021: 400e9, 2022: 800e9, 2023: 350e9, 2024: 600e9, 2025: 1100e9,
    }
    facts = _make_historical_facts("CYCLICAL_CO", pats)
    res = build_munger_financial_analysis("CYCLICAL_CO", raw_facts=facts)

    assert res.compounder_classification == CompounderClassification.CYCLICAL_QUALITY.value
    assert res.long_term_decision["decision_trace"]["quality_gate"] == "PASS"


# =========================================================================
# Scenario F: High CV + structural deterioration -> DETERIORATING_BUSINESS
# =========================================================================
def test_scenario_f_high_cv_with_structural_decay():
    pats = {
        2021: 500e9, 2022: 300e9, 2023: 100e9, 2024: -50e9, 2025: -200e9,
    }
    facts = _make_historical_facts("DECAY_CO", pats)
    res = build_munger_financial_analysis("DECAY_CO", raw_facts=facts)

    assert res.compounder_classification in (
        CompounderClassification.DETERIORATING_BUSINESS.value,
        CompounderClassification.WEAK_BUSINESS.value,
    )
    assert res.long_term_decision["decision_trace"]["quality_gate"] in ("FAIL", "WATCH")


# =========================================================================
# Scenario G: Stable high-quality business (CV < 35%) -> COMPOUNDER
# =========================================================================
def test_scenario_g_stable_high_quality_is_compounder():
    pats = {
        2021: 100e9, 2022: 112e9, 2023: 126e9, 2024: 141e9, 2025: 158e9,
    }
    facts = _make_historical_facts("STABLE_COMPOUNDER", pats)
    res = build_munger_financial_analysis("STABLE_COMPOUNDER", raw_facts=facts)
    norm = res.normalized_earning_power

    assert norm["earnings_volatility"] < 0.35
    assert res.compounder_classification == CompounderClassification.COMPOUNDER.value
    assert res.long_term_decision["decision_trace"]["quality_gate"] == "PASS"


# =========================================================================
# Scenario H: 5Y vs 10Y divergence preserved in audit trace
# =========================================================================
def test_scenario_h_5y_vs_10y_divergence_traceable():
    # 10Y history where last 5Y doubled
    pats = {
        2016: 50e9, 2017: 55e9, 2018: 52e9, 2019: 48e9, 2020: 55e9,
        2021: 100e9, 2022: 120e9, 2023: 110e9, 2024: 130e9, 2025: 150e9,
    }
    facts = _make_historical_facts("EXPANSION_CO", pats)
    res = build_munger_financial_analysis("EXPANSION_CO", raw_facts=facts)
    norm = res.normalized_earning_power

    assert norm["normalized_pat_5y"] > norm["normalized_pat_10y"]
    assert norm["normalized_pat_5y"] == sum(list(pats.values())[-5:]) / 5.0
    assert norm["normalized_pat_10y"] == sum(pats.values()) / 10.0


# =========================================================================
# Scenario I: Missing annual data -> INSUFFICIENT_DATA
# =========================================================================
def test_scenario_i_missing_annual_data():
    # Only 2 years of history
    pats = {2024: 100e9, 2025: 120e9}
    facts = _make_historical_facts("NEW_IPO", pats)
    res = build_munger_financial_analysis("NEW_IPO", raw_facts=facts)

    assert res.compounder_classification == CompounderClassification.INSUFFICIENT_DATA.value
    assert res.data_readiness == "INSUFFICIENT"


# =========================================================================
# Scenario J: Bank archetype -> no industrial CFO/PAT false blocker
# =========================================================================
def test_scenario_j_bank_archetype_no_industrial_cfo_blocker():
    pats = {
        2021: 1000e9, 2022: 1400e9, 2023: 1700e9, 2024: 1800e9, 2025: 1700e9,
    }
    # Bank with volatile/negative operating cash flow (standard deposit/loan cycle)
    cfos = {2021: -500e9, 2022: 2000e9, 2023: -1000e9, 2024: 3000e9, 2025: -200e9}
    facts = _make_historical_facts("ACB", pats, cfo_by_year=cfos)
    res = build_munger_financial_analysis("ACB", raw_facts=facts)

    assert res.overall_financial_quality.get("earnings_quality") == DimensionStatus.NOT_APPLICABLE.value
    assert res.long_term_decision["decision_trace"]["quality_gate"] == "PASS"


# =========================================================================
# Scenario K: Securities archetype -> no industrial CFO/PAT false blocker
# =========================================================================
def test_scenario_k_securities_archetype_no_industrial_cfo_blocker():
    pats = {
        2021: 500e9, 2022: 800e9, 2023: 400e9, 2024: 700e9, 2025: 900e9,
    }
    cfos = {y: -100e9 for y in pats}
    facts = _make_historical_facts("SSI", pats, cfo_by_year=cfos)
    res = build_munger_financial_analysis("SSI", raw_facts=facts)

    assert res.long_term_decision["decision_trace"]["quality_gate"] == "PASS"


# =========================================================================
# Scenario L: FPT Secular Growth Deep Trace
# =========================================================================
def test_scenario_l_fpt_secular_growth_trace():
    # FPT 15-year net profit series (2011-2025)
    fpt_pats = {
        2011: 1681.8e9, 2012: 1540.3e9, 2013: 1607.7e9, 2014: 1632.1e9, 2015: 1930.9e9,
        2016: 1990.6e9, 2017: 2931.5e9, 2018: 2620.2e9, 2019: 3135.4e9, 2020: 3538.0e9,
        2021: 4337.4e9, 2022: 5310.1e9, 2023: 6465.2e9, 2024: 7856.8e9, 2025: 9376.1e9,
    }
    facts = _make_historical_facts("FPT", fpt_pats)
    val_data = {
        "status": "READY",
        "current_price": 74300,
        "bear_iv": 68000,
        "base_iv": 95283,
        "actual_mos_pct": 22.0,
        "required_mos_pct": 20.0,
        "valuation_confidence": "HIGH",
    }
    res = build_munger_financial_analysis("FPT", raw_facts=facts, valuation_data=val_data)
    norm = res.normalized_earning_power

    # 5Y arithmetic average of 2021-2025 = 6,669.1B
    assert round(norm["normalized_pat_5y"] / 1e9, 1) == 6669.1
    # 10Y arithmetic average of 2016-2025 = 4,756.1B
    assert round(norm["normalized_pat_10y"] / 1e9, 1) == 4756.1
    # Quality gate is PASS
    assert res.long_term_decision["decision_trace"]["quality_gate"] == "PASS"


# =========================================================================
# Scenario M: BFC Fertilizer Cyclical Regression
# =========================================================================
def test_scenario_m_bfc_regression():
    bfc_pats = {
        2016: 277.1e9, 2017: 277.0e9, 2018: 193.4e9, 2019: 74.0e9, 2020: 133.2e9,
        2021: 219.6e9, 2022: 149.8e9, 2023: 148.2e9, 2024: 357.0e9, 2025: 309.9e9,
    }
    facts = _make_historical_facts("BFC", bfc_pats)
    val_data = {
        "status": "READY",
        "current_price": 31500,
        "bear_iv": 40000,
        "base_iv": 97100,
        "actual_mos_pct": 67.6,
        "required_mos_pct": 50.0,
        "valuation_confidence": "HIGH",
    }
    res = build_munger_financial_analysis("BFC", raw_facts=facts, valuation_data=val_data)
    norm = res.normalized_earning_power

    assert round(norm["normalized_pat_5y"] / 1e9, 1) == 236.9
    assert round(norm["normalized_pat_10y"] / 1e9, 1) == 213.9
    assert res.long_term_decision["decision_trace"]["quality_gate"] == "PASS"
    assert res.long_term_decision["state"] in ("BUY", "CONDITIONAL_BUY")


# =========================================================================
# Scenario N: HAH Container Shipping Cyclical Regression
# =========================================================================
def test_scenario_n_hah_regression():
    hah_pats = {
        2016: 133.8e9, 2017: 147.3e9, 2018: 135.2e9, 2019: 121.4e9, 2020: 138.3e9,
        2021: 445.5e9, 2022: 821.9e9, 2023: 384.9e9, 2024: 650.5e9, 2025: 1206.5e9,
    }
    facts = _make_historical_facts("HAH", hah_pats)
    val_data = {
        "status": "READY",
        "current_price": 38000,
        "bear_iv": 45000,
        "base_iv": 127600,
        "actual_mos_pct": 70.2,
        "required_mos_pct": 50.0,
        "valuation_confidence": "HIGH",
    }
    res = build_munger_financial_analysis("HAH", raw_facts=facts, valuation_data=val_data)
    norm = res.normalized_earning_power

    assert round(norm["normalized_pat_5y"] / 1e9, 1) == 701.9
    assert round(norm["normalized_pat_10y"] / 1e9, 1) == 418.5
    assert norm["is_peak_earnings"] is True
    assert res.long_term_decision["decision_trace"]["quality_gate"] == "PASS"
    assert res.long_term_decision["state"] in ("BUY", "CONDITIONAL_BUY")


# =========================================================================
# Scenario O: ACB Bank Regression
# =========================================================================
def test_scenario_o_acb_regression():
    acb_pats = {
        2016: 1325.2e9, 2017: 2118.1e9, 2018: 5137.1e9, 2019: 6009.9e9, 2020: 7682.8e9,
        2021: 9602.7e9, 2022: 13688.2e9, 2023: 16044.7e9, 2024: 16789.8e9, 2025: 15624.7e9,
    }
    facts = _make_historical_facts("ACB", acb_pats)
    val_data = {
        "status": "READY",
        "current_price": 24800,
        "bear_iv": 22000,
        "base_iv": 29400,
        "actual_mos_pct": 15.7,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
    }
    res = build_munger_financial_analysis("ACB", raw_facts=facts, valuation_data=val_data)
    norm = res.normalized_earning_power

    assert round(norm["normalized_pat_5y"] / 1e9, 1) == 14350.0
    assert round(norm["normalized_pat_10y"] / 1e9, 1) == 9402.3
    assert res.long_term_decision["decision_trace"]["quality_gate"] == "PASS"
    assert res.long_term_decision["state"] == "WAIT_FOR_MOS"


# =========================================================================
# Scenario P: TCB Bank Regression
# =========================================================================
def test_scenario_p_tcb_regression():
    tcb_pats = {
        2016: 3148.8e9, 2017: 6445.6e9, 2018: 8474.0e9, 2019: 10226.2e9, 2020: 12582.5e9,
        2021: 18415.4e9, 2022: 20436.4e9, 2023: 18190.9e9, 2024: 21760.1e9, 2025: 25954.5e9,
    }
    facts = _make_historical_facts("TCB", tcb_pats)
    val_data = {
        "status": "READY",
        "current_price": 23400,
        "bear_iv": 20000,
        "base_iv": 25400,
        "actual_mos_pct": 7.8,
        "required_mos_pct": 30.0,
        "valuation_confidence": "HIGH",
    }
    res = build_munger_financial_analysis("TCB", raw_facts=facts, valuation_data=val_data)
    norm = res.normalized_earning_power

    assert round(norm["normalized_pat_5y"] / 1e9, 1) == 20951.5
    assert round(norm["normalized_pat_10y"] / 1e9, 1) == 14563.4
    assert res.long_term_decision["decision_trace"]["quality_gate"] == "PASS"
    assert res.long_term_decision["state"] == "WAIT_FOR_MOS"


# =========================================================================
# Scenario Q: TPB Bank Regression
# =========================================================================
def test_scenario_q_tpb_regression():
    tpb_pats = {
        2016: 565.2e9, 2017: 963.6e9, 2018: 1805.2e9, 2019: 3093.8e9, 2020: 3510.2e9,
        2021: 4829.2e9, 2022: 6260.7e9, 2023: 4463.3e9, 2024: 6071.6e9, 2025: 7402.0e9,
    }
    facts = _make_historical_facts("TPB", tpb_pats)
    val_data = {
        "status": "READY",
        "current_price": 14200,
        "bear_iv": 16000,
        "base_iv": 24400,
        "actual_mos_pct": 41.8,
        "required_mos_pct": 30.0,
        "valuation_confidence": "HIGH",
    }
    res = build_munger_financial_analysis("TPB", raw_facts=facts, valuation_data=val_data)
    norm = res.normalized_earning_power

    assert round(norm["normalized_pat_5y"] / 1e9, 1) == 5805.4
    assert round(norm["normalized_pat_10y"] / 1e9, 1) == 3896.5
    assert res.long_term_decision["decision_trace"]["quality_gate"] == "PASS"
    assert res.long_term_decision["state"] in ("BUY", "CONDITIONAL_BUY")


# =========================================================================
# Scenario R: TLG Consumer/Stationery Regression
# =========================================================================
def test_scenario_r_tlg_regression():
    tlg_pats = {
        2011: 80.5e9, 2012: 100.2e9, 2013: 116.6e9, 2014: 147.4e9, 2015: 187.9e9,
        2016: 240.1e9, 2017: 268.1e9, 2018: 294.4e9, 2019: 349.1e9, 2020: 239.8e9,
        2021: 276.7e9, 2022: 401.4e9, 2023: 358.9e9, 2024: 461.7e9, 2025: 446.5e9,
    }
    facts = _make_historical_facts("TLG", tlg_pats)
    val_data = {
        "status": "READY",
        "current_price": 54000,
        "bear_iv": 20000,
        "base_iv": 27800,
        "actual_mos_pct": -93.8,
        "required_mos_pct": 30.0,
        "valuation_confidence": "HIGH",
    }
    res = build_munger_financial_analysis("TLG", raw_facts=facts, valuation_data=val_data)
    norm = res.normalized_earning_power

    assert round(norm["normalized_pat_5y"] / 1e9, 1) == 389.0
    assert round(norm["normalized_pat_10y"] / 1e9, 1) == 333.7
    assert res.long_term_decision["decision_trace"]["quality_gate"] == "PASS"
    assert res.long_term_decision["state"] == "WAIT_FOR_MOS"


# =========================================================================
# Scenario S: CONDITIONAL_BUY Decision Semantics Consistency
# =========================================================================
def test_scenario_s_conditional_buy_semantics():
    pats = {2021: 100e9, 2022: 120e9, 2023: 130e9, 2024: 140e9, 2025: 150e9}
    facts = _make_historical_facts("WATCH_CO", pats)
    val_data = {
        "status": "READY",
        "current_price": 50000,
        "bear_iv": 45000,  # price > bear_iv
        "base_iv": 80000,
        "actual_mos_pct": 37.5,
        "required_mos_pct": 20.0,
        "valuation_confidence": "HIGH",
    }
    res = build_munger_financial_analysis("WATCH_CO", raw_facts=facts, valuation_data=val_data)

    # When MOS passes but monitoring warning exists (or market price > bear IV), decision is CONDITIONAL_BUY
    assert res.long_term_decision["state"] in ("BUY", "CONDITIONAL_BUY")
    assert "watch_coexistence_rationale" in res.long_term_decision["decision_trace"] or "explanation" in res.long_term_decision
