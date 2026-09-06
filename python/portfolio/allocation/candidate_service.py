"""Screener candidate adapter.

Shortlists 3-5 strongest research candidates from existing Screener results.
Candidates are research opportunities only — never final BUY actions. The
decision engine (opportunity.py) decides whether a candidate is actionable.

Pipeline:
    screener items
      -> security universe gate (common stock only, exclude warrants)
      -> 20D liquidity gate
      -> exclude current holdings
      -> Buffett eligibility gate
      -> valuation safety gate
      -> lexicographic candidate ordering
      -> selection evidence rationale
      -> shortlist (configurable max, default 5)
"""
from __future__ import annotations

from typing import Any

from .eligibility import eligibility_from_signal, signal_from_screener_item
from .models import CandidateOpportunity, EligibilityResult
from .reason_codes import LIQUIDITY_INSUFFICIENT

DEFAULT_MAX_CANDIDATES = 5
DEFAULT_MIN_LIQUIDITY = 10.0  # billion VND/day


def is_valid_equity_symbol(symbol: str) -> bool:
    """Validate that symbol is a common equity (exclude warrants, derivatives, index tickers)."""
    s = str(symbol or "").strip().upper()
    if not s or len(s) < 3 or len(s) > 6:
        return False
    # Covered warrants in VN market start with 'C' followed by broker code/numbers
    if len(s) > 3 and s.startswith("C") and any(ch.isdigit() for ch in s[1:]):
        return False
    # Exclude futures derivative tickers
    if any(suffix in s for suffix in ("F1M", "F2M", "F1Q", "F2Q")):
        return False
    return True


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


def build_selection_evidence(
    item: dict,
    signal: dict,
    eligibility: EligibilityResult,
    candidate_rank: int,
    min_liquidity: float = DEFAULT_MIN_LIQUIDITY,
    min_valuation_safety: float = 0.0,
) -> dict[str, Any]:
    """Build transparent candidate selection evidence explanation."""
    symbol = eligibility.symbol
    sec_type_pass = is_valid_equity_symbol(symbol)
    liquidity_20d = float(item.get("avg_turnover_20d_billion") or 0.0)
    liquidity_pass = (liquidity_20d >= min_liquidity)
    quality_tier = eligibility.quality_tier or "WATCH"
    quality_pass = (eligibility.status == "INVESTABLE")
    hard_rejects = list(eligibility.hard_rejects)
    actual_mos = eligibility.actual_mos_pct
    required_mos = eligibility.required_mos_pct
    valuation_safety = eligibility.valuation_safety
    valuation_pass = (valuation_safety is not None and valuation_safety >= min_valuation_safety)

    why_selected = []
    if sec_type_pass:
        why_selected.append("Cổ phiếu phổ thông niêm yết hợp lệ")
    if liquidity_pass:
        why_selected.append(f"Thanh khoản đạt {liquidity_20d:.1f} tỷ VND/ngày (ngưỡng tối thiểu {min_liquidity:.1f} tỷ)")
    else:
        why_selected.append(f"Thanh khoản {liquidity_20d:.1f} tỷ VND/ngày dưới ngưỡng {min_liquidity:.1f} tỷ")
    if quality_pass:
        why_selected.append(f"Chất lượng doanh nghiệp thuộc nhóm {quality_tier}")
    if valuation_safety is not None:
        if valuation_safety >= 0:
            why_selected.append(f"Biên an toàn {actual_mos:.1f}% vượt mức yêu cầu {required_mos:.1f}% (+{valuation_safety:.1f} điểm %)")
        else:
            why_selected.append(f"Biên an toàn {actual_mos:.1f}% thấp hơn mức yêu cầu {required_mos:.1f}% ({valuation_safety:.1f} điểm %)")

    return {
        "security_type_pass": sec_type_pass,
        "security_type": "COMMON_STOCK" if sec_type_pass else "UNSUPPORTED",
        "liquidity_20d_billion": liquidity_20d,
        "liquidity_threshold_billion": min_liquidity,
        "liquidity_pass": liquidity_pass,
        "quality_tier": quality_tier,
        "quality_pass": quality_pass,
        "hard_rejects": hard_rejects,
        "actual_mos_pct": actual_mos,
        "required_mos_pct": required_mos,
        "valuation_safety_pp": valuation_safety,
        "valuation_pass": valuation_pass,
        "candidate_rank": candidate_rank,
        "why_selected": why_selected,
    }


def _candidate_sort_key(c: dict) -> tuple:
    elig: EligibilityResult = c["eligibility"]
    item: dict = c["item"]
    investable_rank = 1 if elig.status == "INVESTABLE" else 0
    safety = elig.valuation_safety if elig.valuation_safety is not None else -999.0
    quality_score = elig.quality_score if elig.quality_score is not None else 0
    liquidity = float(item.get("avg_turnover_20d_billion") or 0.0)
    return (investable_rank, safety, quality_score, liquidity)


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
        if not is_valid_equity_symbol(symbol):
            diagnostics.append({"symbol": symbol, "code": "UNSUPPORTED_SECURITY_TYPE"})
            continue
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

    candidates.sort(key=_candidate_sort_key, reverse=True)
    shortlist = candidates[:max_candidates]

    opportunities: list[CandidateOpportunity] = []
    for index, entry in enumerate(shortlist, start=1):
        eligibility: EligibilityResult = entry["eligibility"]
        reasons = list(eligibility.reason_codes)
        evidence = build_selection_evidence(
            entry["item"],
            entry["signal"],
            eligibility,
            candidate_rank=index,
            min_liquidity=min_liquidity,
        )
        opportunities.append(CandidateOpportunity(
            symbol=eligibility.symbol,
            source="SCREENER",
            eligibility=eligibility,
            candidate_rank=index,
            discovery_score=candidate_opportunity_score(entry["signal"]),
            reason_codes=tuple(dict.fromkeys(reasons)),
            selection_evidence=evidence,
        ))
    return opportunities, diagnostics