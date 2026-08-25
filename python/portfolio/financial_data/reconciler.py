"""
Deterministic Financial Data Reconciliation Engine (QFD-300, QFD-310, QFD-320, QFD-330).

Invariants enforced:
1. Deterministic output: IDs are computed via sha256(canonical_inputs). No uuid4().
2. Evidence hierarchy: Official (100) > Audited PDF (90) > Structured API (70) > HTML Crawler (50) > Manual (10).
3. Independent cross-source rule: CROSS_SOURCE_VERIFIED requires candidates from >=2 distinct provider IDs.
4. Strict non-averaging rule: Never average numbers.
5. Strict non-zero missing rule: Fact MISSING holds value=None.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Set, Tuple

from .models import (
    CanonicalFact,
    FactIdentityKey,
    ProviderFact,
    QualityStatus,
    ReconciliationDecision,
)

# Evidence tier preferences (QFD-020, QFD-320)
PROVIDER_TIER = {
    "official_filing": 100,
    "audited_report_pdf": 90,
    "vnstock_api": 70,
    "vietstock_api": 70,
    "cafef_html": 50,
    "manual_override": 10,
}

DEFAULT_ROUNDING_TOLERANCE = Decimal("0.0005")  # 0.05%


def _generate_deterministic_id(prefix: str, content: str) -> str:
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{h}"


def reconcile_facts(
    identity: FactIdentityKey,
    candidates: List[ProviderFact],
    tolerance: Decimal = DEFAULT_ROUNDING_TOLERANCE,
    rule_version: str = "qfd-reconciler@1.0.0",
) -> Tuple[CanonicalFact, ReconciliationDecision]:
    """
    Deterministically reconcile candidate ProviderFacts for the given FactIdentityKey.
    Returns (CanonicalFact, ReconciliationDecision).
    """
    sorted_candidate_ids = sorted([c.provider_fact_id for c in candidates])
    identity_str = identity.canonical_string()
    
    # Deterministic Decision & Canonical IDs
    id_seed = f"{identity_str}|{','.join(sorted_candidate_ids)}|{rule_version}|{tolerance}"
    decision_id = _generate_deterministic_id("dec", id_seed)
    canonical_id = _generate_deterministic_id("cf", id_seed)

    # 1. No candidates -> MISSING (value is None)
    if not candidates:
        now_utc = datetime.now(timezone.utc).isoformat()
        decision = ReconciliationDecision(
            decision_id=decision_id,
            identity_key=identity,
            rule_version=rule_version,
            candidate_fact_ids=[],
            winning_candidate_id=None,
            chosen_status=QualityStatus.MISSING,
            chosen_value=None,
            tolerance_used=tolerance,
            reason="No candidate facts available",
            decided_at=now_utc,
        )
        canonical = CanonicalFact(
            canonical_fact_id=canonical_id,
            identity=identity,
            value=None,
            quality_status=QualityStatus.MISSING,
            decision_id=decision_id,
            winning_candidate_id=None,
            candidate_ids=[],
            observed_at="",
            valid_from=now_utc,
            tolerance_used=tolerance,
            reason=decision.reason,
        )
        return canonical, decision

    candidate_ids = [c.provider_fact_id for c in candidates]
    latest_observed = max(c.observed_at for c in candidates)
    distinct_providers: Set[str] = {c.provider_id for c in candidates}

    # 2. Single Candidate -> SINGLE_SOURCE
    if len(candidates) == 1:
        single = candidates[0]
        now_utc = datetime.now(timezone.utc).isoformat()
        decision = ReconciliationDecision(
            decision_id=decision_id,
            identity_key=identity,
            rule_version=rule_version,
            candidate_fact_ids=candidate_ids,
            winning_candidate_id=single.provider_fact_id,
            chosen_status=QualityStatus.SINGLE_SOURCE,
            chosen_value=single.value_normalized,
            tolerance_used=tolerance,
            reason=f"Single source candidate from provider '{single.provider_id}'",
            decided_at=now_utc,
        )
        canonical = CanonicalFact(
            canonical_fact_id=canonical_id,
            identity=identity,
            value=single.value_normalized,
            quality_status=QualityStatus.SINGLE_SOURCE,
            decision_id=decision_id,
            winning_candidate_id=single.provider_fact_id,
            candidate_ids=candidate_ids,
            observed_at=latest_observed,
            valid_from=latest_observed,
            tolerance_used=tolerance,
            reason=decision.reason,
        )
        return canonical, decision

    # Sort candidates by: Evidence Tier (desc), Revision (desc), observed_at (desc), provider_fact_id (asc)
    def rank_key(fact: ProviderFact):
        tier = PROVIDER_TIER.get(fact.provider_id, 30)
        return (tier, fact.revision_no, fact.observed_at, fact.provider_fact_id)

    sorted_candidates = sorted(candidates, key=rank_key, reverse=True)
    winner = sorted_candidates[0]
    is_official = winner.provider_id in ("official_filing", "audited_report_pdf")
    base_val = winner.value_normalized

    # Check cross-source agreement within tolerance
    all_agree = True
    for c in sorted_candidates:
        val = c.value_normalized
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
        if is_official:
            status = QualityStatus.OFFICIAL_VERIFIED
            reason = f"Official filing source '{winner.provider_id}' confirmed with agreement"
        elif len(distinct_providers) >= 2:
            # Strictly requires >=2 distinct independent providers (QFD-330)
            status = QualityStatus.CROSS_SOURCE_VERIFIED
            reason = f"Agreement within tolerance {tolerance} across {len(distinct_providers)} distinct independent providers: {sorted(distinct_providers)}"
        else:
            # Multiple records from same single provider -> SINGLE_SOURCE
            status = QualityStatus.SINGLE_SOURCE
            reason = f"Multiple records from single provider '{winner.provider_id}'; not independent cross-source"
        winning_val = winner.value_normalized
        winning_candidate_id = winner.provider_fact_id
    else:
        if is_official:
            status = QualityStatus.OFFICIAL_VERIFIED
            reason = f"Official filing from '{winner.provider_id}' selected; secondary vendor mismatch overridden"
            winning_val = winner.value_normalized
            winning_candidate_id = winner.provider_fact_id
        else:
            status = QualityStatus.CONFLICT
            vals = [str(c.value_normalized) for c in sorted_candidates]
            reason = f"Sources disagree beyond tolerance {tolerance}; values: {vals}"
            winning_val = winner.value_normalized  # Preserved in record but status is CONFLICT
            winning_candidate_id = None

    now_utc = datetime.now(timezone.utc).isoformat()
    decision = ReconciliationDecision(
        decision_id=decision_id,
        identity_key=identity,
        rule_version=rule_version,
        candidate_fact_ids=candidate_ids,
        winning_candidate_id=winning_candidate_id,
        chosen_status=status,
        chosen_value=winning_val,
        tolerance_used=tolerance,
        reason=reason,
        decided_at=now_utc,
    )
    canonical = CanonicalFact(
        canonical_fact_id=canonical_id,
        identity=identity,
        value=winning_val,
        quality_status=status,
        decision_id=decision_id,
        winning_candidate_id=winning_candidate_id,
        candidate_ids=candidate_ids,
        observed_at=latest_observed,
        valid_from=latest_observed,
        tolerance_used=tolerance,
        reason=reason,
    )
    return canonical, decision
