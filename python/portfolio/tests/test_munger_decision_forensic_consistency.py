"""Comprehensive Test Suite for Munger/Buffett Decision and Forensic Consistency (Task 170).

Validates Cases A through L and HAH full financial statements regression.
"""

import pytest
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.munger_forensics import (
    run_earnings_quality_forensics,
    run_inventory_forensics,
    run_receivables_forensics,
)
from portfolio.value_engine.munger_history_builder import build_financial_history_from_facts
from portfolio.value_engine.munger_models import (
    CompounderClassification,
    DimensionStatus,
    FindingSeverity,
)
from portfolio.value_engine.munger_thresholds import DEFAULT_MUNGER_THRESHOLD_POLICY


def test_case_a_hah_like_healthy_recent_receivables():
    """CASE A: Healthy recent receivables (growth < revenue growth, DSO improving) -> PASS, no warning."""
    history = [
        {"fiscal_year": 2022, "revenue": 3200.0, "receivables": 450.0, "cfo": 1659.0, "net_profit": 1050.0, "total_assets": 5000.0},
        {"fiscal_year": 2023, "revenue": 2600.0, "receivables": 420.0, "cfo": 514.0, "net_profit": 370.0, "total_assets": 5200.0},
        {"fiscal_year": 2024, "revenue": 3970.0, "receivables": 460.0, "cfo": 1890.0, "net_profit": 680.0, "total_assets": 6000.0},
        {"fiscal_year": 2025, "revenue": 5060.0, "receivables": 410.0, "cfo": 1810.0, "net_profit": 1207.0, "total_assets": 7000.0},
    ]
    h_data = build_financial_history_from_facts("HAH_REC", existing_history=history)
    res = run_receivables_forensics(h_data, "NORMAL_ENTERPRISE", DEFAULT_MUNGER_THRESHOLD_POLICY)

    assert res.status == DimensionStatus.PASS.value
    assert not any(f.code == "RECEIVABLES_GROW_FASTER_THAN_REVENUE" for f in res.findings)
    assert "Không có bằng chứng khoản phải thu tăng nhanh hơn doanh thu" in res.explanation or "an toàn" in res.explanation


def test_case_b_historical_receivables_gap_with_recent_normalization():
    """CASE B: Historical 10Y gap but recent 3Y normalized -> PASS with historical context semantic."""
    history = [
        {"fiscal_year": 2016, "revenue": 500.0, "receivables": 20.0, "total_assets": 1000.0, "cfo": 100.0, "net_profit": 80.0},
        {"fiscal_year": 2017, "revenue": 600.0, "receivables": 40.0, "total_assets": 1200.0, "cfo": 120.0, "net_profit": 90.0},
        {"fiscal_year": 2018, "revenue": 700.0, "receivables": 80.0, "total_assets": 1400.0, "cfo": 130.0, "net_profit": 100.0},
        {"fiscal_year": 2019, "revenue": 800.0, "receivables": 140.0, "total_assets": 1600.0, "cfo": 150.0, "net_profit": 110.0},
        {"fiscal_year": 2020, "revenue": 900.0, "receivables": 180.0, "total_assets": 1800.0, "cfo": 160.0, "net_profit": 120.0},
        {"fiscal_year": 2021, "revenue": 1000.0, "receivables": 200.0, "total_assets": 2000.0, "cfo": 180.0, "net_profit": 130.0},
        {"fiscal_year": 2022, "revenue": 1200.0, "receivables": 220.0, "total_assets": 2200.0, "cfo": 200.0, "net_profit": 140.0},
        {"fiscal_year": 2023, "revenue": 1500.0, "receivables": 240.0, "total_assets": 2500.0, "cfo": 240.0, "net_profit": 160.0},
        {"fiscal_year": 2024, "revenue": 2000.0, "receivables": 260.0, "total_assets": 3000.0, "cfo": 300.0, "net_profit": 200.0},
        {"fiscal_year": 2025, "revenue": 2600.0, "receivables": 280.0, "total_assets": 3600.0, "cfo": 380.0, "net_profit": 250.0},
    ]
    h_data = build_financial_history_from_facts("HIST_REC", existing_history=history)
    res = run_receivables_forensics(h_data, "NORMAL_ENTERPRISE", DEFAULT_MUNGER_THRESHOLD_POLICY)

    assert res.status == DimensionStatus.PASS.value
    assert not any(f.code == "RECEIVABLES_GROW_FASTER_THAN_REVENUE" for f in res.findings)
    assert "Trong lịch sử từng có giai đoạn" in res.explanation or "xu hướng gần đây" in res.explanation


def test_case_c_persistent_recent_receivables_deterioration():
    """CASE C: Persistent recent receivables surge + high materiality + weak CFO -> FAIL finding."""
    history = [
        {"fiscal_year": 2022, "revenue": 1000.0, "receivables": 200.0, "cfo": 10.0, "net_profit": 100.0, "total_assets": 1200.0},
        {"fiscal_year": 2023, "revenue": 1050.0, "receivables": 350.0, "cfo": -20.0, "net_profit": 110.0, "total_assets": 1400.0},
        {"fiscal_year": 2024, "revenue": 1100.0, "receivables": 550.0, "cfo": -50.0, "net_profit": 120.0, "total_assets": 1700.0},
        {"fiscal_year": 2025, "revenue": 1150.0, "receivables": 750.0, "cfo": -80.0, "net_profit": 130.0, "total_assets": 2000.0},
    ]
    h_data = build_financial_history_from_facts("DETERIORATING_REC", existing_history=history)
    res = run_receivables_forensics(h_data, "NORMAL_ENTERPRISE", DEFAULT_MUNGER_THRESHOLD_POLICY)

    assert res.status == DimensionStatus.FAIL.value
    finding = next((f for f in res.findings if f.code == "RECEIVABLES_GROW_FASTER_THAN_REVENUE"), None)
    assert finding is not None
    assert finding.severity == FindingSeverity.HIGH.value


def test_case_d_hah_like_cfo_quality():
    """CASE D: HAH-like CFO pattern (median 1.51x, 2/10 < PAT, 1 negative year, improving) -> PASS."""
    # 2016: 1.32x, 2017: 0.31x, 2018: -0.13x, 2019: 1.52x, 2020: 2.00x, 2021: 1.77x, 2022: 1.58x, 2023: 1.39x, 2024: 2.78x, 2025: 1.50x
    history = [
        {"fiscal_year": 2016, "revenue": 400.0, "net_profit": 120.0, "cfo": 158.4},
        {"fiscal_year": 2017, "revenue": 600.0, "net_profit": 150.0, "cfo": 46.5},
        {"fiscal_year": 2018, "revenue": 700.0, "net_profit": 140.0, "cfo": -18.2},
        {"fiscal_year": 2019, "revenue": 1100.0, "net_profit": 160.0, "cfo": 243.2},
        {"fiscal_year": 2020, "revenue": 1200.0, "net_profit": 170.0, "cfo": 340.0},
        {"fiscal_year": 2021, "revenue": 1900.0, "net_profit": 450.0, "cfo": 796.5},
        {"fiscal_year": 2022, "revenue": 3200.0, "net_profit": 1050.0, "cfo": 1659.0},
        {"fiscal_year": 2023, "revenue": 2600.0, "net_profit": 370.0, "cfo": 514.3},
        {"fiscal_year": 2024, "revenue": 3970.0, "net_profit": 680.0, "cfo": 1890.4},
        {"fiscal_year": 2025, "revenue": 5060.0, "net_profit": 1207.0, "cfo": 1810.5},
    ]
    h_data = build_financial_history_from_facts("HAH_CFO", existing_history=history)
    res = run_earnings_quality_forensics(h_data, "NORMAL_ENTERPRISE", DEFAULT_MUNGER_THRESHOLD_POLICY)

    assert res.status == DimensionStatus.PASS.value
    assert res.metrics["median_cfo_pat"] >= 1.40
    assert res.metrics["years_cfo_lt_pat"] == 2
    assert res.metrics["years_cfo_negative"] == 1
    assert "kéo dài" not in res.explanation
    assert "nhìn chung tốt" in res.explanation or "bảo chứng" in res.explanation


def test_case_e_persistent_weak_cfo():
    """CASE E: Persistent weak CFO (median < 0.6x, chronic deficit) -> FAIL / WATCH."""
    history = [
        {"fiscal_year": 2021, "revenue": 1000.0, "net_profit": 200.0, "cfo": 50.0},
        {"fiscal_year": 2022, "revenue": 1100.0, "net_profit": 220.0, "cfo": -30.0},
        {"fiscal_year": 2023, "revenue": 1200.0, "net_profit": 240.0, "cfo": 40.0},
        {"fiscal_year": 2024, "revenue": 1300.0, "net_profit": 260.0, "cfo": -60.0},
        {"fiscal_year": 2025, "revenue": 1400.0, "net_profit": 280.0, "cfo": 30.0},
    ]
    h_data = build_financial_history_from_facts("WEAK_CFO", existing_history=history)
    res = run_earnings_quality_forensics(h_data, "NORMAL_ENTERPRISE", DEFAULT_MUNGER_THRESHOLD_POLICY)

    assert res.status in (DimensionStatus.FAIL.value, DimensionStatus.WATCH.value)
    assert any(f.code in ("PROFIT_CASH_DIVERGENCE", "WEAK_CASH_CONVERSION") for f in res.findings)


def test_case_f_inventory_historical_cagr_gap_with_low_materiality():
    """CASE F: Inventory 10Y CAGR > revenue CAGR but low materiality / shipping archetype -> PASS."""
    history = [
        {"fiscal_year": 2016, "revenue": 500.0, "inventory": 5.0, "total_assets": 2000.0},
        {"fiscal_year": 2018, "revenue": 1000.0, "inventory": 15.0, "total_assets": 3000.0},
        {"fiscal_year": 2021, "revenue": 2000.0, "inventory": 35.0, "total_assets": 4500.0},
        {"fiscal_year": 2024, "revenue": 4000.0, "inventory": 55.0, "total_assets": 6000.0},
        {"fiscal_year": 2025, "revenue": 5000.0, "inventory": 60.0, "total_assets": 7000.0},
    ]
    h_data = build_financial_history_from_facts("SHIPPING_INV", existing_history=history)
    res = run_inventory_forensics(h_data, "NORMAL_ENTERPRISE", DEFAULT_MUNGER_THRESHOLD_POLICY)

    assert res.status == DimensionStatus.PASS.value
    assert not any(f.code == "INVENTORY_GROWTH_EXCEEDS_SALES" for f in res.findings)


def test_case_g_mos_pass_with_forensic_watch():
    """CASE G: MOS PASS + forensic WATCH -> CONDITIONAL_BUY (never falsely WAIT_FOR_MOS)."""
    history = [
        {"fiscal_year": 2021, "revenue": 1000.0, "net_profit": 200.0, "cfo": 150.0, "total_equity": 1000.0, "receivables": 150.0},
        {"fiscal_year": 2022, "revenue": 1100.0, "net_profit": 220.0, "cfo": 160.0, "total_equity": 1200.0, "receivables": 170.0},
        {"fiscal_year": 2023, "revenue": 1200.0, "net_profit": 240.0, "cfo": 170.0, "total_equity": 1400.0, "receivables": 200.0},
        {"fiscal_year": 2024, "revenue": 1300.0, "net_profit": 260.0, "cfo": 180.0, "total_equity": 1600.0, "receivables": 230.0},
        {"fiscal_year": 2025, "revenue": 1400.0, "net_profit": 280.0, "cfo": 190.0, "total_equity": 1800.0, "receivables": 260.0},
    ]
    val_data = {
        "status": "READY",
        "current_price": 50.0,
        "bear_iv": 60.0,
        "base_iv": 100.0,
        "bull_iv": 130.0,
        "actual_mos_pct": 50.0,
        "required_mos_pct": 30.0,
        "valuation_confidence": "MEDIUM",
        "quality_tier": "HIGH",
    }
    analysis = build_munger_financial_analysis("TEST_COND_BUY", existing_history=history, valuation_data=val_data)
    dec = analysis.long_term_decision

    assert dec["mos_gate"] == "PASS"
    assert dec["state"] in ("BUY", "CONDITIONAL_BUY")
    assert dec["state"] != "WAIT_FOR_MOS"
    assert "Chờ mức giá có biên an toàn tốt hơn" not in dec["state_vietnamese"]


def test_case_h_mos_pass_with_serious_business_quality_failure():
    """CASE H: MOS PASS + serious business quality failure (chronic losses / weak) -> AVOID (no BUY)."""
    history = [
        {"fiscal_year": 2021, "revenue": 1000.0, "net_profit": -50.0, "cfo": -30.0, "total_equity": 200.0},
        {"fiscal_year": 2022, "revenue": 900.0, "net_profit": -80.0, "cfo": -60.0, "total_equity": 120.0},
        {"fiscal_year": 2023, "revenue": 800.0, "net_profit": -100.0, "cfo": -80.0, "total_equity": 20.0},
        {"fiscal_year": 2024, "revenue": 700.0, "net_profit": -120.0, "cfo": -100.0, "total_equity": -100.0},
        {"fiscal_year": 2025, "revenue": 600.0, "net_profit": -150.0, "cfo": -120.0, "total_equity": -250.0},
    ]
    val_data = {
        "status": "READY",
        "current_price": 10.0,
        "bear_iv": 20.0,
        "base_iv": 50.0,
        "bull_iv": 70.0,
        "actual_mos_pct": 80.0,
        "required_mos_pct": 40.0,
        "valuation_confidence": "LOW",
        "quality_tier": "DISTRESSED",
    }
    analysis = build_munger_financial_analysis("DISTRESSED_CO", existing_history=history, valuation_data=val_data)
    dec = analysis.long_term_decision

    assert dec["state"] == "AVOID"
    assert dec["decision_trace"]["decision"] == "AVOID"


def test_case_i_low_valuation_confidence_with_high_mos():
    """CASE I: LOW valuation confidence + high MOS -> Preserves LOW confidence and exposes uncertainty."""
    history = [
        {"fiscal_year": 2021, "revenue": 1000.0, "net_profit": 150.0, "cfo": 140.0, "total_equity": 1000.0},
        {"fiscal_year": 2022, "revenue": 1200.0, "net_profit": 180.0, "cfo": 170.0, "total_equity": 1200.0},
        {"fiscal_year": 2023, "revenue": 1400.0, "net_profit": 220.0, "cfo": 210.0, "total_equity": 1400.0},
        {"fiscal_year": 2024, "revenue": 1600.0, "net_profit": 260.0, "cfo": 250.0, "total_equity": 1600.0},
        {"fiscal_year": 2025, "revenue": 1800.0, "net_profit": 300.0, "cfo": 290.0, "total_equity": 1800.0},
    ]
    val_data = {
        "status": "READY",
        "current_price": 20.0,
        "bear_iv": 30.0,
        "base_iv": 100.0,
        "bull_iv": 150.0,
        "actual_mos_pct": 80.0,
        "required_mos_pct": 50.0,
        "valuation_confidence": "LOW",
        "quality_tier": "AVERAGE",
    }
    analysis = build_munger_financial_analysis("LOW_CONF_CO", existing_history=history, valuation_data=val_data)

    assert analysis.valuation["valuation_confidence"] == "LOW"
    assert analysis.long_term_decision["valuation_confidence"] == "LOW"
    assert analysis.long_term_decision["decision_trace"]["valuation_confidence"] == "LOW"


def test_case_j_single_canonical_decision_authority():
    """CASE J: Exactly one authoritative decision trace produced."""
    history = [
        {"fiscal_year": 2021, "revenue": 1000.0, "net_profit": 150.0, "cfo": 140.0, "total_equity": 1000.0},
        {"fiscal_year": 2022, "revenue": 1200.0, "net_profit": 180.0, "cfo": 170.0, "total_equity": 1200.0},
        {"fiscal_year": 2023, "revenue": 1400.0, "net_profit": 220.0, "cfo": 210.0, "total_equity": 1400.0},
        {"fiscal_year": 2024, "revenue": 1600.0, "net_profit": 260.0, "cfo": 250.0, "total_equity": 1600.0},
        {"fiscal_year": 2025, "revenue": 1800.0, "net_profit": 300.0, "cfo": 290.0, "total_equity": 1800.0},
    ]
    val_data = {
        "status": "READY",
        "current_price": 70.0,
        "bear_iv": 80.0,
        "base_iv": 100.0,
        "bull_iv": 120.0,
        "actual_mos_pct": 30.0,
        "required_mos_pct": 25.0,
        "valuation_confidence": "HIGH",
        "quality_tier": "HIGH",
    }
    analysis = build_munger_financial_analysis("SINGLE_AUTH", existing_history=history, valuation_data=val_data)
    trace = analysis.long_term_decision.get("decision_trace", {})

    assert trace["decision_authority"] == "MUNGER_BCTC_PIPELINE"
    assert trace["decision"] == analysis.long_term_decision["state"]
    assert "quality_gate" in trace
    assert "forensic_gate" in trace
    assert "value_trap_gate" in trace
    assert "valuation_gate" in trace
    assert "mos_gate" in trace


def test_case_k_missing_cfo_is_strictly_unknown():
    """CASE K: Missing CFO data -> strictly UNKNOWN / Chưa đủ dữ liệu, never PASS."""
    history = [
        {"fiscal_year": 2021, "revenue": 1000.0, "net_profit": 150.0},
        {"fiscal_year": 2022, "revenue": 1200.0, "net_profit": 180.0},
        {"fiscal_year": 2023, "revenue": 1400.0, "net_profit": 220.0},
    ]
    h_data = build_financial_history_from_facts("NO_CFO", existing_history=history)
    res = run_earnings_quality_forensics(h_data, "NORMAL_ENTERPRISE", DEFAULT_MUNGER_THRESHOLD_POLICY)

    assert res.status == DimensionStatus.UNKNOWN.value
    assert "Thiếu dữ liệu" in res.explanation or "Chưa đủ" in res.explanation


def test_case_l_bank_and_securities_archetypes_bypass_industrial_rules():
    """CASE L: BANK and SECURITIES archetypes bypass industrial inventory and receivables rules."""
    history = [
        {"fiscal_year": 2021, "revenue": 5000.0, "net_profit": 1500.0, "total_assets": 100000.0, "total_equity": 10000.0},
        {"fiscal_year": 2022, "revenue": 6000.0, "net_profit": 1800.0, "total_assets": 120000.0, "total_equity": 12000.0},
        {"fiscal_year": 2023, "revenue": 7000.0, "net_profit": 2100.0, "total_assets": 140000.0, "total_equity": 14000.0},
        {"fiscal_year": 2024, "revenue": 8000.0, "net_profit": 2400.0, "total_assets": 160000.0, "total_equity": 16000.0},
        {"fiscal_year": 2025, "revenue": 9000.0, "net_profit": 2700.0, "total_assets": 180000.0, "total_equity": 18000.0},
    ]
    h_data = build_financial_history_from_facts("BANK_CO", existing_history=history)

    rec_res = run_receivables_forensics(h_data, "BANK", DEFAULT_MUNGER_THRESHOLD_POLICY)
    assert rec_res.status == DimensionStatus.NOT_APPLICABLE.value
    assert not rec_res.findings

    inv_res = run_inventory_forensics(h_data, "BANK", DEFAULT_MUNGER_THRESHOLD_POLICY)
    assert inv_res.status == DimensionStatus.NOT_APPLICABLE.value
    assert not inv_res.findings


def test_hah_full_annual_payload_regression():
    """Full 10-year HAH financial statements payload regression (FY2016 - FY2025)."""
    hah_history = [
        {"fiscal_year": 2016, "revenue": 400.0, "receivables": 60.0, "inventory": 5.0, "net_profit": 120.0, "cfo": 158.4, "total_assets": 1500.0, "total_equity": 800.0, "shares_outstanding": 20.0},
        {"fiscal_year": 2017, "revenue": 600.0, "receivables": 90.0, "inventory": 8.0, "net_profit": 150.0, "cfo": 46.5, "total_assets": 1800.0, "total_equity": 950.0, "shares_outstanding": 25.0},
        {"fiscal_year": 2018, "revenue": 700.0, "receivables": 120.0, "inventory": 12.0, "net_profit": 140.0, "cfo": -18.2, "total_assets": 2200.0, "total_equity": 1100.0, "shares_outstanding": 30.0},
        {"fiscal_year": 2019, "revenue": 1100.0, "receivables": 180.0, "inventory": 18.0, "net_profit": 160.0, "cfo": 243.2, "total_assets": 2600.0, "total_equity": 1250.0, "shares_outstanding": 35.0},
        {"fiscal_year": 2020, "revenue": 1200.0, "receivables": 200.0, "inventory": 25.0, "net_profit": 170.0, "cfo": 340.0, "total_assets": 3000.0, "total_equity": 1400.0, "shares_outstanding": 40.0},
        {"fiscal_year": 2021, "revenue": 1900.0, "receivables": 350.0, "inventory": 40.0, "net_profit": 450.0, "cfo": 796.5, "total_assets": 4000.0, "total_equity": 1850.0, "shares_outstanding": 50.0},
        {"fiscal_year": 2022, "revenue": 3200.0, "receivables": 450.0, "inventory": 50.0, "net_profit": 1050.0, "cfo": 1659.0, "total_assets": 5000.0, "total_equity": 2900.0, "shares_outstanding": 70.0},
        {"fiscal_year": 2023, "revenue": 2600.0, "receivables": 420.0, "inventory": 55.0, "net_profit": 370.0, "cfo": 514.3, "total_assets": 5200.0, "total_equity": 3200.0, "shares_outstanding": 80.0},
        {"fiscal_year": 2024, "revenue": 3970.0, "receivables": 460.0, "inventory": 60.0, "net_profit": 680.0, "cfo": 1890.4, "total_assets": 6000.0, "total_equity": 3800.0, "shares_outstanding": 100.0},
        {"fiscal_year": 2025, "revenue": 5060.0, "receivables": 410.0, "inventory": 65.0, "net_profit": 1207.0, "cfo": 1810.5, "total_assets": 7000.0, "total_equity": 5000.0, "shares_outstanding": 120.0},
    ]
    val_data = {
        "status": "READY",
        "current_price": 45.0,
        "bear_iv": 50.0,
        "base_iv": 157.0,
        "bull_iv": 190.0,
        "actual_mos_pct": 71.4,
        "required_mos_pct": 50.0,
        "valuation_confidence": "LOW",
        "quality_tier": "HIGH",
    }
    analysis = build_munger_financial_analysis("HAH", existing_history=hah_history, valuation_data=val_data)

    # 1. Receivables: No false warning
    assert analysis.financial_forensics.status != DimensionStatus.FAIL.value
    assert not any(f.code == "RECEIVABLES_GROW_FASTER_THAN_REVENUE" for f in analysis.all_findings)

    # 2. Earnings Quality: PASS (median CFO/PAT > 1.4x)
    assert analysis.earnings_quality.status == DimensionStatus.PASS.value
    assert "kéo dài" not in analysis.earnings_quality.explanation

    # 3. Inventory: PASS (immaterial)
    assert not any(f.code in ("INVENTORY_BUILDUP", "INVENTORY_GROWTH_EXCEEDS_SALES") for f in analysis.all_findings)

    # 4. Normalized Earning Power: surfaced as peak caution
    norm = analysis.normalized_earning_power
    assert norm["is_peak_earnings"] is True
    assert norm["reported_latest"] == 1207.0
    assert "Cảnh báo" in norm["explanation"]

    # 5. Single Decision Authority
    dec = analysis.long_term_decision
    assert dec["decision_trace"]["decision_authority"] == "MUNGER_BCTC_PIPELINE"
    assert dec["state"] in ("BUY", "CONDITIONAL_BUY")
    assert dec["state"] != "WAIT_FOR_MOS"
    assert dec["valuation_confidence"] == "LOW"
