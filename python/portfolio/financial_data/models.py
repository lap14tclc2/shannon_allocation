"""
QPort Vietnamese Financial Data System Foundation Models (QFD-200 to QFD-260, QFD-330, QFD-520).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class StatementType(str, Enum):
    BALANCE_SHEET = "BALANCE_SHEET"
    INCOME_STATEMENT = "INCOME_STATEMENT"
    CASH_FLOW = "CASH_FLOW"


class PeriodType(str, Enum):
    INSTANT = "INSTANT"
    QUARTER = "QUARTER"
    YTD = "YTD"
    FY = "FY"


class ConsolidationScope(str, Enum):
    CONSOLIDATED = "CONSOLIDATED"
    SEPARATE = "SEPARATE"
    UNKNOWN = "UNKNOWN"


class EntityType(str, Enum):
    NORMAL_ENTERPRISE = "NORMAL_ENTERPRISE"
    BANK = "BANK"
    SECURITIES = "SECURITIES"
    INSURANCE = "INSURANCE"


class QualityStatus(str, Enum):
    OFFICIAL_VERIFIED = "OFFICIAL_VERIFIED"
    CROSS_SOURCE_VERIFIED = "CROSS_SOURCE_VERIFIED"
    SINGLE_SOURCE = "SINGLE_SOURCE"
    DERIVED = "DERIVED"
    CONFLICT = "CONFLICT"
    QUARANTINED = "QUARANTINED"
    MISSING = "MISSING"


@dataclass(frozen=True)
class FactIdentityKey:
    """
    Economic identity key of a financial fact (QFD-210).
    Excludes provider_id, revision_no, and observed_at.
    """
    security_id: str
    statement_type: StatementType
    period_end: str  # YYYY-MM-DD
    period_type: PeriodType
    fiscal_year: int
    fiscal_quarter: Optional[int]
    consolidation_scope: ConsolidationScope
    line_item_code: str
    currency: str = "VND"

    def canonical_string(self) -> str:
        return (
            f"{self.security_id}|{self.statement_type.value}|{self.period_end}|"
            f"{self.period_type.value}|{self.fiscal_year}|{self.fiscal_quarter}|"
            f"{self.consolidation_scope.value}|{self.line_item_code}|{self.currency}"
        )


@dataclass
class ProviderFact:
    """
    Normalized fact from a specific provider / document (QFD-220).
    """
    security_id: str
    symbol_observed: str
    statement_type: StatementType
    line_item_code: str
    label_observed: str
    value_raw: str
    value_normalized: Decimal
    currency: str
    scale_observed: Decimal
    period_start: Optional[str]
    period_end: str
    period_type: PeriodType
    fiscal_year: int
    fiscal_quarter: Optional[int]
    consolidation_scope: ConsolidationScope
    provider_id: str
    source_document_id: str
    observed_at: str  # ISO-8601 UTC
    parser_version: str
    revision_no: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    provider_fact_id: str = ""

    def __post_init__(self):
        if not self.provider_fact_id:
            # Deterministic ID generation based on content
            raw_key = (
                f"{self.provider_id}|{self.source_document_id}|{self.security_id}|"
                f"{self.statement_type.value}|{self.line_item_code}|{self.period_end}|"
                f"{self.period_type.value}|{self.fiscal_year}|{self.fiscal_quarter}|"
                f"{self.value_normalized}|{self.revision_no}|{self.observed_at}"
            )
            self.provider_fact_id = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @property
    def identity_key(self) -> FactIdentityKey:
        return FactIdentityKey(
            security_id=self.security_id,
            statement_type=self.statement_type,
            period_end=self.period_end,
            period_type=self.period_type,
            fiscal_year=self.fiscal_year,
            fiscal_quarter=self.fiscal_quarter,
            consolidation_scope=self.consolidation_scope,
            line_item_code=self.line_item_code,
            currency=self.currency,
        )


@dataclass
class ReconciliationDecision:
    """
    Audit record of the reconciliation decision (QFD-230, QFD-300, QFD-420).
    """
    decision_id: str
    identity_key: FactIdentityKey
    rule_version: str
    candidate_fact_ids: List[str]
    winning_candidate_id: Optional[str]
    chosen_status: QualityStatus
    chosen_value: Optional[Decimal]
    tolerance_used: Optional[Decimal]
    reason: str
    decided_at: str


@dataclass
class CanonicalFact:
    """
    Reconciled canonical fact served to consumers (QFD-200, QFD-230, QFD-250, QFD-520).
    value is None when quality_status is MISSING.
    """
    canonical_fact_id: str
    identity: FactIdentityKey
    value: Optional[Decimal]
    quality_status: QualityStatus
    decision_id: str
    winning_candidate_id: Optional[str]
    candidate_ids: List[str]
    observed_at: str
    valid_from: str = ""
    valid_to: Optional[str] = None
    superseded_by: Optional[str] = None
    published_at: Optional[str] = None
    tolerance_used: Optional[Decimal] = None
    reason: str = ""
