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
    """AC5 & AC6: CONDITIONAL_BUY exposes explicit condition and separates blockers from monitoring signals."""
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
    assert len(dec["conditions"]) > 0
    assert dec["conditions"][0]["metric"] == "bear_iv_headroom"
    assert dec["conditions"][0]["threshold"] == 45000.0
    assert dec["blocking_reasons"] == []
    assert len(dec["monitoring_reasons"]) > 0
    assert dec["watch_coexistence_rationale"] is not None
    assert "không phải lỗi chặn mua (Hard Blocker)" in dec["watch_coexistence_rationale"]


def test_buy_when_all_hard_gates_pass_with_monitoring_signals():
    """P0: When all hard gates pass and no conditional condition, decision is BUY with monitoring signals separated."""
    pats = [100e9, 250e9, 120e9, 310e9, 309.9e9]
    history = [
        {"fiscal_year": 2020 + i, "net_profit": pats[i], "revenue": 2000e9 + i * 100e9, "equity": 1000e9 + i * 150e9, "operating_cash_flow": 220e9, "total_debt": 300e9}
        for i in range(5)
    ]

    val_data = {
        "status": "READY",
        "current_price": 48600.0,
        "base_iv": 147901.0,
        "bear_iv": 90000.0,
        "bull_iv": 180000.0,
        "actual_mos_pct": 67.1,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }

    munger = build_munger_financial_analysis("BFC_BUY_TEST", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    dec = m_dict["long_term_decision"]
    assert dec["state"] == "BUY"
    assert dec["mos_gate"] == "PASS"
    assert dec["blocking_reasons"] == []
    assert len(dec["monitoring_reasons"]) > 0
    assert "Độ biến động LNST lịch sử tương đối cao" in " ".join(dec["monitoring_reasons"])
    assert "Đạt chuẩn mua tích sản" in dec["primary_reason"]
    assert dec["conditions"] == []


def test_earnings_durability_vs_volatility_separation():
    """P1: Earnings durability (persistence) is separated from volatility (CV)."""
    pats = [100e9, 250e9, 120e9, 310e9, 309.9e9]
    history = [
        {"fiscal_year": 2020 + i, "net_profit": pats[i], "revenue": 2000e9 + i * 100e9, "equity": 1000e9 + i * 150e9, "operating_cash_flow": 220e9, "total_debt": 300e9}
        for i in range(5)
    ]

    munger = build_munger_financial_analysis("BFC_DUR_TEST", existing_history=history)
    dur = munger.to_dict()["earnings_durability"]

    assert dur["status"] == "PASS"
    assert dur["metrics"]["profitable_years"] == 5
    assert dur["metrics"]["negative_earnings_years"] == 0
    assert dur["metrics"]["earnings_persistence_rate"] == 1.0
    assert dur["metrics"]["pat_volatility"] is not None
    assert "tính bền bỉ đạt chuẩn" in dur["explanation"]


def test_stress_test_independence_and_neutral_semantics():
    """P1: Q3 and Q4 stress tests have independent calculation provenance and neutral semantics."""
    history = [
        {"fiscal_year": 2020 + i, "net_profit": 200e9, "revenue": 2000e9, "equity": 1000e9, "operating_cash_flow": 200e9, "total_debt": 200e9}
        for i in range(5)
    ]
    val_data = {
        "status": "READY",
        "current_price": 48600.0,
        "base_iv": 147901.0,
        "bear_iv": 90000.0,
        "bull_iv": 180000.0,
        "actual_mos_pct": 67.1,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }

    munger = build_munger_financial_analysis("STRESS_TEST", existing_history=history, valuation_data=val_data)
    tc = munger.to_dict()["thesis_challenge"]

    q3 = next(q for q in tc["questions"] if q["question_number"] == 3)
    q4 = next(q for q in tc["questions"] if q["question_number"] == 4)
    q8 = next(q for q in tc["questions"] if q["question_number"] == 8)

    assert q3["metrics"]["scenario"] == "OWNER_EARNINGS_HAIRCUT_30"
    assert q3["metrics"]["baseline"] == "NORMALIZED_EARNING_POWER"
    assert "Vẫn đạt ngưỡng MOS" in q3["summary_vi"]

    assert q4["metrics"]["scenario"] == "VALUATION_MODEL_MARGIN_ERROR_30"
    assert q4["metrics"]["baseline"] == "CANONICAL_INTRINSIC_VALUE"
    assert "Vẫn đạt ngưỡng MOS" in q4["summary_vi"]

    assert "ngưỡng theo dõi của QPort" in q8["summary_vi"]


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


def test_canonical_price_propagation_across_layers():
    """P0 Invariant: ONE ANALYSIS RUN = ONE CANONICAL MARKET PRICE across valuation, liquidity, and decision."""
    canonical_price = 48600.0
    history = [
        {"fiscal_year": 2020 + i, "net_profit": 200e9, "revenue": 1000e9, "equity": 800e9, "operating_cash_flow": 190e9, "total_debt": 100e9}
        for i in range(5)
    ]
    val_data = {
        "status": "READY",
        "current_price": canonical_price,
        "base_iv": 147901.0,
        "bear_iv": 90000.0,
        "bull_iv": 180000.0,
        "actual_mos_pct": round(((147901.0 - canonical_price) / 147901.0) * 100, 1),
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "INVESTABLE",
    }

    munger = build_munger_financial_analysis("BFC", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()

    assert m_dict["valuation"]["current_price"] == canonical_price
    assert m_dict["liquidity"]["latest_price"] == canonical_price
    # Displayed MOS is exactly reproducible from canonical price and Base IV
    expected_mos = round(((147901.0 - canonical_price) / 147901.0) * 100, 1)
    assert m_dict["valuation"]["actual_mos_pct"] == expected_mos


def test_stress_test_independence():
    """AC11 & AC12: Stress tests Q3 (earnings power haircut) vs Q4 (valuation model error) are independent."""
    canonical_price = 48600.0
    base_iv = 100000.0
    history = [
        {"fiscal_year": 2020 + i, "net_profit": 200e9, "revenue": 1000e9, "equity": 800e9, "operating_cash_flow": 190e9, "total_debt": 100e9}
        for i in range(5)
    ]
    val_data = {
        "status": "READY",
        "current_price": canonical_price,
        "base_iv": base_iv,
        "actual_mos_pct": 51.4,
        "required_mos_pct": 25.0,
    }

    munger = build_munger_financial_analysis("STRESS_TEST", existing_history=history, valuation_data=val_data)
    m_dict = munger.to_dict()
    challenge = m_dict.get("thesis_challenge", {})
    stress_map = challenge.get("stress_tests", {})

    assert "q3_stress" in stress_map
    assert "q4_stress" in stress_map
    q3 = stress_map["q3_stress"]
    q4 = stress_map["q4_stress"]

    # Q3 tests -30% and -50% earnings power impact
    assert q3["minus_30_iv"] == 70000.0
    assert q3["minus_50_iv"] == 50000.0
    # Q4 tests 30% valuation model error
    assert q4["haircut_iv"] == 70000.0
    assert q4["haircut_pct"] == 30.0
