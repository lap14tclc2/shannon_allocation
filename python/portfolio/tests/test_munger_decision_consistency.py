"""Regression tests for Munger/Buffett decision consistency, liquidity, market price, and evidence traceability (Task 173)."""

import pytest
from portfolio.value_engine.liquidity_evaluator import classify_liquidity, evaluate_symbol_liquidity
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_models import CompounderClassification
from portfolio.canonical_valuation import build_canonical_valuation


def test_liquidity_invariant_missing_not_safe():
    """AC1: Missing trading value must NEVER claim >5B/day or PASS threshold."""
    # Case 1: Volume exists, but trading value is None
    code, vi_label, comment = classify_liquidity(
        avg_val_20d_billion=None,
        avg_vol_20d=150_000,
        coverage_pct=95.0,
        trading_days=20,
    )
    assert code == "LIQUIDITY_INSUFFICIENT_DATA"
    assert vi_label == "Chưa đủ dữ liệu thanh khoản"
    assert "chưa đủ dữ liệu để xác nhận giá trị giao dịch bình quân" in comment
    assert ">5 tỷ" not in comment

    # Case 2: Trading value < 5B/day
    code_weak, vi_weak, comment_weak = classify_liquidity(
        avg_val_20d_billion=3.2,
        avg_vol_20d=250_000,
        coverage_pct=90.0,
        trading_days=20,
    )
    assert code_weak == "LIQUIDITY_WEAK"
    assert vi_weak == "Thanh khoản thấp"
    assert "<5 tỷ/ngày" in comment_weak
    assert ">5 tỷ/ngày" not in comment_weak

    # Case 3: Trading value >= 5B/day with >= 60% coverage
    code_ok, vi_ok, comment_ok = classify_liquidity(
        avg_val_20d_billion=6.5,
        avg_vol_20d=250_000,
        coverage_pct=80.0,
        trading_days=20,
    )
    assert code_ok == "LIQUIDITY_ACCEPTABLE"
    assert vi_ok == "Thanh khoản đủ"
    assert ">5 tỷ/ngày" in comment_ok


def test_canonical_market_price_and_mos_reproducibility():
    """AC2 & AC3: One canonical market price snapshot and reproducible MOS."""
    # Synthetic valuation data
    curr_price = 45000.0
    base_iv = 60000.0
    actual_mos = round(((base_iv - curr_price) / base_iv) * 100, 1)  # 25.0%

    history = [
        {"fiscal_year": 2020 + i, "net_profit": 200e9 + i * 20e9, "revenue": 1000e9 + i * 50e9, "equity": 800e9, "operating_cash_flow": 190e9, "total_debt": 100e9}
        for i in range(5)
    ]

    val_data = {
        "status": "READY",
        "current_price": curr_price,
        "base_iv": base_iv,
        "bear_iv": 40000.0,
        "bull_iv": 75000.0,
        "actual_mos_pct": actual_mos,
        "required_mos_pct": 20.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }

    munger = build_munger_financial_analysis("TEST_SYM", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    dec = m_dict["long_term_decision"]
    assert dec["actual_mos_pct"] == actual_mos
    assert dec["mos_gate"] == "PASS"
    assert dec["decision_authority"] == "MUNGER_BCTC_PIPELINE"
    assert dec["state"] in ("BUY", "CONDITIONAL_BUY")


def test_conditional_buy_separates_blockers_from_monitoring():
    """AC5 & AC6: CONDITIONAL_BUY explains non-fatal monitoring signals without blocking."""
    # BFC-like case: High ROE, good PAT growth, but CV volatility ~ 43.9%
    pats = [100e9, 250e9, 120e9, 310e9, 309.9e9]
    history = [
        {"fiscal_year": 2020 + i, "net_profit": pats[i], "revenue": 2000e9 + i * 100e9, "equity": 1000e9 + i * 150e9, "operating_cash_flow": 220e9, "total_debt": 300e9}
        for i in range(5)
    ]

    val_data = {
        "status": "READY",
        "current_price": 46750.0,
        "base_iv": 68000.0,
        "bear_iv": 45000.0,
        "bull_iv": 80000.0,
        "actual_mos_pct": 31.25,
        "required_mos_pct": 25.0,
        "valuation_confidence": "MEDIUM",
        "quality_tier": "INVESTABLE",
    }

    munger = build_munger_financial_analysis("BFC_TEST", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    dec = m_dict["long_term_decision"]
    assert dec["state"] == "CONDITIONAL_BUY"
    assert dec["mos_gate"] == "PASS"
    assert "Điều kiện mua đã đạt theo các cổng chính" in dec["primary_reason"]
    assert "chỉ tiêu cần tiếp tục theo dõi" in dec["primary_reason"]
    assert dec["watch_coexistence_rationale"] is not None
    assert "không phải lỗi chặn mua (Hard Blocker)" in dec["watch_coexistence_rationale"]
    assert len(dec["monitoring_reasons"]) > 0


def test_compounder_classification_not_blindly_pat_cagr():
    """AC10: Highly volatile cyclical earnings are classified as CYCLICAL_QUALITY, not durable COMPOUNDER."""
    # Volatile earnings pattern (e.g. fertilizer / commodity)
    pats = [80e9, 350e9, 110e9, 420e9, 310e9]
    history = [
        {"fiscal_year": 2020 + i, "net_profit": pats[i], "revenue": 1500e9 + i * 100e9, "equity": 800e9 + i * 100e9, "operating_cash_flow": 200e9, "total_debt": 200e9}
        for i in range(5)
    ]

    munger = build_munger_financial_analysis("CYCLIC_TEST", existing_history=history)
    m_dict = munger.to_dict()

    # Volatility CV > 0.35 must yield CYCLICAL_QUALITY rather than durable COMPOUNDER
    assert m_dict["compounder_classification"] == CompounderClassification.CYCLICAL_QUALITY.value
