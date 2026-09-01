"""Tests for the High-Quality Stock Screener Engine and API route."""
import json
import os
import pytest

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "postgresql://qport:qport@127.0.0.1:5432/qport")

from portfolio.screener import get_screener_results, compute_all_screener_scores
from app.main import portfolio_screener_endpoint



def test_screener_engine_scoring_and_filtering():
    # 1. Test score calculation & filtering (>= 80 points)
    res_80 = get_screener_results(mos_filter="all", min_liquidity=0, min_score=80, exchange="ALL", search="", sort_by="score")
    assert res_80["ok"] is True
    assert "items" in res_80
    assert res_80["filters"]["min_score"] == 80
    for item in res_80["items"]:
        assert item["total_score"] >= 80
        assert item["tier"] in ("EXCEPTIONAL", "HIGH_QUALITY")
        assert len(item["symbol"]) >= 3

    # 2. Test exchange filter
    res_hose = get_screener_results(mos_filter="all", min_liquidity=0, min_score=80, exchange="HOSE", search="", sort_by="score")
    assert res_hose["ok"] is True
    for item in res_hose["items"]:
        assert item["exchange"] == "HOSE"

    # 3. Test search query
    res_search = get_screener_results(mos_filter="all", min_liquidity=0, min_score=60, exchange="ALL", search="VNM", sort_by="score")
    assert res_search["ok"] is True
    symbols = [it["symbol"] for it in res_search["items"]]
    assert "VNM" in symbols

    # 4. Test sort by ROE
    res_roe = get_screener_results(mos_filter="all", min_liquidity=0, min_score=70, exchange="ALL", sort_by="roe")
    assert res_roe["ok"] is True
    items_roe = [it["avg_roe_5y"] for it in res_roe["items"] if it["avg_roe_5y"] is not None]
    if len(items_roe) >= 2:
        assert items_roe[0] >= items_roe[-1]


def test_screener_api_endpoint(monkeypatch):
    from app import main
    monkeypatch.setattr(main, "require_portfolio_user", lambda session: type("User", (), {"username": "admin", "role": "ADMIN"})())

    res = portfolio_screener_endpoint(mos_filter="all", min_liquidity=0, min_score=80, exchange="HOSE", search="", sort_by="score")
    assert res["ok"] is True
    assert "items" in res
    assert isinstance(res["items"], list)
    for item in res["items"]:
        assert item["total_score"] >= 80
        assert item["exchange"] == "HOSE"


def test_screener_buffett_margin_of_safety_and_liquidity():
    # 1. Test Buffett qualified filter (MOS >= required MOS)
    res_buffett = get_screener_results(mos_filter="buffett_qualified", min_liquidity=0, sort_by="mos")
    assert res_buffett["ok"] is True
    assert len(res_buffett["items"]) > 0
    for item in res_buffett["items"]:
        assert item["is_buffett_qualified"] is True
        assert item["margin_of_safety"] >= item.get("required_mos", 25.0)

    # 2. Test Liquidity filter (>= 10B/day)
    res_liq = get_screener_results(mos_filter="all", min_liquidity=10.0, sort_by="liquidity")
    assert res_liq["ok"] is True
    for item in res_liq["items"]:
        assert (item.get("avg_turnover_20d_billion") or 0) >= 10.0

    # 3. Test Positive MOS filter
    res_pos = get_screener_results(mos_filter="positive", sort_by="mos")
    assert res_pos["ok"] is True
    for item in res_pos["items"]:
        assert item["is_positive_mos"] is True
        assert item["margin_of_safety"] > 0


def test_screener_matches_canonical_valuation_report(monkeypatch):
    """user-test.md: screener KHÔNG dùng engine định giá riêng — public IV/MOS/req-MOS/
    status phải khớp CHÍNH XÁC canonical ValuationReport từ detail endpoint."""
    items = {i["symbol"]: i for i in compute_all_screener_scores(force_refresh=True)}
    dgc = items.get("DGC")
    if dgc is None:
        pytest.skip("DGC không có trong universe screener.")

    from app import main
    from portfolio.finance_catalog import _schema_connection, FINANCE_SCHEMA

    class _FakeStore:
        def latest_price(self, ticker):
            with _schema_connection(FINANCE_SCHEMA) as db:
                row = db.execute(
                    """SELECT close FROM (
                           SELECT close, ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trading_date DESC) as rn
                           FROM market_prices WHERE symbol=?
                       ) sub WHERE rn=1""",
                    (str(ticker).upper(),),
                ).fetchone()
            return {"close": float(row["close"])} if row and row["close"] else None

    class _FakeSvc:
        store = _FakeStore()

    monkeypatch.setattr(
        main, "require_portfolio_user",
        lambda session: {"id": 1, "username": "tester", "role": "USER", "created_at": "2026-01-01T00:00:00Z"},
    )
    monkeypatch.setattr(main, "portfolio", lambda user: _FakeSvc())

    resp = main.portfolio_symbol_valuation("DGC")
    payload = json.loads(resp.body)
    assert payload.get("ok") is True, payload.get("code", payload)
    rep = payload["report"]
    pub_iv = rep.get("public_base_iv")
    pub_mos = rep.get("public_mos")
    req_mos = (rep.get("margin_of_safety_analysis") or {}).get("required_mos_pct")
    pill = rep.get("valuation_pill")
    model_status = rep.get("model_status")
    qs = rep.get("quality_scorecard") or {}

    def close(a, b, tol=0.1):
        if a is None or b is None:
            return a is None and b is None
        return abs(float(a) - float(b)) <= tol

    assert close(dgc["intrinsic_value"], pub_iv), (dgc["intrinsic_value"], pub_iv)
    assert close(dgc["margin_of_safety"], pub_mos), (dgc["margin_of_safety"], pub_mos)
    assert close(dgc["required_mos"], req_mos, 0.01), (dgc["required_mos"], req_mos)
    assert dgc["valuation_status"] == pill, (dgc["valuation_status"], pill)
    assert dgc["model_status"] == model_status, (dgc["model_status"], model_status)
    assert dgc["total_score"] == qs.get("total_score"), (dgc["total_score"], qs.get("total_score"))
    assert dgc["capital_allocation_score"] == qs.get("capital_allocation_score"), (
        dgc["capital_allocation_score"], qs.get("capital_allocation_score"),
    )

    # user-test.md (TASK-084) + feedback.txt (TASK-085): screener phải khớp CHÍNH XÁC
    # canonical ValuationReport — IV/MOS/req-MOS/status/model/quality đều đồng nhất.
    # Sau refactor regime-aware normalization (latest comparable regime 2018–2025,
    # giữ peak CYCLICAL_EXTREME), DGC được định giá ATTRACTIVE — đây là KẾT QUẢ HỢP LỆ
    # của engine regime mới, không phải false-positive heuristic như trước refactor.
    assert dgc["valuation_status"] == pill
    assert dgc["model_status"] == model_status
    # user-test.md §35 — screener expose data_status/regime_status từ canonical report.
    assert dgc["data_status"] == rep.get("data_status"), (dgc.get("data_status"), rep.get("data_status"))
    assert dgc["regime_status"] == rep.get("regime_status"), (dgc.get("regime_status"), rep.get("regime_status"))
    assert dgc["numeric_confidence"] == rep.get("numeric_confidence")
    # DGC: comparable regime 2018-2025 (>=7 FY), không banner đỏ.
    w = rep.get("normalization_window") or {}
    assert w.get("comparable_regime_start") == 2018
    assert w.get("comparable_regime_end") == 2025
    assert w.get("normalization_years", 0) >= 7
    assert dgc["regime_status"] == "SPLIT_REGIME"
    assert dgc["data_status"] == "VALID_WITH_CLASSIFIED_EVENTS"
    assert rep.get("cause_confidence") == "UNKNOWN"


def test_screener_universe_covers_all_priced_symbols():
    """user-test.md §19/§37: screener phải bao phủ toàn universe mã có BCTC + giá."""
    from portfolio.finance_catalog import backfill_market_prices
    # limit=0 -> không fetch mạng, chỉ trả summary shape.
    summary = backfill_market_prices(limit=0, max_workers=2)
    assert set(summary) >= {"requested", "fetched_price", "rows_saved", "failed", "remaining"}
    assert summary["requested"] == 0

    universe = compute_all_screener_scores(force_refresh=True)
    # Universe phải lớn hơn 1000 (không còn chỉ 334): mọi mã có facts + ≥2 năm + giá.
    assert len(universe) > 1000, len(universe)
    # Các mã lớn từng thiếu giá nay phải có mặt.
    symbols = {i["symbol"] for i in universe}
    assert {"HSG", "PLX", "SSI", "DGC", "VNM"}.issubset(symbols)
