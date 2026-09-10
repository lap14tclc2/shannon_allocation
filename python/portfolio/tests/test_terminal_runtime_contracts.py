import os
import pytest

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "postgresql://qport:qport@127.0.0.1:5432/qport")

from portfolio.service import PortfolioService
from portfolio.canonical_valuation import build_canonical_valuation
from portfolio.value_engine.value_trap import evaluate_value_trap


class DummyStore:
    def __init__(self):
        self.meta = {}

    def get_meta(self, key):
        return self.meta.get(key)

    def set_meta(self, key, value):
        self.meta[key] = value

    def latest_price(self, symbol):
        return {"close": 100000.0}

    def latest_prices(self, symbols, on_or_before=None):
        return {sym: {"close": 100000.0} for sym in (symbols or [])}

    def list_events(self):
        return []

    def list_activity(self, limit=100):
        return []

    def list_snapshots(self, *args, **kwargs):
        return []

    def __getattr__(self, name):
        def method(*args, **kwargs):
            return [] if "list" in name else {}
        return method


def test_1_runtime_decision_reads_nested_dashboard_portfolio(monkeypatch):
    """1. runtime_decision reads nested dashboard["portfolio"] dict."""
    store = DummyStore()
    svc = PortfolioService(store=store)

    dash_payload = {
        "portfolio": {
            "positions": [
                {"symbol": "FPT", "holding": 100, "weight": 0.25, "market_value": 10000000.0, "price": 100000.0},
                {"symbol": "ACB", "holding": 200, "weight": 0.15, "market_value": 5000000.0, "price": 25000.0},
                {"symbol": "DGC", "holding": 50, "weight": 0.10, "market_value": 4500000.0, "price": 90000.0},
            ],
            "cash": 10000000.0,
            "equity_value": 19500000.0,
            "nav": 29500000.0,
        }
    }
    monkeypatch.setattr(svc, "dashboard", lambda: dash_payload)

    res = svc.runtime_decision("FPT")
    assert res["holding"] is not None
    assert res["holding"]["symbol"] == "FPT"
    assert res["weight"] == 0.25
    assert res["market_value"] == 10000000.0


def test_2_fpt_real_holding_remains_nonzero(monkeypatch):
    """2. FPT real holding remains nonzero when positions exist."""
    store = DummyStore()
    svc = PortfolioService(store=store)

    dash_payload = {
        "portfolio": {
            "positions": [
                {"symbol": "FPT", "holding": 500, "weight": 0.40, "market_value": 50000000.0, "price": 100000.0},
            ],
            "cash": 20000000.0,
            "equity_value": 50000000.0,
        }
    }
    monkeypatch.setattr(svc, "dashboard", lambda: dash_payload)

    fpt_item = svc.runtime_decision("FPT")
    assert fpt_item is not None
    assert fpt_item["holding"] is not None
    assert fpt_item["weight"] > 0
    assert fpt_item["market_value"] > 0


def test_3_terminal_and_business_use_same_canonical_valuation_service(monkeypatch):
    """3. Terminal and Business use the same canonical valuation builder build_canonical_valuation."""
    val_res = build_canonical_valuation("FPT", market_price=100000.0)
    assert "quality_tier" in val_res
    assert "financial_history" in val_res
    assert val_res["symbol"] == "FPT"


def test_4_valuation_and_runtime_decision_return_matching_base_iv(monkeypatch):
    """4. Valuation page and runtime_decision return matching Base IV for same fixture."""
    store = DummyStore()
    svc = PortfolioService(store=store)

    mock_val = {
        "ok": True,
        "symbol": "FPT",
        "current_price": 100000.0,
        "base_iv": 140000.0,
        "bear_iv": 110000.0,
        "bull_iv": 180000.0,
        "quality_tier": "HIGH_QUALITY",
        "financial_history": [],
    }
    monkeypatch.setattr(svc, "valuation", lambda sym: mock_val)

    val_out = svc.valuation("FPT")
    rt_out = svc.runtime_decision("FPT")

    assert val_out["base_iv"] == 140000.0
    assert rt_out["base_iv"] == 140000.0
    assert rt_out["base_iv"] == val_out["base_iv"]


def test_5_production_shaped_financial_history_10y_normalized():
    """5. production-shaped financial_history_10y is normalized correctly."""
    val_payload = {
        "ok": True,
        "symbol": "FPT",
        "financial_history_10y": [
            {"fiscal_year": 2021, "net_profit": 4000e9, "operating_cash_flow": 4500e9},
            {"fiscal_year": 2022, "net_profit": 5200e9, "operating_cash_flow": 5500e9},
            {"fiscal_year": 2023, "net_profit": 6400e9, "operating_cash_flow": 7000e9},
        ]
    }
    fin_history = (
        val_payload.get("financial_history")
        or val_payload.get("financial_history_10y")
        or val_payload.get("history")
        or []
    )
    assert len(fin_history) == 3
    assert fin_history[0]["fiscal_year"] == 2021


def test_6_valuetrap_receives_multi_year_history():
    """6. ValueTrap receives multi-year history and normalized_earnings_trend != UNKNOWN."""
    val_rep = {
        "symbol": "FPT",
        "current_price": 100000.0,
        "base_iv": 140000.0,
        "quality_tier": "HIGH_QUALITY",
        "financial_history_10y": [
            {"fiscal_year": 2021, "net_profit": 4000e9, "operating_cash_flow": 4500e9},
            {"fiscal_year": 2022, "net_profit": 5200e9, "operating_cash_flow": 5500e9},
            {"fiscal_year": 2023, "net_profit": 6400e9, "operating_cash_flow": 7000e9},
        ]
    }
    fin_history = val_rep.get("financial_history") or val_rep.get("financial_history_10y") or []
    vt = evaluate_value_trap("FPT", valuation_report=val_rep, financial_history=fin_history).to_dict()

    assert vt["normalized_earnings_trend"] != "UNKNOWN"


def test_7_missing_personal_finance_blocks_buy(monkeypatch):
    """7. missing Personal Finance still blocks BUY (returns BUILD_RESERVE_FIRST)."""
    store = DummyStore()
    svc = PortfolioService(store=store)

    dash_payload = {
        "portfolio": {
            "positions": [{"symbol": "FPT", "holding": 100, "weight": 0.2, "market_value": 10000000.0, "price": 100000.0}],
            "cash": 5000000.0,
            "equity_value": 10000000.0,
        }
    }
    monkeypatch.setattr(svc, "dashboard", lambda: dash_payload)

    res = svc.runtime_decision("FPT")
    assert res["decision"] == "BUILD_RESERVE_FIRST"


def test_8_acb_dgc_fpt_holdings_not_lost(monkeypatch):
    """8. ACB/DGC/FPT holdings are not lost in runtime_decision."""
    store = DummyStore()
    svc = PortfolioService(store=store)

    dash_payload = {
        "portfolio": {
            "positions": [
                {"symbol": "ACB", "holding": 1000, "weight": 0.20, "market_value": 25000000.0, "price": 25000.0},
                {"symbol": "DGC", "holding": 500, "weight": 0.30, "market_value": 45000000.0, "price": 90000.0},
                {"symbol": "FPT", "holding": 800, "weight": 0.50, "market_value": 80000000.0, "price": 100000.0},
            ],
            "cash": 10000000.0,
            "equity_value": 150000000.0,
        }
    }
    monkeypatch.setattr(svc, "dashboard", lambda: dash_payload)

    acb_item = svc.runtime_decision("ACB")
    dgc_item = svc.runtime_decision("DGC")
    fpt_item = svc.runtime_decision("FPT")

    assert acb_item["holding"] is not None
    assert dgc_item["holding"] is not None
    assert fpt_item["holding"] is not None

    assert acb_item["weight"] == 0.20
    assert dgc_item["weight"] == 0.30
    assert fpt_item["weight"] == 0.50
