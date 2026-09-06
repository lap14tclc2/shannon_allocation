"""QPort Allocation domain (Buffett Core + Thorp Overlay).

V1 scope: deterministic, conservative, read-only capital-allocation advice.

- Buffett Core decides WHAT is worth owning (eligibility from the canonical
  value engine, keeping Quality distinct from Valuation).
- Thorp Overlay decides HOW MUCH capital is exposed (sizing bands + risk cap
  driven by the canonical ``portfolio.risk.portfolio_risk`` engine).
- Opportunity-cost logic decides WHEN capital moves, defaulting to
  HOLD / KEEP_CASH.

No Kelly sizing, no numerical expected alpha, no auto-execution in V1.
"""
from .models import (
    ACTION_ORDER,
    AllocationDecision,
    CandidateOpportunity,
    EligibilityResult,
    PortfolioFitResult,
    PortfolioAllocationReport,
    SizingResult,
)
from .reason_codes import (
    CASH_PREFERRED,
    CORRELATION_HIGH,
    DATA_INSUFFICIENT,
    DIVERSIFICATION_IMPROVES,
    DIVERSIFICATION_WORSENS,
    HARD_REJECT,
    LIQUIDITY_INSUFFICIENT,
    NO_SUPERIOR_REPLACEMENT,
    PORTFOLIO_FIT_IMPROVES,
    PORTFOLIO_FIT_WEAK,
    POSITION_CONCENTRATED,
    QUALITY_DETERIORATING,
    QUALITY_STRONG,
    RISK_CONTRIBUTION_HIGH,
    SUPERIOR_REPLACEMENT_AVAILABLE,
    TECHNICAL_CONFIRMATION,
    TECHNICAL_DETERIORATION,
    VALUATION_ATTRACTIVE,
    VALUATION_CONFIDENCE_LOW,
    VALUATION_EXPENSIVE,
    VALUATION_FAIR,
    VALUATION_SAFETY_IMPROVES,
    VALUATION_SAFETY_INSUFFICIENT,
    VALUATION_SAFETY_NEGATIVE,
    VALUATION_SAFETY_POSITIVE,
    reason_code_vi,
)

__all__ = [
    "EligibilityResult",
    "PortfolioFitResult",
    "SizingResult",
    "AllocationDecision",
    "CandidateOpportunity",
    "PortfolioAllocationReport",
    "ACTION_ORDER",
    "reason_code_vi",
]