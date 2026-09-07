"""
Regression and data integrity tests for /risk diagnostics analytics.
Ensures weight normalization, coverage semantics, correlation nulls, evidence-backed permanent loss labels,
and bank-specific balance sheet logic.
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
    """Req 1 & 8: NAV weight is primary weight (FPT 52.7% NAV weight), equity_weight is exposed explicitly (80.1%)."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    metrics = risk_res["symbol_metrics"]
    fpt = metrics["FPT"]

    # Primary weight must be NAV weight (527M / 1000M = 0.527)
    assert abs(fpt["weight"] - 0.527) < 1e-4
    assert abs(fpt["nav_weight"] - 0.527) < 1e-4

    # Equity weight is market_value / total_equity (527M / 658M = ~0.8009)
    assert abs(fpt["equity_weight"] - (527.0 / 658.0)) < 1e-4

    # Check position_rows retain consistent NAV weight semantics
    for row in risk_res.get("position_rows", positions):
        if row["symbol"] == "FPT":
            assert abs(row["weight"] - 0.527) < 1e-4


def test_risk_contribution_coverage_semantics(sample_portfolio_data):
    """Req 2 & 3: Incomplete data sets risk_coverage_status to INSUFFICIENT or PARTIAL."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    assert risk_res["risk_coverage_status"] == "INSUFFICIENT"
    assert risk_res["risk_eligible_symbols"] == ["DGC"]
    assert risk_res["risk_total_symbols"] == 3
    assert abs(risk_res["risk_eligible_nav_weight"] - 0.031) < 1e-4

    # Warnings check: DATA_QUALITY warning with reason code DATA_QUALITY_INSUFFICIENT should be raised
    dq_warnings = [w for w in risk_res["warnings"] if w.get("category") == "DATA_QUALITY"]
    assert len(dq_warnings) > 0
    assert "DATA_QUALITY_INSUFFICIENT" in dq_warnings[0]["reason_codes"]


def test_no_fabricated_correlation_nulls(sample_portfolio_data):
    """Req 3, 4, 5: Pairwise correlation between missing history symbols stays None, no 0.35 fallback."""
    positions, histories = sample_portfolio_data
    risk_res = portfolio_risk(positions, histories)

    matrix = risk_res["correlation_matrix"]
    assert "FPT" in matrix
    assert "ACB" in matrix
    assert "DGC" in matrix

    # Pairwise missing correlation must be None, NOT 0.35 or 0.0
    assert matrix["FPT"]["ACB"] is None
    assert matrix["FPT"]["DGC"] is None
    assert matrix["ACB"]["FPT"] is None
    assert risk_res["average_correlation"] is None


def test_missing_moat_evidence_returns_unknown():
    """Req 5 & 11: Missing moat evidence yields UNKNOWN, never DETERIORATING."""
    res = assess_permanent_loss_risk_for_symbol("FPT", None, 0.527)
    assert res["moat"] == "UNKNOWN"
    assert res["moat_text"] == "Chưa đủ dữ liệu"
    assert "Chưa có dữ liệu" in res["moat_evidence"] or "Chưa đủ" in res["moat_evidence"]


def test_bank_specific_balance_sheet_logic():
    """Req 6 & 12: Bank (ACB) uses bank-specific metrics (CAR, NPL), not industrial D/E ratio."""
    bank_fund = {
        "quality_tier": "HIGH_QUALITY",
        "is_bank": True,
        "car_ratio": 0.12,
        "npl_ratio": 0.015,
        "credit_cost": 0.008,
    }
    res = assess_permanent_loss_risk_for_symbol("ACB", bank_fund, 0.10)
    assert res["balance_sheet"] in ("SAFE", "BANK_SAFE")
    assert "CAR" in res["balance_sheet_evidence"] or "NPL" in res["balance_sheet_evidence"] or "Ngân hàng" in res["balance_sheet_evidence"]


def test_permanent_loss_evidence_strings():
    """Req 7 & 10: Permanent loss response includes evidence strings for fundamental dimensions."""
    fund_data = {
        "quality_tier": "HIGH_QUALITY",
        "roe_avg_3y": 0.22,
        "de_ratio": 0.4,
        "pe_ratio": 15.0,
        "actual_mos_pct": 0.25,
        "required_mos_pct": 0.15,
        "moat": "WIDE",
        "moat_notes": "Lợi thế chi phí chuyển đổi cao",
    }
    res = assess_permanent_loss_risk_for_symbol("FPT", fund_data, 0.527)
    assert "business_quality_evidence" in res
    assert "balance_sheet_evidence" in res
    assert "moat_evidence" in res
    assert "valuation_evidence" in res
    assert "thesis_evidence" in res
    assert res["evidence_strength"] in ("CONFIRMED", "INDICATIVE", "INSUFFICIENT")
