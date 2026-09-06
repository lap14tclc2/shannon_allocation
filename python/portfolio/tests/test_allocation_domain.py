"""Allocation domain model + reason-code contract tests."""
from __future__ import annotations

import pytest

from portfolio.allocation.models import (
    ACTIONS,
    CONFIDENCE_LEVELS,
    CONVICTION_TIERS,
    ELIGIBILITY_STATUSES,
    FIT_LEVELS,
    AllocationDecision,
    CandidateOpportunity,
    EligibilityResult,
    PortfolioFitResult,
    PortfolioAllocationReport,
    SizingResult,
)
from portfolio.allocation.reason_codes import (
    ALL_REASON_CODES,
    DATA_INSUFFICIENT,
    HARD_REJECT,
    reason_code_vi,
)


def test_allocation_actions_are_the_canonical_six():
    assert set(ACTIONS) == {"BUY_MORE", "HOLD", "WATCH", "REDUCE", "SELL", "KEEP_CASH"}


def test_eligibility_statuses_are_canonical():
    assert set(ELIGIBILITY_STATUSES) == {"INVESTABLE", "WATCHLIST", "INELIGIBLE"}


def test_confidence_and_fit_levels():
    assert set(CONFIDENCE_LEVELS) == {"HIGH", "MEDIUM", "LOW"}
    assert set(FIT_LEVELS) == {"GOOD", "MODERATE", "WEAK", "UNAVAILABLE"}
    assert set(CONVICTION_TIERS) == {"STARTER", "NORMAL", "HIGH_CONVICTION"}


def test_reason_codes_are_centralized_and_non_empty():
    assert HARD_REJECT in ALL_REASON_CODES
    assert DATA_INSUFFICIENT in ALL_REASON_CODES
    assert len(ALL_REASON_CODES) >= 20
    for code in ALL_REASON_CODES:
        assert code.isupper() and "_" in code


def test_reason_code_vi_maps_every_canonical_code():
    for code in ALL_REASON_CODES:
        label = reason_code_vi(code)
        assert isinstance(label, str) and label
    assert reason_code_vi("UNKNOWN_CODE_XYZ") == "UNKNOWN_CODE_XYZ"


def test_model_serialization_is_stable():
    eligibility = EligibilityResult(
        symbol="FPT", status="INVESTABLE", quality_tier="HIGH_QUALITY",
        quality_score=85, valuation_safety=7.0, reason_codes=("QUALITY_STRONG",),
    )
    payload = eligibility.to_dict()
    assert payload["symbol"] == "FPT"
    assert payload["status"] == "INVESTABLE"
    assert payload["valuation_safety"] == 7.0
    assert tuple(payload["reason_codes"]) == ("QUALITY_STRONG",)


def test_report_serialization_includes_holdings_and_opportunities():
    report = PortfolioAllocationReport(
        portfolio_id=7,
        verdict="NO_ACTION_REQUIRED",
        posture="KEEP_CASH",
        cash_current=0.3,
        cash_suggested_range=(0.2, 0.3),
        no_action_required=True,
        holdings=(AllocationDecision(symbol="FPT", action="HOLD", kind="HOLDING", current_weight=0.5),),
        opportunities=(
            CandidateOpportunity(
                symbol="VNM",
                source="SCREENER",
                eligibility=EligibilityResult(symbol="VNM", status="INVESTABLE"),
                candidate_rank=1,
            ),
        ),
    )
    payload = report.to_dict()
    assert payload["portfolio_id"] == 7
    assert payload["cash_suggested_range"] == [0.2, 0.3]
    assert payload["holdings"][0]["action"] == "HOLD"
    assert payload["opportunities"][0]["eligibility"]["status"] == "INVESTABLE"


def test_allocation_decision_never_represents_an_execution():
    decision = AllocationDecision(symbol="FPT", action="BUY_MORE", kind="CANDIDATE")
    assert decision.action == "BUY_MORE"
    assert "execute" not in str(decision.to_dict()).lower()


def test_portfolio_fit_result_missing_risk_defaults_to_unavailable():
    fit = PortfolioFitResult(symbol="VNM", current_weight=0.0, proposed_weight=0.1)
    assert fit.fit == "UNAVAILABLE"
    assert fit.risk_available is True  # explicit flag, defaults conservative


def test_sizing_result_defaults_are_starter_band():
    sizing = SizingResult(symbol="X")
    assert sizing.target_min == 0.03
    assert sizing.target_mid == 0.04
    assert sizing.target_max == 0.05
    assert sizing.risk_cap == 0.20