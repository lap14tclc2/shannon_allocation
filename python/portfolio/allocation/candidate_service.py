"""Screener candidate adapter.

Shortlists 3-5 strongest research candidates from existing Screener results.
Candidates are research opportunities only — never final BUY actions. The
decision engine (opportunity.py) decides whether a candidate is actionable.

Flow:
    screener items
      -> liquidity filter
      -> exclude current holdings
      -> Buffett eligibility adapter
      -> opportunity-score ranking
      -> shortlist (configurable max, default 5)
"""
from __future__ import annotations

from .eligibility import eligibility_from_signal, signal_from_screener_item
from .models import CandidateOpportunity, EligibilityResult
from .reason_codes import LIQUIDITY_INSUFFICIENT

DEFAULT_MAX_CANDIDATES = 5
DEFAULT_MIN_LIQUIDITY = 10.0  # billion VND/day


def _valuation_safety_band(safety: float | None) -> float:
    """Map valuation_safety (pp) to a 0..1 band, distinct from Quality."""
    if safety is None:
        return 0.0
    if safety >= 10.0:
        return 1.0
    if safety >= 0.0:
        return 0.6
    if safety >= -10.0:
        return 0.3
    return 0.0


def candidate_opportunity_score(signal: dict) -> float:
    """Transparent candidate-discovery ordering score (quality + valuation only).

    This ranks research candidates for the shortlist ONLY. It is explicitly NOT
    a decision input: BUY/HOLD/REDUCE/SELL are decided by explicit gates in
    ``opportunity.py`` (no unvalidated composite score in V1).
    """
    quality = signal.get("quality_score")
    quality_norm = (float(quality) / 100.0) if quality is not None else 0.0
    actual_mos = signal.get("actual_mos_pct")
    required_mos = signal.get("required_mos_pct")
    safety = None
    if actual_mos is not None and required_mos is not None:
        safety = float(actual_mos) - float(required_mos)
    return round(0.5 * quality_norm + 0.5 * _valuation_safety_band(safety), 4)


def shortlist_candidates(
    items: list[dict],
    *,
    exclude_symbols: set[str] | None = None,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    min_liquidity: float = DEFAULT_MIN_LIQUIDITY,
) -> tuple[list[CandidateOpportunity], list[dict]]:
    """Return (shortlisted candidates, rejected/reason diagnostics).

    ``items`` are canonical screener result rows (dependency-injected so the
    adapter is testable without a live finance DB).
    """
    exclude = {str(s).upper() for s in (exclude_symbols or [])}
    max_candidates = max(1, int(max_candidates))
    min_liquidity = max(0.0, float(min_liquidity))

    candidates: list[dict] = []
    diagnostics: list[dict] = []
    seen: set[str] = set()

    for item in items:
        symbol = str(item.get("symbol") or "").upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        if symbol in exclude:
            diagnostics.append({"symbol": symbol, "code": "EXCLUDED_HOLDING"})
            continue
        liquidity = float(item.get("avg_turnover_20d_billion") or 0.0)
        if liquidity < min_liquidity:
            diagnostics.append({
                "symbol": symbol, "code": "LIQUIDITY_INSUFFICIENT",
                "liquidity": liquidity, "min_liquidity": min_liquidity,
            })
            continue
        signal = signal_from_screener_item(item)
        eligibility = eligibility_from_signal(signal)
        if eligibility.status != "INVESTABLE":
            diagnostics.append({
                "symbol": symbol, "code": "NOT_INVESTABLE",
                "status": eligibility.status, "reason_codes": list(eligibility.reason_codes),
            })
            continue
        candidates.append({"item": item, "signal": signal, "eligibility": eligibility})

    candidates.sort(key=lambda c: candidate_opportunity_score(c["signal"]), reverse=True)
    shortlist = candidates[:max_candidates]

    opportunities: list[CandidateOpportunity] = []
    for index, entry in enumerate(shortlist, start=1):
        eligibility: EligibilityResult = entry["eligibility"]
        reasons = list(eligibility.reason_codes)
        opportunities.append(CandidateOpportunity(
            symbol=eligibility.symbol,
            source="SCREENER",
            eligibility=eligibility,
            candidate_rank=index,
            discovery_score=candidate_opportunity_score(entry["signal"]),
            reason_codes=tuple(dict.fromkeys(reasons)),
        ))
    return opportunities, diagnostics