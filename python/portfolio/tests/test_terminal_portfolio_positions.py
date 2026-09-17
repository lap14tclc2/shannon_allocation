"""
Terminal Portfolio Position Management — 20 test cases (TASK-150).

Uses CorrectablePortfolioService with an in-memory SQLite store (tmp_path).
No HTTP layer — tests domain logic directly.
"""
from __future__ import annotations

import pytest

from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.storage import PortfolioStore
from portfolio.validation import InputValidationError


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def svc(tmp_path):
    store = PortfolioStore(tmp_path / "portfolio.sqlite3")
    return CorrectablePortfolioService(store=store)


def _add(svc, symbol, qty, avg_cost):
    return svc.add_position(symbol, qty, avg_cost, created_by="test")


# ── 1. Empty portfolio ─────────────────────────────────────────────────────────

def test_empty_portfolio_positions_view(svc):
    result = svc.positions_view()
    assert result["ok"] is True
    assert result["positions"] == []
    assert result["summary"]["total_invested"] == 0
    assert result["summary"]["total_market_value"] is None


# ── 2. Add FPT ────────────────────────────────────────────────────────────────

def test_add_fpt(svc):
    r = _add(svc, "FPT", 3000, 73800)
    assert r["ok"] is True
    view = svc.positions_view()
    assert len(view["positions"]) == 1
    pos = view["positions"][0]
    assert pos["symbol"] == "FPT"
    assert pos["shares"] == 3000
    assert pos["average_cost"] == pytest.approx(73800)
    assert pos["invested_value"] == pytest.approx(3000 * 73800)


# ── 3. Add two positions (FPT + ACB) ─────────────────────────────────────────

def test_add_two_positions(svc):
    _add(svc, "FPT", 3000, 73800)
    _add(svc, "ACB", 19210, 19780)
    view = svc.positions_view()
    symbols = {p["symbol"] for p in view["positions"]}
    assert symbols == {"FPT", "ACB"}
    assert len(view["positions"]) == 2


# ── 4. Duplicate FPT rejected ─────────────────────────────────────────────────

def test_duplicate_symbol_rejected(svc):
    _add(svc, "FPT", 3000, 73800)
    with pytest.raises(InputValidationError) as exc:
        _add(svc, "FPT", 1000, 80000)
    assert exc.value.code == "DUPLICATE_POSITION"
    assert "FPT" in str(exc.value)
    # Only one FPT in portfolio
    view = svc.positions_view()
    assert len(view["positions"]) == 1


# ── 5. Edit FPT quantity ──────────────────────────────────────────────────────

def test_edit_fpt_quantity(svc):
    _add(svc, "FPT", 3000, 73800)
    svc.update_position("FPT", 4000, 73800, created_by="test")
    pos = svc.positions_view()["positions"][0]
    assert pos["shares"] == 4000
    assert pos["average_cost"] == pytest.approx(73800)


# ── 6. Edit FPT average_cost ──────────────────────────────────────────────────

def test_edit_fpt_average_cost(svc):
    _add(svc, "FPT", 3000, 73800)
    svc.update_position("FPT", 3000, 72000, created_by="test")
    pos = svc.positions_view()["positions"][0]
    assert pos["average_cost"] == pytest.approx(72000)
    assert pos["invested_value"] == pytest.approx(3000 * 72000)


# ── 7. Delete FPT — only FPT removed ─────────────────────────────────────────

def test_delete_fpt_leaves_acb(svc):
    _add(svc, "FPT", 3000, 73800)
    _add(svc, "ACB", 19210, 19780)
    svc.delete_position("FPT", created_by="test")
    view = svc.positions_view()
    symbols = {p["symbol"] for p in view["positions"]}
    assert "FPT" not in symbols
    assert "ACB" in symbols


# ── 8. Delete nonexistent symbol ─────────────────────────────────────────────

def test_delete_nonexistent_symbol(svc):
    with pytest.raises(InputValidationError) as exc:
        svc.delete_position("XXXX", created_by="test")
    assert exc.value.code == "POSITION_NOT_FOUND"


# ── 9. Invalid quantity ────────────────────────────────────────────────────────

def test_invalid_quantity_zero(svc):
    with pytest.raises(Exception):
        _add(svc, "FPT", 0, 73800)


def test_invalid_quantity_negative(svc):
    with pytest.raises(Exception):
        _add(svc, "FPT", -100, 73800)


# ── 10. Invalid average_cost ──────────────────────────────────────────────────

def test_invalid_average_cost_zero(svc):
    with pytest.raises(Exception):
        _add(svc, "FPT", 3000, 0)


def test_invalid_average_cost_too_small(svc):
    # Price must be >= MIN_EQUITY_PRICE_VND = 1000 VND
    with pytest.raises(Exception):
        _add(svc, "FPT", 3000, 73)  # 73 VND — likely a fractional entry mistake


# ── 11. Invalid symbol ────────────────────────────────────────────────────────

def test_invalid_symbol_empty(svc):
    with pytest.raises(Exception):
        _add(svc, "", 3000, 73800)


def test_invalid_symbol_too_long(svc):
    with pytest.raises(InputValidationError):
        _add(svc, "TOOLONGSYMBOL", 3000, 73800)


# ── 12. Cash update ───────────────────────────────────────────────────────────

def test_cash_update(svc):
    svc.set_cash_reserve(50_000_000)
    result = svc.get_cash()
    assert result["ok"] is True
    assert result["cash_reserve"] == pytest.approx(50_000_000)


def test_cash_appears_in_positions_view_summary(svc):
    svc.set_cash_reserve(50_000_000)
    view = svc.positions_view()
    assert view["cash_reserve"] == pytest.approx(50_000_000)
    assert view["summary"]["cash_reserve"] == pytest.approx(50_000_000)


# ── 13. Portfolio persistence ─────────────────────────────────────────────────

def test_portfolio_persists_across_service_instances(tmp_path):
    store_path = tmp_path / "portfolio.sqlite3"
    svc1 = CorrectablePortfolioService(store=PortfolioStore(store_path))
    _add(svc1, "FPT", 3000, 73800)

    # New service instance, same store path
    svc2 = CorrectablePortfolioService(store=PortfolioStore(store_path))
    view = svc2.positions_view()
    assert len(view["positions"]) == 1
    assert view["positions"][0]["symbol"] == "FPT"


# ── 14. Market price unavailable — graceful output ────────────────────────────

def test_market_price_unavailable_graceful(svc):
    # No market prices ingested → price should be None
    svc._sync_symbol = lambda *args, **kwargs: None
    _add(svc, "FPT", 3000, 73800)
    view = svc.positions_view()
    pos = view["positions"][0]
    assert pos["market_price"] is None
    assert pos["unrealized_pnl"] is None
    assert pos["unrealized_pnl_pct"] is None
    # invested_value always present
    assert pos["invested_value"] == pytest.approx(3000 * 73800)


# ── 15-17. P/L calculation ────────────────────────────────────────────────────

def test_pl_calculation(svc):
    """P/L = market_value - invested_value when market price is available."""
    # seed the market price manually
    _add(svc, "FPT", 3000, 73800)
    svc.store.upsert_market_prices([{"symbol": "FPT", "close": 80000, "trading_date": "2026-09-12"}])
    view = svc.positions_view()
    pos = view["positions"][0]
    invested = 3000 * 73800          # 221,400,000
    market = 3000 * 80000            # 240,000,000
    pnl = market - invested          # 18,600,000
    assert pos["invested_value"] == pytest.approx(invested)
    assert pos["market_value"] == pytest.approx(market)
    assert pos["unrealized_pnl"] == pytest.approx(pnl)


def test_pl_pct_calculation(svc):
    _add(svc, "FPT", 3000, 73800)
    svc.store.upsert_market_prices([{"symbol": "FPT", "close": 80000, "trading_date": "2026-09-12"}])
    view = svc.positions_view()
    pos = view["positions"][0]
    invested = 3000 * 73800
    pnl = 3000 * 80000 - invested
    expected_pct = round(pnl / invested * 100, 2)
    assert pos["unrealized_pnl_pct"] == pytest.approx(expected_pct, abs=0.01)


# ── 18. Portfolio weight calculation ─────────────────────────────────────────

def test_portfolio_weight_with_two_positions(svc):
    _add(svc, "FPT", 3000, 73800)
    _add(svc, "ACB", 19210, 19780)
    svc.store.upsert_market_prices([
        {"symbol": "FPT", "close": 80000, "trading_date": "2026-09-12"},
        {"symbol": "ACB", "close": 22000, "trading_date": "2026-09-12"},
    ])
    view = svc.positions_view()
    total_weight = sum(p["weight"] for p in view["positions"])
    assert total_weight == pytest.approx(1.0, abs=1e-6)


# ── 19. Multiple positions summary ────────────────────────────────────────────

def test_multiple_positions_summary(svc):
    _add(svc, "FPT", 3000, 73800)
    _add(svc, "ACB", 19210, 19780)
    view = svc.positions_view()
    expected_invested = 3000 * 73800 + 19210 * 19780
    assert view["summary"]["total_invested"] == pytest.approx(expected_invested)


# ── 20. Complex ledger guard ──────────────────────────────────────────────────

def test_complex_ledger_blocks_terminal_edit(svc):
    """If a symbol has BUY events, Terminal update_position must be rejected."""
    # Seed cash first so BUY does not make cash negative
    svc.append_event(
        {"event_type": "CASH_DEPOSIT", "event_date": "2026-01-01", "amount": 1_000_000_000},
        created_by="test",
    )
    # Add via BUY (complex ledger)
    svc.append_event(
        {"event_type": "BUY", "event_date": "2026-01-02", "symbol": "FPT",
         "quantity": 3000, "price": 73800, "broker_code": "SSI"},
        created_by="test",
    )
    # Terminal update should be rejected
    with pytest.raises(InputValidationError) as exc:
        svc.update_position("FPT", 4000, 72000, created_by="test")
    assert exc.value.code == "COMPLEX_LEDGER"

    # But view should still show has_complex_ledger=True
    view = svc.positions_view()
    fpt = next((p for p in view["positions"] if p["symbol"] == "FPT"), None)
    assert fpt is not None
    assert fpt["has_complex_ledger"] is True


# ── 21. Force refresh market price sync ─────────────────────────────────────────

def test_positions_view_force_refresh(svc):
    """Verify positions_view(force_refresh=True) invokes live sync."""
    _add(svc, "FPT", 3000, 73800)
    # Seed an old price
    svc.store.upsert_market_prices([{"symbol": "FPT", "close": 70000, "trading_date": "2026-09-01"}])
    
    # Mock _sync_symbol to simulate live price update
    sync_called = []
    def fake_sync(sym, today, force=False):
        sync_called.append((sym, force))
        svc.store.upsert_market_prices([{"symbol": sym, "close": 75000, "trading_date": "2026-09-17"}])
        return {"ok": True}

    svc._sync_symbol = fake_sync
    res = svc.positions_view(force_refresh=True)
    assert len(sync_called) == 1
    assert sync_called[0] == ("FPT", True)
    fpt = next(p for p in res["positions"] if p["symbol"] == "FPT")
    assert fpt["market_price"] == 75000
    assert fpt["unrealized_pnl"] == (75000 - 73800) * 3000
