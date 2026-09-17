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
    AVOID_SOLVENCY = "AVOID_SOLVENCY"               # Giá trị nội tại âm / mất khả năng thanh toán
    UNVALUABLE = "UNVALUABLE"                       # Nằm ngoài vòng tròn năng lực, không thể chuẩn hóa dòng tiền
    DEEP_VALUE = "DEEP_VALUE"                       # Legacy compatible alias
    UNDERVALUED = "UNDERVALUED"                     # Legacy compatible alias
    OVERVALUED = "OVERVALUED"                       # Legacy compatible alias
    GROWTH_PRICED_IN = "GROWTH_PRICED_IN"           # Legacy compatible alias
    MODEL_INCOMPLETE = "MODEL_INCOMPLETE"           # Thiếu dữ liệu mô hình đặc thù
    MODEL_PENDING = "MODEL_PENDING"                 # Đang hoàn thiện mô hình
    ARCHETYPE_UNSUPPORTED = "ARCHETYPE_UNSUPPORTED" # Chưa xác định được mô hình định giá phù hợp
    FALLBACK_MODEL_ONLY = "FALLBACK_MODEL_ONLY"     # Chỉ có mô hình định giá tham chiếu, chưa verified


class ModelStatus(str, Enum):
    MODEL_VERIFIED = "MODEL_VERIFIED"
    MODEL_INCOMPLETE = "MODEL_INCOMPLETE"
    MODEL_PARTIAL = "MODEL_PARTIAL"
    MODEL_ESTIMATED = "MODEL_ESTIMATED"
    MODEL_PENDING = "MODEL_PENDING"
    FALLBACK_MODEL = "FALLBACK_MODEL"
    FALLBACK_MODEL_ONLY = "FALLBACK_MODEL_ONLY"
    ARCHETYPE_UNKNOWN = "ARCHETYPE_UNKNOWN"
    ARCHETYPE_UNSUPPORTED = "ARCHETYPE_UNSUPPORTED"


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
    normalization_years: Optional[int] = None
    normalization_method: str = "LATEST_FY"  # LATEST_FY | POSITIVE_AVG | MID_CYCLE_MEDIAN
    mid_cycle_margin: Optional[Decimal] = None
    mid_cycle_revenue: Optional[Decimal] = None
    maintenance_capex_confidence: str = "MEDIUM"  # HIGH | MEDIUM | LOW
    owner_earnings_confidence: str = "MEDIUM"  # HIGH | MEDIUM | LOW
    maintenance_capex_method: str = "MIN_DEPRECIATION_CAPEX_PROXY"  # EXPLICIT_PPE_ROLLFORWARD | MIN_DEPRECIATION_CAPEX_PROXY
    current_owner_earnings: Optional[Decimal] = None
    normalized_owner_earnings: Optional[Decimal] = None
    normalization_input_years: List[int] = field(default_factory=list)


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
    terminal_value_contribution_pct: Optional[Decimal] = None
    scenario_warnings: List[str] = field(default_factory=list)
    # Cash-flow basis invariant (audit 2026-08-29): NI-based Owner Earnings is
    # an equity cash flow (after interest) -> discount at Cost of Equity to get
    # Equity Value directly; FCFF -> WACC -> Enterprise Value -> subtract Net Debt.
    cashflow_basis: str = "NET_INCOME_OWNER_EARNINGS"  # NET_INCOME_OWNER_EARNINGS | FCFE | FCFF | RESIDUAL_INCOME | NAV_COMPONENTS
    discount_rate_basis: str = "COST_OF_EQUITY"  # COST_OF_EQUITY | WACC
    result_type: str = "EQUITY_VALUE"  # EQUITY_VALUE | ENTERPRISE_VALUE
    debt_adjustment_policy: str = "NO_NET_DEBT_ADJUSTMENT"  # NO_NET_DEBT_ADJUSTMENT | SUBTRACT_NET_DEBT
    # Present value of the discounted cash-flow stream (equity-cashflow DCFs).
    # For equity-basis models this IS the equity value; enterprise_value is kept
    # only for backward compatibility and equals equity_value there.
    present_value: Optional[Decimal] = None
    # RIM-specific semantic fields (feedback 31/08): the discounted residual
    # income stream and its terminal component, named semantically instead of
    # overloading ``enterprise_value`` (which is kept only for legacy compat).
    residual_income_pv: Optional[Decimal] = None
    terminal_residual_income_pv: Optional[Decimal] = None
    share_basis: Optional[Dict[str, Any]] = None


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
    sensitivity_type: str = "DCF"  # DCF | RIM_ROE_COE
    col_label: str = "Tỷ lệ chiết khấu (r)"
    row_label: str = "Tăng trưởng dài hạn (g)"


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
    owner_earnings_bridge: Optional[OwnerEarningsBridge]
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
    growth_derivation: Optional[Dict[str, Any]] = None
    base_iv: Optional[Decimal] = None
    margin_of_safety_pct: Optional[Decimal] = None
    valuation_pill: Optional[str] = None
    verdict: Optional[str] = None
    sector_conflict_warning: Optional[str] = None
    model_status: str = "MODEL_VERIFIED"
    sotp_breakdown: Optional[Dict[str, Any]] = None
    rnav_breakdown: Optional[Dict[str, Any]] = None
    kcn_lease_parameters: Optional[Dict[str, Any]] = None
    holding_cash_quality: Optional[Dict[str, Any]] = None
    sotp_sensitivity_matrix: Optional[SensitivityMatrix] = None
    # When model_status != MODEL_VERIFIED, public base_iv / margin_of_safety_pct
    # are nulled and the computed numbers move here for audit/debug only.
    fallback_valuation: Optional[Dict[str, Any]] = None
    # Public surface (audit TASK-065/068): exposed IV/MOS only when the model is
    # VERIFIED. Non-verified models keep the numbers in ``diagnostic_fallback``.
    public_base_iv: Optional[Decimal] = None
    public_bear_iv: Optional[Decimal] = None
    public_bull_iv: Optional[Decimal] = None
    public_mos: Optional[Decimal] = None
    public_epv: Optional[Decimal] = None
    diagnostic_fallback: Optional[Dict[str, Any]] = None
    # Cảnh báo định giá (feedback 31/08): cổ phiếu không đạt chuẩn Buffett/Munger
    # (hard reject hoặc điểm chất lượng quá thấp) KHÔNG công bố IV/MOS; lý do
    # được nêu trong trường này và hiển thị nổi bật trên UI.
    valuation_warning: Optional[str] = None
    # Danh sách dữ liệu cần thiết để hoàn thiện mô hình định giá (tiếng Việt),
    # dùng cho các mã MODEL_INCOMPLETE / ARCHETYPE_UNSUPPORTED / FALLBACK...
    missing_data: List[str] = field(default_factory=list)
    # Cảnh báo dữ liệu lịch sử bất thường (user-test.md 31/08): revenue/LNST/CFO
    # nhảy bất thường giữa các năm -> nghi mapping/source error, cần đối soát nguồn.
    data_anomalies: List[Dict[str, Any]] = field(default_factory=list)
    # Canonical Share Basis metadata and provenance
    share_basis: Optional[Dict[str, Any]] = None
    valuation_snapshot: Optional[Dict[str, Any]] = None
    # feedback.txt — Numeric-Only Validation & Regime Engine:
    # - numeric_confidence: độ tin cậy SỐ LIỆU (HIGH/MEDIUM/LOW) sau khi resolve anomaly.
    # - cause_confidence: độ tin cậy về NGUYÊN NHÂN (TCBS-only -> luôn UNKNOWN).
    # - regime_analysis: các regime phát hiện (structural break split) + latest comparable.
    # - normalization_window: window thực dùng cho mid-cycle normalization.
    # - data_status (user-test.md §5): VALID / VALID_WITH_CLASSIFIED_EVENTS /
    #   SUSPICIOUS / CONFLICTED / INSUFFICIENT.
    # - regime_status (user-test.md §35): SINGLE_REGIME | SPLIT_REGIME.
    numeric_confidence: Optional[str] = None
    cause_confidence: Optional[str] = None
    data_status: Optional[str] = None
    regime_status: Optional[str] = None
    # feedback.txt §14 — UFVS validation confidence 0..100 + level.
    validation_confidence: Optional[int] = None
    validation_confidence_level: Optional[str] = None
    regime_analysis: List[Dict[str, Any]] = field(default_factory=list)
    normalization_window: Optional[Dict[str, Any]] = None
    source_fact_ids: List[str] = field(default_factory=list)
    engine_version: str = "1.0.0"
    computed_at: str = ""
