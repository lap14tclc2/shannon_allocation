"""
Buffett-Munger Business Quality Scorer & Hard Reject Engine (Thang 100).

Evaluates 7 pillars of Business Quality:
1. Predictability (10 pts)
2. Moat (20 pts)
3. Return Economics (20 pts)
4. Financial Strength (15 pts)
5. Cash Quality (10 pts)
6. Capital Allocation (15 pts)
7. Governance (10 pts)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from .archetypes import EconomicArchetype, ArchetypeOverlay, ArchetypeProfile


class QualityTier(str, Enum):
    EXCEPTIONAL = "EXCEPTIONAL"  # 90-100
    HIGH_QUALITY = "HIGH_QUALITY"  # 80-89
    INVESTABLE = "INVESTABLE"  # 70-79
    WATCH = "WATCH"  # 60-69
    LOW_QUALITY = "LOW_QUALITY"  # < 60


class HardRejectReason(str, Enum):
    CIRCLE_OF_COMPETENCE_FAIL = "CIRCLE_OF_COMPETENCE_FAIL"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
    ACCOUNTING_UNRELIABLE = "ACCOUNTING_UNRELIABLE"
    SOLVENCY_RISK = "SOLVENCY_RISK"
    UNNORMALIZABLE_EARNINGS = "UNNORMALIZABLE_EARNINGS"
    EXCESSIVE_DILUTION = "EXCESSIVE_DILUTION"


@dataclass
class QualityScorecard:
    total_score: int  # 0-100
    tier: QualityTier
    predictability_score: int  # /10
    moat_score: int  # /20
    return_economics_score: int  # /20
    financial_strength_score: int  # /15
    cash_quality_score: int  # /10
    capital_allocation_score: int  # /15
    governance_score: int  # /10
    hard_rejects: List[HardRejectReason] = field(default_factory=list)
    summary: str = ""


class QualityScorer:
    """Computes deterministic 100-point Buffett Quality Score."""

    @classmethod
    def evaluate(
        cls,
        archetype_prof: ArchetypeProfile,
        financial_history_10y: List[Dict[str, Any]],
        five_year_avg_roe: Optional[float],
        five_year_avg_cash_conversion: Optional[float],
        net_debt_vnd: float,
        latest_cfo: float,
        true_dilution_5y_pct: Optional[float],
    ) -> QualityScorecard:
        hard_rejects: List[HardRejectReason] = []
        
        # Check history depth
        valid_years = [h for h in financial_history_10y if h.get("net_profit") is not None]
        if len(valid_years) < 3:
            hard_rejects.append(HardRejectReason.DATA_INSUFFICIENT)

        is_bank = archetype_prof.archetype == EconomicArchetype.COMMERCIAL_BANK
        is_compounder = ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER in archetype_prof.overlays
        is_cyclical = ArchetypeOverlay.HIGH_CYCLICALITY in archetype_prof.overlays

        # 1. Predictability (10 pts)
        pred_pts = 5
        if is_compounder:
            pred_pts = 10
        elif is_bank:
            pred_pts = 8
        elif is_cyclical:
            pred_pts = 4
        else:
            pred_pts = 7

        # 2. Moat (20 pts)
        moat_pts = 8
        if five_year_avg_roe:
            if five_year_avg_roe >= 22.0:
                moat_pts = 20
            elif five_year_avg_roe >= 17.0:
                moat_pts = 16
            elif five_year_avg_roe >= 13.0:
                moat_pts = 12
            else:
                moat_pts = 6

        # 3. Return Economics & iROIC (20 pts)
        ret_pts = 10
        if five_year_avg_roe:
            if five_year_avg_roe >= 20.0:
                ret_pts = 20
            elif five_year_avg_roe >= 15.0:
                ret_pts = 16
            elif five_year_avg_roe >= 10.0:
                ret_pts = 10
            else:
                ret_pts = 4

        # 4. Financial Strength (15 pts)
        fin_pts = 10
        if is_bank:
            fin_pts = 13
        elif net_debt_vnd <= 0:
            fin_pts = 15  # Net cash fortress
        elif latest_cfo > 0:
            payback = net_debt_vnd / latest_cfo
            if payback < 2.0:
                fin_pts = 14
            elif payback < 4.0:
                fin_pts = 10
            else:
                fin_pts = 5
        else:
            fin_pts = 4
            if net_debt_vnd > 10e12:
                hard_rejects.append(HardRejectReason.SOLVENCY_RISK)

        # 5. Cash Quality (10 pts)
        cash_pts = 7
        if is_bank:
            cash_pts = 8  # Standardized for banks
        elif five_year_avg_cash_conversion:
            if five_year_avg_cash_conversion >= 90:
                cash_pts = 10
            elif five_year_avg_cash_conversion >= 70:
                cash_pts = 8
            elif five_year_avg_cash_conversion >= 40:
                cash_pts = 5
            else:
                cash_pts = 2

        # 6. Capital Allocation (15 pts)
        cap_pts = 10
        if true_dilution_5y_pct is not None:
            if true_dilution_5y_pct < 2.0:
                cap_pts = 15  # Outstanding ownership protection
            elif true_dilution_5y_pct < 8.0:
                cap_pts = 12
            elif true_dilution_5y_pct < 20.0:
                cap_pts = 7
            else:
                cap_pts = 3
                hard_rejects.append(HardRejectReason.EXCESSIVE_DILUTION)

        # 7. Governance (10 pts)
        gov_pts = 8  # Standard listed baseline

        total = pred_pts + moat_pts + ret_pts + fin_pts + cash_pts + cap_pts + gov_pts

        if total >= 90:
            tier = QualityTier.EXCEPTIONAL
        elif total >= 80:
            tier = QualityTier.HIGH_QUALITY
        elif total >= 70:
            tier = QualityTier.INVESTABLE
        elif total >= 60:
            tier = QualityTier.WATCH
        else:
            tier = QualityTier.LOW_QUALITY

        summary = (
            f"Điểm Chất lượng Doanh nghiệp: {total}/100 ({tier.value}). "
            f"Moat: {moat_pts}/20, Sinh lời: {ret_pts}/20, Tài chính: {fin_pts}/15, Phân bổ vốn: {cap_pts}/15."
        )

        return QualityScorecard(
            total_score=total,
            tier=tier,
            predictability_score=pred_pts,
            moat_score=moat_pts,
            return_economics_score=ret_pts,
            financial_strength_score=fin_pts,
            cash_quality_score=cash_pts,
            capital_allocation_score=cap_pts,
            governance_score=gov_pts,
            hard_rejects=hard_rejects,
            summary=summary,
        )
