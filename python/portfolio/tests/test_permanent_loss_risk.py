"""Tests for Permanent Capital Loss Risk model and separation from Market Volatility Risk."""

from __future__ import annotations

import math
import pytest

from portfolio.permanent_loss_risk import (
    assess_permanent_loss_risk_for_symbol,
    assess_portfolio_permanent_loss_risk,
    calculate_position_stress_test,
)
from portfolio.risk import portfolio_risk
from portfolio.risk_warnings import generate_risk_warnings


def test_1_high_volatility_does_not_imply_high_permanent_loss_risk():
    """Requirement 1: High volatility does not automatically imply high permanent-loss risk."""
    signal = {
        "symbol": "HIGHVOL",
        "quality_tier": "HIGH_QUALITY",
        "hard_rejects": [],
        "financial_strength_score": 85,
        "actual_mos_pct": 25.0,
        "required_mos_pct": 15.0,
        "valuation_confidence": "HIGH",
    }
    # Company has strong fundamentals & positive MOS
    result = assess_permanent_loss_risk_for_symbol("HIGHVOL", signal, weight=0.15)
    assert result["severity"] in ("LOW", "MODERATE")
    assert result["severity"] != "HIGH"
    assert result["thesis_status"] == "INTACT"


def test_2_high_risk_contribution_does_not_trigger_business_risk_warning():
    """Requirement 2: High risk contribution does not automatically trigger business-risk warning."""
    signal = {
        "symbol": "DGC",
        "quality_tier": "HIGH_QUALITY",
        "hard_rejects": [],
        "financial_strength_score": 90,
        "actual_mos_pct": 20.0,
        "required_mos_pct": 15.0,
        "industry": "HÓA CHẤT",
    }
    # DGC with 42.2% weight and 59.5% risk contribution
    result = assess_permanent_loss_risk_for_symbol("DGC", signal, weight=0.422)

    assert result["severity"] in ("LOW", "MODERATE")
    assert result["thesis_status"] == "INTACT"
    # Business quality is strong
    assert result["business_quality"] == "HIGH_QUALITY"


def test_3_price_decline_alone_does_not_break_thesis():
    """Requirement 3: Price decline alone does not break thesis."""
    signal = {
        "symbol": "FPT",
        "quality_tier": "EXCEPTIONAL",
        "hard_rejects": [],
        "financial_strength_score": 95,
        "actual_mos_pct": 10.0,
        "required_mos_pct": 15.0,
    }
    # Simulate -30% price drop
    result = assess_permanent_loss_risk_for_symbol("FPT", signal, weight=0.25, market_price_change_30d=-0.30)
    assert result["thesis_status"] == "INTACT"
    assert result["thesis_status"] != "BROKEN"


def test_4_solvency_hard_reject_causes_high_permanent_loss_risk():
    """Requirement 4: Solvency hard reject => high permanent-loss risk."""
    signal = {
        "symbol": "BADDEBT",
        "quality_tier": "INVESTABLE",
        "hard_rejects": ["SOLVENCY_RISK"],
        "financial_strength_score": 20,
    }
    result = assess_permanent_loss_risk_for_symbol("BADDEBT", signal, weight=0.10)
    assert result["severity"] == "HIGH"
    assert result["thesis_status"] == "BROKEN"


def test_5_accounting_unreliability_causes_high_permanent_loss_risk():
    """Requirement 5: Accounting unreliability => high permanent-loss risk."""
    signal = {
        "symbol": "FRAUD",
        "quality_tier": "INVESTABLE",
        "hard_rejects": ["ACCOUNTING_UNRELIABLE"],
    }
    result = assess_permanent_loss_risk_for_symbol("FRAUD", signal, weight=0.10)
    assert result["severity"] == "HIGH"
    assert result["thesis_status"] == "BROKEN"


def test_6_quality_deterioration_causes_elevated_or_high_risk():
    """Requirement 6: Quality deterioration => elevated/high risk."""
    signal = {
        "symbol": "DECAY",
        "quality_tier": "LOW_QUALITY",
        "hard_rejects": [],
    }
    result = assess_permanent_loss_risk_for_symbol("DECAY", signal, weight=0.10)
    assert result["severity"] in ("ELEVATED", "HIGH")
    assert result["thesis_status"] == "BROKEN"


def test_7_valuation_overpayment_raises_valuation_risk_not_business_quality_risk():
    """Requirement 7: Valuation overpayment raises valuation risk but not business-quality risk."""
    signal = {
        "symbol": "EXPENSIVE",
        "quality_tier": "EXCEPTIONAL",
        "hard_rejects": [],
        "financial_strength_score": 95,
        "actual_mos_pct": -30.0,  # Strongly overvalued
        "required_mos_pct": 15.0,
    }
    result = assess_permanent_loss_risk_for_symbol("EXPENSIVE", signal, weight=0.10)
    # Valuation risk is HIGH/ELEVATED
    assert result["valuation_risk"] in ("ELEVATED", "HIGH")
    # But business quality remains EXCEPTIONAL
    assert result["business_quality"] == "EXCEPTIONAL"
    assert result["business_quality_text"] == "Xuất sắc"


def test_8_missing_data_returns_unknown():
    """Requirement 8: Missing data => UNKNOWN (UNKNOWN != SAFE)."""
    result = assess_permanent_loss_risk_for_symbol("NODATA", signal=None, weight=0.10)
    assert result["severity"] == "UNKNOWN"
    assert result["severity_text"] == "Chưa đủ dữ liệu"
    assert "UNKNOWN != SAFE" in result["main_concerns"][0]


def test_9_bank_specific_assessment_avoids_industrial_leverage_rules():
    """Requirement 9: Bank-specific assessment does not use inappropriate industrial leverage rules."""
    signal = {
        "symbol": "ACB",
        "quality_tier": "HIGH_QUALITY",
        "archetype": "BANK",
        "hard_rejects": [],
        "financial_strength_score": 50,  # Industrial score might be moderate, but bank balance sheet is safe
    }
    result = assess_permanent_loss_risk_for_symbol("ACB", signal, weight=0.20)
    assert result["balance_sheet"] == "BANK_SAFE"
    assert result["balance_sheet_text"] == "Chỉ số an toàn ngân hàng tốt"
    assert result["severity"] in ("LOW", "MODERATE")


def test_10_cyclical_business_evaluated_with_cyclical_durability():
    """Requirement 10: Cyclical business can be high volatility but moderate permanent-loss risk."""
    signal = {
        "symbol": "HPG",
        "quality_tier": "HIGH_QUALITY",
        "industry": "THÉP",
        "archetype": "COMMODITY_CYCLICAL",
        "hard_rejects": [],
        "financial_strength_score": 85,
        "actual_mos_pct": 10.0,
        "required_mos_pct": 15.0,
    }
    result = assess_permanent_loss_risk_for_symbol("HPG", signal, weight=0.15)
    assert result["earnings_durability"] == "CYCLICAL"
    assert result["earnings_durability_text"] == "Mang tính chu kỳ"
    assert result["severity"] == "MODERATE"


def test_11_market_risk_and_permanent_loss_rendered_separately():
    """Requirement 11: Market-risk warnings and permanent-loss warnings are rendered separately."""
    positions = [
        {"symbol": "DGC", "weight": 0.422, "market_value": 422000000},
        {"symbol": "FPT", "weight": 0.578, "market_value": 578000000},
    ]
    # Build histories for histories parameter
    histories = {
        "DGC": [{"trading_date": f"2026-01-{i:02d}", "close": 100 + i} for i in range(1, 45)],
        "FPT": [{"trading_date": f"2026-01-{i:02d}", "close": 80 + (i % 3)} for i in range(1, 45)],
    }
    signals = {
        "DGC": {"symbol": "DGC", "quality_tier": "HIGH_QUALITY", "hard_rejects": [], "industry": "HÓA CHẤT"},
        "FPT": {"symbol": "FPT", "quality_tier": "EXCEPTIONAL", "hard_rejects": []},
    }

    res = portfolio_risk(positions, histories, valuation_signals=signals)
    assert "market_risk" in res
    assert "permanent_loss_risk" in res
    assert "symbol_risk" in res
    assert "DGC" in res["symbol_risk"]
    assert "market_risk" in res["symbol_risk"]["DGC"]
    assert "permanent_loss_risk" in res["symbol_risk"]["DGC"]


def test_12_high_concentration_produces_concentration_reminder_not_sell():
    """Requirement 12: DGC-like high concentration produces concentration reminder, not automatic sell."""
    positions = [{"symbol": "DGC", "weight": 0.422, "market_value": 422000000}]
    histories = {"DGC": [{"trading_date": f"2026-01-{i:02d}", "close": 100} for i in range(1, 45)]}
    signals = {"DGC": {"symbol": "DGC", "quality_tier": "HIGH_QUALITY", "hard_rejects": []}}

    res = portfolio_risk(positions, histories, valuation_signals=signals)
    dgc_perm = res["symbol_risk"]["DGC"]["permanent_loss_risk"]
    assert dgc_perm["concentrated_thesis_risk"] is not None
    assert "DGC chiếm 42.2% danh mục" in dgc_perm["concentrated_thesis_risk"]
    # Verify no action is returned
    assert "action" not in res
    assert "recommendation" not in res


def test_13_stress_test_math_correct():
    """Requirement 13: Simple -30% position stress test math is correct."""
    stress = calculate_position_stress_test(0.4217)
    assert stress is not None
    shocks = {s["price_shock_pct"]: s["nav_impact_pct"] for s in stress["shocks"]}
    # -30% shock: 0.4217 * -0.30 = -0.12651 -> rounded -0.1265
    assert math.isclose(shocks[-0.30], -0.1265, abs_tol=1e-3)


def test_14_no_trade_action_returned_from_risk():
    """Requirement 14: No BUY/SELL/REDUCE action returned from /risk."""
    positions = [{"symbol": "DGC", "weight": 1.0, "market_value": 1000.0}]
    histories = {"DGC": [{"trading_date": f"2026-01-{i:02d}", "close": 100} for i in range(1, 45)]}
    res = portfolio_risk(positions, histories)

    res_str = str(res)
    for forbidden_action in ("'BUY'", "'SELL'", "'REDUCE'", "'BUY_MORE'"):
        assert forbidden_action not in res_str


def test_15_portfolio_risk_is_advisory_only():
    """Requirement 15: Allocation remains the only capital-action surface."""
    positions = [{"symbol": "FPT", "weight": 0.5, "market_value": 500.0}]
    histories = {"FPT": [{"trading_date": f"2026-01-{i:02d}", "close": 100} for i in range(1, 45)]}
    res = portfolio_risk(positions, histories)
    assert "symbol_risk" in res
    assert "action" not in res


def test_16_no_ledger_mutation():
    """Requirement 16: Permanent loss risk engine does not mutate position rows or state."""
    positions = [{"symbol": "FPT", "weight": 0.5, "market_value": 500.0}]
    original_copy = [dict(p) for p in positions]
    assess_portfolio_permanent_loss_risk(positions)
    assert positions == original_copy
