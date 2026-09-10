import os
import pytest

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "postgresql://qport:qport@127.0.0.1:5432/qport")

import app.main as main
from portfolio.service import PortfolioService
from portfolio.storage import PortfolioStore


@pytest.fixture
def mock_app_service(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.sqlite3"
    svc = PortfolioService(store=PortfolioStore(db_path))
    dummy_user = type("User", (), {"username": "local_user", "role": "USER"})()

    monkeypatch.setattr(main, "require_portfolio_user", lambda session=None: dummy_user)
    monkeypatch.setattr(main, "portfolio", lambda u=None: svc)
    return svc


def test_1_api_terminal_endpoint_returns_ok(mock_app_service):
    """1. /api/portfolio/terminal returns ok: True and valid structure."""
    res = main.api_portfolio_terminal()
    assert res["ok"] is True
    assert "fortress" in res
    assert "holdings_matrix" in res
    assert "coach_summary" in res


def test_2_api_business_endpoint_returns_ok_for_symbols(mock_app_service):
    """2. /api/portfolio/business/{symbol} returns ok: True for FPT, ACB, DGC."""
    for sym in ("FPT", "ACB", "DGC"):
        res = main.api_portfolio_business(sym)
        assert res["ok"] is True
        assert res["symbol"] == sym
        assert "business_review" in res
        assert "value_trap" in res
        assert "decision" in res
        assert "munger_checklist" in res


def test_3_api_capital_endpoint_returns_ok(mock_app_service):
    """3. /api/portfolio/capital returns ok: True for configured and unconfigured states."""
    # Unconfigured state
    mock_app_service.store.set_meta("personal_balance_sheet_json", "")
    res1 = main.api_portfolio_capital()
    assert res1["ok"] is True
    assert res1["configured"] is False
    assert res1["durability"]["survival_reserve_status"] == "UNKNOWN"

    # Configured state
    pf_payload = {
        "monthly_net_income": 50000000,
        "monthly_essential_spending": 20000000,
        "safe_liquid_assets": 240000000,
        "near_term_liabilities": 0,
    }
    main.api_portfolio_personal_finance_post(body=pf_payload)
    res2 = main.api_portfolio_capital()
    assert res2["ok"] is True
    assert res2["configured"] is True
    assert res2["durability"]["survival_reserve_status"] == "SAFE"


def test_4_api_history_endpoint_returns_ok(mock_app_service):
    """4. /api/portfolio/history returns ok: True, nav_history, transactions, summary."""
    res = main.api_portfolio_history()
    assert res["ok"] is True
    assert "nav_history" in res
    assert "transactions" in res
    assert "summary" in res
