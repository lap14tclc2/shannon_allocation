"""
Point-in-Time Financial Fact and Provenance Storage (QFD-200, QFD-230, QFD-420, QFD-520).

Stores:
- Raw envelopes with payload hashes
- Provider facts
- Canonical facts and reconciliation decisions
- Point-in-time querying filtering on `as_of` timestamp to prevent look-ahead bias
"""
from __future__ import annotations

from typing import Dict, List, Optional
from .connectors import RawEnvelope, SourceDocument
from .models import CanonicalFact, FactIdentityKey, ProviderFact, QualityStatus, StatementType
from .reconciler import reconcile_facts


class FinancialDataStore:
    def __init__(self):
        self._raw_envelopes: Dict[str, RawEnvelope] = {}
        self._source_documents: Dict[str, SourceDocument] = {}
        self._provider_facts: List[ProviderFact] = []
        self._canonical_facts: Dict[FactIdentityKey, List[CanonicalFact]] = {}

    def save_envelope(self, envelope: RawEnvelope) -> None:
        self._raw_envelopes[envelope.envelope_id] = envelope

    def get_envelope(self, envelope_id: str) -> Optional[RawEnvelope]:
        return self._raw_envelopes.get(envelope_id)

    def save_provider_facts(self, facts: List[ProviderFact]) -> None:
        self._provider_facts.extend(facts)

    def reconcile_and_store(self, identity: FactIdentityKey) -> CanonicalFact:
        """
        Gathers all stored ProviderFacts matching the identity key,
        runs deterministic reconciliation, and stores the resulting CanonicalFact.
        """
        candidates = [
            f for f in self._provider_facts
            if f.identity_key == identity
        ]
        canonical = reconcile_facts(identity, candidates)
        if identity not in self._canonical_facts:
            self._canonical_facts[identity] = []
        self._canonical_facts[identity].append(canonical)
        return canonical

    def get_canonical_facts(
        self,
        security_id: str,
        statement_type: Optional[StatementType] = None,
        as_of: Optional[str] = None,
        include_conflicts: bool = False,
    ) -> List[CanonicalFact]:
        """
        Point-in-time canonical fact query (QFD-500, QFD-520).
        If `as_of` (ISO-8601 UTC) is specified, only returns facts observed on or before `as_of`.
        Mutes CONFLICT and QUARANTINED unless explicitly requested.
        """
        results: List[CanonicalFact] = []
        for identity, history in self._canonical_facts.items():
            if identity.security_id != security_id:
                continue
            if statement_type and identity.statement_type != statement_type:
                continue

            # Point-in-time filter
            valid_versions = history
            if as_of:
                valid_versions = [f for f in history if f.observed_at <= as_of]

            if not valid_versions:
                continue

            # Take the latest available version as of `as_of`
            latest = valid_versions[-1]
            if not include_conflicts and latest.quality_status in (QualityStatus.CONFLICT, QualityStatus.QUARANTINED):
                continue
            results.append(latest)

        return results
