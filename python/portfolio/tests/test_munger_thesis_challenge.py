"""Unit and Integration Tests for Automated Munger Investment Thesis Challenge Engine (Task 141)."""

import pytest
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_thesis_challenge import (
    ThesisChallengeAnswerStatus,
    run_thesis_challenge_analysis,
)


@pytest.fixture
def mock_normal_munger_analysis():
    return {
        "symbol": "FPT",
        "archetype": "NORMAL_ENTERPRISE",
        "data_readiness": "READY",
        "all_findings": [],
        "hard_financial_failures": [],
        "financial_warnings": [],
        "value_trap_assessment": {"status": "CLEAR", "deterioration_classification": "NO_DETERIORATION"},
        "normalized_earning_power": {
            "reported_latest": 7500e9,
            "normalized_5y": 6800e9,
            "normalized_10y": 5200e9,
        },
        "overall_financial_quality": {"growth": "PASS", "profitability": "PASS", "debt_liquidity": "PASS"},
        "long_term_decision": {"state": "WAIT_FOR_MOS", "actual_mos_pct": 12.5, "required_mos_pct": 25.0, "mos_gate": "FAIL"},
        "valuation": {
            "status": "READY",
            "base_iv": 145000.0,
            "current_price": 128000.0,
            "actual_mos_pct": 12.5,
            "required_mos_pct": 25.0,
            "mos_gate": "FAIL",
        },
        "profitability_analysis": {"metrics": {"median_roe": 0.245, "margin_trend": "EXPANDING"}},
        "debt_liquidity": {"metrics": {"latest_debt_equity": 0.35}},
        "compounder_classification": "COMPOUNDER",
    }


def test_all_eight_questions_received(mock_normal_munger_analysis):
    res = run_thesis_challenge_analysis(mock_normal_munger_analysis)
    assert len(res.questions) == 8
    q_nums = [q.question_number for q in res.questions]
    assert q_nums == list(range(1, 9))


def test_q2_bctc_limitation_statement(mock_normal_munger_analysis):
    res = run_thesis_challenge_analysis(mock_normal_munger_analysis)
    q2 = next(q for q in res.questions if q.question_number == 2)
    assert "BCTC không thể chứng minh trực tiếp" in q2.limitations


def test_q3_normalized_earnings_stress_recalculation(mock_normal_munger_analysis):
    res = run_thesis_challenge_analysis(mock_normal_munger_analysis)
    q3 = next(q for q in res.questions if q.question_number == 3)
    assert "minus_30_iv" in q3.metrics
    assert "minus_50_iv" in q3.metrics
    # Base IV 145,000 * 0.70 = 101,500
    assert q3.metrics["minus_30_iv"] == 101500.0


def test_q4_valuation_haircut_30_percent(mock_normal_munger_analysis):
    res = run_thesis_challenge_analysis(mock_normal_munger_analysis)
    q4 = next(q for q in res.questions if q.question_number == 4)
    assert q4.metrics["haircut_pct"] == 30.0
    # Base IV 145,000 * 0.70 = 101,500
    assert q4.metrics["haircut_iv"] == 101500.0


def test_q5_pbs_missing_returns_insufficient_data(mock_normal_munger_analysis):
    res = run_thesis_challenge_analysis(mock_normal_munger_analysis, personal_balance_sheet=None)
    q5 = next(q for q in res.questions if q.question_number == 5)
    assert q5.answer_status == ThesisChallengeAnswerStatus.INSUFFICIENT_DATA
    assert "Chưa đủ dữ liệu tài chính cá nhân" in q5.summary_vi


def test_q5_pbs_available_returns_resilient(mock_normal_munger_analysis):
    pbs = {"safe_liquid_assets": 500e6, "monthly_burn_rate": 25e6, "survival_months": 20.0, "margin_debt": 0}
    res = run_thesis_challenge_analysis(mock_normal_munger_analysis, personal_balance_sheet=pbs)
    q5 = next(q for q in res.questions if q.question_number == 5)
    assert q5.answer_status == ThesisChallengeAnswerStatus.RESILIENT


def test_q7_price_decline_alone_cannot_imply_value(mock_normal_munger_analysis):
    # Set high risk value trap
    analysis = dict(mock_normal_munger_analysis)
    analysis["value_trap_assessment"] = {"status": "HIGH_RISK"}
    res = run_thesis_challenge_analysis(analysis)
    q7 = next(q for q in res.questions if q.question_number == 7)
    assert q7.metrics["classification"] == "POSSIBLE_VALUE_TRAP"
    assert q7.answer_status == ThesisChallengeAnswerStatus.VULNERABLE


def test_q8_measurable_invalidation_criteria(mock_normal_munger_analysis):
    res = run_thesis_challenge_analysis(mock_normal_munger_analysis)
    assert len(res.invalidation_criteria) >= 3
    for crit in res.invalidation_criteria:
        assert "metric" in crit
        assert "trigger" in crit
        assert "reason" in crit


def test_archetype_specific_bank_rules():
    bank_analysis = {
        "symbol": "ACB",
        "archetype": "BANK",
        "data_readiness": "READY",
        "all_findings": [],
        "hard_financial_failures": [],
        "financial_warnings": [],
        "value_trap_assessment": {"status": "CLEAR"},
        "normalized_earning_power": {"normalized_5y": 15000e9},
        "overall_financial_quality": {"profitability": "PASS"},
        "long_term_decision": {"state": "WAIT_FOR_MOS"},
        "valuation": {"status": "READY", "base_iv": 32000.0, "current_price": 24000.0, "actual_mos_pct": 25.0, "required_mos_pct": 20.0, "mos_gate": "PASS"},
        "profitability_analysis": {"metrics": {"median_roe": 0.21, "margin_trend": "STABLE"}},
        "debt_liquidity": {"metrics": {"latest_debt_equity": None}},  # Bank no industrial D/E
    }
    res = run_thesis_challenge_analysis(bank_analysis)
    assert res.archetype == "BANK"
    q8 = next(q for q in res.questions if q.question_number == 8)
    assert any("ROE Ngân hàng" in c["metric"] for c in res.invalidation_criteria)


def test_decision_preservation_and_contradiction_check(mock_normal_munger_analysis):
    analysis = dict(mock_normal_munger_analysis)
    analysis["long_term_decision"] = {"state": "BUY"}
    analysis["hard_financial_failures"] = ["CRITICAL_ACCOUNTING_FAIL"]
    res = run_thesis_challenge_analysis(analysis)
    # Decision remains BUY in munger analysis payload, but contradiction is flagged
    assert res.decision_contradiction is True
    assert "Decision Contradiction" in res.contradiction_details
