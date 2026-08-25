"""
QPort Value Engine Data Contracts & Models (QVE-051, QVE-170, QVE-180).

Immutable structures for Owner Earnings bridges, valuation models, sensitivity matrices,
and audit-grade reproducible Valuation Reports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class ValuationModelType(str, Enum):
    OWNER_EARNINGS_DCF = "OWNER_EARNINGS_DCF"
    EARNINGS_POWER_VALUE = "EARNINGS_POWER_VALUE"
    REVERSE_DCF = "REVERSE_DCF"
    DIVIDEND_DISCOUNT = "DIVIDEND_DISCOUNT"
    RESIDUAL_INCOME = "RESIDUAL_INCOME"
    JUSTIFIED_PB = "JUSTIFIED_PB"


class ScenarioType(str, Enum):
    BEAR = "BEAR"
    BASE = "BASE"
    BULL = "BULL"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    BLOCKED = "BLOCKED"


@dataclass
class OwnerEarningsBridge:
    net_income: Decimal
    depreciation_amortization: Decimal
    maintenance_capex: Decimal
    growth_capex_estimated: Decimal
    working_capital_change: Decimal
    owner_earnings: Decimal
    formula_description: str
    source_fact_ids: List[str] = field(default_factory=list)


@dataclass
class ValuationScenario:
    scenario_type: ScenarioType
    discount_rate: Decimal  # e.g. 0.11 for 11%
    growth_stage1_rate: Decimal  # e.g. 0.15 for 15%
    growth_stage1_years: int  # e.g. 5
    terminal_growth_rate: Decimal  # e.g. 0.035 for 3.5%
    projected_cash_flows: List[Decimal]
    terminal_value: Decimal
    enterprise_value: Decimal
    net_debt: Decimal
    equity_value: Decimal
    intrinsic_value_per_share: Decimal
    margin_of_safety_pct: Optional[Decimal] = None


@dataclass
class EPVResult:
    normalized_operating_earnings: Decimal
    tax_rate: Decimal
    nopat: Decimal
    cost_of_capital: Decimal
    reproduction_cost_assets: Optional[Decimal]
    epv_enterprise_value: Decimal
    net_debt: Decimal
    epv_equity_value: Decimal
    epv_per_share: Decimal
    margin_of_safety_pct: Optional[Decimal] = None


@dataclass
class ReverseDCFResult:
    current_market_price: Decimal
    implied_stage1_growth_rate: Decimal  # Growth % implied by market
    discount_rate_used: Decimal
    terminal_growth_used: Decimal
    verdict: str  # e.g., "Market prices aggressive growth (22.5%)"


@dataclass
class SensitivityMatrix:
    discount_rates: List[Decimal]  # Column headers
    terminal_growth_rates: List[Decimal]  # Row headers
    grid_values_per_share: List[List[Decimal]]  # 2D Grid of intrinsic values


@dataclass
class ValuationReport:
    report_id: str
    symbol: str
    valuation_date: str
    fiscal_period_latest: str
    currency: str
    current_market_price: Decimal
    shares_outstanding: Decimal
    diluted_shares_estimate: Decimal
    confidence_level: ConfidenceLevel
    confidence_reasons: List[str]
    owner_earnings_bridge: OwnerEarningsBridge
    scenarios: Dict[ScenarioType, ValuationScenario]
    epv_result: Optional[EPVResult]
    reverse_dcf_result: Optional[ReverseDCFResult]
    sensitivity_matrix: Optional[SensitivityMatrix]
    source_fact_ids: List[str]
    engine_version: str
    computed_at: str
