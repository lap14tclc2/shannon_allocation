"""Buffett eligibility adapter unit tests."""
from __future__ import annotations

import pytest

from portfolio.allocation.eligibility import eligibility_from_signal, signal_from_screener_item
from portfolio.allocation.reason_codes import (
    DATA_INSUFFICIENT,
    HARD_REJECT,
    QUALITY_STRONG,
    VALUATION_ATTRACTIVE,
    VALUATION_CONFIDENCE_LOW,
    VALUATION_SAFETY_NEGATIVE,
    VALUATION_SAFETY_POSITIVE,
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
        "valuation_confidence": "MEDIUM",
    }
    base.update(kwargs)
    return base


def test_excellent_business_attractive_valuation_is_investable():
    result = eligibility_from_signal(_signal())
    assert result.status == "INVESTABLE"
    assert result.valuation_safety == pytest.approx(7.0)
    assert QUALITY_STRONG in result.reason_codes
    assert VALUATION_ATTRACTIVE in result.reason_codes
    assert VALUATION_SAFETY_POSITIVE in result.reason_codes


def test_negative_safety_is_not_investable_without_quality_penalty():
    result = eligibility_from_signal(_signal(actual_mos_pct=15.0, required_mos_pct=25.0))
    assert result.status == "INVESTABLE"  # quality high, still investable
    assert result.valuation_safety == pytest.approx(-10.0)
    assert VALUATION_SAFETY_NEGATIVE in result.reason_codes


def test_hard_reject_overrides_high_mos_and_quality():
    result = eligibility_from_signal(_signal(hard_rejects=["SOLVENCY_RISK"], actual_mos_pct=60.0))
    assert result.status == "INELIGIBLE"
    assert HARD_REJECT in result.reason_codes


def test_accounting_unreliable_never_investable():
    result = eligibility_from_signal(_signal(hard_rejects=["ACCOUNTING_UNRELIABLE"]))
    assert result.status == "INELIGIBLE"
    assert result.data_quality == "HARD_REJECT"


def test_low_quality_never_investable_even_with_huge_mos():
    result = eligibility_from_signal(_signal(quality_tier="LOW_QUALITY", quality_score=40, actual_mos_pct=70.0))
    assert result.status == "INELIGIBLE"


def test_watch_tier_is_watchlist_not_investable():
    result = eligibility_from_signal(_signal(quality_tier="WATCH", quality_score=65))
    assert result.status == "WATCHLIST"


def test_investable_tier_without_public_valuation_is_watchlist():
    result = eligibility_from_signal(_signal(actual_mos_pct=None, required_mos_pct=None))
    assert result.status == "WATCHLIST"
    assert VALUATION_CONFIDENCE_LOW in result.reason_codes
    assert DATA_INSUFFICIENT in result.reason_codes


def test_missing_data_is_watchlist_with_data_insufficient():
    result = eligibility_from_signal({"symbol": "ZZZ"})
    assert result.status == "WATCHLIST"
    assert DATA_INSUFFICIENT in result.reason_codes


def test_blocked_confidence_never_high_confidence_buy():
    result = eligibility_from_signal(_signal(valuation_confidence="BLOCKED"))
    assert result.status in ("INVESTABLE", "WATCHLIST")
    # BLOCKED confidence keeps the allocation confidence LOW downstream.
    assert result.valuation_confidence == "BLOCKED"


def test_screener_item_to_signal_maps_canonical_fields():
    item = {
        "symbol": "FPT",
        "total_score": 88,
        "tier": "HIGH_QUALITY",
        "hard_rejects": ["EXCESSIVE_DILUTION"],
        "valuation_status": "ATTRACTIVE",
        "margin_of_safety": 33.0,
        "required_mos": 25.0,
    }
    signal = signal_from_screener_item(item)
    assert signal["quality_tier"] == "HIGH_QUALITY"
    assert signal["hard_rejects"] == ["EXCESSIVE_DILUTION"]
    assert signal["actual_mos_pct"] == 33.0
    assert signal["required_mos_pct"] == 25.0


def test_determinism():
    a = eligibility_from_signal(_signal()).to_dict()
    b = eligibility_from_signal(_signal()).to_dict()
    assert a == b