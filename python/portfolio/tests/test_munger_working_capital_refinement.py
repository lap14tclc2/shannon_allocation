"""Test suite for refined Munger working capital separation, compounder classification, and decision trace (Task 172)."""

import pytest
from portfolio.value_engine.value_trap import evaluate_value_trap
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_models import CompounderClassification


def test_working_capital_separation_inventory_only():
    """Verify that when inventory grows faster than revenue but receivables grow slower,
    evidence matrix generates INVENTORY_DIVERGENCE and does NOT conflate receivables."""
    # Mock financial history where receivables grow at 5% (slower than revenue at 15%),
    # but inventory grows at 30% (faster than revenue at 15%).
    history = [
        {"fiscal_year": 2021, "revenue": 1000.0, "net_profit": 100.0, "receivables": 100.0, "inventory": 100.0, "cfo": 90.0, "total_assets": 1200.0, "total_debt": 200.0, "cash_and_equivalents": 300.0, "equity": 800.0},
        {"fiscal_year": 2022, "revenue": 1150.0, "net_profit": 120.0, "receivables": 105.0, "inventory": 130.0, "cfo": 100.0, "total_assets": 1400.0, "total_debt": 200.0, "cash_and_equivalents": 350.0, "equity": 900.0},
        {"fiscal_year": 2023, "revenue": 1320.0, "net_profit": 140.0, "receivables": 110.0, "inventory": 170.0, "cfo": 80.0, "total_assets": 1600.0, "total_debt": 200.0, "cash_and_equivalents": 400.0, "equity": 1000.0},
    ]

    vt = evaluate_value_trap(
        symbol="TEST_INV",
        valuation_report={"current_price": 50000, "bear_iv": 60000, "base_iv": 80000, "status": "READY"},
        financial_history=history,
    )

    risk_codes = [item["risk_code"] for item in vt.evidence_matrix]
    assert "INVENTORY_DIVERGENCE" in risk_codes
    assert "RECEIVABLES_DIVERGENCE" not in risk_codes
    assert "WORKING_CAPITAL_DIVERGENCE" not in risk_codes

    # Check top risks
    titles = [r.get("title_vi", "") for r in vt.top_risks]
    assert any("hàng tồn kho" in t.lower() for t in titles)
    assert not any("khoản phải thu" in t.lower() for t in titles)


def test_working_capital_separation_receivables_only():
    """Verify that when receivables grow faster than revenue but inventory grows slower,
    evidence matrix generates RECEIVABLES_DIVERGENCE and does NOT conflate inventory."""
    history = [
        {"fiscal_year": 2021, "revenue": 1000.0, "net_profit": 100.0, "receivables": 150.0, "inventory": 100.0, "cfo": 90.0, "total_assets": 1200.0, "total_debt": 200.0, "cash_and_equivalents": 300.0, "equity": 800.0},
        {"fiscal_year": 2022, "revenue": 1100.0, "net_profit": 110.0, "receivables": 200.0, "inventory": 105.0, "cfo": 60.0, "total_assets": 1400.0, "total_debt": 200.0, "cash_and_equivalents": 300.0, "equity": 900.0},
        {"fiscal_year": 2023, "revenue": 1200.0, "net_profit": 120.0, "receivables": 280.0, "inventory": 110.0, "cfo": 50.0, "total_assets": 1600.0, "total_debt": 200.0, "cash_and_equivalents": 300.0, "equity": 1000.0},
    ]

    vt = evaluate_value_trap(
        symbol="TEST_REC",
        valuation_report={"current_price": 50000, "bear_iv": 60000, "base_iv": 80000, "status": "READY"},
        financial_history=history,
    )

    risk_codes = [item["risk_code"] for item in vt.evidence_matrix]
    assert "RECEIVABLES_DIVERGENCE" in risk_codes
    assert "INVENTORY_DIVERGENCE" not in risk_codes


def test_compounder_classification_and_watch_coexistence():
    """Verify compounder classification criteria and explicit watch coexistence rationale."""
    # 1. Test Stable Compounder (FPT-like)
    stable_history = [
        {"fiscal_year": 2019, "revenue": 1000.0, "net_profit": 200.0, "equity": 800.0, "cfo": 220.0, "receivables": 150.0, "inventory": 80.0, "total_debt": 100.0, "cash_and_equivalents": 300.0, "total_assets": 1200.0, "shares_outstanding": 100.0},
        {"fiscal_year": 2020, "revenue": 1200.0, "net_profit": 250.0, "equity": 1000.0, "cfo": 270.0, "receivables": 170.0, "inventory": 90.0, "total_debt": 100.0, "cash_and_equivalents": 400.0, "total_assets": 1400.0, "shares_outstanding": 100.0},
        {"fiscal_year": 2021, "revenue": 1450.0, "net_profit": 310.0, "equity": 1250.0, "cfo": 330.0, "receivables": 200.0, "inventory": 100.0, "total_debt": 100.0, "cash_and_equivalents": 500.0, "total_assets": 1700.0, "shares_outstanding": 100.0},
        {"fiscal_year": 2022, "revenue": 1750.0, "net_profit": 380.0, "equity": 1550.0, "cfo": 400.0, "receivables": 240.0, "inventory": 110.0, "total_debt": 100.0, "cash_and_equivalents": 600.0, "total_assets": 2100.0, "shares_outstanding": 100.0},
        {"fiscal_year": 2023, "revenue": 2100.0, "net_profit": 460.0, "equity": 1900.0, "cfo": 480.0, "receivables": 280.0, "inventory": 120.0, "total_debt": 100.0, "cash_and_equivalents": 750.0, "total_assets": 2500.0, "shares_outstanding": 100.0},
    ]

    stable_res = build_munger_financial_analysis(
        symbol="STABLE_CO",
        existing_history=stable_history,
        valuation_data={"status": "READY", "current_price": 50000, "base_iv": 80000, "bear_iv": 60000, "actual_mos_pct": 37.5, "required_mos_pct": 15.0},
    )

    assert stable_res.compounder_classification == CompounderClassification.COMPOUNDER.value
    assert stable_res.long_term_decision["state"] == "BUY"

    # 2. Test Cyclical Quality (BFC/HAH-like with high volatility)
    cyclical_history = [
        {"fiscal_year": 2019, "revenue": 1000.0, "net_profit": 80.0, "equity": 800.0, "cfo": 70.0, "receivables": 100.0, "inventory": 100.0, "total_debt": 200.0, "cash_and_equivalents": 100.0, "total_assets": 1200.0, "shares_outstanding": 100.0},
        {"fiscal_year": 2020, "revenue": 900.0, "net_profit": 50.0, "equity": 820.0, "cfo": 40.0, "receivables": 90.0, "inventory": 110.0, "total_debt": 200.0, "cash_and_equivalents": 90.0, "total_assets": 1200.0, "shares_outstanding": 100.0},
        {"fiscal_year": 2021, "revenue": 1800.0, "net_profit": 350.0, "equity": 1100.0, "cfo": 200.0, "receivables": 130.0, "inventory": 250.0, "total_debt": 300.0, "cash_and_equivalents": 150.0, "total_assets": 1600.0, "shares_outstanding": 100.0},
        {"fiscal_year": 2022, "revenue": 2200.0, "net_profit": 500.0, "equity": 1500.0, "cfo": 250.0, "receivables": 160.0, "inventory": 400.0, "total_debt": 350.0, "cash_and_equivalents": 200.0, "total_assets": 2100.0, "shares_outstanding": 100.0},
        {"fiscal_year": 2023, "revenue": 1400.0, "net_profit": 120.0, "equity": 1550.0, "cfo": 180.0, "receivables": 120.0, "inventory": 300.0, "total_debt": 250.0, "cash_and_equivalents": 220.0, "total_assets": 2000.0, "shares_outstanding": 100.0},
    ]

    cyclical_res = build_munger_financial_analysis(
        symbol="CYC_CO",
        existing_history=cyclical_history,
        valuation_data={"status": "READY", "current_price": 30000, "base_iv": 50000, "bear_iv": 35000, "actual_mos_pct": 40.0, "required_mos_pct": 25.0},
    )

    # Must be classified as CYCLICAL_QUALITY, NOT permanent COMPOUNDER
    assert cyclical_res.compounder_classification == CompounderClassification.CYCLICAL_QUALITY.value

    # Decision trace must contain watch_coexistence_rationale if there are warnings
    assert "watch_coexistence_rationale" in cyclical_res.long_term_decision
    assert "decision_trace" in cyclical_res.long_term_decision
    assert "watch_coexistence_rationale" in cyclical_res.long_term_decision["decision_trace"]
    if cyclical_res.financial_warnings:
        assert cyclical_res.long_term_decision["watch_coexistence_rationale"] is not None
        assert "Biên an toàn" in cyclical_res.long_term_decision["watch_coexistence_rationale"]

