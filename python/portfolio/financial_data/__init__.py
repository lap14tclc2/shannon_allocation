"""
QPort Vietnamese Financial Data Foundation Package.
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
    StatementType,
)
from .reconciler import reconcile_facts
from .store import FinancialDataStore
from .taxonomy import get_taxonomy_for_entity

__all__ = [
    "StatementType",
    "PeriodType",
    "ConsolidationScope",
    "EntityType",
    "QualityStatus",
    "FactIdentityKey",
    "ProviderFact",
    "CanonicalFact",
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
]
