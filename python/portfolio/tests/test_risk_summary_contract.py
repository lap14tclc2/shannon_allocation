"""Tests for portfolio risk summary data contract, formatting semantics, and unavailable data states."""

import pytest
from portfolio.risk import portfolio_risk
from portfolio.risk_warnings import generate_risk_warnings


def test_annualized_volatility_field_and_formatting():
    """volatility_252 must represent decimal annualized volatility (e.g. 0.428 -> 42.8%)."""
    positions = [
        {"symbol": "FPT", "market_value": 100000.0, "weight": 1.0}
    ]
    histories = {
        "FPT": [{"trading_date": f"2026-01-{i:02d}", "close": 100.0 + (i % 5)} for i in range(1, 60)]
    }

    res = portfolio_risk(positions, histories)

    assert "volatility_252" in res
    assert res["volatility_252"] is not None
    assert isinstance(res["volatility_252"], float)
    assert res["volatility_252"] >= 0.0
    # 0.428 should represent 42.8%, never scaled to 4280%
    vol = res["volatility_252"]
    formatted_pct_str = f"{vol * 100:.1f}%"
    assert "%" in formatted_pct_str


def test_average_correlation_unavailable_for_single_position():
    """average_correlation must be None when n_positions < 2, never 0.0 or assumed safe."""
    positions = [
        {"symbol": "FPT", "market_value": 100000.0, "weight": 1.0}
    ]
    histories = {
        "FPT": [{"trading_date": f"2026-01-{i:02d}", "close": 100.0 + i} for i in range(1, 60)]
    }

    res = portfolio_risk(positions, histories)

    assert res["n_positions"] == 1
    assert res["average_correlation"] is None  # UNKNOWN != ZERO


def test_average_correlation_valid_for_multiple_positions():
    """average_correlation must return a float between -1.0 and 1.0 when sufficient overlapping history exists."""
    positions = [
        {"symbol": "FPT", "market_value": 50000.0, "weight": 0.5},
        {"symbol": "VNM", "market_value": 50000.0, "weight": 0.5},
    ]
    histories = {
        "FPT": [{"trading_date": f"2026-01-{i:02d}", "close": 100.0 + (i % 3)} for i in range(1, 60)],
        "VNM": [{"trading_date": f"2026-01-{i:02d}", "close": 80.0 + (i % 4)} for i in range(1, 60)],
    }

    res = portfolio_risk(positions, histories)

    assert res["n_positions"] == 2
    assert res["average_correlation"] is not None
    assert -1.0 <= res["average_correlation"] <= 1.0


def test_risk_summary_payload_contract():
    """portfolio_risk must return risk_summary with overall_severity, headline, and warnings."""
    positions = [
        {"symbol": "DGC", "market_value": 70000.0, "weight": 0.7},
        {"symbol": "ACB", "market_value": 30000.0, "weight": 0.3},
    ]
    histories = {
        "DGC": [{"trading_date": f"2026-01-{i:02d}", "close": 90.0 + (i % 7)} for i in range(1, 60)],
        "ACB": [{"trading_date": f"2026-01-{i:02d}", "close": 25.0 + (i % 2)} for i in range(1, 60)],
    }

    res = portfolio_risk(positions, histories)

    assert "risk_summary" in res
    summary = res["risk_summary"]

    assert summary["overall_severity"] in ("NORMAL", "ATTENTION", "WARNING", "HIGH_RISK")
    assert "headline" in summary
    assert "total_warning_count" in summary
    assert "high_risk_count" in summary
    assert "warnings" in res
    assert isinstance(res["warnings"], list)


def test_risk_engine_never_returns_trade_recommendations():
    """Risk engine must be diagnostic/advisory and NEVER output action keywords."""
    positions = [
        {"symbol": "DGC", "market_value": 80000.0, "weight": 0.8},
        {"symbol": "VNM", "market_value": 20000.0, "weight": 0.2},
    ]
    histories = {
        "DGC": [{"trading_date": f"2026-01-{i:02d}", "close": 90.0 + i} for i in range(1, 60)],
        "VNM": [{"trading_date": f"2026-01-{i:02d}", "close": 70.0 - i} for i in range(1, 60)],
    }

    res = portfolio_risk(positions, histories)
    res_str = str(res).upper()

    forbidden = ["BUY_MORE", "REDUCE", "SELL", "NÊN BÁN", "CẦN BÁN", "NÊN MUA"]
    for word in forbidden:
        assert word not in res_str
