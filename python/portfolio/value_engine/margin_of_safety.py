"""
Dynamic Margin of Safety Engine for Vietnamese Stock Universe.

Computes required Margin of Safety based on sector baseline, confidence, cyclicality, and leverage.
Clamps required MOS strictly between 20% and 50%.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List
from .archetypes import ArchetypeOverlay, ArchetypeProfile
from .quality_scorer import QualityTier


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


class MarginOfSafetyEngine:
    """Calculates dynamic required margin of safety and validates value investment status."""

    @classmethod
    def calculate(
        cls,
        archetype_prof: ArchetypeProfile,
        quality_tier: QualityTier,
        actual_base_mos: float,
        has_solvency_risk: bool = False,
        confidence_is_low: bool = False,
    ) -> MOSCalculation:
        base_mos = archetype_prof.base_required_mos * 100.0
        
        # Penalties
        cyclicality_pen = 10.0 if ArchetypeOverlay.HIGH_CYCLICALITY in archetype_prof.overlays else 0.0
        leverage_pen = 10.0 if has_solvency_risk else (5.0 if ArchetypeOverlay.CAPITAL_INTENSIVE in archetype_prof.overlays else 0.0)
        confidence_pen = 10.0 if confidence_is_low else 0.0
        
        # Discounts
        predictability_disc = 5.0 if quality_tier in (QualityTier.EXCEPTIONAL, QualityTier.HIGH_QUALITY) else 0.0
        
        raw_required = base_mos + cyclicality_pen + leverage_pen + confidence_pen - predictability_disc
        # Clamp strictly between 20.0% and 50.0%
        clamped_required = max(20.0, min(50.0, raw_required))
        
        satisfied = actual_base_mos >= clamped_required
        
        if satisfied and quality_tier in (QualityTier.EXCEPTIONAL, QualityTier.HIGH_QUALITY) and not has_solvency_risk:
            verdict = "HIGH_CONVICTION_VALUE"
        elif satisfied:
            verdict = "ATTRACTIVE"
        elif actual_base_mos >= -15.0:
            verdict = "FAIRLY_VALUED"
        elif quality_tier == QualityTier.LOW_QUALITY:
            verdict = "AVOID_QUALITY"
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
        )
