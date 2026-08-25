"""
Deterministic Financial Data Reconciliation Engine (QFD-300, QFD-310, QFD-320).

Enforces:
1. Reconciles candidates with identical FactIdentityKey.
2. Exact match or relative tolerance (e.g. 0.05% for rounding/scale differences).
3. NEVER averages accounting numbers (strict non-averaging invariant).
4. Evidence-tier and revision ranking.
5. Emits CanonicalFact with QualityStatus and provenance audit decision.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional
from .models import CanonicalFact, FactIdentityKey, ProviderFact, QualityStatus

# Evidence tier preferences (higher is more authoritative)
PROVIDER_TIER = {
    "official_filing": 100,
    "audited_report_pdf": 90,
    "cafef_html": 50,
    "vnstock_api": 50,
    "vietstock_api": 50,
    "manual_override": 10,
}

DEFAULT_ROUNDING_TOLERANCE = Decimal("0.0005")  # 0.05%


def reconcile_facts(
    identity: FactIdentityKey,
    candidates: List[ProviderFact],
    tolerance: Decimal = DEFAULT_ROUNDING_TOLERANCE,
    rule_version: str = "qfd-reconciler@1.0.0",
) -> CanonicalFact:
    """
    Deterministically reconcile multiple candidate facts for the same identity key.
    """
    if not candidates:
        return CanonicalFact(
            canonical_fact_id=str(uuid.uuid4()),
            identity=identity,
            value=Decimal("0"),
            quality_status=QualityStatus.MISSING,
            decision_id=str(uuid.uuid4()),
            winning_candidate_id=None,
            candidate_ids=[],
            observed_at="",
            reason="No candidate facts provided",
        )

    candidate_ids = [c.source_document_id for c in candidates]
    latest_observed = max(c.observed_at for c in candidates)

    if len(candidates) == 1:
        single = candidates[0]
        return CanonicalFact(
            canonical_fact_id=str(uuid.uuid4()),
            identity=identity,
            value=single.value_normalized,
            quality_status=QualityStatus.SINGLE_SOURCE,
            decision_id=str(uuid.uuid4()),
            winning_candidate_id=single.source_document_id,
            candidate_ids=candidate_ids,
            observed_at=latest_observed,
            reason=f"Single source fact from provider '{single.provider_id}'",
        )

    # Sort candidates by: Tier (desc), Revision (desc), observed_at (desc)
    def rank_key(fact: ProviderFact):
        tier = PROVIDER_TIER.get(fact.provider_id, 30)
        return (tier, fact.revision_no, fact.observed_at)

    sorted_candidates = sorted(candidates, key=rank_key, reverse=True)
    winner = sorted_candidates[0]

    # Check cross-source agreement
    values = [c.value_normalized for c in sorted_candidates]
    base_val = winner.value_normalized

    is_official = winner.provider_id in ("official_filing", "audited_report_pdf")
    
    # Check if all candidates agree within tolerance
    all_agree = True
    for val in values:
        if base_val == Decimal("0"):
            if val != Decimal("0"):
                all_agree = False
                break
        else:
            diff = abs(val - base_val) / abs(base_val)
            if diff > tolerance:
                all_agree = False
                break

    if all_agree:
        status = QualityStatus.OFFICIAL_VERIFIED if is_official else QualityStatus.CROSS_SOURCE_VERIFIED
        reason = f"All {len(candidates)} sources agree within tolerance {tolerance}"
        winning_val = winner.value_normalized
    else:
        if is_official:
            # Official source overrides secondary vendor discrepancies
            status = QualityStatus.OFFICIAL_VERIFIED
            reason = f"Official filing from '{winner.provider_id}' selected; secondary provider mismatch ignored"
            winning_val = winner.value_normalized
        else:
            status = QualityStatus.CONFLICT
            reason = f"Sources disagree beyond tolerance {tolerance}; distinct values: {[str(v) for v in values]}"
            winning_val = winner.value_normalized

    return CanonicalFact(
        canonical_fact_id=str(uuid.uuid4()),
        identity=identity,
        value=winning_val,
        quality_status=status,
        decision_id=str(uuid.uuid4()),
        winning_candidate_id=winner.source_document_id if status != QualityStatus.CONFLICT else None,
        candidate_ids=candidate_ids,
        observed_at=latest_observed,
        tolerance_used=tolerance,
        reason=reason,
    )
