"""Allocation sizing band tests."""
from __future__ import annotations

import pytest

from portfolio.allocation.sizing import (
    DEFAULT_HARD_CAP,
    MAX_HARD_CAP,
    bands_for_tier,
    conviction_mid,
    conviction_tier_for,
    risk_cap_for_fit,
    sizing_for,
)


def _signal(**kwargs):
    base = {
        "symbol": "FPT",
        "quality_tier": "HIGH_QUALITY",
        "quality_score": 85,
        "hard_rejects": [],
        "valuation_status": "ATTRACTIVE",
        "actual_mos_pct": 32.0,
        "required_mos_pct": 25.0,
    }
    base.update(kwargs)
    return base


def test_governance_bands():
    assert bands_for_tier("STARTER") == (0.03, 0.04, 0.05)
    assert bands_for_tier("NORMAL") == (0.07, 0.10, 0.12)
    assert bands_for_tier("HIGH_CONVICTION") == (0.12, 0.15, 0.18)


def test_default_hard_cap_is_twenty_percent():
    assert DEFAULT_HARD_CAP == 0.20
    assert MAX_HARD_CAP == 0.30


def test_conviction_tier_derivation():
    assert conviction_tier_for(_signal(quality_tier="EXCEPTIONAL", actual_mos_pct=40.0)) == "HIGH_CONVICTION"
    assert conviction_tier_for(_signal(actual_mos_pct=30.0)) == "HIGH_CONVICTION"
    assert conviction_tier_for(_signal(quality_tier="INVESTABLE", actual_mos_pct=30.0)) == "NORMAL"
    assert conviction_tier_for(_signal(actual_mos_pct=10.0)) == "STARTER"
    assert conviction_tier_for(_signal(quality_tier="LOW_QUALITY", actual_mos_pct=60.0)) == "STARTER"


def test_risk_cap_degrades_by_fit():
    assert risk_cap_for_fit("GOOD") == 0.20
    assert risk_cap_for_fit("MODERATE") == pytest.approx(0.12)
    assert risk_cap_for_fit("WEAK") == pytest.approx(0.05)
    # Missing risk history degrades safely (never zero, never full).
    unavailable_cap = risk_cap_for_fit("UNAVAILABLE")
    assert unavailable_cap > 0.0
    assert unavailable_cap < risk_cap_for_fit("GOOD")


def test_target_mid_is_min_conviction_and_risk_cap():
    sizing = sizing_for(_signal(), fit="GOOD")
    assert sizing.conviction_tier == "HIGH_CONVICTION"
    assert sizing.target_mid == min(conviction_mid("HIGH_CONVICTION"), 0.20)

    sizing_weak = sizing_for(_signal(), fit="WEAK")
    assert sizing_weak.target_mid == pytest.approx(min(0.15, 0.05))
    assert sizing_weak.target_max == pytest.approx(0.05)


def test_missing_risk_history_adds_data_insufficient_reason():
    sizing = sizing_for(_signal(), fit="UNAVAILABLE")
    assert "DATA_INSUFFICIENT" in sizing.reason_codes
    assert sizing.risk_cap < DEFAULT_HARD_CAP


def test_weak_fit_marks_risk_contribution_high():
    sizing = sizing_for(_signal(), fit="WEAK")
    assert "RISK_CONTRIBUTION_HIGH" in sizing.reason_codes


def test_hard_cap_is_clamped():
    assert sizing_for(_signal(), hard_cap=0.99).risk_cap <= MAX_HARD_CAP
    assert sizing_for(_signal(), fit="GOOD", hard_cap=0.01).risk_cap >= 0.05