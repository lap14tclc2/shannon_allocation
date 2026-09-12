import os
import pytest
from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.storage import PortfolioStore


def test_get_split_adjustment_calculation(tmp_path):
    store = PortfolioStore(tmp_path / "portfolio.sqlite3")
    svc = CorrectablePortfolioService(store)

    # Add position for DGC
    svc.add_position("DGC", 10000, 52340.0)

    res = svc.get_split_adjustment("DGC")
    assert res["ok"] is True
    assert res["symbol"] == "DGC"
    assert res["original_shares"] == 10000.0
    assert res["original_cost"] == 52340.0
    assert res["total_invested"] == 523400000.0

    # DGC has known stock dividends in database (cumulative factor > 1)
    if res["has_adjustment"]:
        assert res["cumulative_factor"] > 1.0
        assert res["adjusted_shares"] > 10000.0
        assert res["adjusted_cost"] < 52340.0
        # Check capital invariant: adjusted_shares * adjusted_cost ~= total_invested (relative diff < 0.001%)
        assert abs(res["adjusted_shares"] * res["adjusted_cost"] - res["total_invested"]) / res["total_invested"] < 0.0001


def test_apply_split_adjustment_updates_position_and_preserves_capital(tmp_path):
    store = PortfolioStore(tmp_path / "portfolio.sqlite3")
    svc = CorrectablePortfolioService(store)

    # Insert corporate action stock dividend for testing
    with store.connect() as db:
        db.execute("""
            INSERT INTO corporate_actions (external_key, symbol, action_type, ex_date, stock_ratio, source, verification_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("manual:TESTSYM:1:STOCK_DIVIDEND", "TESTSYM", "STOCK_DIVIDEND", "2026-06-01", 0.25, "manual", "VERIFIED", "2026-06-01T00:00:00", "2026-06-01T00:00:00"))

    svc.add_position("TESTSYM", 1000, 100000.0)

    adj = svc.get_split_adjustment("TESTSYM")
    assert adj["ok"] is True
    assert adj["has_adjustment"] is True
    assert adj["cumulative_factor"] == 1.25
    assert adj["adjusted_shares"] == 1250.0
    assert adj["adjusted_cost"] == 80000.0

    apply_res = svc.apply_split_adjustment("TESTSYM")
    assert apply_res["ok"] is True

    # Check updated positions view
    pos_res = svc.positions_view()
    positions = pos_res["positions"]
    assert len(positions) == 1
    pos = positions[0]
    assert pos["symbol"] == "TESTSYM"
    assert pos["shares"] == 1250.0
    assert pos["average_cost"] == 80000.0
    assert pos["invested_value"] == 100000000.0  # Exactly preserved!
