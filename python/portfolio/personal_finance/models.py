"""Models for Personal Balance Sheet & Capital Durability Domain."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PersonalBalanceSheetInput:
    """Inputs representing personal survival balance sheet facts."""

    monthly_net_income: float = 0.0
    monthly_essential_spending: float = 0.0
    monthly_discretionary_spending: float = 0.0

    safe_liquid_assets: float = 0.0  # Cash, savings deposits, short T-bills outside equity portfolio
    near_term_liabilities: float = 0.0  # Debt / commitments due in near_term_horizon_months
    near_term_horizon_months: int = 12

    consumer_debt: float = 0.0
    personal_debt: float = 0.0
    margin_debt: float = 0.0
    monthly_debt_service: float = 0.0

    lifecycle_stage: str = "EARNING_ACCUMULATION"  # EARNING_ACCUMULATION, MID_CAREER, PRE_RETIREMENT, RETIREMENT
    target_survival_months: float = 12.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PersonalBalanceSheetInput:
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class CapitalDurabilityMetrics:
    """Durability metrics derived from personal balance sheet and portfolio ledgers."""

    net_worth: float = 0.0
    investable_net_worth: float = 0.0
    survival_months: float = 0.0
    reserve_target_amount: float = 0.0
    survival_reserve_status: str = "UNKNOWN"  # SAFE, ATTENTION, UNSAFE, UNKNOWN

    opportunity_cash: float = 0.0
    available_long_term_capital: float = 0.0
    near_term_liability_status: str = "UNKNOWN"  # COVERED, UNCOVERED, UNKNOWN

    status: str = "UNKNOWN"  # SAFE, ATTENTION, UNSAFE, UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StressTestScenarioResult:
    """Outcome of crash / job-loss stress scenario."""

    scenario_name: str
    stressed_nav: float
    remaining_safe_assets: float
    survival_months: float
    forced_equity_sale_required: bool
    near_term_liability_covered: bool
    margin_call_possible: bool
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
