"""Unit tests for Buffett-Munger 12D Financial Matrix metrics (Task 144)."""

import pytest
from portfolio.value_engine.munger_archetype_analyzers import (
    analyze_normal_enterprise,
    analyze_bank,
    analyze_securities,
)
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis

def mock_enterprise_history():
    years = list(range(2016, 2026))
    by_year = {}
    for i, y in enumerate(years):
        rev = 1000.0 * (1.10 ** i)
        pat = 100.0 * (1.12 ** i)
        eq = 500.0 * (1.15 ** i)
        debt = 100.0
        sh = 50.0 * (1.05 ** i)
        cfo = pat * 1.1
        by_year[y] = {
            "revenue": rev,
            "net_profit": pat,
            "equity": eq,
            "total_debt": debt,
            "outstanding_shares": sh,
            "cfo": cfo,
            "total_assets": eq + debt,
        }
    return {"years": years, "by_year": by_year}


def test_normal_enterprise_metrics_populated():
    hist = mock_enterprise_history()
    results = analyze_normal_enterprise(hist)

    # 1. Growth
    growth = results["growth"]
    assert growth.metrics.get("revenue_cagr") is not None
    assert growth.metrics.get("net_profit_cagr") is not None
    assert growth.metrics.get("annual_share_growth") is not None

    # 2. Profitability & Margin Trend
    prof = results["profitability"]
    assert prof.metrics.get("margin_trend") in ["EXPANDING", "STABLE", "DECLINING"]
    assert prof.metrics.get("median_roe") is not None

    # 3. Durability & Profit Volatility
    dur = results["durability"]
    assert dur.metrics.get("pat_volatility") is not None
    assert dur.metrics.get("profit_volatility") is not None

    # 4. Debt / Equity Dual Keys
    bs = results["balance_sheet"]
    assert bs.metrics.get("latest_debt_equity") is not None
    assert bs.metrics.get("debt_equity_ratio") is not None

    # 5. Dilution
    dilution = results["dilution"]
    assert dilution.metrics.get("annual_share_growth") is not None
    assert dilution.metrics.get("share_cagr") is not None
    assert dilution.metrics.get("eps_cagr") is not None


def test_bank_archetype_not_applicable_metrics():
    hist = mock_enterprise_history()
    results = analyze_bank(hist)

    # Debt Liquidity should be NOT_APPLICABLE for industrial debt/equity
    debt_res = results["debt_liquidity"]
    assert "INDUSTRIAL_DEBT_EQUITY" in debt_res.not_applicable
    assert debt_res.metrics.get("equity_assets_ratio") is not None

    # Cash Flow Quality should be NOT_APPLICABLE for industrial CFO/PAT
    cfo_res = results.get("cash_flow_quality") or results.get("earnings_quality")
    if cfo_res:
        assert "INDUSTRIAL_CFO_PAT" in cfo_res.not_applicable


def test_securities_archetype_metrics():
    hist = mock_enterprise_history()
    results = analyze_securities(hist)

    prof = results["profitability"]
    assert prof.metrics.get("fvtpl_dependence_ratio") is not None
    assert prof.metrics.get("margin_trend") is not None
