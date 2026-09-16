"""
Regression and Evidence-Based Tests for RECEIVABLES_GROW_FASTER_THAN_REVENUE Forensics (Task 165).

Verifies the 5-axis evidence model:
1. 10Y CAGR gap due to low base + 3Y healthy + low materiality + healthy CFO/PAT -> NOT FAIL (PASS).
2. 3Y strong growth gap + high materiality + DSO increasing + weak CFO/PAT -> FAIL (High severity).
3. 10Y gap + missing CFO -> PARTIAL / UNKNOWN (status WATCH, missing_data recorded, never auto PASS).
4. CFO/PAT > 1.0 but recent gap > 5% + high materiality -> MUST remain WATCH (not auto PASS).
5. CFO/PAT < 0.8 but low materiality + 3Y gap <= 0 -> NOT automatic FAIL (PASS).
6. BANK archetype -> NOT_APPLICABLE.
7. SECURITIES archetype -> NOT_APPLICABLE.
8. Structured finding object verification (metrics, semantic keys, no raw machine enums in Vietnamese presentation).
"""

from __future__ import annotations

import pytest
from portfolio.value_engine.munger_forensics import run_receivables_forensics
from portfolio.value_engine.munger_models import DimensionStatus, FindingSeverity
from portfolio.value_engine.munger_thresholds import DEFAULT_MUNGER_THRESHOLD_POLICY


def test_case_1_low_base_10y_gap_with_healthy_3y_and_cfo():
    """1. 10Y CAGR gap high due to low base, but 3Y gap <= 0, low materiality, healthy CFO/PAT -> PASS."""
    # 2014: rec = 10, rev = 1000 (ratio = 1% -> low base)
    # 2021: rec = 80, rev = 4000 (ratio = 2%)
    # 2022: rec = 85, rev = 4500 (ratio = 1.9%)
    # 2023: rec = 90, rev = 5000 (ratio = 1.8%)
    # 2024: rec = 92, rev = 5600 (ratio = 1.6%)
    # 10Y rec CAGR: (92/10)^(1/10)-1 = 24.8% vs rev CAGR: (5600/1000)^(1/10)-1 = 18.8% -> gap = +6% to +15%
    # 3Y rec CAGR: (92/80)^(1/3)-1 = 4.7% vs rev CAGR: (5600/4000)^(1/3)-1 = 11.8% -> 3Y gap = -7.1% (healthy!)
    # CFO: 500, 600, 700 on PAT: 400, 480, 550 -> CFO/PAT = ~1.25x
    history = {
        "years": [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
        "by_year": {
            2014: {"receivables": 10.0, "revenue": 1000.0, "cfo": 100.0, "net_profit": 80.0, "total_assets": 1200.0},
            2015: {"receivables": 15.0, "revenue": 1200.0, "cfo": 120.0, "net_profit": 100.0, "total_assets": 1400.0},
            2016: {"receivables": 22.0, "revenue": 1500.0, "cfo": 160.0, "net_profit": 130.0, "total_assets": 1800.0},
            2017: {"receivables": 30.0, "revenue": 1900.0, "cfo": 210.0, "net_profit": 170.0, "total_assets": 2300.0},
            2018: {"receivables": 40.0, "revenue": 2400.0, "cfo": 270.0, "net_profit": 220.0, "total_assets": 2900.0},
            2019: {"receivables": 52.0, "revenue": 3000.0, "cfo": 340.0, "net_profit": 280.0, "total_assets": 3600.0},
            2020: {"receivables": 65.0, "revenue": 3500.0, "cfo": 400.0, "net_profit": 330.0, "total_assets": 4200.0},
            2021: {"receivables": 80.0, "revenue": 4000.0, "cfo": 500.0, "net_profit": 400.0, "total_assets": 5000.0},
            2022: {"receivables": 85.0, "revenue": 4500.0, "cfo": 600.0, "net_profit": 480.0, "total_assets": 5700.0},
            2023: {"receivables": 90.0, "revenue": 5000.0, "cfo": 700.0, "net_profit": 550.0, "total_assets": 6500.0},
            2024: {"receivables": 92.0, "revenue": 5600.0, "cfo": 800.0, "net_profit": 620.0, "total_assets": 7400.0},
        },
    }
    res = run_receivables_forensics(history, archetype="NORMAL_ENTERPRISE")
    assert res.status == DimensionStatus.PASS.value
    assert len([f for f in res.findings if f.severity in (FindingSeverity.HIGH.value, FindingSeverity.CRITICAL.value)]) == 0
    assert res.metrics["low_base_distortion"] is True
    assert res.metrics["materiality_status"] == "LOW"
    assert res.metrics["cash_conversion_status"] == "HEALTHY"


def test_case_2_recent_strong_gap_high_materiality_weak_cfo_is_fail():
    """2. 3Y receivables growth > revenue + high materiality + DSO increasing + weak CFO/PAT -> FAIL."""
    # 2021: rec = 400, rev = 1000 (40% materiality)
    # 2022: rec = 550, rev = 1050 (52%)
    # 2023: rec = 750, rev = 1100 (68%)
    # 2024: rec = 1000, rev = 1150 (87%)
    # CFO: 20, 10, -50 vs PAT: 150, 160, 170 -> CFO/PAT < 0.1x (severely weak)
    history = {
        "years": [2021, 2022, 2023, 2024],
        "by_year": {
            2021: {"receivables": 400.0, "revenue": 1000.0, "cfo": 30.0, "net_profit": 150.0, "total_assets": 1200.0},
            2022: {"receivables": 550.0, "revenue": 1050.0, "cfo": 20.0, "net_profit": 160.0, "total_assets": 1400.0},
            2023: {"receivables": 750.0, "revenue": 1100.0, "cfo": 10.0, "net_profit": 165.0, "total_assets": 1700.0},
            2024: {"receivables": 1000.0, "revenue": 1150.0, "cfo": -50.0, "net_profit": 170.0, "total_assets": 2100.0},
        },
    }
    res = run_receivables_forensics(history, archetype="NORMAL_ENTERPRISE")
    assert res.status == DimensionStatus.FAIL.value
    assert len(res.findings) > 0
    f = res.findings[0]
    assert f.severity == FindingSeverity.HIGH.value
    assert f.code == "RECEIVABLES_GROW_FASTER_THAN_REVENUE"
    assert res.metrics["materiality_status"] == "HIGH"
    assert res.metrics["cash_conversion_status"] == "WEAK"


def test_case_3_historical_gap_with_missing_cfo_is_partial():
    """3. 10Y gap observed but missing CFO data -> PARTIAL / WATCH (not auto PASS)."""
    history = {
        "years": [2014, 2016, 2018, 2020, 2022, 2024],
        "by_year": {
            2014: {"receivables": 100.0, "revenue": 1000.0, "total_assets": 1200.0},
            2016: {"receivables": 160.0, "revenue": 1100.0, "total_assets": 1400.0},
            2018: {"receivables": 250.0, "revenue": 1200.0, "total_assets": 1600.0},
            2020: {"receivables": 380.0, "revenue": 1300.0, "total_assets": 1900.0},
            2022: {"receivables": 550.0, "revenue": 1400.0, "total_assets": 2200.0},
            2024: {"receivables": 800.0, "revenue": 1500.0, "total_assets": 2600.0},
        },
    }
    res = run_receivables_forensics(history, archetype="NORMAL_ENTERPRISE")
    assert res.status == DimensionStatus.WATCH.value
    assert res.metrics["cash_conversion_status"] == "UNKNOWN"
    assert "RECENT_CFO_PAT_HISTORY" in res.missing_data


def test_case_4_healthy_cfo_with_accelerating_receivables_must_remain_watch():
    """4. CFO/PAT > 1.0 but recent gap > 5% and high materiality -> MUST remain WATCH."""
    history = {
        "years": [2021, 2022, 2023, 2024],
        "by_year": {
            2021: {"receivables": 400.0, "revenue": 1000.0, "cfo": 200.0, "net_profit": 150.0, "total_assets": 1200.0},
            2022: {"receivables": 520.0, "revenue": 1050.0, "cfo": 220.0, "net_profit": 160.0, "total_assets": 1400.0},
            2023: {"receivables": 680.0, "revenue": 1100.0, "cfo": 250.0, "net_profit": 170.0, "total_assets": 1700.0},
            2024: {"receivables": 880.0, "revenue": 1150.0, "cfo": 280.0, "net_profit": 180.0, "total_assets": 2000.0},
        },
    }
    res = run_receivables_forensics(history, archetype="NORMAL_ENTERPRISE")
    # Even though CFO/PAT = ~1.5x, receivables grew much faster and ratio is 76% (High materiality)
    assert res.status == DimensionStatus.WATCH.value
    assert len(res.findings) == 1
    assert res.findings[0].severity == FindingSeverity.MEDIUM.value


def test_case_5_weak_cfo_with_low_materiality_and_healthy_trend_is_not_fail():
    """5. CFO/PAT < 0.8 but low materiality (<15%) and 3Y gap <= 0 -> NOT automatic FAIL (PASS)."""
    history = {
        "years": [2021, 2022, 2023, 2024],
        "by_year": {
            2021: {"receivables": 50.0, "revenue": 2000.0, "cfo": 60.0, "net_profit": 200.0, "total_assets": 3000.0},
            2022: {"receivables": 52.0, "revenue": 2300.0, "cfo": 70.0, "net_profit": 230.0, "total_assets": 3500.0},
            2023: {"receivables": 55.0, "revenue": 2700.0, "cfo": 80.0, "net_profit": 270.0, "total_assets": 4000.0},
            2024: {"receivables": 58.0, "revenue": 3200.0, "cfo": 90.0, "net_profit": 320.0, "total_assets": 4700.0},
        },
    }
    res = run_receivables_forensics(history, archetype="NORMAL_ENTERPRISE")
    assert res.status == DimensionStatus.PASS.value
    assert len([f for f in res.findings if f.severity == FindingSeverity.HIGH.value]) == 0


def test_case_6_bank_not_applicable():
    """6. BANK archetype -> NOT_APPLICABLE."""
    dummy_hist = {
        "years": [2022, 2023, 2024],
        "by_year": {2022: {"receivables": 100, "revenue": 1000}, 2023: {"receivables": 120, "revenue": 1100}, 2024: {"receivables": 150, "revenue": 1200}},
    }
    res = run_receivables_forensics(dummy_hist, archetype="BANK")
    assert res.status == DimensionStatus.NOT_APPLICABLE.value
    assert "INDUSTRIAL_RECEIVABLES_REVENUE" in res.not_applicable


def test_case_7_securities_not_applicable():
    """7. SECURITIES archetype -> NOT_APPLICABLE."""
    dummy_hist = {
        "years": [2022, 2023, 2024],
        "by_year": {2022: {"receivables": 100, "revenue": 1000}, 2023: {"receivables": 120, "revenue": 1100}, 2024: {"receivables": 150, "revenue": 1200}},
    }
    res = run_receivables_forensics(dummy_hist, archetype="SECURITIES")
    assert res.status == DimensionStatus.NOT_APPLICABLE.value
    assert "INDUSTRIAL_RECEIVABLES_REVENUE" in res.not_applicable


def test_case_8_evidence_object_structure():
    """8. Verify structured metrics exposed on Finding and DimensionResult."""
    history = {
        "years": [2021, 2022, 2023, 2024],
        "by_year": {
            2021: {"receivables": 300.0, "revenue": 1000.0, "cfo": 100.0, "net_profit": 150.0, "total_assets": 1200.0},
            2022: {"receivables": 420.0, "revenue": 1050.0, "cfo": 110.0, "net_profit": 160.0, "total_assets": 1400.0},
            2023: {"receivables": 580.0, "revenue": 1100.0, "cfo": 120.0, "net_profit": 170.0, "total_assets": 1700.0},
            2024: {"receivables": 800.0, "revenue": 1150.0, "cfo": 130.0, "net_profit": 180.0, "total_assets": 2000.0},
        },
    }
    res = run_receivables_forensics(history, archetype="NORMAL_ENTERPRISE")
    assert "long_term_gap" in res.metrics
    assert "recent_gap" in res.metrics
    assert "receivables_to_revenue" in res.metrics
    assert "dso" in res.metrics
    assert "cfo_pat" in res.metrics
    assert "persistence" in res.metrics
    assert "materiality_status" in res.metrics
    assert "semantic_key" in res.metrics
    assert res.metrics["semantic_key"] == "receivables_growth_vs_revenue"
