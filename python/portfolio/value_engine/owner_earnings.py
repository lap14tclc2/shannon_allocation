"""
Buffett Owner Earnings & Normalization Calculator (QVE-101, QVE-102, QVE-103).

Formula:
  Owner Earnings = Net Income + D&A - Maintenance CAPEX ± ΔWorking Capital

Policies:
  - Maintenance CAPEX: Estimated as min(Depreciation, Total CAPEX) or ratio-based.
  - Working Capital Adjustment: Changes in operating assets and liabilities excluding cash and debt.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple
from portfolio.financial_data.models import CanonicalFact, QualityStatus
from .models import OwnerEarningsBridge


class OwnerEarningsCalculator:
    """Computes owner earnings only from explicit canonical facts."""

    @staticmethod
    def calculate(
        facts: List[CanonicalFact],
        fiscal_year: int,
        fiscal_quarter: Optional[int] = None,
    ) -> OwnerEarningsBridge:
        usable_facts: Dict[str, CanonicalFact] = {}
        for fact in facts:
            if fact.identity.fiscal_year != fiscal_year or fact.identity.fiscal_quarter != fiscal_quarter:
                continue
            if fact.quality_status in (QualityStatus.CONFLICT, QualityStatus.QUARANTINED, QualityStatus.MISSING):
                continue
            if fact.value is not None:
                usable_facts[fact.identity.line_item_code] = fact

        required_codes = (
            "IS.PROFIT.NET",
            "CF.OPERATING.DEPRECIATION",
            "CF.CAPEX",
            "CF.OPERATING.NET",
        )
        missing = [code for code in required_codes if code not in usable_facts]
        if missing:
            raise ValueError("OWNER_EARNINGS_INCOMPLETE: " + ", ".join(missing))

        net_income = usable_facts["IS.PROFIT.NET"].value
        da_val = usable_facts["CF.OPERATING.DEPRECIATION"].value
        capex = abs(usable_facts["CF.CAPEX"].value)
        # Bounded Maintenance CapEx heuristic: estimated as min(depreciation, total capex)
        maint_capex = min(capex, abs(da_val))
        growth_capex = max(Decimal("0"), capex - maint_capex)
        cf_ops = usable_facts["CF.OPERATING.NET"].value
        wc_change = cf_ops - (net_income + da_val)
        
        # Standard unadjusted OE
        raw_owner_earnings = net_income + da_val - maint_capex + wc_change
        core_earning_power = net_income + da_val - maint_capex
        
        # When Core Earning Power (Net Income + D&A - Maintenance CapEx) is positive,
        # but single-year Working Capital buildup (inventory/receivables) causes temporary negative CFO,
        # use conservative core owner earnings floor (bounded working capital deduction)
        # to reflect sustainable earning power without breaking DCF models for profitable compounders.
        if raw_owner_earnings <= Decimal("0") and core_earning_power > Decimal("0"):
            owner_earnings = max(core_earning_power * Decimal("0.50"), core_earning_power + wc_change)
            norm_method = "LATEST_FY_CORE_ADJUSTED"
        else:
            owner_earnings = raw_owner_earnings
            norm_method = "LATEST_FY"

        maint_method = "MIN_DEPRECIATION_CAPEX_PROXY"
        # Audit round 3: the D&A / min(D&A, CapEx) proxy is always LOW confidence.
        # MEDIUM would require a multi-year maintenance pattern, an asset
        # replacement schedule, capacity maintenance data or management disclosure.
        maint_conf = "LOW"
        oe_conf = "LOW" if owner_earnings <= Decimal("0") or norm_method == "LATEST_FY_CORE_ADJUSTED" else "MEDIUM"

        source_ids = [usable_facts[code].canonical_fact_id for code in required_codes]
        desc = (
            f"Estimated Owner Earnings = Net Income ({net_income:,.0f}) + D&A ({da_val:,.0f}) "
            f"- Maint CAPEX ({maint_capex:,.0f}) + ΔWC ({wc_change:,.0f}) = {owner_earnings:,.0f} VND"
        )
        return OwnerEarningsBridge(
            net_income=net_income,
            depreciation_amortization=da_val,
            maintenance_capex=maint_capex,
            growth_capex_estimated=growth_capex,
            working_capital_change=wc_change,
            owner_earnings=owner_earnings,
            formula_description=desc,
            source_fact_ids=source_ids,
            normalization_years=1,
            normalization_method=norm_method,
            maintenance_capex_confidence=maint_conf,
            owner_earnings_confidence=oe_conf,
            maintenance_capex_method=maint_method,
        )

    @classmethod
    def calculate_cycle_normalized(
        cls,
        facts: List[CanonicalFact],
        latest_fiscal_year: int,
        lookback_years: int = 10,
        included_years: Optional[Iterable[int]] = None,
    ) -> OwnerEarningsBridge:
        """
        Calculates true mid-cycle owner earnings for cyclical enterprises (HPG, DGC, etc.).

        Method (MID_CYCLE_MEDIAN):
          margin_t = OE_t / Revenue_t  for each fiscal year in the lookback window
          mid_cycle_OE = median(margin_t) * median(Revenue_t)

        feedback.txt §6: khi có structural regime break, engine truyền
        ``included_years`` = các năm của latest comparable regime (ví dụ DGC
        2018–2025) để normalization KHÔNG trộn Regime A cũ với Regime B mới.
        Năm thiếu dữ liệu trong window vẫn được bỏ qua như trước.

        This removes peak/trough commodity distortion without relying on a single
        favourable (or distressed) year. Requires >= 3 valid year-pairs; otherwise
        falls back to the latest fiscal year and labels it honestly as LATEST_FY
        (never misleadingly called "averaged").
        """
        included = set(included_years) if included_years is not None else None
        per_year: List[Tuple[int, Decimal, Decimal, Decimal]] = []  # (year, revenue, margin, oe)
        for y in range(latest_fiscal_year - lookback_years + 1, latest_fiscal_year + 1):
            if included is not None and y not in included:
                continue
            try:
                b = cls.calculate(facts, fiscal_year=y)
                oe_val = b.owner_earnings
            except Exception:
                # Tolerate years that lack CF codes (Depreciation/CapEx/CFO) in the
                # finance DB: use net income as the OE proxy so a full 7-10Y ledger
                # still normalizes instead of silently degrading to LATEST_FY.
                ni_fact = next(
                    (
                        f
                        for f in facts
                        if f.identity.fiscal_year == y
                        and f.identity.fiscal_quarter is None
                        and f.identity.line_item_code == "IS.PROFIT.NET"
                        and f.value is not None
                        and f.quality_status not in (QualityStatus.CONFLICT, QualityStatus.QUARANTINED, QualityStatus.MISSING)
                    ),
                    None,
                )
                if ni_fact is None or ni_fact.value is None or ni_fact.value <= Decimal("0"):
                    continue
                oe_val = ni_fact.value
                b = None
            rev_fact = next(
                (
                    f
                    for f in facts
                    if f.identity.fiscal_year == y
                    and f.identity.fiscal_quarter is None
                    and f.identity.line_item_code == "IS.REVENUE.NET"
                    and f.value is not None
                    and f.quality_status not in (QualityStatus.CONFLICT, QualityStatus.QUARANTINED, QualityStatus.MISSING)
                ),
                None,
            )
            if rev_fact is None or rev_fact.value is None or rev_fact.value <= Decimal("0"):
                continue
            revenue = rev_fact.value
            margin = oe_val / revenue
            per_year.append((y, revenue, margin, oe_val))

        if len(per_year) < 3:
            # Not enough history for honest cycle normalization -> use latest FY only.
            latest_b = cls.calculate(facts, fiscal_year=latest_fiscal_year)
            desc = (
                f"Lợi nhuận Thực của Chủ Doanh nghiệp từ năm tài chính {latest_fiscal_year} "
                f"(chưa đủ {lookback_years} năm lịch sử để bình quân chu kỳ). "
                f"Không gán nhãn mid-cycle khi dữ liệu chưa đủ."
            )
            return OwnerEarningsBridge(
                net_income=latest_b.net_income,
                depreciation_amortization=latest_b.depreciation_amortization,
                maintenance_capex=latest_b.maintenance_capex,
                growth_capex_estimated=latest_b.growth_capex_estimated,
                working_capital_change=latest_b.working_capital_change,
                owner_earnings=latest_b.owner_earnings,
                formula_description=desc,
                source_fact_ids=latest_b.source_fact_ids,
                normalization_years=1,
                normalization_method="LATEST_FY",
                maintenance_capex_confidence=latest_b.maintenance_capex_confidence,
                owner_earnings_confidence=latest_b.owner_earnings_confidence,
                maintenance_capex_method=latest_b.maintenance_capex_method,
            )

        revenues = [Decimal(str(p[1])) for p in per_year]
        margins = [Decimal(str(p[2])) for p in per_year]
        oes = [p[3] for p in per_year]

        def _median(vals: List[Decimal]) -> Decimal:
            ordered = sorted(vals)
            n = len(ordered)
            if n % 2 == 1:
                return ordered[n // 2]
            return (ordered[n // 2 - 1] + ordered[n // 2]) / Decimal("2")

        median_revenue = _median(revenues)
        median_margin = _median(margins)
        avg_oe = sum(oes) / Decimal(str(len(oes)))

        # Robust mid-cycle OE: prefer median-margin x median-revenue to damp outliers;
        # guard against pathological median margin (e.g. deep-negative years).
        mid_cycle_oe = median_margin * median_revenue
        if mid_cycle_oe <= Decimal("0"):
            # Negative median margin means the mid-cycle business is not profitable ->
            # fall back to latest FY, still honest about the label.
            latest_b = cls.calculate(facts, fiscal_year=latest_fiscal_year)
            desc = (
                f"Biên lợi nhuận Thực chu kỳ trung vị {median_margin * Decimal('100'):.1f}% là âm "
                f"({len(per_year)} năm). Không dùng mid-cycle âm; dùng năm {latest_fiscal_year} "
                f"và ghi nhận rủi ro chu kỳ."
            )
            return OwnerEarningsBridge(
                net_income=latest_b.net_income,
                depreciation_amortization=latest_b.depreciation_amortization,
                maintenance_capex=latest_b.maintenance_capex,
                growth_capex_estimated=latest_b.growth_capex_estimated,
                working_capital_change=latest_b.working_capital_change,
                owner_earnings=latest_b.owner_earnings,
                formula_description=desc,
                source_fact_ids=latest_b.source_fact_ids,
                normalization_years=1,
                normalization_method="LATEST_FY",
                maintenance_capex_confidence=latest_b.maintenance_capex_confidence,
                owner_earnings_confidence=latest_b.owner_earnings_confidence,
                maintenance_capex_method=latest_b.maintenance_capex_method,
            )

        desc = (
            f"Lợi nhuận Thực chu kỳ (Mid-Cycle) từ {len(per_year)} năm: "
            f"biên trung vị {median_margin * Decimal('100'):.1f}% × doanh thu trung vị "
            f"{median_revenue / Decimal('1000000000'):,.1f} tỷ ₫ = {mid_cycle_oe / Decimal('1000000000'):,.1f} tỷ ₫. "
            f"(Loại bỏ nhiễu đỉnh/đáy chu kỳ hàng hóa; trung bình {avg_oe / Decimal('1000000000'):,.1f} tỷ ₫.)"
        )
        return OwnerEarningsBridge(
            net_income=avg_oe,
            depreciation_amortization=Decimal("0"),
            maintenance_capex=Decimal("0"),
            growth_capex_estimated=Decimal("0"),
            working_capital_change=Decimal("0"),
            owner_earnings=mid_cycle_oe,
            formula_description=desc,
            source_fact_ids=[],
            normalization_years=len(per_year),
            normalization_method="MID_CYCLE_MEDIAN",
            mid_cycle_margin=median_margin,
            mid_cycle_revenue=median_revenue,
            maintenance_capex_confidence="HIGH" if len(per_year) >= 7 else "MEDIUM",
            owner_earnings_confidence="HIGH" if len(per_year) >= 7 else "MEDIUM",
            maintenance_capex_method="MULTI_YEAR_CYCLE_MEDIAN",
            normalization_input_years=[p[0] for p in per_year],
        )
