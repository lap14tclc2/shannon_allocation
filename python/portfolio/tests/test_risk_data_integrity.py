"""
Regression and data integrity tests for /risk diagnostics analytics.
Ensures weight normalization, coverage semantics, correlation nulls, evidence-backed permanent loss labels,
bank-specific balance sheet logic, moat strength vs trend separation, and solvency evidence consistency.
"""

import pytest
import pandas as pd
import numpy as np
from portfolio.risk import portfolio_risk
from portfolio.permanent_loss_risk import (
    assess_permanent_loss_risk_for_symbol,
)


@pytest.fixture
def sample_portfolio_data():
    """Portfolio with 3 positions and cash (34.2% cash, FPT 52.7% NAV weight, ACB 10% NAV weight, DGC 3.1% NAV weight)."""
    position_rows = [
        {"symbol": "FPT", "market_value": 527_000_000, "weight": 0.527, "price": 130000},
        {"symbol": "ACB", "market_value": 100_000_000, "weight": 0.100, "price": 25000},
        {"symbol": "DGC", "market_value": 31_000_000, "weight": 0.031, "price": 100000},
        {"symbol": "CASH", "market_value": 342_000_000, "weight": 0.342, "price": 1.0},
    ]

    # 250 distinct business daily return history entries for DGC only. FPT and ACB have no/insufficient price histories.
    np.random.seed(42)
    dgc_prices = [100.0]
    for _ in range(250):
        dgc_prices.append(dgc_prices[-1] * (1.0 + np.random.normal(0.0005, 0.02)))

    dates = pd.date_range("2025-01-01", periods=251, freq="B").strftime("%Y-%m-%d")

    histories = {
        "DGC": [
            {"trading_date": dates[i], "close": dgc_prices[i]}
            for i in range(251)
        ],
        "FPT": [
            {"trading_date": dates[i], "close": 130.0}
            for i in range(5)  # Insufficient history (< 40 observations)
        ],
        "ACB": [],  # Missing history
    }

    return position_rows, histories


def test_weight_semantics_normalization(sample_portfolio_data):
    """NAV weight is primary weight (FPT 52.7% NAV weight), equity_weight is exposed explicitly (80.1%)."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    metrics = risk_res["symbol_metrics"]
    fpt = metrics["FPT"]

    # Primary weight must be NAV weight (527M / 1000M = 0.527)
    assert abs(fpt["weight"] - 0.527) < 1e-4
    assert abs(fpt["nav_weight"] - 0.527) < 1e-4

    # Equity weight is market_value / total_equity (527M / 658M = ~0.8009)
    assert abs(fpt["equity_weight"] - (527.0 / 658.0)) < 1e-4


# ---------------------------------------------------------------------------
# 21 Specific Regression Invariant Tests as per Prompt Requirements
# ---------------------------------------------------------------------------

def test_req_1_nav_coverage_insufficient_status(sample_portfolio_data):
    """Regression Test 1: 3.1% NAV coverage => market-risk data status INSUFFICIENT."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    assert risk_res["risk_coverage_status"] == "INSUFFICIENT"
    assert risk_res["market_risk"]["status"] == "INSUFFICIENT_DATA"
    assert risk_res["market_risk"]["status_text"] == "Chưa đủ dữ liệu"


def test_req_2_insufficient_data_cannot_return_high_volatility_severity(sample_portfolio_data):
    """Regression Test 2: Insufficient data cannot return overall HIGH_RISK volatility severity."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    assert risk_res["market_risk"]["overall_severity"] == "INSUFFICIENT_DATA"
    assert risk_res["overall_severity"] == "INSUFFICIENT_DATA"


def test_req_3_fpt_ineligible_risk_contribution_none(sample_portfolio_data):
    """Regression Test 3: FPT ineligible => risk_contribution is None."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    fpt = risk_res["symbol_metrics"]["FPT"]
    assert fpt["risk_contribution"] is None
    assert fpt["risk_contribution_status"] == "UNAVAILABLE"


def test_req_4_acb_ineligible_risk_contribution_none(sample_portfolio_data):
    """Regression Test 4: ACB ineligible => risk_contribution is None."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    acb = risk_res["symbol_metrics"]["ACB"]
    assert acb["risk_contribution"] is None
    assert acb["risk_contribution_status"] == "UNAVAILABLE"


def test_req_5_null_contribution_text(sample_portfolio_data):
    """Regression Test 5: Ineligible symbol risk_contribution_text is 'Chưa tính được'."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    fpt = risk_res["symbol_metrics"]["FPT"]
    assert fpt["risk_contribution_text"] == "Chưa tính được"


def test_req_6_dgc_only_eligible_scope(sample_portfolio_data):
    """Regression Test 6: DGC-only risk universe => 100% scope ELIGIBLE_UNIVERSE_ONLY."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    dgc = risk_res["symbol_metrics"]["DGC"]
    assert dgc["risk_contribution"] == 1.0
    assert dgc["risk_contribution_scope"] == "ELIGIBLE_UNIVERSE_ONLY"


def test_req_7_ui_headline_never_claims_full_portfolio_for_dgc(sample_portfolio_data):
    """Regression Test 7: UI text never claims DGC is '100% tổng biến động danh mục'."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    dgc = risk_res["symbol_metrics"]["DGC"]
    assert "tổng biến động danh mục" not in dgc["risk_contribution_text"].lower()
    assert "đo lường được" in dgc["risk_contribution_text"] or "đủ dữ liệu" in dgc["risk_contribution_text"]


def test_req_8_insufficient_coverage_portfolio_var_none(sample_portfolio_data):
    """Regression Test 8: Insufficient coverage => portfolio VaR None."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    assert risk_res["portfolio_daily_var_95"] is None


def test_req_9_insufficient_coverage_portfolio_cvar_none(sample_portfolio_data):
    """Regression Test 9: Insufficient coverage => portfolio CVaR None."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    assert risk_res["portfolio_daily_cvar_95"] is None


def test_req_10_insufficient_coverage_portfolio_downside_vol_none(sample_portfolio_data):
    """Regression Test 10: Insufficient coverage => portfolio downside volatility None."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    assert risk_res["portfolio_downside_volatility"] is None


def test_req_11_symbol_level_dgc_metrics_allowed(sample_portfolio_data):
    """Regression Test 11: Symbol-level DGC metrics remain allowed when DGC has sufficient price history."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    dgc = risk_res["symbol_metrics"]["DGC"]
    assert dgc["annualized_volatility"] is not None
    assert dgc["daily_var_95"] is not None
    assert dgc["daily_cvar_95"] is not None


def test_req_12_effective_positions_labeled_by_weight(sample_portfolio_data):
    """Regression Test 12: Effective positions from HHI is labeled by-weight, not independent."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    # Warnings or summary should not state "independent positions" or "đa dạng hóa thực tế"
    for w in risk_res.get("warnings", []):
        if w.get("category") == "CONCENTRATION":
            assert "thực tế như số lượng" not in w.get("message", "")
            assert "độc lập" not in w.get("message", "")
            assert "tỷ trọng" in w.get("message", "") or "tập trung" in w.get("message", "")


def test_req_13_concentration_warning_works_without_price_history(sample_portfolio_data):
    """Regression Test 13: Concentration warning still works without price history (FPT 52.7% NAV)."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    conc_warnings = [w for w in risk_res["warnings"] if "CONCENTRATION" in w.get("category") or w.get("category") == "DIVERSIFICATION"]
    assert len(conc_warnings) > 0
    assert any("FPT" in w.get("summary", "") or "FPT" in w.get("title", "") for w in conc_warnings)


def test_req_14_correlation_null_remains_null(sample_portfolio_data):
    """Regression Test 14: Correlation null remains null."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    matrix = risk_res["correlation_matrix"]
    assert matrix["FPT"]["ACB"] is None
    assert matrix["FPT"]["DGC"] is None


def test_req_15_no_synthetic_correlation(sample_portfolio_data):
    """Regression Test 15: No synthetic correlation (e.g., fallback 0.35)."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    assert risk_res["average_correlation"] is None


def test_req_16_solvency_hard_reject_and_no_violation_cannot_coexist():
    """Regression Test 16: True solvency hard reject and 'no solvency violation' cannot coexist."""
    fund_data = {
        "hard_rejects": ["SOLVENCY_RISK"],
        "quality_tier": "DISTRESSED",
    }
    res = assess_permanent_loss_risk_for_symbol("TEST", fund_data, 0.20)
    assert "Không có vi phạm Solvency" not in res["thesis_evidence"]
    assert "Không có vi phạm Solvency" not in res["balance_sheet_evidence"]
    assert "vi phạm khả năng thanh toán" in res["balance_sheet_evidence"].lower() or "solvency" in res["balance_sheet_evidence"].lower()


def test_req_17_non_hard_reject_solvency_does_not_use_reject_word():
    """Regression Test 17: Non-hard-reject solvency score does not use the word 'Reject'."""
    fund_data = {
        "hard_rejects": [],
        "de_ratio": 1.2,
        "solvency_score": 10.0,
    }
    res = assess_permanent_loss_risk_for_symbol("FPT", fund_data, 0.527)
    assert "Reject" not in res["balance_sheet_text"]
    assert "Reject" not in res["balance_sheet_evidence"]


def test_req_18_single_moat_score_cannot_produce_deteriorating_trend():
    """Regression Test 18: Single moat score cannot produce DETERIORATING trend."""
    fund_data = {
        "moat": "NARROW",
        "moat_score": 7.0,  # Low score
    }
    res = assess_permanent_loss_risk_for_symbol("FPT", fund_data, 0.527)
    assert res["moat_trend"] == "UNKNOWN"
    assert res["moat_trend"] != "DETERIORATING"


def test_req_19_moat_7_out_of_100_yields_weak_strength_and_unknown_trend():
    """Regression Test 19: Moat 7/100 yields moat_strength = WEAK and moat_trend = UNKNOWN."""
    fund_data = {
        "moat_score": 7.0,
    }
    res = assess_permanent_loss_risk_for_symbol("FPT", fund_data, 0.527)
    assert res["moat_strength"] == "WEAK"
    assert res["moat_trend"] == "UNKNOWN"
    assert "yếu" in res["moat_strength_text"].lower()


def test_req_20_permanent_loss_unknown_never_becomes_low():
    """Regression Test 20: Permanent loss UNKNOWN never becomes LOW automatically."""
    res = assess_permanent_loss_risk_for_symbol("UNKNOWN_SYM", None, 0.10)
    assert res["overall_risk"] == "UNKNOWN"
    assert res["overall_risk"] != "LOW"
