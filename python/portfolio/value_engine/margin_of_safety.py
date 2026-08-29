"""
Dynamic Margin of Safety Engine for Vietnamese Stock Universe.

Computes required Margin of Safety based on sector baseline, confidence, cyclicality, and leverage.
Clamps required MOS strictly between 20% and 50%.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List
from .archetypes import ArchetypeOverlay, ArchetypeProfile
from .quality_scorer import QualityTier

# Confidence -> additional required MOS (audit P0-1)
CONFIDENCE_MOS_PENALTY = {
    "HIGH": 0.0,
    "MEDIUM": 5.0,
    "LOW": 10.0,
    "BLOCKED": 10.0,
}


@dataclass
class MOSCalculation:
    required_mos_pct: float  # e.g. 25.0 for 25%
    base_sector_mos_pct: float
    cyclicality_penalty_pct: float
    leverage_penalty_pct: float
    confidence_penalty_pct: float
    predictability_discount_pct: float
    actual_base_mos_pct: float
    mos_satisfied: bool
    verdict_status: str
    confidence_level: str = "MEDIUM"
    has_negative_intrinsic_value: bool = False
    hard_rejects: List[str] = field(default_factory=list)
    leverage_evidence: dict = field(default_factory=dict)


class MarginOfSafetyEngine:
    """Calculates dynamic required margin of safety and validates value investment status."""

    @classmethod
    def _leverage_penalty(
        cls,
        *,
        has_solvency_risk: bool,
        is_capital_intensive: bool,
        net_debt: float | None = None,
        debt_payback_years: float | None = None,
        net_debt_to_ebitda: float | None = None,
    ) -> tuple[float, dict]:
        """Derive a leverage MOS penalty from REAL leverage metrics (P1 audit).

        Priority:
          1. A hard SOLVENCY_RISK reject -> maximum penalty (10).
          2. net_debt_to_ebitda >= 6.0  -> 10 (debt far exceeds EBITDA).
          3. debt_payback_years >= 10    -> 10 (CFO cannot service debt quickly).
          4. net_debt_to_ebitda >= 4.0  or debt_payback_years >= 5 -> 6.
          5. net_debt_to_ebitda >= 2.0  or debt_payback_years >= 2 -> 3.
          6. Positive net debt with no EBITDA/payback evidence -> 3 (conservative).
          7. Net cash (net_debt <= 0)    -> 0.
        ``is_capital_intensive`` alone no longer adds a penalty; it only matters
        when combined with real leverage evidence.
        """
        evidence = {
            "net_debt": net_debt,
            "debt_payback_years": debt_payback_years,
            "net_debt_to_ebitda": net_debt_to_ebitda,
        }
        if has_solvency_risk:
            return 10.0, evidence
        if net_debt is not None and net_debt <= 0:
            return 0.0, evidence
        nd_ebitda = float(net_debt_to_ebitda) if net_debt_to_ebitda is not None else None
        payback = float(debt_payback_years) if debt_payback_years is not None else None
        if nd_ebitda is not None and nd_ebitda >= 6.0:
            return 10.0, evidence
        if payback is not None and payback >= 10.0:
            return 10.0, evidence
        if (nd_ebitda is not None and nd_ebitda >= 4.0) or (payback is not None and payback >= 5.0):
            return 6.0, evidence
        if (nd_ebitda is not None and nd_ebitda >= 2.0) or (payback is not None and payback >= 2.0):
            return 3.0, evidence
        if net_debt is not None and net_debt > 0:
            # Positive debt but no coverage evidence: keep a small conservative penalty.
            return 3.0, evidence
        return 0.0, evidence

    @classmethod
    def calculate(
        cls,
        archetype_prof: ArchetypeProfile,
        quality_tier: QualityTier,
        actual_base_mos: float,
        has_solvency_risk: bool = False,
        confidence_level: str = "MEDIUM",
        has_negative_intrinsic_value: bool = False,
        hard_rejects: List[str] | None = None,
        net_debt: float | None = None,
        debt_payback_years: float | None = None,
        net_debt_to_ebitda: float | None = None,
    ) -> MOSCalculation:
        hard_rejects = [str(r) for r in (hard_rejects or [])]
        # P0 audit (2026-08-29): a hard reject (EXCESSIVE_DILUTION, SOLVENCY_RISK,
        # ACCOUNTING_UNRELIABLE, DATA_INSUFFICIENT, ...) overrides the final verdict.
        # Even a satisfied MOS can never yield ATTRACTIVE / HIGH_CONVICTION_VALUE.
        reject_override = None
        if hard_rejects:
            if "SOLVENCY_RISK" in hard_rejects:
                reject_override = "AVOID_SOLVENCY"
            elif "UNNORMALIZABLE_EARNINGS" in hard_rejects or "CIRCLE_OF_COMPETENCE_FAIL" in hard_rejects:
                reject_override = "UNVALUABLE"
            else:
                reject_override = "AVOID_QUALITY"
        # Hard invariant (audit 68-symbol): a negative intrinsic value is never
        # FAIRLY_VALUED. MOS is meaningless for a destroyed equity value.
        if has_negative_intrinsic_value:
            verdict = "AVOID_SOLVENCY" if has_solvency_risk else "UNVALUABLE"
            return MOSCalculation(
                required_mos_pct=0.0,
                base_sector_mos_pct=archetype_prof.base_required_mos * 100.0,
                cyclicality_penalty_pct=0.0,
                leverage_penalty_pct=0.0,
                confidence_penalty_pct=0.0,
                predictability_discount_pct=0.0,
                actual_base_mos_pct=round(actual_base_mos, 1),
                mos_satisfied=False,
                verdict_status=verdict,
                confidence_level=str(confidence_level).upper(),
                has_negative_intrinsic_value=True,
                hard_rejects=hard_rejects,
            )

        base_mos = archetype_prof.base_required_mos * 100.0

        # Penalties
        cyclicality_pen = 10.0 if ArchetypeOverlay.HIGH_CYCLICALITY in archetype_prof.overlays else 0.0
        is_capital_intensive = ArchetypeOverlay.CAPITAL_INTENSIVE in archetype_prof.overlays
        leverage_pen, leverage_evidence = cls._leverage_penalty(
            has_solvency_risk=has_solvency_risk,
            is_capital_intensive=is_capital_intensive,
            net_debt=net_debt,
            debt_payback_years=debt_payback_years,
            net_debt_to_ebitda=net_debt_to_ebitda,
        )
        confidence_pen = CONFIDENCE_MOS_PENALTY.get(str(confidence_level).upper(), 5.0)

        # Discounts
        predictability_disc = 5.0 if quality_tier in (QualityTier.EXCEPTIONAL, QualityTier.HIGH_QUALITY) else 0.0

        raw_required = base_mos + cyclicality_pen + leverage_pen + confidence_pen - predictability_disc
        # Clamp strictly between 20.0% and 50.0%
        clamped_required = max(20.0, min(50.0, raw_required))

        satisfied = actual_base_mos >= clamped_required

        confidence_high = str(confidence_level).upper() == "HIGH"
        # P0 audit (2026-08-29): LOW_QUALITY is a hard quality gate. A LOW_QUALITY
        # business must NEVER be ATTRACTIVE / HIGH_CONVICTION_VALUE even when the
        # valuation math (MOS) is satisfied. This invariant runs BEFORE the
        # satisfied-MOS branch so FRT-like cases (LOW_QUALITY + MOS 48%) resolve
        # to AVOID_QUALITY, not ATTRACTIVE.
        if quality_tier == QualityTier.LOW_QUALITY:
            verdict = "AVOID_QUALITY"
        elif (
            satisfied
            and confidence_high
            and quality_tier in (QualityTier.EXCEPTIONAL, QualityTier.HIGH_QUALITY)
            and not has_solvency_risk
        ):
            verdict = "HIGH_CONVICTION_VALUE"
        elif satisfied:
            verdict = "ATTRACTIVE"
        elif actual_base_mos >= -15.0:
            verdict = "FAIRLY_VALUED"
        elif quality_tier == QualityTier.LOW_QUALITY:
            verdict = "AVOID_QUALITY"
        else:
            verdict = "WATCH"

        # P0 audit (2026-08-29): hard rejects override any valuation-positive verdict.
        if reject_override and verdict in ("HIGH_CONVICTION_VALUE", "ATTRACTIVE", "FAIRLY_VALUED"):
            verdict = reject_override

        return MOSCalculation(
            required_mos_pct=round(clamped_required, 1),
            base_sector_mos_pct=round(base_mos, 1),
            cyclicality_penalty_pct=cyclicality_pen,
            leverage_penalty_pct=leverage_pen,
            confidence_penalty_pct=confidence_pen,
            predictability_discount_pct=predictability_disc,
            actual_base_mos_pct=round(actual_base_mos, 1),
            mos_satisfied=satisfied,
            verdict_status=verdict,
            confidence_level=str(confidence_level).upper(),
            hard_rejects=hard_rejects,
            leverage_evidence=leverage_evidence,
        )
