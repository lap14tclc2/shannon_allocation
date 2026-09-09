"""Domain models for Buffett-Munger policy decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class InvestmentDecisionContext:
    """Canonical aggregate representing all evidence needed to make a Buffett-Munger decision."""

    symbol: str

    # Holding / Position Context
    current_weight: float = 0.0
    current_market_value: float = 0.0
    cost_basis: float | None = None
    shares_held: float = 0.0

    # Business Analysis Dimensions (PASS, WATCH, FAIL, UNKNOWN, NOT_APPLICABLE)
    circle_of_competence: str = "UNKNOWN"
    quality_score: float | None = None
    quality_tier: str | None = None
    accounting_reliability: str = "UNKNOWN"
    financial_strength: str = "UNKNOWN"
    earnings_durability: str = "UNKNOWN"
    capital_allocation_quality: str = "UNKNOWN"
    moat_assessment: str = "UNKNOWN"

    # Valuation & MOS Context
    current_price: float = 0.0
    bear_iv: float | None = None
    base_iv: float | None = None
    bull_iv: float | None = None
    required_mos: float | None = None
    actual_mos: float | None = None
    valuation_confidence: str = "UNKNOWN"
    model_status: str = "INVALID"

    # Personal Balance Sheet / Fortress Context
    survival_reserve_status: str = "UNKNOWN"
    available_long_term_capital: float = 0.0
    near_term_liability_status: str = "UNKNOWN"

    # Workstream Status Summaries
    business_review_status: str = "UNKNOWN"
    value_trap_status: str = "INSUFFICIENT_DATA"

    # Evidence Lists
    hard_rejects: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Diagnostic Data Status
    data_readiness: dict[str, str] = field(default_factory=dict)

    as_of: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InvestmentDecisionContext:
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
