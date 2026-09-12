"""Canonical Data Models for Munger Financial Statement Analysis Engine (Task 136)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DimensionStatus(str, Enum):
    PASS = "PASS"
    WATCH = "WATCH"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DeteriorationClassification(str, Enum):
    NO_DETERIORATION = "NO_DETERIORATION"
    LIKELY_CYCLICAL = "LIKELY_CYCLICAL"
    POSSIBLY_CYCLICAL = "POSSIBLY_CYCLICAL"
    POSSIBLY_STRUCTURAL = "POSSIBLY_STRUCTURAL"
    STRUCTURAL = "STRUCTURAL"
    UNKNOWN = "UNKNOWN"


class CompounderClassification(str, Enum):
    COMPOUNDER = "COMPOUNDER"
    POTENTIAL_COMPOUNDER = "POTENTIAL_COMPOUNDER"
    AVERAGE_BUSINESS = "AVERAGE_BUSINESS"
    CYCLICAL_QUALITY = "CYCLICAL_QUALITY"
    WEAK_BUSINESS = "WEAK_BUSINESS"
    DETERIORATING_BUSINESS = "DETERIORATING_BUSINESS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class HistoryDepthClass(str, Enum):
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"  # <3Y
    LIMITED = "LIMITED"                            # 3-4Y
    USABLE = "USABLE"                              # 5-6Y
    STRONG = "STRONG"                              # 7-9Y
    DEEP_HISTORY = "DEEP_HISTORY"                  # 10Y+


@dataclass
class FinancialFinding:
    """Canonical forensic finding traceable to financial statement evidence."""

    code: str
    category: str  # ACCOUNTING, EARNINGS_QUALITY, CASH_FLOW, BALANCE_SHEET, DEBT, WORKING_CAPITAL, CAPITAL_ALLOCATION, DILUTION, PROFITABILITY, DURABILITY, STRUCTURAL_DETERIORATION, VALUATION
    severity: str  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    confidence: str  # HIGH, MEDIUM, LOW
    status: str  # PASS, WATCH, FAIL, UNKNOWN, NOT_APPLICABLE
    start_period: int
    end_period: int
    metrics: Dict[str, Any] = field(default_factory=dict)
    evidence_fact_ids: List[str] = field(default_factory=list)
    explanation: str = ""
    archetype: str = "NORMAL_ENTERPRISE"
    impact: str = ""

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        try:
            from .vietnamese_presenter import enrich_finding_dict
            return enrich_finding_dict(raw)
        except Exception:
            return raw


@dataclass
class FinancialDimensionResult:
    """Canonical result model for a single financial analysis dimension."""

    status: str  # PASS, WATCH, FAIL, UNKNOWN, NOT_APPLICABLE
    confidence: str  # HIGH, MEDIUM, LOW
    metrics: Dict[str, Any] = field(default_factory=dict)
    findings: List[FinancialFinding] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    missing_data: List[str] = field(default_factory=list)
    not_applicable: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["findings"] = [f.to_dict() if hasattr(f, "to_dict") else f for f in self.findings]
        return res


@dataclass
class FinancialBusinessAnalysis:
    """Comprehensive Munger-Style Financial Statement Analysis Output Payload."""

    symbol: str
    archetype: str  # NORMAL_ENTERPRISE, BANK, SECURITIES, etc.
    history_start: int
    history_end: int
    history_years: int
    history_depth: str  # INSUFFICIENT_HISTORY, LIMITED, USABLE, STRONG, DEEP_HISTORY
    data_readiness: str  # READY, PARTIAL, INSUFFICIENT
    provider: str  # ssi, tcbs

    # 12 Core Financial Dimensions
    growth_analysis: FinancialDimensionResult
    profitability_analysis: FinancialDimensionResult
    earnings_durability: FinancialDimensionResult
    earnings_quality: FinancialDimensionResult
    cash_flow_quality: FinancialDimensionResult
    balance_sheet_strength: FinancialDimensionResult
    debt_liquidity: FinancialDimensionResult
    capital_efficiency: FinancialDimensionResult
    capital_allocation: FinancialDimensionResult
    dilution_analysis: FinancialDimensionResult
    accounting_consistency: FinancialDimensionResult
    financial_forensics: FinancialDimensionResult

    # Derived Summaries & Forensic Outputs
    normalized_earning_power: Dict[str, Any] = field(default_factory=dict)
    structural_deterioration: Dict[str, Any] = field(default_factory=dict)
    cyclical_analysis: Dict[str, Any] = field(default_factory=dict)
    value_trap_assessment: Dict[str, Any] = field(default_factory=dict)
    valuation: Dict[str, Any] = field(default_factory=dict)
    long_term_decision: Dict[str, Any] = field(default_factory=dict)
    thesis_challenge: Dict[str, Any] = field(default_factory=dict)
    evidence_based_conclusion: Dict[str, Any] = field(default_factory=dict)

    compounder_classification: str = CompounderClassification.INSUFFICIENT_DATA.value
    overall_financial_quality: Dict[str, str] = field(default_factory=dict)  # dimension_name -> PASS/WATCH/FAIL/UNKNOWN/NOT_APPLICABLE
    hard_financial_failures: List[str] = field(default_factory=list)
    financial_warnings: List[str] = field(default_factory=list)
    all_findings: List[FinancialFinding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Convert nested dataclasses to dicts properly
        for attr in [
            "growth_analysis",
            "profitability_analysis",
            "earnings_durability",
            "earnings_quality",
            "cash_flow_quality",
            "balance_sheet_strength",
            "debt_liquidity",
            "capital_efficiency",
            "capital_allocation",
            "dilution_analysis",
            "accounting_consistency",
            "financial_forensics",
        ]:
            val = getattr(self, attr)
            if hasattr(val, "to_dict"):
                d[attr] = val.to_dict()
        d["all_findings"] = [f.to_dict() if hasattr(f, "to_dict") else f for f in self.all_findings]
        return d
