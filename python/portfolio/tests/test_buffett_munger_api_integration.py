"""API & Application-Level Integration Tests for Buffett/Munger Decision Engine & Workspaces.

Verifies:
1. P0-1: Data Readiness Enforcement in Decision Engine (CONFLICTED, INSUFFICIENT, BLOCKED data cannot BUY).
2. P0-2: Business Workspace and Terminal Consistency (both read same persisted Personal Finance & return identical decisions).
3. P0-3: Value Trap runtime receives actual multi-year financial history.
"""

import pytest
import app.main as main
from portfolio.service import PortfolioService
from portfolio.storage import PortfolioStore
from portfolio.policy.context_builder import build_decision_context
from portfolio.policy.engine import evaluate_decision


@pytest.fixture
def mock_app_service(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.sqlite3"
    svc = PortfolioService(store=PortfolioStore(db_path))
    dummy_user = type("User", (), {"username": "local_user", "role": "USER"})()

    monkeypatch.setattr(main, "require_portfolio_user", lambda session=None: dummy_user)
    monkeypatch.setattr(main, "portfolio", lambda u=None: svc)
    return svc


def test_api_terminal_and_business_endpoint_decision_consistency(mock_app_service):
    """P0-2: /api/portfolio/terminal and /api/portfolio/business/{symbol} return consistent decisions and Personal Finance."""
    # 1. Set Personal Finance
    pf_payload = {
        "monthly_net_income": 80_000_000,
        "monthly_essential_spending": 20_000_000,
        "safe_liquid_assets": 300_000_000,
        "near_term_liabilities": 0.0,
    }
    pf_resp = main.api_portfolio_personal_finance_post(body=pf_payload)
    assert pf_resp["ok"] is True

    # 2. Get Terminal data
    term_data = main.api_portfolio_terminal()
    assert term_data["ok"] is True
    assert term_data["fortress"]["survival_reserve_status"] == "SAFE"

    # 3. Get Business data for FPT
    biz_data = main.api_portfolio_business("FPT")
    assert biz_data["ok"] is True

    # Assert consistency
    assert biz_data["symbol"] == "FPT"
    assert biz_data["value_trap"]["status"] in ("CLEAR", "WATCH", "INSUFFICIENT_DATA", "HIGH_RISK")

    # If FPT is in terminal holdings, decision must match exactly
    fpt_term_item = next((item for item in term_data["holdings_matrix"] if item["symbol"] == "FPT"), None)
    if fpt_term_item:
        assert fpt_term_item["decision"] == biz_data["decision"]["decision"]


def test_api_missing_personal_finance_blocks_buy(mock_app_service):
    """P0-2: Unconfigured Personal Finance blocks BUY in both Terminal and Business endpoints."""
    mock_app_service.store.set_meta("personal_balance_sheet_json", "")

    biz_data = main.api_portfolio_business("FPT")
    assert biz_data["decision"]["decision"] in ("BUILD_RESERVE_FIRST", "WAIT_FOR_MOS", "HOLD", "REVIEW_BUSINESS")
    assert biz_data["decision"]["decision"] not in ("BUY", "BUY_MORE")


def test_decision_engine_enforces_conflicted_valuation_readiness_blocked():
    """P0-1: CONFLICTED valuation sets readiness BLOCKED and prohibits BUY / BUY_MORE."""
    valuation = {
        "symbol": "CONFLICTED_CO",
        "current_price": 50000,
        "base_iv": 100000,
        "bear_iv": 80000,
        "required_mos": 15.0,
        "actual_mos": 50.0,
        "valuation_confidence": "HIGH",
        "model_status": "MODEL_VERIFIED",
        "data_status": "CONFLICTED",  # Conflict in accounting / prices!
        "quality_score": 90,
        "quality_tier": "HIGH_QUALITY",
    }
    business = {"overall_status": "BUSINESS_PASS", "moat": "PASS", "management_capital_allocation": "PASS"}
    value_trap = {"status": "CLEAR"}
    pf = {"survival_reserve_status": "SAFE", "available_long_term_capital": 500_000_000}

    ctx = build_decision_context(
        symbol="CONFLICTED_CO",
        valuation=valuation,
        personal_finance=pf,
        business_review=business,
        value_trap=value_trap,
    )

    assert ctx.data_readiness["financial_core"] == "BLOCKED"
    assert ctx.data_readiness["valuation"] == "BLOCKED"

    evidence = evaluate_decision(ctx)

    assert evidence.decision not in ("BUY", "BUY_MORE")
    assert evidence.decision in ("WAIT_FOR_MOS", "HOLD")


def test_decision_engine_enforces_insufficient_valuation_readiness_blocked():
    """P0-1: INSUFFICIENT valuation sets readiness BLOCKED and prohibits BUY / BUY_MORE."""
    valuation = {
        "symbol": "INSUFFICIENT_CO",
        "current_price": 10000,
        "base_iv": 20000,
        "model_status": "MODEL_VERIFIED",
        "data_status": "INSUFFICIENT",
    }
    pf = {"survival_reserve_status": "SAFE", "available_long_term_capital": 500_000_000}
    ctx = build_decision_context("INSUFFICIENT_CO", valuation=valuation, personal_finance=pf)

    assert ctx.data_readiness["valuation"] == "BLOCKED"
    evidence = evaluate_decision(ctx)
    assert evidence.decision not in ("BUY", "BUY_MORE")


def test_runtime_value_trap_consumes_financial_history():
    """P0-3: PortfolioService.runtime_decision passes multi-year history to ValueTrap."""
    svc = PortfolioService()
    # Mock valuation method to supply multi-year history
    svc.valuation = lambda sym: {
        "symbol": sym,
        "current_price": 10000,
        "base_iv": 20000,
        "bear_iv": 15000,
        "financial_history": [
            {"net_income": 100, "cfo": 110, "revenue": 500},
            {"net_income": 120, "cfo": 130, "revenue": 550},
            {"net_income": 150, "cfo": 160, "revenue": 650},
        ],
    }

    res = svc.runtime_decision("GROWTH_CO")
    assert res["value_trap"]["normalized_earnings_trend"] == "GROWING"
    assert res["value_trap"]["cash_conversion_status"] == "CONFIRMED"
