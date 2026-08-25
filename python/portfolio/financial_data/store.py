"""
Bitemporal Point-in-Time Financial Fact & Provenance Storage (QFD-200, QFD-230, QFD-320, QFD-420, QFD-520).

Stores:
- Append-only RawEnvelopes with content hashes
- SourceDocuments
- ProviderFacts
- ReconciliationDecisions
- CanonicalFacts with bitemporal intervals (valid_from, valid_to, superseded_by)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
from .connectors import RawEnvelope, SourceDocument
from .models import (
    CanonicalFact,
    FactIdentityKey,
    ProviderFact,
    QualityStatus,
    ReconciliationDecision,
    StatementType,
)
from .reconciler import reconcile_facts


class FinancialDataStore:
    def __init__(self):
        self._raw_envelopes: Dict[str, RawEnvelope] = {}
        self._source_documents: Dict[str, SourceDocument] = {}
        self._provider_facts: List[ProviderFact] = []
        self._decisions: Dict[str, ReconciliationDecision] = {}
        self._canonical_facts: Dict[FactIdentityKey, List[CanonicalFact]] = {}

    def save_envelope(self, envelope: RawEnvelope) -> None:
        self._raw_envelopes[envelope.envelope_id] = envelope

    def get_envelope(self, envelope_id: str) -> Optional[RawEnvelope]:
        return self._raw_envelopes.get(envelope_id)

    def save_source_document(self, doc: SourceDocument) -> None:
        self._source_documents[doc.document_id] = doc

    def get_source_document(self, document_id: str) -> Optional[SourceDocument]:
        return self._source_documents.get(document_id)

    def save_provider_facts(self, facts: List[ProviderFact]) -> None:
        self._provider_facts.extend(facts)

    def get_decision(self, decision_id: str) -> Optional[ReconciliationDecision]:
        return self._decisions.get(decision_id)

    def reconcile_and_store(self, identity: FactIdentityKey) -> CanonicalFact:
        """
        Reconciles candidate ProviderFacts matching the identity key.
        Maintains bitemporal intervals when restatements occur.
        """
        candidates = [f for f in self._provider_facts if f.identity_key == identity]
        canonical, decision = reconcile_facts(identity, candidates)
        
        # Store decision audit
        self._decisions[decision.decision_id] = decision

        if identity not in self._canonical_facts:
            self._canonical_facts[identity] = []
        else:
            # Handle Restatement / Revision bitemporal succession (QFD-320)
            now_iso = datetime.now(timezone.utc).isoformat()
            if self._canonical_facts[identity]:
                prev_fact = self._canonical_facts[identity][-1]
                prev_fact.valid_to = now_iso
                prev_fact.superseded_by = canonical.canonical_fact_id

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
        Point-in-time canonical query (QFD-500, QFD-520).
        If `as_of` is provided:
        - Only considers facts observed/valid on or before `as_of`.
        - Respects `valid_from <= as_of < (valid_to or infinity)`.
        - Mutes CONFLICT and QUARANTINED facts by default.
        """
        results: List[CanonicalFact] = []
        for identity, history in self._canonical_facts.items():
            if identity.security_id != security_id:
                continue
            if statement_type and identity.statement_type != statement_type:
                continue

            if as_of:
                # Find the version that was active at time `as_of`
                matching_version = None
                for fact in history:
                    if fact.valid_from and fact.valid_from <= as_of:
                        if fact.valid_to is None or fact.valid_to > as_of:
                            matching_version = fact
                if not matching_version:
                    continue
                chosen = matching_version
            else:
                if not history:
                    continue
                chosen = history[-1]

            if not include_conflicts and chosen.quality_status in (QualityStatus.CONFLICT, QualityStatus.QUARANTINED, QualityStatus.MISSING):
                continue
            results.append(chosen)

        return results
