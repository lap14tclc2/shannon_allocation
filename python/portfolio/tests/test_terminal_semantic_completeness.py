import os
import pytest
from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.storage import PortfolioStore


def test_terminal_positions_view_market_price_fallback(tmp_path):
    store = PortfolioStore(tmp_path / "portfolio.sqlite3")
    svc = CorrectablePortfolioService(store)

    # Add position for FPT and DGC
    svc.add_position("FPT", 100, 70000.0)
    svc.add_position("DGC", 200, 35000.0)
    svc.set_cash_reserve(50000000.0)

    res = svc.positions_view()
    assert res["ok"] is True
    assert len(res["positions"]) == 2
    assert res["cash_reserve"] == 50000000.0

    summary = res["summary"]
    assert summary["total_invested"] == 100 * 70000.0 + 200 * 35000.0
    assert summary["total_positions_count"] == 2
    assert summary["total_portfolio_value"] >= summary["total_invested"] + 50000000.0


def test_terminal_positions_view_unvalued_position_handling(tmp_path):
    store = PortfolioStore(tmp_path / "portfolio.sqlite3")
    svc = CorrectablePortfolioService(store)

    # Non-existent symbol in market prices table (valid symbol <= 10 chars)
    svc.add_position("XYZ999", 50, 10000.0)
    svc.set_cash_reserve(10000000.0)

    res = svc.positions_view()
    assert res["ok"] is True
    assert len(res["positions"]) == 1
    pos = res["positions"][0]
    assert pos["symbol"] == "XYZ999"
    assert pos["invested_value"] == 500000.0

    summary = res["summary"]
    assert summary["total_invested"] == 500000.0
    assert summary["unvalued_positions_count"] == 1
    assert summary["valued_positions_count"] == 0
    assert summary["all_positions_valued"] is False
    # Total portfolio value should not silently drop the unvalued position to 0
    assert summary["total_portfolio_value"] == 500000.0 + 10000000.0
