"""Task 139 Integration & Regression Test Suite: Forensic Correctness + Canonical MOS Authority.

Tests:
1. Detailed receivable rows must not map to aggregate receivables (no unsafe substring matching).
2. Aggregate and component rows cannot silently collide into canonical facts.
3. DGC receivable raw SSI lineage verification.
4. Receivables forensic persistence and materiality checks (WATCH vs FAIL).
5. Forensic WATCH status does not automatically become ValueTrap HIGH_RISK.
6. Forensic WATCH status does not automatically become DETERIORATING_BUSINESS (AVOID).
7. BANK archetype forensic applicability (industrial rules are NOT_APPLICABLE).
8. SECURITIES archetype forensic applicability (industrial rules are NOT_APPLICABLE).
9. Canonical required MOS single authority across components.
10. Runtime MOS consistency (canonical valuation == Munger analysis == InvestmentDecisionContext).
11. Missing MOS remains missing (NULL != DEFAULT).
12. Golden symbols (ACB, DGC, FPT, VIX) integration.
"""

from __future__ import annotations

import pytest
from portfolio.financial_data.ssi_ingestion import map_ssi_line_item, normalize_string, CANONICAL_LINE_MAPPINGS
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_forensics import run_receivables_forensics, run_earnings_quality_forensics
from portfolio.value_engine.munger_models import DimensionStatus, DeteriorationClassification, CompounderClassification
from portfolio.canonical_valuation import build_canonical_valuation
from portfolio.policy.context_builder import build_decision_context
from portfolio.policy.models import InvestmentDecisionContext


def test_detailed_receivable_row_no_aggregate_collision():
    """1. Detailed/subcomponent receivable rows must NOT map to aggregate BS.ASSETS.RECEIVABLES."""
    detail_rows = [
        "Phải thu khách hàng",
        "Trả trước cho người bán",
        "Phải thu nội bộ",
        "Phải thu khác",
        "Dự phòng phải thu ngắn hạn khó đòi",
        "Phải thu về cho vay ngắn hạn",
        "Thuế GTGT được khấu trừ",
    ]
    for row_name in detail_rows:
        code, status = map_ssi_line_item(row_name, "BALANCE_SHEET")
        assert code != "BS.ASSETS.RECEIVABLES", f"Detail row {row_name} incorrectly mapped to aggregate BS.ASSETS.RECEIVABLES"


def test_exact_aggregate_receivable_rows_mapped_correctly():
    """2. Exact aggregate receivables line items are mapped to BS.ASSETS.RECEIVABLES."""
    aggregate_rows = [
        "Các khoản phải thu",
        "Phải thu ngắn hạn",
        "Các khoản phải thu ngắn hạn",
        "Tổng các khoản phải thu",
    ]
    for row_name in aggregate_rows:
        code, status = map_ssi_line_item(row_name, "BALANCE_SHEET")
        assert status == "MAPPED"
        assert code == "BS.ASSETS.RECEIVABLES", f"Aggregate row {row_name} failed to map to BS.ASSETS.RECEIVABLES"


def test_dgc_receivables_lineage_and_mapping():
    """3. Verify DGC receivables mapping & lineage from SSI raw line name."""
    raw_name = "Các khoản phải thu"
    norm = normalize_string(raw_name)
    assert norm == "cac khoan phai thu"
    code, status = map_ssi_line_item(raw_name, "BALANCE_SHEET")
    assert status == "MAPPED"
    assert code == "BS.ASSETS.RECEIVABLES"


def test_receivables_forensics_distinguishes_watch_from_fail():
    """4. Receivables forensics distinguishes WATCH from FAIL."""
    # Test healthy growth (PASS)
    healthy_hist = {
        "years": [2021, 2022, 2023, 2024, 2025],
        "by_year": {
            2021: {"revenue": 1000.0, "receivables": 100.0},
            2022: {"revenue": 1200.0, "receivables": 110.0},
            2023: {"revenue": 1400.0, "receivables": 120.0},
            2024: {"revenue": 1600.0, "receivables": 130.0},
            2025: {"revenue": 1800.0, "receivables": 140.0},
        },
    }
    res_pass = run_receivables_forensics(healthy_hist, archetype="NORMAL_ENTERPRISE")
    assert res_pass.status == DimensionStatus.PASS.value

    # Test moderate intensity rise (WATCH)
    watch_hist = {
        "years": [2021, 2022, 2023, 2024, 2025],
        "by_year": {
            2021: {"revenue": 1000.0, "receivables": 100.0},
            2022: {"revenue": 1100.0, "receivables": 150.0},
            2023: {"revenue": 1200.0, "receivables": 200.0},
            2024: {"revenue": 1300.0, "receivables": 250.0},
            2025: {"revenue": 1400.0, "receivables": 280.0},
        },
    }
    res_watch = run_receivables_forensics(watch_hist, archetype="NORMAL_ENTERPRISE")
    assert res_watch.status in (DimensionStatus.WATCH.value, DimensionStatus.PASS.value)
    assert res_watch.status != DimensionStatus.FAIL.value


def test_watch_forensic_does_not_become_high_risk_valuetrap():
    """5. WATCH-level forensic finding does NOT automatically escalate ValueTrap to HIGH_RISK."""
    analysis = build_munger_financial_analysis("FPT")
    vt = analysis.value_trap_assessment
    assert vt["status"] != "HIGH_RISK"
    assert vt["status"] in ("CLEAR", "WATCH")


def test_watch_forensic_does_not_become_deteriorating_business():
    """6. WATCH-level forensic finding does NOT classify business as DETERIORATING_BUSINESS."""
    analysis = build_munger_financial_analysis("FPT")
    assert analysis.compounder_classification != CompounderClassification.DETERIORATING_BUSINESS.value
    assert analysis.structural_deterioration["classification"] != DeteriorationClassification.STRUCTURAL.value


def test_bank_archetype_forensics_applicability():
    """7. BANK archetype treats industrial receivables and CFO forensics as NOT_APPLICABLE."""
    hist = {
        "years": [2021, 2022, 2023, 2024, 2025],
        "by_year": {y: {"revenue": 100.0, "receivables": 500.0} for y in [2021, 2022, 2023, 2024, 2025]},
    }
    rec_bank = run_receivables_forensics(hist, archetype="BANK")
    assert rec_bank.status == DimensionStatus.NOT_APPLICABLE.value

    eq_bank = run_earnings_quality_forensics(hist, archetype="BANK")
    assert eq_bank.status == DimensionStatus.NOT_APPLICABLE.value


def test_securities_archetype_forensics_applicability():
    """8. SECURITIES archetype treats industrial receivables and CFO forensics as NOT_APPLICABLE."""
    hist = {
        "years": [2021, 2022, 2023, 2024, 2025],
        "by_year": {y: {"revenue": 100.0, "receivables": 500.0} for y in [2021, 2022, 2023, 2024, 2025]},
    }
    rec_sec = run_receivables_forensics(hist, archetype="SECURITIES")
    assert rec_sec.status == DimensionStatus.NOT_APPLICABLE.value

    eq_sec = run_earnings_quality_forensics(hist, archetype="SECURITIES")
    assert eq_sec.status == DimensionStatus.NOT_APPLICABLE.value


def test_canonical_required_mos_single_authority():
    """9. Single required MOS authority is respected when passed into munger_analyzer."""
    val_data = {
        "status": "READY",
        "current_price": 50000.0,
        "base_iv": 100000.0,
        "actual_mos_pct": 50.0,
        "required_mos_pct": 40.0,
        "valuation_confidence": "HIGH",
    }
    analysis = build_munger_financial_analysis("FPT", valuation_data=val_data)
    assert analysis.valuation["required_mos_pct"] == 40.0
    assert analysis.long_term_decision["required_mos_pct"] == 40.0


def test_runtime_mos_consistency_across_layers():
    """10. Runtime required MOS is consistent across canonical valuation, munger, and decision context."""
    val = build_canonical_valuation("FPT", market_price=70000.0)
    munger = build_munger_financial_analysis("FPT", valuation_data=val)
    ctx = build_decision_context(
        symbol="FPT",
        valuation=val,
        business_review=munger.to_dict(),
        value_trap=munger.value_trap_assessment,
    )

    req_val = val.get("required_mos_pct")
    req_munger = munger.valuation.get("required_mos_pct")
    req_ctx = ctx.required_mos_pct

    assert req_val is not None
    assert req_val == req_munger
    assert req_munger == req_ctx


def test_missing_mos_does_not_silently_default():
    """11. Missing required MOS does NOT silently default to 40% or 30%."""
    ctx = build_decision_context("UNKNOWN_SYM", valuation=None)
    assert ctx.required_mos is None
    assert ctx.required_mos_pct is None


def test_golden_symbols_integration(postgresql_db=None):
    """12. Integration check for golden symbols (ACB, DGC, FPT, VIX)."""
    for sym in ["ACB", "DGC", "FPT", "VIX"]:
        val = build_canonical_valuation(sym, market_price=50000.0)
        munger = build_munger_financial_analysis(sym, valuation_data=val)
        ctx = build_decision_context(
            symbol=sym,
            valuation=val,
            business_review=munger.to_dict(),
            value_trap=munger.value_trap_assessment,
        )

        assert val["ok"] is True
        assert munger.archetype in ("NORMAL_ENTERPRISE", "BANK", "SECURITIES")
        assert val.get("required_mos_pct") == munger.valuation.get("required_mos_pct")
        assert munger.valuation.get("required_mos_pct") == ctx.required_mos_pct
        assert munger.value_trap_assessment["status"] != "HIGH_RISK" or sym not in ("DGC", "ACB", "FPT", "VIX")
