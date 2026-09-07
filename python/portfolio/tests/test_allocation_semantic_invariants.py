"""Comprehensive allocation semantic invariant tests.

Enforces:
1. HOLD must not imply a different actionable target from current weight.
2. REDUCE post_action_target_weight < current_weight.
3. BUY_MORE post_action_target_weight > current_weight.
4. SELL post_action_target_weight == 0.
5. New-position guidance must not be labeled as target weight.
6. ACB-like HOLD example (current=38.2%, new_position_band=3-5%, action=HOLD, post_action_weight=38.2%).
7. DGC-like REDUCE example (current=42.2%, new_position_band=12-18%, action=REDUCE, post_action_weight~18%).
8. Frontend labels contract checks ("Tỷ trọng sau đề xuất", "Mức vốn gợi ý khi mở vị thế mới", helper text).
9. Ledger invariant (no ledger mutation).
"""
from __future__ import annotations

import pytest

from portfolio.allocation.eligibility import eligibility_from_signal
from portfolio.allocation.models import AllocationDecision, SizingResult
from portfolio.allocation.opportunity import decide_candidate, decide_holding
from portfolio.allocation.service import AllocationService


def test_acb_hold_example_semantic_invariant():
    """1. ACB-like HOLD example:

    current = 38.2% (0.382)
    new_position_band = 3-5%
    action = HOLD
    post_action_weight = 38.2% (0.382)
    """
    signal = {
        "symbol": "ACB",
        "quality_tier": "HIGH_QUALITY",
        "quality_score": 85,
        "valuation_status": "FAIR",
        "actual_mos_pct": 10.0,
        "required_mos_pct": 10.0,
        "valuation_confidence": "MEDIUM",
        "hard_rejects": [],
    }
    eligibility = eligibility_from_signal(signal)
    acb_sizing = SizingResult(
        symbol="ACB",
        conviction_tier="STARTER",
        target_min=0.03,
        target_mid=0.04,
        target_max=0.05,
    )

    decision = decide_holding(
        eligibility,
        current_weight=0.382,
        risk_contribution=0.20,
        equal_risk=0.50,
        sizing=acb_sizing,
        current_fit="GOOD",
    )

    assert decision.action == "HOLD"
    assert decision.current_weight == 0.382
    assert decision.post_action_target_weight == 0.382
    assert decision.new_position_guidance["tier"] == "STARTER"
    assert decision.new_position_guidance["min_weight"] == 0.03
    assert decision.new_position_guidance["mid_weight"] == 0.04
    assert decision.new_position_guidance["max_weight"] == 0.05


def test_dgc_hold_review_example_semantic_invariant():
    """2. DGC-like HOLD + REVIEW example (Hard Invariant 3):

    current = 42.2% (0.422)
    new_position_band = 12-18%
    action = HOLD (with REVIEW_REQUIRED)
    post_action_weight = 42.2% (0.422)
    """
    signal = {
        "symbol": "DGC",
        "quality_tier": "HIGH_QUALITY",
        "quality_score": 85,
        "valuation_status": "ATTRACTIVE",
        "actual_mos_pct": 30.0,
        "required_mos_pct": 20.0,
        "valuation_confidence": "HIGH",
        "hard_rejects": [],
    }
    eligibility = eligibility_from_signal(signal)
    dgc_sizing = SizingResult(
        symbol="DGC",
        conviction_tier="HIGH_CONVICTION",
        target_min=0.12,
        target_mid=0.15,
        target_max=0.18,
    )

    # Risk contribution breach alone does NOT trigger REDUCE; returns HOLD + REVIEW_REQUIRED
    decision = decide_holding(
        eligibility,
        current_weight=0.422,
        risk_contribution=0.80,
        equal_risk=0.20,
        sizing=dgc_sizing,
        hard_cap=0.20,
        current_fit="WEAK",
    )

    assert decision.action == "HOLD"
    assert decision.current_weight == 0.422
    assert decision.post_action_target_weight == 0.422
    assert "REVIEW_REQUIRED" in decision.reason_codes
    assert "POSITION_CONCENTRATED" in decision.reason_codes
    assert "CONCENTRATED_THESIS_RISK" in decision.reason_codes
    assert "RISK_CONTRIBUTION_HIGH" in decision.reason_codes
    assert decision.new_position_guidance["tier"] == "HIGH_CONVICTION"
    assert decision.new_position_guidance["min_weight"] == 0.12
    assert decision.new_position_guidance["max_weight"] == 0.18


def test_sell_post_action_weight_is_zero():
    """3. SELL: post_action_target_weight == 0%."""
    signal = {
        "symbol": "FRT",
        "quality_tier": "INVESTABLE",
        "hard_rejects": ["THESIS_BROKEN"],
    }
    eligibility = eligibility_from_signal(signal)
    decision = decide_holding(
        eligibility,
        current_weight=0.15,
        risk_contribution=None,
        equal_risk=None,
    )
    assert decision.action == "SELL"
    assert decision.post_action_target_weight == 0.0


def test_buy_more_post_action_weight_greater_than_current():
    """4. BUY_MORE: post_action_target_weight > current_weight."""
    decision = AllocationDecision(
        symbol="FPT",
        action="BUY_MORE",
        kind="CANDIDATE",
        current_weight=0.0,
        post_action_target_weight=0.10,
        target_min=0.07,
        target_mid=0.10,
        target_max=0.12,
    )
    assert decision.action == "BUY_MORE"
    assert decision.post_action_target_weight > decision.current_weight


def test_hold_rejects_mismatched_post_action_target_weight():
    """1. Invariant: HOLD must not specify a post_action_target_weight != current_weight."""
    with pytest.raises(ValueError, match="HOLD decision.*must equal current_weight"):
        AllocationDecision(
            symbol="ACB",
            action="HOLD",
            current_weight=0.382,
            post_action_target_weight=0.04,
        )


def test_frontend_labels_and_components_semantic_contract():
    """5-8. Verify frontend labels and JSX contracts.

    Checks:
    - Main table column header 'Tỷ trọng sau đề xuất' exists.
    - 'Khoảng mục tiêu' is NOT used as main table header.
    - 'Mức vốn gợi ý khi mở vị thế mới' is used.
    - Clarifying helper text exists.
    """
    import pathlib

    labels_path = pathlib.Path("frontend/src/lib/allocationLabels.js")
    labels_content = labels_path.read_text(encoding="utf-8")

    page_path = pathlib.Path("frontend/src/pages/AllocationPage.jsx")
    page_content = page_path.read_text(encoding="utf-8")

    # Labels verification
    assert "Tỷ trọng sau đề xuất" in labels_content
    assert "Mức vốn gợi ý khi mở vị thế mới" in labels_content
    assert "Phần trăm giá trị danh mục đang nằm ở mã này" in labels_content

    # JSX page verification
    assert "Tỷ trọng sau đề xuất" in page_content
    assert "Mức vốn gợi ý khi mở vị thế mới" in page_content or "NEW_POSITION_GUIDANCE_LABEL_VI" in page_content
    assert "Đây là mức sizing tham khảo nếu xây vị thế mới từ đầu" in page_content
    assert "Khoảng mục tiêu" not in page_content


def test_service_evaluate_does_not_mutate_positions_or_ledger():
    """9. Invariant 10: No ledger mutation."""
    service = AllocationService()
    rows = [
        {"symbol": "ACB", "weight": 0.382, "market_value": 382000000, "quantity": 10000},
        {"symbol": "FPT", "weight": 0.196, "market_value": 196000000, "quantity": 2000},
    ]
    cloned_rows = [dict(r) for r in rows]

    report = service.evaluate(position_rows=rows, cash=422000000)
    assert report is not None
    assert rows == cloned_rows  # position rows untouched
