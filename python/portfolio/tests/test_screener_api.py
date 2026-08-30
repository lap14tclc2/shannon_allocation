"""Tests for the High-Quality Stock Screener Engine and API route."""
import os
import pytest

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "postgresql://qport:qport@127.0.0.1:5432/qport")

from portfolio.screener import get_screener_results, compute_all_screener_scores
from app.main import portfolio_screener_endpoint



def test_screener_engine_scoring_and_filtering():
    # 1. Test score calculation & filtering (>= 80 points)
    res_80 = get_screener_results(min_score=80, exchange="ALL", search="", sort_by="score")
    assert res_80["ok"] is True
    assert "items" in res_80
    assert res_80["filters"]["min_score"] == 80
    for item in res_80["items"]:
        assert item["total_score"] >= 80
        assert item["tier"] in ("EXCEPTIONAL", "HIGH_QUALITY")
        assert len(item["symbol"]) >= 3

    # 2. Test exchange filter
    res_hose = get_screener_results(min_score=80, exchange="HOSE", search="", sort_by="score")
    assert res_hose["ok"] is True
    for item in res_hose["items"]:
        assert item["exchange"] == "HOSE"

    # 3. Test search query
    res_search = get_screener_results(min_score=60, exchange="ALL", search="VNM", sort_by="score")
    assert res_search["ok"] is True
    symbols = [it["symbol"] for it in res_search["items"]]
    assert "VNM" in symbols

    # 4. Test sort by ROE
    res_roe = get_screener_results(min_score=70, exchange="ALL", sort_by="roe")
    assert res_roe["ok"] is True
    items_roe = [it["avg_roe_5y"] for it in res_roe["items"] if it["avg_roe_5y"] is not None]
    if len(items_roe) >= 2:
        assert items_roe[0] >= items_roe[-1]


def test_screener_api_endpoint(monkeypatch):
    from app import main
    monkeypatch.setattr(main, "require_portfolio_user", lambda session: type("User", (), {"username": "admin", "role": "ADMIN"})())

    res = portfolio_screener_endpoint(mos_filter="all", min_score=80, exchange="HOSE", search="", sort_by="score")
    assert res["ok"] is True
    assert "items" in res
    assert isinstance(res["items"], list)
    for item in res["items"]:
        assert item["total_score"] >= 80
        assert item["exchange"] == "HOSE"


def test_screener_buffett_margin_of_safety():
    # Test Buffett qualified filter (MOS >= required MOS)
    res_buffett = get_screener_results(mos_filter="buffett_qualified", sort_by="mos")
    assert res_buffett["ok"] is True
    assert len(res_buffett["items"]) > 0
    for item in res_buffett["items"]:
        assert item["is_buffett_qualified"] is True
        assert item["margin_of_safety"] >= item.get("required_mos", 25.0)

    # Test Positive MOS filter
    res_pos = get_screener_results(mos_filter="positive", sort_by="mos")
    assert res_pos["ok"] is True
    for item in res_pos["items"]:
        assert item["is_positive_mos"] is True
        assert item["margin_of_safety"] > 0
