"""
Economic Dilution Classifier (QVE-P0, audit 2026-08-29).

Separates NON_ECONOMIC_SHARE_CHANGE from ECONOMIC_DILUTION:

    NON_ECONOMIC_SHARE_CHANGE
      - stock dividend
      - bonus shares
      - stock split

    ECONOMIC_DILUTION
      - ESOP below fair value
      - rights issue with value transfer
      - new capital raising
      - convertibles
      - share-funded acquisition

Only the second group may feed ``EXCESSIVE_DILUTION``. A raw share-count
increase alone is never dilution; it must be measured against the expected
share count implied by all recorded non-economic share events.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Non-economic corporate action types that just multiply the existing share
# base (they do not transfer economic value out of existing shareholders).
NON_ECONOMIC_ACTION_TYPES = ("STOCK_DIVIDEND", "BONUS_SHARE", "SPLIT")

# Economic-dilution action types (capital raising / value transfer to new holders).
ECONOMIC_ACTION_TYPES = ("RIGHTS_ISSUE", "STOCK_ISSUE", "ESOP", "CONVERTIBLE")


def classify_share_change(
    *,
    shares_old: float,
    shares_new: float,
    non_economic_events: Optional[List[Dict[str, Any]]] = None,
    economic_events: Optional[List[Dict[str, Any]]] = None,
    excess_threshold_pct: float = 20.0,
) -> Dict[str, Any]:
    """Classify a 5Y share-count change into non-economic vs economic dilution.

    Args:
        shares_old: share count at the start of the window.
        shares_new: share count at the end of the window.
        non_economic_events: events with a ``stock_ratio`` that merely multiply
            the share base (stock dividend / bonus shares / split). Each event is
            a dict with at least ``action_type`` and ``stock_ratio`` (decimal, e.g.
            0.10 = +10%).
        economic_events: informational list of capital-raising events (not used to
            adjust the expected share base, but surfaced for the audit trail).
        excess_threshold_pct: economic dilution above this pct is EXCESSIVE.

    Returns a breakdown dict with ``raw_share_change_pct``,
    ``non_economic_share_change_pct``, ``economic_dilution_pct``,
    ``classification``, ``non_economic_events`` and ``economic_events``.
    """
    shares_old = float(shares_old or 0)
    shares_new = float(shares_new or 0)
    if shares_old <= 0:
        return {
            "raw_share_change_pct": None,
            "non_economic_share_change_pct": None,
            "economic_dilution_pct": None,
            "classification": "NO_BASE",
            "non_economic_events": [],
            "economic_events": [],
        }

    raw_share_change_pct = ((shares_new - shares_old) / shares_old) * 100.0

    non_economic_events = [dict(e) for e in (non_economic_events or [])]
    economic_events = [dict(e) for e in (economic_events or [])]

    # Expected share base after all non-economic multipliers.
    cumulative_multiplier = 1.0
    for event in non_economic_events:
        ratio = event.get("stock_ratio")
        try:
            ratio_f = float(ratio) if ratio not in (None, "") else None
        except (TypeError, ValueError):
            ratio_f = None
        if ratio_f is not None and ratio_f > 0:
            cumulative_multiplier *= (1.0 + ratio_f)

    expected_shares = shares_old * cumulative_multiplier
    economic_dilution_pct = max(0.0, ((shares_new - expected_shares) / shares_old) * 100.0)
    non_economic_share_change_pct = (expected_shares - shares_old) / shares_old * 100.0

    # Classification. P0 audit (2026-08-29): a residual, unexplained share increase
    # is NOT proven economic dilution. Without actual ESOP / rights issue / private
    # placement / convertible / M&A share evidence, the classifier must return
    # UNEXPLAINED_SHARE_CHANGE (confidence LOW, requires verification) and must
    # NOT feed EXCESSIVE_DILUTION.
    if economic_dilution_pct >= excess_threshold_pct and not economic_events:
        classification = "UNEXPLAINED_SHARE_CHANGE"
    elif economic_dilution_pct >= excess_threshold_pct and economic_events:
        classification = "EXCESSIVE_DILUTION"
    elif economic_dilution_pct >= 5.0 and economic_events:
        classification = "ECONOMIC_DILUTION"
    elif economic_events and economic_dilution_pct >= 0.5:
        classification = "ECONOMIC_DILUTION_MINOR"
    elif non_economic_share_change_pct > 1.0 and economic_dilution_pct < 5.0:
        classification = "NON_ECONOMIC_SHARE_CHANGE"
    else:
        classification = "NO_MATERIAL_CHANGE"

    return {
        "raw_share_change_pct": round(raw_share_change_pct, 1),
        "non_economic_share_change_pct": round(non_economic_share_change_pct, 1),
        "economic_dilution_pct": round(economic_dilution_pct, 1),
        "classification": classification,
        "excess_threshold_pct": excess_threshold_pct,
        "expected_shares_from_non_economic": round(expected_shares, 2),
        "non_economic_events": non_economic_events,
        "economic_events": economic_events,
    }