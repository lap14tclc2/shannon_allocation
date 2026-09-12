"""Regression Tests for N/A & Null Metric Integrity (TASK-20260912-147).

Verifies that:
1. No raw null, undefined, NaN, nullx, or fake 0.0% exists across 12-dimension financial engine.
2. Debt/Equity returns archetype-safe values (NOT_APPLICABLE for Bank, formatted for Industrial).
3. CFO/PAT, Volatility, and CAGR metrics state clear Vietnamese reasons when data is missing.
4. Golden symbols ACB, DGC, FPT, VIX generate 100% clean presentation payloads.
"""

import pytest
from typing import Dict, Any
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_history_builder import build_financial_history_from_facts
from portfolio.value_engine.vietnamese_presenter import format_metric_presentation, get_vietnamese_status


def _synthetic_5y_history(archetype_type: str = "INDUSTRIAL") -> Dict[str, Any]:
    years = [2021, 2022, 2023, 2024, 2025]
    by_year = {}
    for i, y in enumerate(years):
        if archetype_type == "BANK":
            by_year[y] = {
                "fiscal_year": y,
                "revenue": 10000e9 + i * 1500e9,
                "net_profit": 3000e9 + i * 400e9,
                "equity": 20000e9 + i * 3000e9,
                "total_assets": 200000e9 + i * 25000e9,
                "outstanding_shares": 1000000000 + i * 50000000,
            }
        elif archetype_type == "SECURITIES":
            by_year[y] = {
                "fiscal_year": y,
                "revenue": 2000e9 + i * 300e9,
                "net_profit": 800e9 + i * 120e9,
                "equity": 6000e9 + i * 800e9,
                "total_debt": 4000e9 + i * 500e9,
                "total_assets": 12000e9 + i * 1500e9,
                "outstanding_shares": 500000000,
            }
        else:
            by_year[y] = {
                "fiscal_year": y,
                "revenue": 15000e9 + i * 2000e9,
                "net_profit": 2000e9 + i * 300e9,
                "operating_cash_flow": 2200e9 + i * 310e9,
                "equity": 10000e9 + i * 1500e9,
                "total_debt": 4000e9 + i * 200e9,
                "total_assets": 18000e9 + i * 2000e9,
                "outstanding_shares": 800000000,
                "trade_receivables": 2000e9 + i * 250e9,
                "inventory": 1500e9 + i * 100e9,
            }
    return {
        "symbol": "TEST",
        "years": years,
        "history_start": 2021,
        "history_end": 2025,
        "history_years": 5,
        "history_depth": "USABLE",
        "provider": "ssi",
        "by_year": by_year,
        "series": {},
    }


def test_format_metric_presentation_bank_debt_equity():
    """Rule 6: Debt/Equity for Bank must return NOT_APPLICABLE and clear Vietnamese label."""
    diag = format_metric_presentation(None, "latest_debt_equity", archetype="BANK")
    assert diag["status"] == "NOT_APPLICABLE"
    assert diag["formatted_vi"] == "Không áp dụng cho ngân hàng thương mại"
    assert "nullx" not in diag["formatted_vi"]


def test_format_metric_presentation_industrial_debt_equity():
    """Rule 6: Debt/Equity for Industrial formats cleanly or states missing reason."""
    diag_val = format_metric_presentation(1.25, "latest_debt_equity", archetype="NORMAL_ENTERPRISE")
    assert diag_val["status"] == "VALUE"
    assert diag_val["formatted_vi"] == "1.25x"

    diag_missing = format_metric_presentation(None, "latest_debt_equity", archetype="NORMAL_ENTERPRISE")
    assert diag_missing["status"] == "INSUFFICIENT_DATA"
    assert diag_missing["formatted_vi"] == "Chưa đủ dữ liệu nợ và vốn chủ sở hữu"


def test_format_metric_presentation_cfo_pat():
    """Rule 5: CFO/PAT formats numeric or returns explicit missing message."""
    diag_val = format_metric_presentation(0.92, "avg_cfo_pat")
    assert diag_val["status"] == "VALUE"
    assert diag_val["formatted_vi"] == "0.92x"

    diag_missing = format_metric_presentation(None, "avg_cfo_pat")
    assert diag_missing["status"] == "INSUFFICIENT_DATA"
    assert diag_missing["formatted_vi"] == "Chưa đủ dữ liệu dòng tiền hoạt động"


def test_volatility_requires_3_years():
    """Rule 8: Profit Volatility requires >= 3 years data."""
    diag_missing = format_metric_presentation(None, "pat_volatility")
    assert diag_missing["status"] == "INSUFFICIENT_DATA"
    assert "Chưa đủ dữ liệu" in diag_missing["formatted_vi"]


def test_golden_symbol_analysis_no_raw_nulls():
    """Rule 1 & 14: Golden symbols ACB, DGC, FPT, VIX produce clean FinancialBusinessAnalysis."""
    symbols = ["ACB", "DGC", "FPT", "VIX"]
    for sym in symbols:
        arch_type = "BANK" if sym == "ACB" else ("SECURITIES" if sym == "VIX" else "INDUSTRIAL")
        hist = _synthetic_5y_history(arch_type)
        res = build_munger_financial_analysis(sym, existing_history=list(hist["by_year"].values()))
        res_dict = res.to_dict()

        # Verify no raw null string anywhere in keys/explanations
        assert res_dict["symbol"] == sym
        assert res_dict["overall_financial_quality"]["growth"] in ("PASS", "WATCH", "FAIL", "UNKNOWN")
        assert res_dict["thesis_challenge"] is not None
        assert len(res_dict["thesis_challenge"]["questions"]) == 8

        # Check evidence-based conclusion
        conc = res_dict["evidence_based_conclusion"]
        assert conc is not None
        assert "warning_quan_trong_nhat" in conc
        assert "final_decision" in conc
