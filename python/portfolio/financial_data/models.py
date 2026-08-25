"""
QPort Vietnamese Financial Data System Foundation Models.

Implements contracts and data structures specified in:
- QFD-200: Three layers of data
- QFD-210: Financial fact identity key
- QFD-220: ProviderFact contract
- QFD-230: Provenance and evidence chain
- QFD-240: Reporting period normalization
- QFD-250: Units, currency, and sign conventions
- QFD-260: Entity-specific taxonomies
- QFD-330: Quality status lifecycle
"""
from __future__ import annotations

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
class CanonicalFact:
    """
    Reconciled canonical fact served to consumers (QFD-200, QFD-230).
    """
    canonical_fact_id: str
    identity: FactIdentityKey
    value: Decimal
    quality_status: QualityStatus
    decision_id: str
    winning_candidate_id: Optional[str]
    candidate_ids: List[str]
    observed_at: str
    published_at: Optional[str] = None
    tolerance_used: Optional[Decimal] = None
    reason: str = ""
