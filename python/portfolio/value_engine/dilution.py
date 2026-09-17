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
NON_ECONOMIC_ACTION_TYPES = (
    "STOCK_DIVIDEND",
    "BONUS_SHARE",
    "BONUS_SHARES",
    "STOCK_SPLIT",
    "REVERSE_SPLIT",
    "SPLIT",
)

# Economic-dilution action types (capital raising / value transfer to new holders).
ECONOMIC_ACTION_TYPES = (
    "RIGHTS_ISSUE",
    "NEW_SHARE_ISSUANCE",
    "STOCK_ISSUE",
    "ESOP",
    "MA_SHARE_ISSUANCE",
    "MA_ISSUANCE",
    "CONVERTIBLE",
    "OTHER_DILUTION",
)


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
        economic_events: capital-raising events that may transfer economic value
            out of existing shareholders. A dict may carry:
              - ``action_type`` (RIGHTS_ISSUE / STOCK_ISSUE / ESOP / CONVERTIBLE ...)
              - ``stock_ratio`` (shares issued as a decimal fraction of existing shares)
              - ``shares_issued`` (absolute shares issued)
              - ``issue_price`` and ``fair_value`` / ``market_price`` (for the
                value-transfer estimate ValueTransfer = SharesIssued * max(FV-IP, 0))
        excess_threshold_pct: economic dilution above this pct is EXCESSIVE.

    Returns a breakdown dict with ``raw_share_change_pct``,
    ``non_economic_share_change_pct``, ``economic_dilution_pct`` (residual),
    ``confirmed_economic_dilution_pct`` (capped by event value-transfer evidence),
    ``unexplained_share_change_pct`` (residual minus confirmed), ``classification``,
    and the event lists.
    """
    shares_old = float(shares_old or 0)
    shares_new = float(shares_new or 0)
    if shares_old <= 0:
        return {
            "raw_share_change_pct": None,
            "non_economic_share_change_pct": None,
            "economic_dilution_pct": None,
            "confirmed_economic_dilution_pct": None,
            "unexplained_share_change_pct": None,
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
    residual_pct = max(0.0, ((shares_new - expected_shares) / shares_old) * 100.0)
    non_economic_share_change_pct = (expected_shares - shares_old) / shares_old * 100.0

    # P1 audit (2026-08-29): confirmed economic dilution is capped by the economic
    # value transfer implied by ACTUAL events, never the whole residual.
    #   ValueTransfer_pct = sum(SharesIssued_pct_i * max(FairValue_i - IssuePrice_i, 0) / FairValue_i)
    # When prices are unavailable, confirmed is capped at the total shares issued by
    # economic events (sum of stock_ratio), which is a strict upper bound on the
    # share count those events explain.
    confirmed_economic_pct = _confirmed_dilution_from_events(
        economic_events=economic_events,
        shares_old=shares_old,
        residual_pct=residual_pct,
    )
    unexplained_pct = max(0.0, residual_pct - confirmed_economic_pct)

    # Classification. P0 audit (2026-08-29): a residual, unexplained share increase
    # is NOT proven economic dilution. Without actual ESOP / rights issue / private
    # placement / convertible / M&A share evidence, the classifier must return
    # UNEXPLAINED_SHARE_CHANGE (confidence LOW, requires verification) and must
    # NOT feed EXCESSIVE_DILUTION.
    if confirmed_economic_pct >= excess_threshold_pct:
        classification = "EXCESSIVE_DILUTION"
    elif confirmed_economic_pct >= 5.0:
        classification = "ECONOMIC_DILUTION"
    elif economic_events and confirmed_economic_pct >= 0.5:
        classification = "ECONOMIC_DILUTION_MINOR"
    elif unexplained_pct >= excess_threshold_pct:
        classification = "UNEXPLAINED_SHARE_CHANGE"
    elif non_economic_share_change_pct > 1.0 and residual_pct < 5.0:
        classification = "NON_ECONOMIC_SHARE_CHANGE"
    else:
        classification = "NO_MATERIAL_CHANGE"

    # P1 audit (2026-08-29): only the confirmed (event-evidence) amount is carried as
    # confirmed economic dilution. The unexplained residual is surfaced separately so
    # the quality/capital-allocation scoring never penalises as if proven. When a
    # classification is confirmed (EXCESSIVE/ECONOMIC/MINOR) the remaining residual
    # above the confirmed amount is still reported as unexplained for transparency.
    if confirmed_economic_pct is not None and confirmed_economic_pct > 0.5:
        confirmed_economic = confirmed_economic_pct
    else:
        confirmed_economic = None
    unexplained = unexplained_pct if unexplained_pct > 0.5 else None

    return {
        "raw_share_change_pct": round(raw_share_change_pct, 1),
        "non_economic_share_change_pct": round(non_economic_share_change_pct, 1),
        # Feedback 03:56 (P1): `economic_dilution_pct` KHÔNG được mang giá trị
        # residual chưa xác nhận (94.8% unexplained). Rename residual ->
        # `residual_share_change_pct`; `economic_dilution_pct` chỉ mang phần đã
        # xác nhận (null khi UNEXPLAINED / NON_ECONOMIC).
        "residual_share_change_pct": round(residual_pct, 1),
        "economic_dilution_pct": round(confirmed_economic, 1) if confirmed_economic is not None else None,
        "confirmed_economic_dilution_pct": round(confirmed_economic, 1) if confirmed_economic is not None else None,
        "unexplained_share_change_pct": round(unexplained, 1) if unexplained is not None else None,
        "classification": classification,
        "excess_threshold_pct": excess_threshold_pct,
        "expected_shares_from_non_economic": round(expected_shares, 2),
        "non_economic_events": non_economic_events,
        "economic_events": economic_events,
    }


def _confirmed_dilution_from_events(
    *,
    economic_events: List[Dict[str, Any]],
    shares_old: float,
    residual_pct: float,
) -> float:
    """Confirmed economic dilution (in % of the old share base) from event evidence.

    For each economic event:
      - shares_issued_pct = stock_ratio (decimal) OR shares_issued / shares_old.
      - If issue_price and fair_value are present, the value-transfer fraction is
        max(FV - IP, 0) / FV, so a near-fair issuance contributes ~0.
      - Without prices, the event can only confirm the share count it actually
        issued (stock_ratio) - never the whole residual.

    The confirmed amount is the min(residual, sum of event value-transfer %).
    """
    if not economic_events:
        return 0.0
    total_confirmed = 0.0
    for event in economic_events:
        ratio = event.get("stock_ratio")
        shares_issued = event.get("shares_issued")
        try:
            ratio_f = float(ratio) if ratio not in (None, "") else None
        except (TypeError, ValueError):
            ratio_f = None
        try:
            shares_issued_f = float(shares_issued) if shares_issued not in (None, "") else None
        except (TypeError, ValueError):
            shares_issued_f = None
        shares_pct = None
        if ratio_f is not None and ratio_f > 0:
            shares_pct = ratio_f
        elif shares_issued_f is not None and shares_old > 0:
            shares_pct = shares_issued_f / shares_old

        issue_price = _number(event.get("issue_price"))
        fair_value = _number(event.get("fair_value")) or _number(event.get("market_price"))
        if shares_pct is None:
            continue
        if issue_price is not None and fair_value is not None and fair_value > 0:
            transfer_frac = max(0.0, (fair_value - issue_price) / fair_value)
        else:
            transfer_frac = 1.0
        total_confirmed += shares_pct * transfer_frac * 100.0
    return min(residual_pct, max(0.0, total_confirmed))


def _number(value) -> Optional[float]:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None