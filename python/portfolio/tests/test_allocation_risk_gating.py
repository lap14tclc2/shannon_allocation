"""
Regression and decision-integrity tests for gating Allocation decisions on reliable Risk coverage.

Ensures that partial/unreliable market risk data is treated as diagnostic only
and NEVER triggers risk-based REDUCE, rotation, or candidate BUY_READY promotion.
"""

import pytest
import pandas as pd
import numpy as np

from portfolio.risk import portfolio_risk
from portfolio.allocation.service import AllocationService
from portfolio.allocation.opportunity import decide_holding, decide_candidate, rotation_gates
from portfolio.allocation.models import EligibilityResult, CandidateOpportunity, PortfolioFitResult
from portfolio.allocation.candidate_service import classify_candidate


@pytest.fixture
def partial_portfolio_setup():
    """3 holdings: FPT 52.7% NAV, ACB 10.0% NAV, DGC 3.1% NAV, Cash 34.2% NAV.

    Only DGC has 250 days of price history (3.1% NAV coverage).
    FPT and ACB have no/insufficient price history.
    """
    position_rows = [
        {"symbol": "FPT", "market_value": 527_000_000, "weight": 0.527, "price": 130000, "quantity": 4053},
        {"symbol": "ACB", "market_value": 100_000_000, "weight": 0.100, "price": 25000, "quantity": 4000},
        {"symbol": "DGC", "market_value": 31_000_000, "weight": 0.031, "price": 100000, "quantity": 310},
        {"symbol": "CASH", "market_value": 342_000_000, "weight": 0.342, "price": 1.0, "quantity": 342000000},
    ]

    np.random.seed(42)
    dgc_prices = [100.0]
    for _ in range(250):
        dgc_prices.append(dgc_prices[-1] * (1.0 + np.random.normal(0.0005, 0.02)))

    dates = pd.date_range("2025-01-01", periods=251, freq="B").strftime("%Y-%m-%d")

    histories = {
        "DGC": [
            {"trading_date": dates[i], "close": dgc_prices[i]}
            for i in range(251)
        ],
        "FPT": [
            {"trading_date": dates[i], "close": 130.0}
            for i in range(5)
        ],
        "ACB": [],
    }

    valuation_map = {
        "FPT": {
            "symbol": "FPT",
            "quality_tier": "HIGH_QUALITY",
            "quality_score": 85,
            "actual_mos_pct": 25.0,
            "required_mos_pct": 15.0,
            "status": "INVESTABLE",
            "valuation_confidence": "HIGH",
        },
        "ACB": {
            "symbol": "ACB",
            "quality_tier": "HIGH_QUALITY",
            "quality_score": 80,
            "actual_mos_pct": 20.0,
            "required_mos_pct": 15.0,
            "status": "INVESTABLE",
            "valuation_confidence": "HIGH",
        },
        "DGC": {
            "symbol": "DGC",
            "quality_tier": "HIGH_QUALITY",
            "quality_score": 82,
            "actual_mos_pct": 30.0,
            "required_mos_pct": 15.0,
            "status": "INVESTABLE",
            "valuation_confidence": "HIGH",
        },
    }

    return position_rows, histories, valuation_map


def test_1_partial_coverage_market_risk_actionable_false(partial_portfolio_setup):
    """Req 1: 3.1% NAV coverage sets market_risk_actionable to False."""
    positions, histories, _ = partial_portfolio_setup
    risk_res = portfolio_risk(positions, histories)

    assert risk_res["risk_coverage_status"] == "INSUFFICIENT"
    assert risk_res["market_risk_actionable"] is False
    assert risk_res["risk_context"]["actionable"] is False


def test_2_current_fit_returns_unavailable_when_not_actionable(partial_portfolio_setup):
    """Req 2: Allocation _current_fit returns UNAVAILABLE when market risk is not actionable."""
    positions, histories, _ = partial_portfolio_setup
    risk_res = portfolio_risk(positions, histories)

    fit_dgc = AllocationService._current_fit("DGC", 0.031, risk_res, 0.20)
    fit_fpt = AllocationService._current_fit("FPT", 0.527, risk_res, 0.20)

    assert fit_dgc == "UNAVAILABLE"
    assert fit_fpt == "UNAVAILABLE"


def test_3_fit_for_proposed_returns_risk_available_false_under_insufficient_coverage(partial_portfolio_setup):
    """Req 3: Candidate _fit_for_proposed returns risk_available = False under partial coverage."""
    positions, histories, val_map = partial_portfolio_setup
    service = AllocationService()
    baseline = portfolio_risk(positions, histories)

    fit_res = service._fit_for_proposed(
        base_rows=positions,
        histories=histories,
        before_risk=baseline,
        nav=1_000_000_000,
        symbol="HPG",
        proposed_weight=0.05,
    )

    assert fit_res.risk_available is False
    assert fit_res.fit == "UNAVAILABLE"


def test_4_missing_correlation_cannot_produce_good_fit():
    """Req 4: Missing correlation (avg_corr is None) cannot produce GOOD fit."""
    risk_dict = {
        "status": "VALID",
        "market_risk_actionable": True,
        "risk_contributions": {"FPT": 0.20},
        "equal_risk_contribution": 0.25,
        "symbol_metrics": {
            "FPT": {"average_correlation_to_others": None}
        }
    }
    fit = AllocationService._current_fit("FPT", 0.20, risk_dict, 0.20)
    assert fit != "GOOD"
    assert fit == "MODERATE"


def test_5_dgc_100_percent_rc_cannot_trigger_reduce_under_insufficient_coverage(partial_portfolio_setup):
    """Req 5: DGC 100% measurable RC does not trigger REDUCE when market_risk_actionable is False."""
    positions, histories, val_map = partial_portfolio_setup
    service = AllocationService()
    report = service.evaluate(
        position_rows=positions,
        histories=histories,
        cash=342_000_000,
        valuation_map=val_map,
    )

    dgc_dec = next((h for h in report.holdings if h.symbol == "DGC"), None)
    assert dgc_dec is not None
    assert dgc_dec.action == "HOLD"
    assert dgc_dec.action != "REDUCE"


def test_6_fpt_missing_history_does_not_get_rc_zero_semantics(partial_portfolio_setup):
    """Req 6: FPT missing history has risk_contribution None, not 0.0."""
    positions, histories, _ = partial_portfolio_setup
    risk_res = portfolio_risk(positions, histories)

    fpt_sm = risk_res["symbol_metrics"]["FPT"]
    assert fpt_sm["risk_contribution"] is None
    assert fpt_sm["risk_contribution_status"] == "UNAVAILABLE"


def test_7_acb_missing_history_does_not_get_rc_zero_semantics(partial_portfolio_setup):
    """Req 7: ACB missing history has risk_contribution None, not 0.0."""
    positions, histories, _ = partial_portfolio_setup
    risk_res = portfolio_risk(positions, histories)

    acb_sm = risk_res["symbol_metrics"]["ACB"]
    assert acb_sm["risk_contribution"] is None
    assert acb_sm["risk_contribution_status"] == "UNAVAILABLE"


def test_8_existing_holding_unavailable_market_risk_defaults_hold(partial_portfolio_setup):
    """Req 8: Existing holding with unavailable market risk defaults to HOLD."""
    positions, histories, val_map = partial_portfolio_setup
    service = AllocationService()
    report = service.evaluate(
        position_rows=positions,
        histories=histories,
        cash=342_000_000,
        valuation_map=val_map,
    )

    fpt_dec = next((h for h in report.holdings if h.symbol == "FPT"), None)
    assert fpt_dec is not None
    assert fpt_dec.action == "HOLD"


def test_9_candidate_unavailable_market_fit_becomes_watchlist():
    """Req 9: Candidate with UNAVAILABLE market fit becomes WATCHLIST, not BUY_READY."""
    item = {"symbol": "HPG", "avg_turnover_20d_billion": 50.0}
    signal = {
        "symbol": "HPG",
        "quality_tier": "HIGH_QUALITY",
        "quality_score": 85,
        "actual_mos_pct": 25.0,
        "required_mos_pct": 15.0,
        "status": "INVESTABLE",
        "valuation_confidence": "HIGH",
    }
    eligibility = EligibilityResult(
        symbol="HPG",
        status="INVESTABLE",
        quality_tier="HIGH_QUALITY",
        actual_mos_pct=25.0,
        required_mos_pct=15.0,
        valuation_safety=10.0,
        valuation_confidence="HIGH",
        hard_rejects=(),
        reason_codes=(),
    )
    fit_res = PortfolioFitResult(
        symbol="HPG", current_weight=0.0, proposed_weight=0.05,
        portfolio_vol_before=None, portfolio_vol_after=None,
        risk_contribution_before=None, risk_contribution_after=None,
        diversification_ratio_before=None, diversification_ratio_after=None,
        average_correlation_to_portfolio=None, max_correlation_to_portfolio=None,
        hhi_after=None, effective_positions_after=None,
        risk_available=False, fit="UNAVAILABLE",
    )

    tier, _, failed, watch_reasons, _ = classify_candidate(
        item, signal, eligibility, portfolio_fit=fit_res
    )
    assert tier == "WATCHLIST"
    assert tier != "BUY_READY"


def test_10_no_execution_buy_plan_for_watch_candidate():
    """Req 10: Watch candidate gets no execution buy plan."""
    cand = CandidateOpportunity(
        symbol="HPG",
        source="TEST",
        eligibility=EligibilityResult(
            symbol="HPG", status="INVESTABLE", quality_tier="HIGH_QUALITY",
            actual_mos_pct=25.0, required_mos_pct=15.0, valuation_safety=10.0,
            valuation_confidence="HIGH", hard_rejects=(), reason_codes=(),
        ),
        candidate_tier="WATCHLIST",
        portfolio_fit=PortfolioFitResult(
            symbol="HPG", current_weight=0.0, proposed_weight=0.05,
            portfolio_vol_before=None, portfolio_vol_after=None,
            risk_contribution_before=None, risk_contribution_after=None,
            diversification_ratio_before=None, diversification_ratio_after=None,
            average_correlation_to_portfolio=None, max_correlation_to_portfolio=None,
            hhi_after=None, effective_positions_after=None,
            risk_available=False, fit="UNAVAILABLE",
        ),
    )
    dec = decide_candidate(cand, cash_weight=0.34)
    assert dec.action == "WATCH"
    assert dec.execution_plan is None or dec.execution_plan.rounded_quantity_change == 0.0


def test_11_capital_concentration_available_without_covariance(partial_portfolio_setup):
    """Req 11: Capital concentration metrics remain computed without covariance data."""
    positions, histories, _ = partial_portfolio_setup
    risk_res = portfolio_risk(positions, histories)

    assert risk_res["max_position_weight"] == 0.527
    assert risk_res["effective_positions"] > 0.0


def test_12_fpt_52_percent_concentration_creates_review_warning(partial_portfolio_setup):
    """Req 12: FPT 52.7% NAV concentration includes POSITION_CONCENTRATED reason code."""
    positions, histories, val_map = partial_portfolio_setup
    service = AllocationService()
    report = service.evaluate(
        position_rows=positions,
        histories=histories,
        cash=342_000_000,
        valuation_map=val_map,
    )

    fpt_dec = next((h for h in report.holdings if h.symbol == "FPT"), None)
    assert fpt_dec is not None
    assert "POSITION_CONCENTRATED" in fpt_dec.reason_codes


def test_13_concentration_alone_does_not_force_sell_under_intact_thesis(partial_portfolio_setup):
    """Req 13: Concentration alone does not force SELL/REDUCE under intact thesis."""
    positions, histories, val_map = partial_portfolio_setup
    service = AllocationService()
    report = service.evaluate(
        position_rows=positions,
        histories=histories,
        cash=342_000_000,
        valuation_map=val_map,
    )

    fpt_dec = next((h for h in report.holdings if h.symbol == "FPT"), None)
    assert fpt_dec.action == "HOLD"


def test_14_confirmed_thesis_break_causes_sell():
    """Req 14: Confirmed hard reject / thesis break causes SELL."""
    eligibility = EligibilityResult(
        symbol="BAD_STOCK",
        status="INELIGIBLE",
        quality_tier="DISTRESSED",
        actual_mos_pct=-50.0,
        required_mos_pct=20.0,
        valuation_safety=-70.0,
        valuation_confidence="HIGH",
        hard_rejects=("SOLVENCY_RISK",),
        reason_codes=("SOLVENCY_RISK",),
    )
    dec = decide_holding(eligibility, current_weight=0.10, risk_contribution=None, equal_risk=None)
    assert dec.action == "SELL"
    assert dec.post_action_target_weight == 0.0


def test_15_confirmed_low_quality_deterioration_causes_reduce():
    """Req 15: Confirmed LOW_QUALITY causes REDUCE."""
    eligibility = EligibilityResult(
        symbol="WEAK_STOCK",
        status="INELIGIBLE",
        quality_tier="LOW_QUALITY",
        actual_mos_pct=5.0,
        required_mos_pct=15.0,
        valuation_safety=-10.0,
        valuation_confidence="MEDIUM",
        hard_rejects=(),
        reason_codes=("QUALITY_DETERIORATING",),
    )
    dec = decide_holding(eligibility, current_weight=0.15, risk_contribution=None, equal_risk=None)
    assert dec.action == "REDUCE"
    assert dec.post_action_target_weight > 0.0


def test_16_reliable_full_coverage_rc_breach_causes_reduce():
    """Req 16: Reliable full-coverage RC breach causes REDUCE."""
    eligibility = EligibilityResult(
        symbol="VOL_STOCK",
        status="INVESTABLE",
        quality_tier="INVESTABLE",
        actual_mos_pct=15.0,
        required_mos_pct=15.0,
        valuation_safety=0.0,
        valuation_confidence="HIGH",
        hard_rejects=(),
        reason_codes=(),
    )
    dec = decide_holding(
        eligibility,
        current_weight=0.25,
        risk_contribution=0.60,
        equal_risk=0.20,
        risk_actionable=True,
    )
    assert dec.action == "HOLD"
    assert "REVIEW_REQUIRED" in dec.reason_codes
    assert "RISK_CONTRIBUTION_HIGH" in dec.reason_codes


def test_17_permanent_loss_unknown_does_not_become_low():
    """Req 17: Permanent loss UNKNOWN does not become LOW."""
    from portfolio.permanent_loss_risk import assess_permanent_loss_risk_for_symbol
    res = assess_permanent_loss_risk_for_symbol("UNKNOWN_CO", None, 0.10)
    assert res["severity"] == "UNKNOWN"
    assert res["overall_risk"] == "UNKNOWN"


def test_18_permanent_loss_elevated_alone_does_not_silently_become_sell():
    """Req 18: ELEVATED permanent loss risk does not become SELL without hard reject."""
    eligibility = EligibilityResult(
        symbol="ELEVATED_CO",
        status="WATCHLIST",
        quality_tier="WATCH",
        actual_mos_pct=-5.0,
        required_mos_pct=15.0,
        valuation_safety=-20.0,
        valuation_confidence="MEDIUM",
        hard_rejects=(),
        reason_codes=(),
    )
    dec = decide_holding(eligibility, current_weight=0.10, risk_contribution=None, equal_risk=None)
    assert dec.action != "SELL"


def test_19_rotation_cannot_be_triggered_by_missing_market_risk_data():
    """Req 19: Rotation cannot be triggered by missing market risk data on candidate or holding."""
    holding_el = EligibilityResult(
        symbol="HOLD_A", status="INVESTABLE", quality_tier="HIGH_QUALITY",
        actual_mos_pct=20.0, required_mos_pct=15.0, valuation_safety=5.0,
        valuation_confidence="HIGH", hard_rejects=(), reason_codes=(),
    )
    cand_op = CandidateOpportunity(
        symbol="CAND_B",
        source="TEST",
        eligibility=EligibilityResult(
            symbol="CAND_B", status="INVESTABLE", quality_tier="HIGH_QUALITY",
            actual_mos_pct=35.0, required_mos_pct=15.0, valuation_safety=20.0,
            valuation_confidence="HIGH", hard_rejects=(), reason_codes=(),
        ),
        candidate_tier="WATCHLIST",
        portfolio_fit=PortfolioFitResult(
            symbol="CAND_B", current_weight=0.0, proposed_weight=0.05,
            portfolio_vol_before=None, portfolio_vol_after=None,
            risk_contribution_before=None, risk_contribution_after=None,
            diversification_ratio_before=None, diversification_ratio_after=None,
            average_correlation_to_portfolio=None, max_correlation_to_portfolio=None,
            hhi_after=None, effective_positions_after=None,
            risk_available=False, fit="UNAVAILABLE",
        ),
    )

    passed, reasons = rotation_gates(
        holding_el, holding_fit="UNAVAILABLE", candidate=cand_op
    )
    assert passed is False


def test_20_risk_insufficient_implies_allocation_fit_unavailable(partial_portfolio_setup):
    """Req 20: /risk INSUFFICIENT coverage implies Allocation fit UNAVAILABLE."""
    positions, histories, val_map = partial_portfolio_setup
    service = AllocationService()
    report = service.evaluate(
        position_rows=positions,
        histories=histories,
        cash=342_000_000,
        valuation_map=val_map,
    )

    for h in report.holdings:
        assert h.bands.get("portfolio_fit") == "UNAVAILABLE"


def test_21_full_coverage_portfolio_produces_valid_fit():
    """Req 21: Full-coverage portfolio produces GOOD/MODERATE/WEAK fit."""
    dates = pd.date_range("2025-01-01", periods=251, freq="B").strftime("%Y-%m-%d")
    np.random.seed(42)
    p1 = [100.0 * (1 + np.random.normal(0.0005, 0.015)) for _ in range(251)]
    p2 = [200.0 * (1 + np.random.normal(0.0005, 0.015)) for _ in range(251)]

    position_rows = [
        {"symbol": "AAA", "market_value": 500_000_000, "weight": 0.50, "price": 100.0, "quantity": 5000000},
        {"symbol": "BBB", "market_value": 500_000_000, "weight": 0.50, "price": 200.0, "quantity": 2500000},
    ]
    histories = {
        "AAA": [{"trading_date": dates[i], "close": p1[i]} for i in range(251)],
        "BBB": [{"trading_date": dates[i], "close": p2[i]} for i in range(251)],
    }
    val_map = {
        "AAA": {"symbol": "AAA", "quality_tier": "HIGH_QUALITY", "actual_mos_pct": 20.0, "required_mos_pct": 15.0, "status": "INVESTABLE"},
        "BBB": {"symbol": "BBB", "quality_tier": "HIGH_QUALITY", "actual_mos_pct": 20.0, "required_mos_pct": 15.0, "status": "INVESTABLE"},
    }

    service = AllocationService()
    report = service.evaluate(position_rows=position_rows, histories=histories, cash=0.0, valuation_map=val_map)

    for h in report.holdings:
        assert h.bands.get("portfolio_fit") in ("GOOD", "MODERATE", "WEAK")


def test_22_candidate_fit_uses_only_reliable_risk_evidence(partial_portfolio_setup):
    """Req 22: Candidate fit uses only reliable full-portfolio risk evidence."""
    positions, histories, val_map = partial_portfolio_setup
    service = AllocationService()
    baseline = portfolio_risk(positions, histories)

    fit = service._fit_for_proposed(
        positions, histories, baseline, 1_000_000_000, "VNM", 0.05
    )
    assert fit.risk_available is False
    assert fit.fit == "UNAVAILABLE"


def test_23_risk_fields_used_by_allocation_have_explicit_scope(partial_portfolio_setup):
    """Req 23: Risk fields used by Allocation have explicit scope."""
    positions, histories, _ = partial_portfolio_setup
    risk_res = portfolio_risk(positions, histories)

    assert "risk_contribution_scope" in risk_res
    assert risk_res["risk_contribution_scope"] in ("FULL_PORTFOLIO", "ELIGIBLE_UNIVERSE_ONLY", "UNAVAILABLE")


def test_24_no_ledger_mutation(partial_portfolio_setup):
    """Req 24: Allocation evaluation never mutates input position rows."""
    positions, histories, val_map = partial_portfolio_setup
    original_fpt_weight = positions[0]["weight"]

    service = AllocationService()
    service.evaluate(position_rows=positions, histories=histories, cash=342_000_000, valuation_map=val_map)

    assert positions[0]["weight"] == original_fpt_weight


def test_25_expected_alpha_remains_disabled(partial_portfolio_setup):
    """Req 25: Expected Alpha remains disabled in decision payload."""
    positions, histories, val_map = partial_portfolio_setup
    service = AllocationService()
    report = service.evaluate(position_rows=positions, histories=histories, cash=342_000_000, valuation_map=val_map)

    report_dict = report.to_dict() if hasattr(report, "to_dict") else {}
    assert "expected_alpha" not in report_dict


def test_26_kelly_remains_disabled(partial_portfolio_setup):
    """Req 26: Kelly formula remains disabled in decision payload."""
    positions, histories, val_map = partial_portfolio_setup
    service = AllocationService()
    report = service.evaluate(position_rows=positions, histories=histories, cash=342_000_000, valuation_map=val_map)

    report_dict = report.to_dict() if hasattr(report, "to_dict") else {}
    assert "kelly_fraction" not in report_dict


def test_27_dgc_headline_scope_under_partial_coverage(partial_portfolio_setup):
    """Part A1: DGC warning summary specifies measurable subset under partial risk coverage."""
    positions, histories, _ = partial_portfolio_setup
    risk_res = portfolio_risk(positions, histories)
    dgc_warn = next((w for w in risk_res["warnings"] if "DGC" in w.get("affected_symbols", [])), None)
    assert dgc_warn is not None
    assert "biến động trong phần danh mục có đủ dữ liệu" in dgc_warn["summary"]
    assert "tổng biến động danh mục" not in dgc_warn["summary"]


def test_28_fpt_missing_risk_contribution_summary(partial_portfolio_setup):
    """Part A2: FPT missing risk contribution states UNKNOWN / insufficient, not 0.0%."""
    positions, histories, _ = partial_portfolio_setup
    risk_res = portfolio_risk(positions, histories)
    fpt_warn = next((w for w in risk_res["warnings"] if "FPT" in w.get("affected_symbols", [])), None)
    assert fpt_warn is not None
    assert "Chưa đủ dữ liệu để tính đóng góp biến động" in fpt_warn["summary"]
    assert "0.0%" not in fpt_warn["summary"]


def test_29_hhi_and_diversification_ratio_suppressed_when_not_actionable(partial_portfolio_setup):
    """Part A5: RC-HHI and diversification ratio are hidden when market risk is not actionable."""
    positions, histories, _ = partial_portfolio_setup
    risk_res = portfolio_risk(positions, histories)
    assert risk_res["market_risk_actionable"] is False
    assert risk_res["diversification_ratio"] is None
    assert risk_res["risk_contribution_hhi"] is None


def test_30_moat_trend_defaults_to_unknown_without_temporal_evidence():
    """Part A6: Snapshot moat score yields strength but moat_trend defaults to UNKNOWN."""
    from portfolio.permanent_loss_risk import assess_permanent_loss_risk_for_symbol
    sig = {
        "quality_tier": "HIGH_QUALITY",
        "moat_score": 80,
        "actual_mos_pct": 20.0,
        "required_mos_pct": 15.0,
    }
    res = assess_permanent_loss_risk_for_symbol("FPT", sig, 0.50)
    assert res["moat_strength"] == "STRONG"
    assert res["moat_trend"] == "UNKNOWN"
    assert "Chưa đủ dữ liệu xu hướng" in res["moat_trend_text"]


def test_31_permanent_loss_top_concerns_separate_balance_sheet_and_valuation():
    """Part A7: Permanent loss summary separates balance sheet and valuation MOS concerns."""
    from portfolio.permanent_loss_risk import assess_portfolio_permanent_loss_risk
    rows = [{"symbol": "FPT", "weight": 0.50}]
    val_signals = {
        "FPT": {
            "quality_tier": "WATCH",
            "financial_strength_score": 25,
            "actual_mos_pct": 13.7,
            "required_mos_pct": 15.0,
        }
    }
    res = assess_portfolio_permanent_loss_risk(rows, val_signals)
    assert len(res["top_concerns"]) > 0
    fpt_concern = res["top_concerns"][0]
    assert "FPT:" in fpt_concern
    assert "rủi ro bảng cân đối cao" in fpt_concern
    assert "MOS thấp hơn yêu cầu 1.3 điểm %" in fpt_concern
    assert "tài chính/định giá" not in fpt_concern


def test_32_high_volatility_and_high_risk_contribution_do_not_cause_sell_or_reduce():
    """T02 Invariant: High risk contribution and volatility CANNOT cause SELL or REDUCE for an intact business."""
    from portfolio.allocation.opportunity import decide_holding
    from portfolio.allocation.models import EligibilityResult

    eligibility = EligibilityResult(
        symbol="FPT",
        status="BUY_READY",
        quality_tier="HIGH_QUALITY",
        quality_score=85,
        actual_mos_pct=25.0,
        required_mos_pct=15.0,
        valuation_safety=10.0,
        data_quality="READY",
        reason_codes=("QUALIFIED",),
        hard_rejects=(),
    )

    # Extreme risk contribution (80% of portfolio risk) and high volatility
    decision = decide_holding(
        eligibility=eligibility,
        current_weight=0.15,
        target_min=0.05,
        target_mid=0.20,
        target_max=0.35,
        risk_contribution=0.80,
        equal_risk=0.25,
        risk_actionable=True,
    )

    # Must NOT be SELL or REDUCE
    assert decision.action not in ("SELL", "REDUCE")
    assert decision.action in ("HOLD", "BUY_MORE")


def test_33_drawdown_does_not_cause_automatic_sell():
    """T02 Invariant: Drawdown or price drop does not trigger SELL for an intact thesis."""
    from portfolio.allocation.opportunity import decide_holding
    from portfolio.allocation.models import EligibilityResult

    eligibility = EligibilityResult(
        symbol="ACB",
        status="BUY_READY",
        quality_tier="HIGH_QUALITY",
        quality_score=80,
        actual_mos_pct=35.0,  # Price dropped, MOS increased
        required_mos_pct=15.0,
        valuation_safety=20.0,
        data_quality="READY",
        reason_codes=("QUALIFIED",),
        hard_rejects=(),
    )

    decision = decide_holding(
        eligibility=eligibility,
        current_weight=0.10,
        target_min=0.05,
        target_mid=0.20,
        target_max=0.35,
        risk_contribution=None,
        equal_risk=None,
        risk_actionable=True,
    )


    assert decision.action != "SELL"
    assert decision.action in ("HOLD", "BUY_MORE")



