"""
Dynamic Margin of Safety Engine for Vietnamese Stock Universe.

Computes required Margin of Safety based on sector baseline, confidence, cyclicality, and leverage.
Clamps required MOS strictly between 20% and 50%.

P0 audit (2026-08-29 / TASK-068, TASK-069, TASK-070):
  - Hard-reject precedence: any ``hard_rejects`` overrides the final verdict and
    may never resolve to ATTRACTIVE / HIGH_CONVICTION_VALUE / FAIRLY_VALUED.
  - Leverage penalty is driven by real debt metrics (net debt, debt payback years,
    net debt / EBITDA) instead of the CAPITAL_INTENSIVE overlay alone.
  - ``has_solvency_risk`` means ONLY the SOLVENCY_RISK hard reject (not any hard
    reject) for the +10 penalty; EXCESSIVE_DILUTION on a net-cash balance sheet
    must not be charged a leverage penalty.
  - LOW_QUALITY tier never resolves to ATTRACTIVE / HIGH_CONVICTION_VALUE even
    when the MOS math is satisfied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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
    leverage_evidence: Dict[str, Any] = field(default_factory=dict)


class MarginOfSafetyEngine:
    """Calculates dynamic required margin of safety and validates value investment status."""

    @classmethod
    def calculate(
        cls,
        archetype_prof: ArchetypeProfile,
        quality_tier: QualityTier,
        actual_base_mos: float,
        has_solvency_risk: bool = False,
        confidence_level: str = "MEDIUM",
        has_negative_intrinsic_value: bool = False,
        hard_rejects: Optional[List[str]] = None,
        net_debt: Optional[float] = None,
        debt_payback_years: Optional[float] = None,
        net_debt_to_ebitda: Optional[float] = None,
    ) -> MOSCalculation:
        hard_rejects = [str(h).upper() for h in (hard_rejects or [])]

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
        leverage_pen, leverage_evidence = cls._leverage_penalty(
            archetype_prof=archetype_prof,
            has_solvency_risk=has_solvency_risk,
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

        # P0 hard-reject precedence (TASK-068/069): a hard reject overrides the
        # verdict regardless of how attractive the MOS math looks.
        if hard_rejects:
            if "SOLVENCY_RISK" in hard_rejects:
                verdict = "AVOID_SOLVENCY"
            elif "UNNORMALIZABLE_EARNINGS" in hard_rejects or "ACCOUNTING_UNRELIABLE" in hard_rejects:
                verdict = "UNVALUABLE"
            else:
                # EXCESSIVE_DILUTION, DATA_INSUFFICIENT, CIRCLE_OF_COMPETENCE_FAIL...
                verdict = "AVOID_QUALITY"
        elif quality_tier == QualityTier.LOW_QUALITY:
            # P0 audit (TASK-068): LOW_QUALITY + satisfied MOS must resolve to
            # AVOID_QUALITY, never ATTRACTIVE / HIGH_CONVICTION_VALUE.
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
        else:
            verdict = "WATCH"

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

    @staticmethod
    def _leverage_penalty(
        *,
        archetype_prof: ArchetypeProfile,
        has_solvency_risk: bool,
        net_debt: Optional[float],
        debt_payback_years: Optional[float],
        net_debt_to_ebitda: Optional[float],
    ) -> tuple[float, Dict[str, Any]]:
        """Leverage penalty from real balance-sheet / coverage metrics (TASK-068).

        Precedence:
          1. SOLVENCY_RISK hard reject  -> +10 (always, even net cash).
          2. Net cash (net_debt <= 0)   -> +0.
          3. Positive debt with debt-payback years or ND/EBITDA available -> scaled.
          4. Positive debt with no coverage metrics -> conservative +3 (or +5 for
             CAPITAL_INTENSIVE businesses).
        """
        evidence: Dict[str, Any] = {
            "net_debt": net_debt,
            "debt_payback_years": debt_payback_years,
            "net_debt_to_ebitda": net_debt_to_ebitda,
        }
        if has_solvency_risk:
            return 10.0, evidence
        if net_debt is not None and net_debt <= 0:
            return 0.0, evidence
        if debt_payback_years is not None:
            if debt_payback_years < 2.0:
                pen = 0.0
            elif debt_payback_years < 4.0:
                pen = 3.0
            elif debt_payback_years < 8.0:
                pen = 6.0
            else:
                pen = 10.0
            return pen, evidence
        if net_debt_to_ebitda is not None:
            if net_debt_to_ebitda < 1.0:
                pen = 0.0
            elif net_debt_to_ebitda < 2.0:
                pen = 3.0
            elif net_debt_to_ebitda < 4.0:
                pen = 6.0
            else:
                pen = 10.0
            return pen, evidence
        if ArchetypeOverlay.CAPITAL_INTENSIVE in archetype_prof.overlays:
            return 5.0, evidence
        return 3.0, evidence