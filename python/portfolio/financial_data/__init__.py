"""
QPort Vietnamese Financial Data Foundation Package (QFD-200 to QFD-520).
"""
from .connectors import (
    CafeFHtmlAdapter,
    FinancialApiProvider,
    FinancialHtmlProvider,
    RawEnvelope,
    SourceDocument,
    VnstockApiAdapter,
)
from .metrics import ComputedMetric, compute_metrics
from .models import (
    CanonicalFact,
    ConsolidationScope,
    EntityType,
    FactIdentityKey,
    PeriodType,
    ProviderFact,
    QualityStatus,
    ReconciliationDecision,
    StatementType,
)
from .reconciler import reconcile_facts
from .store import FinancialDataStore
from .taxonomy import get_required_period_type, get_taxonomy_for_entity

__all__ = [
    "StatementType",
    "PeriodType",
    "ConsolidationScope",
    "EntityType",
    "QualityStatus",
    "FactIdentityKey",
    "ProviderFact",
    "CanonicalFact",
    "ReconciliationDecision",
    "SourceDocument",
    "RawEnvelope",
    "FinancialApiProvider",
    "FinancialHtmlProvider",
    "VnstockApiAdapter",
    "CafeFHtmlAdapter",
    "FinancialDataStore",
    "ComputedMetric",
    "compute_metrics",
    "reconcile_facts",
    "get_taxonomy_for_entity",
    "get_required_period_type",
]
