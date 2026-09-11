"""Tests for Task 136: Business Workspace Symbol & Company Search Entry Point."""

import os
import pytest
from portfolio.finance_catalog import search_securities_lookup
from portfolio.canonical_valuation import build_canonical_valuation
from portfolio.service import PortfolioService


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_search_symbols_api_returns_canonical_securities():
    """Verify symbol search lookup queries Finance DB catalog for ticker and company name."""
    results_fpt = search_securities_lookup("FPT", limit=10)
    assert len(results_fpt) > 0
    symbols = [r["symbol"] for r in results_fpt]
    assert "FPT" in symbols

    results_acb = search_securities_lookup("ACB", limit=10)
    assert len(results_acb) > 0
    assert any(r["symbol"] == "ACB" for r in results_acb)

    results_bank = search_securities_lookup("Ngân hàng", limit=10)
    assert len(results_bank) > 0


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_non_held_candidate_symbol_research():
    """Verify non-held candidate symbols can be researched using the same Business engine."""
    svc = PortfolioService(store=None)
    for candidate in ["ACB", "FPT", "DGC", "VIX"]:
        rt = svc.runtime_decision(candidate)
        assert rt["symbol"] == candidate
        assert rt["valuation"]["ok"] is True
        assert rt["valuation"]["base_iv"] is not None
        assert rt["business_review"] is not None
        assert rt["value_trap"] is not None
        assert rt["evidence"]["decision"] in (
            "BUY", "BUY_MORE", "HOLD", "HOLD_NO_NEW_CAPITAL",
            "WAIT_FOR_MOS", "BUILD_RESERVE_FIRST", "REVIEW_BUSINESS",
            "AVOID", "SELL_REVIEW", "SELL"
        )


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_candidate_vs_holding_uses_same_underlying_business_valuation():
    """Verify portfolio holding status does NOT alter underlying intrinsic valuation."""
    val_direct = build_canonical_valuation("FPT", market_price=100000.0)
    
    svc = PortfolioService(store=None)
    rt = svc.runtime_decision("FPT")
    
    assert rt["valuation"]["base_iv"] == val_direct["base_iv"]
    assert rt["valuation"]["bear_iv"] == val_direct["bear_iv"]
    assert rt["valuation"]["bull_iv"] == val_direct["bull_iv"]
