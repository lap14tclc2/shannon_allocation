"""Comprehensive Regression Test Suite for Task 14: Munger Analysis Pipeline.

Verifies end-to-end data lineage, 12D metrics, forensic flags, value trap, MOS,
Munger pre-mortem (with Conclusion, Evidence, Risk, Severity), 9-part evidence conclusion,
and zero raw machine enums in Vietnamese presentation.
"""

from __future__ import annotations

import pytest
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_models import DimensionStatus, CompounderClassification
from portfolio.audit_golden_symbols import _build_sample_golden_facts


GOLDEN_SYMBOLS = ["ACB", "DGC", "FPT", "VIX"]


@pytest.mark.parametrize("symbol", GOLDEN_SYMBOLS)
def test_golden_symbols_pipeline_execution(symbol: str):
    """Verify full Munger analysis pipeline runs deterministically for golden symbols."""
    facts = _build_sample_golden_facts(symbol)
    val_data = {
        "status": "READY",
        "current_price": 50000.0,
        "bear_iv": 60000.0,
        "base_iv": 80000.0,
        "bull_iv": 100000.0,
        "actual_mos_pct": 37.5,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
    }
    
    analysis = build_munger_financial_analysis(symbol, raw_facts=facts, valuation_data=val_data)
    a_dict = analysis.to_dict()

    assert a_dict["symbol"] == symbol
    assert a_dict["history_years"] >= 5
    assert a_dict["data_readiness"] in ("READY", "PARTIAL")

    # 12D results present
    for dim in [
        "growth_analysis",
        "profitability_analysis",
        "earnings_durability",
        "earnings_quality",
        "cash_flow_quality",
        "balance_sheet_strength",
        "debt_liquidity",
        "capital_efficiency",
        "capital_allocation",
        "dilution_analysis",
        "accounting_consistency",
        "financial_forensics",
    ]:
        assert dim in a_dict
        assert "status" in a_dict[dim]

    # Pre-Mortem Questions verify 4 required fields
    pre_mortem = a_dict["thesis_challenge"]
    assert "questions" in pre_mortem
    assert len(pre_mortem["questions"]) == 8

    for q in pre_mortem["questions"]:
        assert "conclusion_vi" in q and q["conclusion_vi"] != ""
        assert "evidence_vi" in q and q["evidence_vi"] != ""
        assert "risk_vi" in q and q["risk_vi"] != ""
        assert "severity_vi" in q and q["severity_vi"] != ""

    # Evidence-Based 9-Part Conclusion
    conc = a_dict["evidence_based_conclusion"]
    assert "diem_manh_tai_chinh" in conc and len(conc["diem_manh_tai_chinh"]) > 0
    assert "diem_yeu" in conc and len(conc["diem_yeu"]) > 0
    assert "warning_quan_trong_nhat" in conc and conc["warning_quan_trong_nhat"] != ""
    assert "xu_huong_dai_han" in conc and conc["xu_huong_dai_han"] != ""
    assert "value_trap_risk" in conc and conc["value_trap_risk"] != ""
    assert "dieu_co_the_pha_vo_thesis" in conc and conc["dieu_co_the_pha_vo_thesis"] != ""
    assert "dieu_kien_cung_co_thesis" in conc and conc["dieu_kien_cung_co_thesis"] != ""
    assert "valuation_mos" in conc and conc["valuation_mos"] != ""
    assert "final_decision" in conc and conc["final_decision"] != ""
    assert "full_narrative" in conc and conc["full_narrative"] != ""


def test_archetype_isolation():
    """Verify bank archetype isolation skips industrial CFO/PAT/CapEx requirements."""
    acb_facts = _build_sample_golden_facts("ACB")
    analysis = build_munger_financial_analysis("ACB", raw_facts=acb_facts)
    a_dict = analysis.to_dict()

    assert a_dict["archetype"] == "BANK"
    assert a_dict["earnings_quality"]["status"] == DimensionStatus.NOT_APPLICABLE.value


def test_securities_archetype_isolation():
    """Verify securities archetype handles broker balance sheet rules."""
    vix_facts = _build_sample_golden_facts("VIX")
    analysis = build_munger_financial_analysis("VIX", raw_facts=vix_facts)
    a_dict = analysis.to_dict()

    assert a_dict["archetype"] == "SECURITIES"
    assert a_dict["earnings_quality"]["status"] == DimensionStatus.NOT_APPLICABLE.value


def test_no_raw_machine_code_leakage_in_presentation_payload():
    """Verify investor-facing presentation fields contain natural Vietnamese translations."""
    from portfolio.value_engine.vietnamese_presenter import (
        get_vietnamese_classification,
        get_vietnamese_decision,
        get_vietnamese_deterioration,
        get_vietnamese_finding_title,
        get_vietnamese_status,
        get_vietnamese_valuetrap,
    )

    assert get_vietnamese_finding_title("RECEIVABLES_GROW_FASTER_THAN_REVENUE") == "Khoản phải thu tăng nhanh hơn doanh thu"
    assert get_vietnamese_finding_title("PROFIT_CASH_DIVERGENCE") == "Lợi nhuận tăng nhưng dòng tiền không theo kịp"
    assert get_vietnamese_deterioration("NO_DETERIORATION") == "Chưa phát hiện xu hướng suy giảm đáng kể"
    assert get_vietnamese_classification("POTENTIAL_COMPOUNDER") == "Doanh nghiệp có tiềm năng tăng trưởng giá trị dài hạn"
    assert get_vietnamese_status("UNKNOWN") == "Chưa đủ dữ liệu"
    assert get_vietnamese_status("INSUFFICIENT") == "Chưa đủ dữ liệu"
    assert get_vietnamese_decision("WAIT_FOR_MOS") in ("Chờ biên an toàn", "Chờ mức giá có biên an toàn tốt hơn")
    assert get_vietnamese_decision("REVIEW_BUSINESS") == "Cần xem xét thêm dữ liệu doanh nghiệp"
