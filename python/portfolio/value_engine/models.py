"""
QPort Value Engine Data Contracts & Models (QVE-051, QVE-080, QVE-170, QVE-180).

Immutable structures for Business Quality Diagnostics, Buffett Qualitative Assessments,
Owner Earnings bridges, valuation models, sensitivity matrices, and Valuation Reports.
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


class MoatRating(str, Enum):
    WIDE = "WIDE"          # Lợi thế cạnh tranh bền vững sâu rộng
    NARROW = "NARROW"      # Có lợi thế cạnh tranh nhất định
    NONE = "NONE"          # Không có hào kinh tế rõ rệt


class ValuationPill(str, Enum):
    HIGH_CONVICTION_VALUE = "HIGH_CONVICTION_VALUE" # Doanh nghiệp tuyệt vời ở mức giá có biên an toàn lớn
    ATTRACTIVE = "ATTRACTIVE"                       # Thị giá dưới giá trị nội tại Base (đạt Required MOS)
    FAIRLY_VALUED = "FAIRLY_VALUED"                 # Thị giá nằm quanh vùng giá trị nội tại (-15% <= MoS <= 15%)
    FAIR_VALUE = "FAIR_VALUE"                       # Alias
    WATCH = "WATCH"                                 # Doanh nghiệp tốt nhưng giá chưa đủ biên an toàn
    AVOID_QUALITY = "AVOID_QUALITY"                 # Doanh nghiệp chất lượng thấp hoặc đòn bẩy rủi ro
    UNVALUABLE = "UNVALUABLE"                       # Nằm ngoài vòng tròn năng lực, không thể chuẩn hóa dòng tiền
    DEEP_VALUE = "DEEP_VALUE"                       # Legacy compatible alias
    UNDERVALUED = "UNDERVALUED"                     # Legacy compatible alias
    OVERVALUED = "OVERVALUED"                       # Legacy compatible alias
    GROWTH_PRICED_IN = "GROWTH_PRICED_IN"           # Legacy compatible alias


@dataclass
class ValueInvestingAssessment:
    """
    Buffett-Munger Qualitative & Diagnostic Evaluation (QVE-080, QVE-083, QVE-085, QVE-088).
    """
    moat_rating: MoatRating
    valuation_status: ValuationPill
    moat_summary: str
    capital_allocation_diagnosis: str
    earnings_quality_diagnosis: str
    financial_resilience_diagnosis: str
    valuation_verdict: str
    key_risks_and_invariants: List[str]


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
    verdict: str  # e.g., "Thị trường đang định giá tăng trưởng 22.5%"


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
    assessment: ValueInvestingAssessment
    owner_earnings_bridge: OwnerEarningsBridge
    scenarios: Dict[ScenarioType, ValuationScenario]
    epv_result: Optional[EPVResult]
    reverse_dcf_result: Optional[ReverseDCFResult]
    sensitivity_matrix: Optional[SensitivityMatrix]
    valuation_multiples: Optional[Dict[str, Any]] = None
    market_comparison: Optional[Dict[str, Any]] = None
    valuation_model: str = "OWNER_EARNINGS_DCF"
    archetype_profile: Optional[Dict[str, Any]] = None
    quality_scorecard: Optional[Dict[str, Any]] = None
    margin_of_safety_analysis: Optional[Dict[str, Any]] = None
    source_fact_ids: List[str] = field(default_factory=list)
    engine_version: str = "1.0.0"
    computed_at: str = ""
