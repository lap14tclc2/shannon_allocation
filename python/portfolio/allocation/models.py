"""Allocation domain contracts (immutable result models).

These are pure data contracts. Business logic lives in the sibling modules
(eligibility, candidate_service, sizing, opportunity, service).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Literal membership is validated at the enum level in the engine; the result
# models keep the exact canonical strings for stable serialization.
ELIGIBILITY_STATUSES = ("INVESTABLE", "WATCHLIST", "INELIGIBLE")
ACTIONS = ("BUY_MORE", "HOLD", "WATCH", "REDUCE", "SELL", "KEEP_CASH")
CONFIDENCE_LEVELS = ("HIGH", "MEDIUM", "LOW")
FIT_LEVELS = ("GOOD", "MODERATE", "WEAK", "UNAVAILABLE")
CONVICTION_TIERS = ("STARTER", "NORMAL", "HIGH_CONVICTION")
OPPORTUNITY_KINDS = ("HOLDING", "CANDIDATE")

# Advisory ordering used by the UI (not an execution order).
ACTION_ORDER: tuple[str, ...] = ACTIONS


def _as_dict(obj: Any) -> dict[str, Any]:
    return asdict(obj)


def _json_safe(value: Any) -> Any:
    """Convert tuples to lists for stable JSON serialization."""
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


@dataclass(frozen=True)
class EligibilityResult:
    """Buffett eligibility derived from canonical value-engine outputs.

    ``valuation_safety = actual_mos_pct - required_mos_pct`` keeps Valuation
    distinct from Quality (no double counting).
    """

    symbol: str
    status: str
    hard_rejects: tuple[str, ...] = ()
    quality_tier: str | None = None
    quality_score: int | None = None
    valuation_status: str | None = None
    valuation_confidence: str | None = None
    valuation_safety: float | None = None
    actual_mos_pct: float | None = None
    required_mos_pct: float | None = None
    reason_codes: tuple[str, ...] = ()
    data_quality: str = "OK"

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(_as_dict(self))


@dataclass(frozen=True)
class PortfolioFitResult:
    """Before/after portfolio-risk comparison for a hypothetical position change.

    Computed exclusively by calling the canonical ``portfolio.risk.portfolio_risk``
    engine on cloned position rows. Missing risk history yields ``UNAVAILABLE``
    fit, never fabricated zero risk.
    """

    symbol: str
    current_weight: float
    proposed_weight: float
    portfolio_vol_before: float | None = None
    portfolio_vol_after: float | None = None
    risk_contribution_before: float | None = None
    risk_contribution_after: float | None = None
    diversification_ratio_before: float | None = None
    diversification_ratio_after: float | None = None
    average_correlation_to_portfolio: float | None = None
    max_correlation_to_portfolio: float | None = None
    hhi_after: float | None = None
    effective_positions_after: float | None = None
    risk_available: bool = True
    fit: str = "UNAVAILABLE"

    def to_dict(self) -> dict[str, Any]:
        return _as_dict(self)


@dataclass(frozen=True)
class SizingResult:
    """Conservative allocation band for a security (governance defaults, not Kelly).

    Band reference (V1 governance defaults):
      starter        3-5%
      normal         7-12%
      high conviction 12-18%
      hard cap       configurable, default 20%
    ``target_mid`` follows ``min(conviction_weight, risk_cap)``.
    """

    symbol: str
    conviction_tier: str = "STARTER"
    target_min: float = 0.03
    target_mid: float = 0.04
    target_max: float = 0.05
    risk_cap: float = 0.20
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _as_dict(self)


def validate_decision_semantics(decision: AllocationDecision) -> bool:
    """Validate decision semantics and invariants.

    Invariants:
    1. REDUCE: target_mid MUST NOT be 0. If target_mid is provided, 0 < target_mid < current_weight (when current_weight > 0).
    2. SELL: target_mid MUST be 0.0, target_min == 0.0, target_max == 0.0.
    3. BUY_MORE: target_mid MUST be > 0.0.
    """
    action = decision.action
    mid = decision.target_mid
    weight = max(0.0, float(decision.current_weight or 0.0))

    if action == "REDUCE":
        if mid is not None and mid <= 0:
            raise ValueError(f"REDUCE decision for {decision.symbol} cannot target <= 0%: target_mid={mid}")
        if mid is not None and weight > 0 and round(mid, 6) >= round(weight, 6):
            raise ValueError(f"REDUCE decision for {decision.symbol} target ({mid}) must be less than current weight ({weight})")

    elif action == "SELL":
        if mid is not None and mid != 0.0:
            raise ValueError(f"SELL decision for {decision.symbol} must target 0%, got {mid}")
        if decision.target_min is not None and decision.target_min != 0.0:
            raise ValueError(f"SELL decision for {decision.symbol} target_min must be 0%, got {decision.target_min}")
        if decision.target_max is not None and decision.target_max != 0.0:
            raise ValueError(f"SELL decision for {decision.symbol} target_max must be 0%, got {decision.target_max}")

    elif action == "BUY_MORE":
        if mid is not None and mid <= 0:
            raise ValueError(f"BUY_MORE decision for {decision.symbol} must have positive target_mid, got {mid}")

    return True


@dataclass(frozen=True)
class AllocationExecutionPlan:
    """Executable advisory share-quantity plan for a single decision.

    NOT an automated trade order. Information and simulation only.
    Reconciles three dimensions together: %, VND money amount, and share quantity.
    """

    symbol: str
    action: str

    current_quantity: float = 0.0
    current_market_value_vnd: float = 0.0
    current_weight: float = 0.0

    target_weight_theoretical: float | None = None
    target_weight_min: float | None = None
    target_weight_max: float | None = None
    target_weight_band_min: float | None = None
    target_weight_band_max: float | None = None
    target_value_vnd: float | None = None

    reference_price: float | None = None
    reference_price_date: str | None = None
    reference_price_source: str | None = None
    price_date: str | None = None
    price_source: str | None = None

    raw_quantity_change: float = 0.0
    rounded_quantity_change: float = 0.0
    lot_size: int = 100

    gross_trade_value: float = 0.0
    gross_trade_value_vnd: float = 0.0
    estimated_fee: float = 0.0
    estimated_fee_vnd: float = 0.0
    estimated_tax: float = 0.0
    estimated_tax_vnd: float = 0.0
    estimated_slippage: float = 0.0
    estimated_slippage_vnd: float = 0.0
    estimated_total_cost: float = 0.0
    estimated_total_cost_vnd: float = 0.0
    net_cash_change_vnd: float = 0.0

    cash_before: float = 0.0
    cash_before_vnd: float = 0.0
    cash_after: float = 0.0
    cash_after_vnd: float = 0.0

    post_trade_quantity: float = 0.0
    post_trade_market_value: float = 0.0
    post_trade_market_value_vnd: float = 0.0
    post_trade_weight: float = 0.0

    target_error_pp: float | None = None
    within_target_band: bool = True

    risk_before: dict[str, Any] | None = None
    risk_after: dict[str, Any] | None = None

    is_executable: bool = True
    blocking_reasons: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(_as_dict(self))


@dataclass(frozen=True)
class AllocationDecision:
    """A single advisory decision for a holding or a candidate.

    ``action`` is recommendation-only and never executes a trade.
    """

    symbol: str
    action: str
    kind: str = "HOLDING"
    current_weight: float = 0.0
    target_min: float | None = None
    target_mid: float | None = None
    target_max: float | None = None
    confidence: str = "LOW"
    reason_codes: tuple[str, ...] = ()
    # Transparent decision evidence: separate dimensions only (quality tier,
    # valuation safety pp, portfolio fit, technical confirmation). NEVER a
    # composite weighted score.
    bands: dict[str, Any] = field(default_factory=dict)
    execution_plan: AllocationExecutionPlan | None = None

    def __post_init__(self) -> None:
        validate_decision_semantics(self)

    def to_dict(self) -> dict[str, Any]:
        payload = _as_dict(self)
        payload["execution_plan"] = self.execution_plan.to_dict() if self.execution_plan else None
        return _json_safe(payload)


@dataclass(frozen=True)
class CandidateOpportunity:
    """A screener-discovered research candidate, classified into explicit candidate tiers."""

    symbol: str
    source: str
    eligibility: EligibilityResult
    candidate_tier: str = "BUY_READY"
    candidate_rank: int = 0
    portfolio_fit: PortfolioFitResult | None = None
    sizing: SizingResult | None = None
    # Research-discovery ordering score only. It ranks candidates for the
    # shortlist and is NEVER used to determine BUY/HOLD/REDUCE/SELL.
    discovery_score: float | None = None
    reason_codes: tuple[str, ...] = ()
    failed_gates: tuple[str, ...] = ()
    watch_reasons: tuple[str, ...] = ()
    max_qualifying_price: float | None = None
    max_qualifying_price_vnd: float | None = None
    decision: AllocationDecision | None = None
    selection_evidence: dict[str, Any] = field(default_factory=dict)
    gate_evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = _as_dict(self)
        payload["eligibility"] = self.eligibility.to_dict() if self.eligibility else None
        payload["portfolio_fit"] = self.portfolio_fit.to_dict() if self.portfolio_fit else None
        payload["sizing"] = self.sizing.to_dict() if self.sizing else None
        payload["decision"] = self.decision.to_dict() if self.decision else None
        return _json_safe(payload)


@dataclass(frozen=True)
class PortfolioAllocationReport:
    """Full advisory portfolio allocation evaluation."""

    portfolio_id: int | None = None
    as_of: str | None = None
    verdict: str = "HOLD"
    posture: str = "HOLD_SELECTIVE_BUY"
    cash_current: float | None = None
    cash_suggested_range: tuple[float, float] | None = None
    no_action_required: bool = True
    holdings: tuple[AllocationDecision, ...] = ()
    opportunities: tuple[CandidateOpportunity, ...] = ()
    watchlist: tuple[CandidateOpportunity, ...] = ()
    rejected: tuple[CandidateOpportunity, ...] = ()
    buy_ready_count: int = 0
    watchlist_count: int = 0
    rejected_count: int = 0
    universe_count: int = 0
    risk_summary: dict[str, Any] = field(default_factory=dict)
    data_quality: dict[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    confidence: str = "LOW"
    simulation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = _as_dict(self)
        payload["holdings"] = [h.to_dict() for h in self.holdings]
        payload["opportunities"] = [o.to_dict() for o in self.opportunities]
        payload["watchlist"] = [o.to_dict() for o in self.watchlist]
        payload["rejected"] = [o.to_dict() for o in self.rejected]
        payload["cash_suggested_range"] = (
            list(self.cash_suggested_range) if self.cash_suggested_range is not None else None
        )
        return _json_safe(payload)