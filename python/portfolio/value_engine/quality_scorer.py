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
    moat_evidence: Dict[str, Any] = field(default_factory=dict)
    capital_allocation_evidence: Dict[str, Any] = field(default_factory=dict)


class QualityScorer:
    """Computes deterministic 100-point Buffett Quality Score."""

    @staticmethod
    def _stat(series: List[Optional[float]]) -> Dict[str, Optional[float]]:
        vals = [v for v in series if v is not None]
        if not vals:
            return {"n": 0, "mean": None, "median": None, "std": None, "cv": None, "min": None, "max": None}
        ordered = sorted(vals)
        n = len(ordered)
        median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0
        mean = sum(ordered) / n
        var = sum((v - mean) ** 2 for v in ordered) / n
        std = var ** 0.5
        cv = (std / abs(mean) * 100.0) if mean else None
        return {"n": n, "mean": mean, "median": median, "std": std, "cv": cv, "min": ordered[0], "max": ordered[-1]}

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
        dilution_classification: Optional[str] = None,
        dilution_evidence: Optional[Dict[str, Any]] = None,
        unexplained_share_change_pct: Optional[float] = None,
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
        pred_pts = 7
        if is_compounder:
            pred_pts = 10
        elif is_bank:
            pred_pts = 8
        elif is_cyclical:
            pred_pts = 4

        # ---- Moat evidence breakdown (audit P1-5) -------------------------------
        revenue_series = [h.get("revenue") for h in financial_history_10y]
        np_series = [h.get("net_profit") for h in financial_history_10y]
        roe_series = [h.get("roe") for h in financial_history_10y]
        cfo_series = [h.get("operating_cash_flow") for h in financial_history_10y]

        margins = []
        for h in financial_history_10y:
            rev = h.get("revenue")
            np_ = h.get("net_profit")
            if rev and np_ and rev > 0:
                margins.append(float(np_) / float(rev) * 100.0)

        roe_stat = cls._stat(roe_series)
        margin_stat = cls._stat(margins)
        rev_stat = cls._stat(revenue_series)

        # Pricing Power (0-4): level of net margin + stability
        pricing = 0
        if margin_stat["n"] >= 3:
            mm = margin_stat["median"] or 0
            cv = margin_stat["cv"] or 999
            if mm >= 12:
                pricing = 4
            elif mm >= 8:
                pricing = 3
            elif mm >= 4:
                pricing = 2
            else:
                pricing = 1
            if cv > 45:  # very unstable margins undermine pricing power
                pricing = max(0, pricing - 1)
        # Cost Advantage (0-4): margin spread + cash conversion efficiency
        cost_adv = 0
        if margin_stat["n"] >= 3:
            mm = margin_stat["median"] or 0
            conv = five_year_avg_cash_conversion
            if mm >= 12:
                cost_adv = 3
            elif mm >= 7:
                cost_adv = 2
            else:
                cost_adv = 1
            if conv is not None and conv >= 85:
                cost_adv += 1
            cost_adv = min(4, cost_adv)
        # Switching Cost (0-4): not directly observable -> inferred from margin persistence
        switch = 0
        if margin_stat["n"] >= 3:
            cv = margin_stat["cv"] or 999
            mm = margin_stat["median"] or 0
            if cv < 25 and mm >= 8:
                switch = 4
            elif cv < 40 and mm >= 6:
                switch = 3
            elif cv < 60:
                switch = 2
            else:
                switch = 1
        # Scale / Distribution (0-4): absolute revenue scale (proxy)
        scale = 0
        if rev_stat["n"] >= 3:
            med_rev = rev_stat["median"] or 0
            if med_rev >= 30e12:
                scale = 4
            elif med_rev >= 10e12:
                scale = 3
            elif med_rev >= 3e12:
                scale = 2
            elif med_rev >= 1e12:
                scale = 1
        # ROIC / ROE Persistence (0-4): Return level + stability
        persist = 0
        if roe_stat["n"] >= 4:
            rmed = roe_stat["median"] or 0
            rcv = roe_stat["cv"] or 999
            if rmed >= 20 and rcv < 30:
                persist = 4
            elif rmed >= 15:
                persist = 3
            elif rmed >= 10:
                persist = 2
            else:
                persist = 1
        # Durability (0-4): history depth + positive earnings years
        durable = 0
        pos_years = sum(1 for v in np_series if v is not None and v > 0)
        hist_len = len(financial_history_10y)
        if hist_len >= 9 and pos_years >= hist_len - 1:
            durable = 4
        elif hist_len >= 7:
            durable = 3
        elif hist_len >= 5:
            durable = 2
        elif hist_len >= 3:
            durable = 1

        moat_raw = pricing + cost_adv + switch + scale + persist + durable
        moat_pts = min(20, round(moat_raw * 20 / 24))
        # Guard: ROE alone can never create WIDE moat. Need margin + persistence evidence.
        if margin_stat["n"] < 3 or roe_stat["n"] < 4:
            moat_pts = min(moat_pts, 11)  # cap below NARROW-to-WIDE boundary

        moat_tier_code = "WIDE" if moat_pts >= 14 else "NARROW" if moat_pts >= 8 else "NONE"

        return_persist_key = "roe_persistence" if is_bank else "return_persistence"
        moat_evidence = {
            "pricing_power": {"score": pricing, "max": 4, "median_net_margin_pct": round(margin_stat["median"], 2) if margin_stat["median"] is not None else None, "margin_cv_pct": round(margin_stat["cv"], 1) if margin_stat["cv"] is not None else None},
            "cost_advantage": {"score": cost_adv, "max": 4, "cash_conversion_5y": five_year_avg_cash_conversion},
            "switching_cost": {"score": switch, "max": 4, "inferred_from_margin_persistence": True, "margin_cv_pct": round(margin_stat["cv"], 1) if margin_stat["cv"] is not None else None},
            "scale_distribution": {"score": scale, "max": 4, "median_revenue_vnd": rev_stat["median"]},
            return_persist_key: {"score": persist, "max": 4, "metric": "ROE" if is_bank else "ROIC/ROE", "median_return_pct": round(roe_stat["median"], 2) if roe_stat["median"] is not None else None, "return_cv_pct": round(roe_stat["cv"], 1) if roe_stat["cv"] is not None else None},
            "durability": {"score": durable, "max": 4, "history_years": hist_len, "positive_earnings_years": pos_years},
            "raw_total": moat_raw,
            "total": moat_pts,
            "max": 20,
            "moat_tier": moat_tier_code,
        }
        # -------------------------------------------------------------------------

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

        # 5. Cash Quality (10 pts) -- Banks: ROE persistence; Non-banks: Cash Conversion
        cash_pts = 7
        if is_bank:
            if roe_stat["n"] >= 4 and (roe_stat["median"] or 0) >= 15 and (roe_stat["cv"] or 999) < 35:
                cash_pts = 9
            elif roe_stat["n"] >= 3 and (roe_stat["median"] or 0) >= 12:
                cash_pts = 8
            else:
                cash_pts = 6
        elif five_year_avg_cash_conversion:
            if five_year_avg_cash_conversion >= 90:
                cash_pts = 10
            elif five_year_avg_cash_conversion >= 70:
                cash_pts = 8
            elif five_year_avg_cash_conversion >= 40:
                cash_pts = 5
            else:
                cash_pts = 2

        # 6. Capital Allocation (15 pts) -- Robust iROIC & Reinvestment Efficiency
        cap_pts = 8
        cap_evidence: Dict[str, Any] = {}
        if len(financial_history_10y) >= 4:
            eq_series = [h.get("equity") for h in financial_history_10y]
            np_series2 = [h.get("net_profit") for h in financial_history_10y]
            # Multi-year incremental return on retained equity (cumulative 3Y):
            # iROIC = (NP_latest - NP_t-3) / (Equity_latest - Equity_t-3)
            incr_returns = []
            for i in range(1, len(np_series2)):
                d_np = (np_series2[i] or 0) - (np_series2[i - 1] or 0)
                d_eq = (eq_series[i] or 0) - (eq_series[i - 1] or 0)
                base_eq = eq_series[i - 1] or 0
                # Denominator materiality rule: delta equity must be positive and >= 1% of base equity
                if d_eq and base_eq and (d_eq / base_eq >= 0.01):
                    # Clamp outliers between -50% and +100%
                    ratio = max(-0.5, min(1.0, float(d_np) / float(d_eq)))
                    incr_returns.append(ratio)
            incr_stat = cls._stat(incr_returns)
            incr_med = incr_stat["median"]
            
            # Cumulative 3-year check
            cumul_3y_iroic = None
            if len(np_series2) >= 4 and eq_series[-1] and eq_series[-4]:
                d_np_3y = (np_series2[-1] or 0) - (np_series2[-4] or 0)
                d_eq_3y = (eq_series[-1] or 0) - (eq_series[-4] or 0)
                base_eq_3y = eq_series[-4] or 0
                if d_eq_3y > 0 and base_eq_3y > 0 and (d_eq_3y / base_eq_3y >= 0.03):
                    cumul_3y_iroic = round(float(d_np_3y) / float(d_eq_3y) * 100.0, 2)

            cap_evidence = {
                "incremental_return_median": round(incr_med * 100.0, 2) if incr_med is not None else None,
                "cumulative_3y_iroic_pct": cumul_3y_iroic,
                "incremental_return_years": incr_stat["n"],
                "avg_roe_5y": five_year_avg_roe,
                "economic_dilution_5y_pct": true_dilution_5y_pct,
            }
            if incr_med is not None:
                # Rule P0-5: Capital allocation can NEVER score 15/15 if cumulative iROIC is materially negative (< -5%)
                if cumul_3y_iroic is not None and cumul_3y_iroic < -5.0:
                    cap_pts = 4  # Material value destruction
                elif incr_med < -0.05:
                    cap_pts = 5
                elif (incr_med >= 0.15 or (cumul_3y_iroic and cumul_3y_iroic >= 15.0)) and (true_dilution_5y_pct is None or true_dilution_5y_pct < 2.5):
                    # Rule: Conglomerates/Plantations require segment-level support to score 15/15
                    if archetype_prof and archetype_prof.archetype.value in ("CONGLOMERATE", "RUBBER_PLANTATION", "HOLDING_COMPANY", "CONGLOMERATE_HOLDING"):
                        cap_pts = 12
                        cap_evidence["segment_support_required"] = "Tập đoàn/Đa mảng tài sản: điểm phân bổ vốn giới hạn 12/15 khi chưa có số liệu kiểm toán độc lập từng mảng kinh doanh (Segment-based support)."
                    else:
                        cap_pts = 15
                elif incr_med >= 0.10 or (five_year_avg_roe and five_year_avg_roe >= 14.0 and (true_dilution_5y_pct is None or true_dilution_5y_pct < 3.0)):
                    cap_pts = 13
                elif incr_med >= 0.05:
                    cap_pts = 10
                elif incr_med >= 0.0:
                    cap_pts = 7
                else:
                    cap_pts = 4
        elif true_dilution_5y_pct is not None:
            # fallback when history depth insufficient
            if true_dilution_5y_pct < 2.0:
                cap_pts = 12
            elif true_dilution_5y_pct < 8.0:
                cap_pts = 9
            elif true_dilution_5y_pct < 20.0:
                cap_pts = 5
            else:
                cap_pts = 2
                # P0 audit (2026-08-29): only proven economic dilution (events
                # present) may hard-reject here; unexplained residual growth keeps
                # the low score but is flagged for verification instead.
                if dilution_classification in (None, "EXCESSIVE_DILUTION", "ECONOMIC_DILUTION"):
                    hard_rejects.append(HardRejectReason.EXCESSIVE_DILUTION)

        # P0 audit (2026-08-29): EXCESSIVE_DILUTION requires event-level evidence.
        # A residual share increase with NO economic events (ESOP/rights/placement/
        # convertible/M&A) is UNEXPLAINED_SHARE_CHANGE, not proven dilution. It must
        # not hard-reject; instead it is surfaced for verification.
        is_excessive_dilution = (
            true_dilution_5y_pct is not None
            and true_dilution_5y_pct >= 20.0
            and dilution_classification in (None, "EXCESSIVE_DILUTION", "ECONOMIC_DILUTION")
        )
        if is_excessive_dilution:
            hard_rejects.append(HardRejectReason.EXCESSIVE_DILUTION)

        # P0/P1 audit (2026-08-29): UNEXPLAINED share change is "unknown", never
        # "verified no dilution". Do not hard-reject (missing evidence is not a
        # proven dilution), but never award a clean 15/15 capital-allocation when a
        # material share increase is unexplained. Cap the score instead.
        if (
            dilution_classification == "UNEXPLAINED_SHARE_CHANGE"
            and (unexplained_share_change_pct is not None)
            and float(unexplained_share_change_pct) >= 20.0
        ):
            cap_pts = min(cap_pts, 10)
            cap_evidence["unexplained_share_change_pct"] = round(float(unexplained_share_change_pct), 1)
            cap_evidence["capital_allocation_uncertainty"] = (
                "UNEXPLAINED_SHARE_CHANGE: tăng số lượng CP chưa được giải thích bởi sự kiện cổ phiếu phi kinh tế; "
                "điểm phân bổ vốn bị giới hạn <= 10/15 cho đến khi có event-level evidence."
            )

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
            moat_evidence=moat_evidence,
            capital_allocation_evidence=cap_evidence,
        )
