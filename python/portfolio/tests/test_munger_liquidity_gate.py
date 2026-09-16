"""
Unit tests for Munger Stock Screening Liquidity Gate and Vietnamese Semantics.

Validates:
1. Liquidity evaluation logic and boundary classifications (>=10B strong, >=5B acceptable, <5B weak).
2. Independent evaluation: Liquidity does not overwrite financial quality.
3. Holistic conclusion synthesis combining Quality, Valuation, Value Trap, and Liquidity.
4. Munger candidate filtering by liquidity tier and minimum turnover (min_val_billion).
5. Vietnamese semantic dictionary integrity (no missing enums).
"""

import pytest
from unittest.mock import patch, MagicMock
from portfolio.value_engine.liquidity_evaluator import (
    evaluate_symbol_liquidity,
    synthesize_munger_screening_conclusion_vi,
    LIQUIDITY_CLASSIFICATION_VI,
)
from portfolio.value_engine.munger_candidates import get_munger_candidates
from portfolio.value_engine.vietnamese_presenter import (
    LIQUIDITY_VIETNAMESE,
    get_vietnamese_liquidity,
)


def test_liquidity_classification_constants():
    assert "LIQUIDITY_STRONG" in LIQUIDITY_CLASSIFICATION_VI
    assert LIQUIDITY_CLASSIFICATION_VI["LIQUIDITY_STRONG"] == "Thanh khoản tốt"
    assert LIQUIDITY_CLASSIFICATION_VI["LIQUIDITY_ACCEPTABLE"] == "Thanh khoản đủ"
    assert LIQUIDITY_CLASSIFICATION_VI["LIQUIDITY_WEAK"] == "Thanh khoản thấp"
    assert LIQUIDITY_CLASSIFICATION_VI["LIQUIDITY_INSUFFICIENT_DATA"] == "Chưa đủ dữ liệu thanh khoản"


def test_vietnamese_presenter_liquidity():
    assert get_vietnamese_liquidity("LIQUIDITY_STRONG") == "Thanh khoản tốt"
    assert get_vietnamese_liquidity("LIQUIDITY_ACCEPTABLE") == "Thanh khoản đủ"
    assert get_vietnamese_liquidity("LIQUIDITY_WEAK") == "Thanh khoản thấp"
    assert get_vietnamese_liquidity("UNKNOWN") == "Chưa đủ dữ liệu thanh khoản"
    assert get_vietnamese_liquidity(None) == "Chưa đủ dữ liệu thanh khoản"


def test_liquidity_evaluator_insufficient_data():
    with patch("portfolio.finance_catalog._schema_connection") as mock_conn:
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = []
        mock_conn.return_value.__enter__.return_value = mock_db

        result = evaluate_symbol_liquidity("XYZ")
        assert result["classification"] == "LIQUIDITY_INSUFFICIENT_DATA"
        assert result["classification_vi"] == "Chưa đủ dữ liệu thanh khoản"
        assert result["data_status"] == "INSUFFICIENT_DATA"


def test_liquidity_evaluator_strong_volume():
    # 20 days with 600k volume and 100,000 price -> 60B VND/day (>= 10B)
    mock_rows = [
        {"trading_date": f"2026-09-{i:02d}", "close": 100000.0, "volume": 600000.0}
        for i in range(1, 21)
    ]
    with patch("portfolio.finance_catalog._schema_connection") as mock_conn:
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = mock_rows
        mock_conn.return_value.__enter__.return_value = mock_db

        result = evaluate_symbol_liquidity("FPT")
        assert result["classification"] == "LIQUIDITY_STRONG"
        assert result["classification_vi"] == "Thanh khoản tốt"
        assert result["avg_trading_value_20d_billion"] >= 10.0
        assert result["trading_day_coverage_pct"] == 100.0


def test_liquidity_evaluator_acceptable_volume():
    # 20 days with 250k volume and 30,000 price -> 7.5B VND/day (>= 5B, < 10B)
    mock_rows = [
        {"trading_date": f"2026-09-{i:02d}", "close": 30000.0, "volume": 250000.0}
        for i in range(1, 21)
    ]
    with patch("portfolio.finance_catalog._schema_connection") as mock_conn:
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = mock_rows
        mock_conn.return_value.__enter__.return_value = mock_db

        result = evaluate_symbol_liquidity("MID")
        assert result["classification"] == "LIQUIDITY_ACCEPTABLE"
        assert result["classification_vi"] == "Thanh khoản đủ"
        assert result["avg_trading_value_20d_billion"] >= 5.0
        assert result["avg_trading_value_20d_billion"] < 10.0


def test_liquidity_evaluator_weak_volume():
    # 20 days with 50k volume and 40,000 price -> 2.0B VND/day (< 5B -> WEAK)
    mock_rows = [
        {"trading_date": f"2026-09-{i:02d}", "close": 40000.0, "volume": 50000.0}
        for i in range(1, 21)
    ]
    with patch("portfolio.finance_catalog._schema_connection") as mock_conn:
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = mock_rows
        mock_conn.return_value.__enter__.return_value = mock_db

        result = evaluate_symbol_liquidity("TINY")
        assert result["classification"] == "LIQUIDITY_WEAK"
        assert result["classification_vi"] == "Thanh khoản thấp"
        assert result["avg_trading_value_20d_billion"] < 5.0


def test_screening_conclusion_synthesis():
    # 1. Exceptional Quality + Good Liquidity + Good MOS
    c1 = synthesize_munger_screening_conclusion_vi(
        quality_tier="EXCEPTIONAL",
        compounder_class="COMPOUNDER",
        mos=35.0,
        req_mos=25.0,
        vt_status="CLEAR",
        liquidity_code="LIQUIDITY_STRONG",
    )
    assert "Đạt tiêu chuẩn Munger" in c1
    assert "thanh khoản tốt" in c1

    # 2. Exceptional Quality + Weak Liquidity + Good MOS
    c2 = synthesize_munger_screening_conclusion_vi(
        quality_tier="EXCEPTIONAL",
        compounder_class="COMPOUNDER",
        mos=40.0,
        req_mos=25.0,
        vt_status="CLEAR",
        liquidity_code="LIQUIDITY_WEAK",
    )
    assert "thanh khoản thấp" in c2 or "thanh khoản hạn chế" in c2
    assert "thận trọng" in c2 or "cẩn trọng" in c2

    # 3. Quality good + Low MOS
    c3 = synthesize_munger_screening_conclusion_vi(
        quality_tier="HIGH_QUALITY",
        compounder_class="POTENTIAL_COMPOUNDER",
        mos=5.0,
        req_mos=25.0,
        vt_status="CLEAR",
        liquidity_code="LIQUIDITY_STRONG",
    )
    assert "chưa đủ hấp dẫn" in c3

    # 4. Value trap HIGH_RISK
    c4 = synthesize_munger_screening_conclusion_vi(
        quality_tier="HIGH_QUALITY",
        compounder_class="POTENTIAL_COMPOUNDER",
        mos=30.0,
        req_mos=25.0,
        vt_status="HIGH_RISK",
        liquidity_code="LIQUIDITY_STRONG",
    )
    assert "Rủi ro tài chính" in c4 or "bẫy giá trị" in c4


def test_munger_candidate_liquidity_structure():
    """Verify _evaluate_candidate_symbol is importable and callable."""
    from portfolio.value_engine.munger_candidates import _evaluate_candidate_symbol
    res = _evaluate_candidate_symbol("__NONEXISTENT__")
    assert res is None


def test_munger_candidates_filter_min_val():
    """Verify filtering candidates by min_val_billion."""
    res = get_munger_candidates(min_val_billion=5.0)
    assert res["ok"] is True
    for c in res["candidates"]:
        val_20 = c.get("liquidity", {}).get("avg_trading_value_20d_billion")
        if val_20 is not None:
            assert val_20 >= 5.0


def test_munger_candidates_rejects_under_5b_default():
    """Verify default candidate list never includes stocks under 5.0B VND/day."""
    fake_candidates = [
        {"symbol": "CMF", "liquidity": {"avg_trading_value_20d_billion": 0.04}, "candidate_tier_code": "HIGH_QUALITY", "quality_tier": "HIGH_QUALITY", "company_name": "CMF"},
        {"symbol": "HLB", "liquidity": {"avg_trading_value_20d_billion": 0.04}, "candidate_tier_code": "HIGH_QUALITY", "quality_tier": "HIGH_QUALITY", "company_name": "HLB"},
        {"symbol": "MID_2B", "liquidity": {"avg_trading_value_20d_billion": 2.5}, "candidate_tier_code": "HIGH_QUALITY", "quality_tier": "HIGH_QUALITY", "company_name": "MID_2B"},
        {"symbol": "FPT", "liquidity": {"avg_trading_value_20d_billion": 50.0}, "candidate_tier_code": "EXCEPTIONAL", "quality_tier": "EXCEPTIONAL", "company_name": "FPT"},
        {"symbol": "CTR", "liquidity": {"avg_trading_value_20d_billion": 19.08}, "candidate_tier_code": "EXCEPTIONAL", "quality_tier": "EXCEPTIONAL", "company_name": "CTR"},
    ]
    with patch("portfolio.value_engine.munger_candidates.compute_all_munger_candidates", return_value=fake_candidates):
        res = get_munger_candidates()
        assert res["ok"] is True
        symbols = [c["symbol"] for c in res["candidates"]]
        assert "CMF" not in symbols
        assert "HLB" not in symbols
        assert "MID_2B" not in symbols
        assert "FPT" in symbols
        assert "CTR" in symbols

