"""Unit and semantic tests for deterministic risk warnings and plain-language risk interpretation engine."""

import pytest
from portfolio.risk import portfolio_risk
from portfolio.risk_warnings import generate_risk_warnings, SEVERITY_ORDER


def test_balanced_portfolio_no_high_risk_warnings():
    risk_data = {
        "status": "VALID",
        "quality": {"coverage_weight": 1.0, "missing_symbols": []},
        "max_position_weight": 0.15,
        "largest_position_symbol": "AAA",
        "n_positions": 6,
        "effective_positions": 5.5,
        "hhi": 0.18,
        "risk_contributions": {"AAA": 0.16, "BBB": 0.17, "CCC": 0.16, "DDD": 0.17, "EEE": 0.17, "FFF": 0.17},
        "largest_risk_symbol": "BBB",
        "largest_risk_contribution": 0.17,
        "equal_risk_contribution": 0.1667,
        "volatility_63": 0.15,
        "volatility_252": 0.16,
        "volatility_ratio": 0.9375,
        "daily_var_95": -0.015,
        "daily_cvar_95": -0.022,
        "max_daily_loss": -0.03,
        "average_correlation": 0.25,
        "max_correlation": 0.40,
        "correlation_matrix": {"AAA": {"BBB": 0.3}, "BBB": {"AAA": 0.3}},
    }
    positions = [
        {"symbol": "AAA", "weight": 0.15},
        {"symbol": "BBB", "weight": 0.17},
        {"symbol": "CCC", "weight": 0.17},
        {"symbol": "DDD", "weight": 0.17},
        {"symbol": "EEE", "weight": 0.17},
        {"symbol": "FFF", "weight": 0.17},
    ]

    res = generate_risk_warnings(risk_data, positions)
    summary = res["summary"]
    warnings = res["warnings"]

    assert summary["overall_severity"] in ("NORMAL", "ATTENTION")
    assert summary["high_risk_count"] == 0
    assert summary["warning_count"] == 0


def test_max_weight_concentration_warnings():
    # 20-30% -> ATTENTION, 30-40% -> WARNING, >40% -> HIGH_RISK
    positions_high = [{"symbol": "DGC", "weight": 0.45}, {"symbol": "ACB", "weight": 0.55}]
    risk_high = {
        "status": "VALID",
        "quality": {"coverage_weight": 1.0, "missing_symbols": []},
        "max_position_weight": 0.55,
        "largest_position_symbol": "ACB",
        "n_positions": 2,
        "effective_positions": 1.9,
        "risk_contributions": {"DGC": 0.42, "ACB": 0.58},
        "largest_risk_symbol": "ACB",
        "largest_risk_contribution": 0.58,
    }

    res = generate_risk_warnings(risk_high, positions_high)
    assert res["summary"]["overall_severity"] == "HIGH_RISK"
    acb_warn = next(w for w in res["warnings"] if "ACB" in w["affected_symbols"])
    assert acb_warn["severity"] == "HIGH_RISK"
    assert "ACB" in acb_warn["title"] or "ACB" in acb_warn["summary"]


def test_risk_contribution_breach_warning():
    # DGC weight 35%, but risk contribution 49% -> breach
    positions = [{"symbol": "DGC", "weight": 0.35}, {"symbol": "VNM", "weight": 0.65}]
    risk_data = {
        "status": "VALID",
        "quality": {"coverage_weight": 1.0, "missing_symbols": []},
        "max_position_weight": 0.65,
        "largest_position_symbol": "VNM",
        "n_positions": 2,
        "effective_positions": 1.8,
        "risk_contributions": {"DGC": 0.49, "VNM": 0.51},
        "largest_risk_symbol": "VNM",
        "largest_risk_contribution": 0.51,
        "equal_risk_contribution": 0.50,
    }

    res = generate_risk_warnings(risk_data, positions)
    dgc_warn = next(w for w in res["warnings"] if "DGC" in w["affected_symbols"])
    assert dgc_warn["severity"] in ("WARNING", "HIGH_RISK")
    assert "dữ liệu" not in dgc_warn["id"].lower()
    assert "DGC" in dgc_warn["summary"]


def test_high_correlation_cluster_warning():
    corr_matrix = {
        "ACB": {"ACB": 1.0, "MBB": 0.78, "TCB": 0.72},
        "MBB": {"ACB": 0.78, "MBB": 1.0, "TCB": 0.75},
        "TCB": {"ACB": 0.72, "MBB": 0.75, "TCB": 1.0},
    }
    risk_data = {
        "status": "VALID",
        "quality": {"coverage_weight": 1.0, "missing_symbols": []},
        "correlation_matrix": corr_matrix,
        "max_correlation": 0.78,
        "n_positions": 3,
    }

    res = generate_risk_warnings(risk_data, [])
    corr_warn = next(w for w in res["warnings"] if w["category"] == "CORRELATION_CLUSTER")
    assert corr_warn["severity"] in ("WARNING", "HIGH_RISK")
    assert set(corr_warn["affected_symbols"]) == {"ACB", "MBB", "TCB"}
    assert "tương quan" in corr_warn["summary"].lower() or "tương quan" in corr_warn["title"].lower()


def test_effective_positions_low_warning():
    risk_data = {
        "status": "VALID",
        "quality": {"coverage_weight": 1.0, "missing_symbols": []},
        "n_positions": 8,
        "effective_positions": 2.8,
        "hhi": 0.35,
        "largest_position_symbol": "DGC",
    }
    res = generate_risk_warnings(risk_data, [])
    eff_warn = next(w for w in res["warnings"] if w["category"] == "DIVERSIFICATION")
    assert eff_warn["severity"] in ("WARNING", "HIGH_RISK")
    assert "8" in eff_warn["summary"]
    assert "2.8" in eff_warn["summary"]


def test_sector_concentration_warning():
    positions = [
        {"symbol": "ACB", "weight": 0.25, "sector": "Ngân hàng"},
        {"symbol": "MBB", "weight": 0.20, "sector": "Ngân hàng"},
        {"symbol": "TCB", "weight": 0.15, "sector": "Ngân hàng"},
        {"symbol": "FPT", "weight": 0.40, "sector": "Công nghệ"},
    ]
    risk_data = {"status": "VALID", "quality": {"coverage_weight": 1.0, "missing_symbols": []}}

    res = generate_risk_warnings(risk_data, positions)
    sector_warn = next(w for w in res["warnings"] if w["category"] == "SECTOR_CONCENTRATION")
    assert sector_warn["severity"] in ("WARNING", "HIGH_RISK")
    assert "Ngân hàng" in sector_warn["title"] or "Ngân hàng" in sector_warn["summary"]
    assert set(sector_warn["affected_symbols"]) == {"ACB", "MBB", "TCB"}


def test_var_cvar_statistically_correct_wording_and_disclaimer():
    risk_data = {
        "status": "VALID",
        "quality": {"coverage_weight": 1.0, "missing_symbols": []},
        "daily_var_95": -0.026,
        "daily_cvar_95": -0.041,
    }
    res = generate_risk_warnings(risk_data, [])
    var_warn = next(w for w in res["warnings"] if w["category"] == "TAIL_RISK")

    # Verify statistical correctness & disclaimers
    impact_text = var_warn["impact"]
    guidance_text = var_warn["review_guidance"]

    assert "5% số ngày xấu nhất" in impact_text
    assert "2.6%" in impact_text
    assert "4.1%" in impact_text
    assert "không phải mức lỗ tối đa" in guidance_text.lower() or "không phải mức lỗ tối đa" in impact_text.lower()
    assert "tối đa" not in var_warn["title"].lower()


def test_incomplete_data_produces_data_quality_warning():
    risk_data = {
        "status": "PARTIAL",
        "quality": {"coverage_weight": 0.65, "missing_symbols": ["VNM", "HPG"]},
    }
    res = generate_risk_warnings(risk_data, [])
    dq_warn = next(w for w in res["warnings"] if w["category"] == "DATA_QUALITY")

    assert dq_warn["severity"] == "WARNING"
    assert "VNM" in dq_warn["summary"] and "HPG" in dq_warn["summary"]
    assert "UNKNOWN != SAFE" in dq_warn["impact"] or "không có nghĩa là an toàn" in dq_warn["impact"]


def test_grouped_warning_avoids_duplicate_concentration_cards():
    # ACB is max weight 45% and max risk contribution 52%
    positions = [{"symbol": "ACB", "weight": 0.45}, {"symbol": "FPT", "weight": 0.55}]
    risk_data = {
        "status": "VALID",
        "quality": {"coverage_weight": 1.0, "missing_symbols": []},
        "max_position_weight": 0.45,
        "largest_position_symbol": "ACB",
        "risk_contributions": {"ACB": 0.52, "FPT": 0.48},
        "largest_risk_symbol": "ACB",
        "largest_risk_contribution": 0.52,
    }

    res = generate_risk_warnings(risk_data, positions)
    acb_warnings = [w for w in res["warnings"] if "ACB" in w["affected_symbols"] and w["category"] == "POSITION_CONCENTRATION"]

    # Exactly 1 consolidated warning for ACB position concentration/risk contribution
    assert len(acb_warnings) == 1
    evidence = acb_warnings[0]["evidence"]
    assert evidence["equity_weight"] == 0.45
    assert evidence["risk_contribution"] == 0.52


def test_deterministic_severity_and_priority_ordering():
    risk_data = {
        "status": "PARTIAL",
        "quality": {"coverage_weight": 0.70, "missing_symbols": ["XYZ"]},
        "max_position_weight": 0.42,
        "largest_position_symbol": "DGC",
        "n_positions": 5,
        "effective_positions": 2.1,
        "daily_var_95": -0.03,
        "daily_cvar_95": -0.045,
    }
    positions = [{"symbol": "DGC", "weight": 0.42}, {"symbol": "XYZ", "weight": 0.15}]

    res = generate_risk_warnings(risk_data, positions)
    warnings = res["warnings"]

    # Highest severity first, deterministic sorting
    for i in range(len(warnings) - 1):
        rank_curr = SEVERITY_ORDER[warnings[i]["severity"]]
        rank_next = SEVERITY_ORDER[warnings[i + 1]["severity"]]
        assert rank_curr >= rank_next


def test_zero_trade_action_keywords_returned_by_risk_engine():
    risk_data = {
        "status": "VALID",
        "quality": {"coverage_weight": 1.0, "missing_symbols": []},
        "max_position_weight": 0.50,
        "largest_position_symbol": "DGC",
        "n_positions": 2,
        "effective_positions": 1.8,
        "risk_contributions": {"DGC": 0.55, "VNM": 0.45},
    }
    positions = [{"symbol": "DGC", "weight": 0.50}, {"symbol": "VNM", "weight": 0.50}]

    res = generate_risk_warnings(risk_data, positions)
    full_text = str(res).upper()

    forbidden = ["BUY_MORE", "REDUCE", "SELL", "NÊN BÁN", "CẦN BÁN", "NÊN MUA", "CẦN MUA"]
    for word in forbidden:
        assert word not in full_text, f"Forbidden action word '{word}' found in risk warning output!"


def test_canonical_portfolio_risk_integration():
    positions = [{"symbol": "FPT", "market_value": 100000.0, "weight": 1.0}]
    histories = {
        "FPT": [{"trading_date": f"2026-01-{i:02d}", "close": 100.0 + i} for i in range(1, 60)]
    }

    risk_result = portfolio_risk(positions, histories)

    assert "risk_summary" in risk_result
    assert "warnings" in risk_result
    assert risk_result["risk_summary"]["overall_severity"] in ("NORMAL", "ATTENTION", "WARNING", "HIGH_RISK")
    assert isinstance(risk_result["warnings"], list)
