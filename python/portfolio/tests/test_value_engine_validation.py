"""
Tests for the Numeric-Only Validation & Regime Engine (feedback.txt, TASK-085).

Covers:
1. DGC-like series -> STRUCTURAL_REGIME_BREAK @2018 + CYCLICAL_EXTREME @2021/2022,
   latest comparable regime = 2018-2025.
2. Clean history -> no resolutions, numeric_confidence HIGH.
3. Unit jump (>100x, related metrics không đổi) -> UNRESOLVED_MATERIAL / LOW.
4. SHARE_STRUCTURE_CHANGE (shares nhảy, operating không đổi).
5. calculate_cycle_normalized(included_years=...) chỉ dùng latest comparable regime.
"""
from decimal import Decimal

from portfolio.financial_data.models import (
    CanonicalFact,
    ConsolidationScope,
    FactIdentityKey,
    PeriodType,
    QualityStatus,
    StatementType,
)
from portfolio.value_engine.owner_earnings import OwnerEarningsCalculator
from portfolio.value_engine.validation import run_validation_gate

B = Decimal("1000000000")


def _row(year, revenue, net_profit, cfo, equity, debt, shares):
    def _v(x):
        return float(Decimal(str(x)) * B)

    return {
        "fiscal_year": year,
        "revenue": _v(revenue),
        "net_profit": _v(net_profit),
        "operating_cash_flow": _v(cfo),
        "equity": _v(equity),
        "total_debt": _v(debt),
        "shares_outstanding": _v(shares),
    }


def _dgc_like_history():
    """DGC FY2016-2025 (tỷ VND) — feedback.txt §14."""
    return [
        _row(2016, 2622.0, 320.0, 420.0, 2600.0, 900.0, 50),
        _row(2017, 626.0, 128.0, 220.0, 666.0, 220.0, 50),
        _row(2018, 6090.0, 873.0, 1050.0, 3165.0, 1565.0, 107.8),
        _row(2019, 5091.0, 572.0, 780.0, 3300.0, 1500.0, 129.4),
        _row(2020, 6236.0, 948.0, 1073.0, 3600.0, 1600.0, 148.8),
        _row(2021, 9550.0, 2514.0, 2620.0, 5200.0, 2600.0, 171.1),
        _row(2022, 14444.0, 6037.0, 5937.0, 8200.0, 3900.0, 379.8),
        _row(2023, 9748.0, 3252.0, 3400.0, 9800.0, 3100.0, 379.8),
        _row(2024, 9865.0, 3107.0, 3300.0, 11000.0, 2900.0, 379.8),
        _row(2025, 11262.0, 3154.0, 3500.0, 12400.0, 2800.0, 379.8),
    ]


def test_gate_detects_dgc_structural_break_and_cycle_extremes():
    vr = run_validation_gate(_dgc_like_history())
    assert vr.latest_regime_years == list(range(2018, 2026)), vr.latest_regime_years
    assert vr.numeric_confidence == "HIGH"
    by_year = {r["fiscal_year"]: r for r in vr.resolutions}
    assert by_year[2018]["resolution"]["classification"] == "STRUCTURAL_REGIME_BREAK"
    assert by_year[2018]["resolution"]["confidence"] == "HIGH"
    assert by_year[2018]["resolution"]["persistent"] is True
    assert by_year[2018]["valuation_handling"]["split_regime"] is True
    assert by_year[2021]["resolution"]["classification"] == "CYCLICAL_EXTREME"
    assert by_year[2022]["resolution"]["classification"] == "CYCLICAL_EXTREME"
    assert by_year[2021]["valuation_handling"]["include"] is True
    assert 2018 in by_year  # break year được báo trong resolutions


def test_gate_clean_growing_history_returns_empty_resolutions():
    hist = [
        _row(2016, 100.0, 20.0, 22.0, 300.0, 50.0, 100),
        _row(2017, 120.0, 24.0, 26.0, 340.0, 55.0, 100),
        _row(2018, 140.0, 28.0, 30.0, 380.0, 60.0, 100),
        _row(2019, 165.0, 33.0, 35.0, 430.0, 65.0, 100),
        _row(2020, 190.0, 38.0, 40.0, 480.0, 70.0, 100),
    ]
    vr = run_validation_gate(hist)
    assert vr.resolutions == []
    assert vr.numeric_confidence == "HIGH"
    # Không có structural break -> latest comparable regime = toàn bộ lịch sử.
    assert vr.latest_regime_years == [2016, 2017, 2018, 2019, 2020]


def test_gate_data_status_taxonomy():
    """user-test.md §5/§32 — DATA_STATUS: VALID / VALID_WITH_CLASSIFIED_EVENTS /
    SUSPICIOUS / CONFLICTED / INSUFFICIENT."""
    # VALID — lịch sử sạch.
    clean = [
        _row(2016, 100.0, 20.0, 22.0, 300.0, 50.0, 100),
        _row(2017, 120.0, 24.0, 26.0, 340.0, 55.0, 100),
        _row(2018, 140.0, 28.0, 30.0, 380.0, 60.0, 100),
    ]
    assert run_validation_gate(clean).data_status == "VALID"

    # VALID_WITH_CLASSIFIED_EVENTS + SPLIT_REGIME — DGC-like.
    dgc = run_validation_gate(_dgc_like_history())
    assert dgc.data_status == "VALID_WITH_CLASSIFIED_EVENTS"
    assert dgc.regime_status == "SPLIT_REGIME"
    assert dgc.cause_confidence == "UNKNOWN"

    # CONFLICTED — unit error.
    unit = [
        _row(2016, 100.0, 20.0, 22.0, 300.0, 50.0, 100),
        _row(2017, 100000.0, 21.0, 22.0, 305.0, 51.0, 100),
        _row(2018, 101.0, 20.0, 21.0, 306.0, 50.0, 100),
    ]
    assert run_validation_gate(unit).data_status == "CONFLICTED"

    # INSUFFICIENT — <2 năm.
    assert run_validation_gate([_row(2020, 100.0, 20.0, 22.0, 300.0, 50.0, 100)]).data_status == "INSUFFICIENT"


def test_gate_resolution_has_ufvs_scores():
    """feedback.txt §1-§5/§16 — event có Z (anomaly), A (breadth), C (coherence), P, M."""
    vr = run_validation_gate(_dgc_like_history())
    assert vr.resolutions
    for r in vr.resolutions:
        res = r["resolution"]
        ncs = res.get("numeric_coherence_score")
        assert isinstance(ncs, int) and 0 <= ncs <= 100
        assert res.get("anomaly_score") is not None
        assert 0.0 <= res.get("breadth_score", 0) <= 1.0
        assert 0.0 <= res.get("coherence_score", 0) <= 1.0
        assert 0.0 <= res.get("persistence_score", 0) <= 1.0
        assert 0.0 <= res.get("mean_reversion_score", 0) <= 1.0
    y2018 = next(r for r in vr.resolutions if r["fiscal_year"] == 2018)
    assert y2018["resolution"]["classification"] == "STRUCTURAL_REGIME_BREAK"


def test_gate_valuation_handling_use_policies():
    """feedback.txt §11 — normalization policy: SPLIT_REGIME / INCLUDE / REJECT_FACT ..."""
    vr = run_validation_gate(_dgc_like_history())
    by_year = {r["fiscal_year"]: r for r in vr.resolutions}
    assert by_year[2018]["valuation_handling"]["use"] == "SPLIT_REGIME"  # STRUCTURAL_REGIME_BREAK
    assert by_year[2021]["valuation_handling"]["use"] == "INCLUDE"       # CYCLICAL_EXTREME
    assert by_year[2018]["valuation_handling"]["split_regime"] is True


def test_materiality_grades_use_feedback_names():
    """feedback.txt §10 — IMMATERIAL / LOW / MATERIAL / CRITICAL."""
    from portfolio.value_engine.validation.materiality_checker import assess_materiality
    hist = _dgc_like_history()
    mat = assess_materiality(hist, 2018, window_years=list(range(2018, 2026)))
    assert mat["grade"] in ("IMMATERIAL", "LOW", "MATERIAL", "CRITICAL", "UNKNOWN")
    # DGC 2018 trong window 2018-2025 (đã loại 2016-2017) -> materiality thấp.
    assert mat["grade"] in ("IMMATERIAL", "LOW")


def test_gate_validation_confidence_and_level():
    """feedback.txt §14 — validation_confidence 0..100 + level HIGH/MEDIUM/LOW/UNVERIFIED."""
    vr = run_validation_gate(_dgc_like_history())
    assert 0 <= vr.validation_confidence <= 100
    assert vr.validation_confidence_level in ("HIGH", "MEDIUM", "LOW", "UNVERIFIED")
    # Clean history -> confidence cao (không có anomaly/unresolved).
    clean = [
        _row(2016, 100.0, 20.0, 22.0, 300.0, 50.0, 100),
        _row(2017, 120.0, 24.0, 26.0, 340.0, 55.0, 100),
        _row(2018, 140.0, 28.0, 30.0, 380.0, 60.0, 100),
        _row(2019, 165.0, 33.0, 35.0, 430.0, 65.0, 100),
        _row(2020, 190.0, 38.0, 40.0, 480.0, 70.0, 100),
    ]
    assert run_validation_gate(clean).validation_confidence >= 60
    # Unit error -> confidence thấp (dữ liệu mâu thuẫn).
    unit = [
        _row(2016, 100.0, 20.0, 22.0, 300.0, 50.0, 100),
        _row(2017, 100000.0, 21.0, 22.0, 305.0, 51.0, 100),
        _row(2018, 101.0, 20.0, 21.0, 306.0, 50.0, 100),
    ]
    assert run_validation_gate(unit).validation_confidence < 60


def test_normalization_window_evidence_in_report():
    """user-test.md §27/§38-TestC — normalization_window có candidate/included/excluded years."""
    from portfolio.value_engine import ValuationEngine
    facts = _facts_with_break()
    report = ValuationEngine.evaluate(
        symbol="TEST",
        facts=facts,
        current_market_price=Decimal("50000"),
        shares_outstanding=Decimal("100000000"),
        fiscal_year=2025,
        fundamentals={"sector": "Hóa chất"},
        financial_history=[
            {"fiscal_year": y, "revenue": float(rev), "net_profit": float(np_), "equity": float(np_ * 3),
             "operating_cash_flow": float(cfo), "total_debt": 1e11, "shares_outstanding": 1e8}
            for y, rev, np_, cfo in [
                (2016, 600e9, 70e9, 75e9), (2017, 700e9, 80e9, 85e9),
                (2018, 3000e9, 400e9, 420e9), (2019, 3200e9, 450e9, 460e9),
                (2020, 3400e9, 500e9, 520e9), (2021, 3600e9, 550e9, 560e9),
                (2022, 3800e9, 600e9, 620e9), (2023, 4000e9, 650e9, 670e9),
                (2024, 4200e9, 700e9, 720e9), (2025, 4400e9, 750e9, 770e9),
            ]
        ],
    )
    w = report.normalization_window
    assert w is not None
    assert w["comparable_regime_start"] == 2018
    assert w["comparable_regime_end"] == 2025
    assert 2016 in w["excluded_years"] and 2017 in w["excluded_years"]
    assert 2018 in w["included_years"] and 2025 in w["included_years"]
    assert isinstance(w["candidate_years"], list)
    assert w["normalization_years"] >= 7
    assert report.data_status is not None
    assert report.regime_status == "SPLIT_REGIME"


def test_gate_unit_jump_is_unit_mapping_error():
    hist = [
        _row(2016, 100.0, 20.0, 22.0, 300.0, 50.0, 100),
        _row(2017, 100000.0, 21.0, 22.0, 305.0, 51.0, 100),  # revenue x1000, others ~không đổi
        _row(2018, 101.0, 20.0, 21.0, 306.0, 50.0, 100),
    ]
    vr = run_validation_gate(hist)
    assert vr.numeric_confidence == "LOW"
    # feedback.txt §6/§9: unit error -> UNIT_MAPPING_ERROR_CANDIDATE + CONFLICTED + block
    assert vr.data_status == "CONFLICTED"
    by_year = {r["fiscal_year"]: r for r in vr.resolutions}
    assert 2017 in by_year
    assert by_year[2017]["resolution"]["classification"] == "UNIT_MAPPING_ERROR_CANDIDATE"
    assert by_year[2017]["valuation_handling"]["block"] is True
    assert by_year[2017]["valuation_handling"]["use"] == "REJECT_FACT"


def test_gate_share_structure_change_only():
    # 6 năm, năm 2020 shares +50% nhưng operating ổn định -> SHARE_STRUCTURE_CHANGE.
    hist = [
        _row(2016, 100.0, 20.0, 22.0, 300.0, 50.0, 100),
        _row(2017, 105.0, 21.0, 23.0, 315.0, 51.0, 100),
        _row(2018, 110.0, 22.0, 24.0, 330.0, 52.0, 100),
        _row(2019, 115.0, 23.0, 25.0, 345.0, 53.0, 100),
        _row(2020, 118.0, 24.0, 26.0, 360.0, 54.0, 150),  # shares +50%, operating +~5%
        _row(2021, 122.0, 25.0, 27.0, 375.0, 55.0, 150),
    ]
    vr = run_validation_gate(hist)
    by_year = {r["fiscal_year"]: r for r in vr.resolutions}
    assert 2020 in by_year
    assert by_year[2020]["resolution"]["classification"] == "SHARE_STRUCTURE_CHANGE"
    assert by_year[2020]["valuation_handling"]["include"] is True
    assert by_year[2020]["valuation_handling"]["use"] == "INCLUDE + PER_SHARE_ADJUST"


def _make_fact(code, value, year):
    stype = StatementType.INCOME_STATEMENT if code.startswith("IS.") else (
        StatementType.CASH_FLOW if code.startswith("CF.") else StatementType.BALANCE_SHEET
    )
    return CanonicalFact(
        canonical_fact_id=f"{code}-{year}",
        identity=FactIdentityKey(
            security_id="sec-oe-regime",
            statement_type=stype,
            period_end=f"{year}-12-31",
            period_type=PeriodType.FY,
            fiscal_year=year,
            fiscal_quarter=None,
            consolidation_scope=ConsolidationScope.CONSOLIDATED,
            line_item_code=code,
            currency="VND",
        ),
        value=value,
        quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
        decision_id=f"dec-{code}-{year}",
        winning_candidate_id=None,
        candidate_ids=[],
        observed_at="2026-01-01T00:00:00Z",
    )


def _facts_with_break():
    """2016-2017 regime A (quy mô nhỏ), 2018+ regime B (quy mô lớn, giữ nguyên)."""
    facts = []
    for y, rev, np_, cfo in [
        (2016, 600, 70, 75),
        (2017, 700, 80, 85),
        (2018, 3000, 400, 420),
        (2019, 3200, 450, 460),
        (2020, 3400, 500, 520),
        (2021, 3600, 550, 560),
        (2022, 3800, 600, 620),
        (2023, 4000, 650, 670),
        (2024, 4200, 700, 720),
        (2025, 4400, 750, 770),
    ]:
        facts.append(_make_fact("IS.REVENUE.NET", Decimal(rev) * B, y))
        facts.append(_make_fact("IS.PROFIT.NET", Decimal(np_) * B, y))
        facts.append(_make_fact("IS.PROFIT.OPERATING", Decimal(np_) * B, y))
        facts.append(_make_fact("CF.OPERATING.NET", Decimal(cfo) * B, y))
        facts.append(_make_fact("CF.OPERATING.DEPRECIATION", Decimal("40") * B, y))
        facts.append(_make_fact("CF.CAPEX", Decimal("-80") * B, y))
        facts.append(_make_fact("BS.DEBT.TOTAL", Decimal("300") * B, y))
        facts.append(_make_fact("BS.ASSETS.CASH_AND_EQUIVALENTS", Decimal("120") * B, y))
        facts.append(_make_fact("IS.SHARES.OUTSTANDING", Decimal("100000000"), y))
    return facts


def test_cycle_normalized_included_years_restricts_to_latest_regime():
    facts = _facts_with_break()
    # Không giới hạn: dùng toàn bộ 10 năm.
    full = OwnerEarningsCalculator.calculate_cycle_normalized(
        facts=facts, latest_fiscal_year=2025, lookback_years=10,
    )
    assert full.normalization_method == "MID_CYCLE_MEDIAN"
    assert full.normalization_years == 10
    # Giới hạn latest comparable regime 2018-2025 -> chỉ 8 năm, bỏ 2016-2017.
    restricted = OwnerEarningsCalculator.calculate_cycle_normalized(
        facts=facts,
        latest_fiscal_year=2025,
        lookback_years=10,
        included_years=set(range(2018, 2026)),
    )
    assert restricted.normalization_method == "MID_CYCLE_MEDIAN"
    assert restricted.normalization_years == 8
    assert restricted.mid_cycle_revenue is not None
    # Revenue trung vị regime mới cao hơn hẳn (không còn bị kéo xuống bởi 2016-2017).
    assert restricted.mid_cycle_revenue > full.mid_cycle_revenue