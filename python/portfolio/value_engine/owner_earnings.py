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
from typing import Dict, List, Optional, Tuple
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
        owner_earnings = net_income + da_val - maint_capex + wc_change

        source_ids = [usable_facts[code].canonical_fact_id for code in required_codes]
        desc = (
            f"Estimated Normalized Owner Earnings = Net Income ({net_income:,.0f}) + D&A ({da_val:,.0f}) "
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
        )

    @classmethod
    def calculate_cycle_normalized(
        cls,
        facts: List[CanonicalFact],
        latest_fiscal_year: int,
        lookback_years: int = 5,
    ) -> OwnerEarningsBridge:
        """
        Calculates 5-year cycle-normalized owner earnings for cyclical enterprises (HPG, DGC, etc.).
        Averages multi-year owner earnings to eliminate peak/trough bias.
        """
        oe_list: List[Decimal] = []
        bridges: List[OwnerEarningsBridge] = []
        for y in range(latest_fiscal_year - lookback_years + 1, latest_fiscal_year + 1):
            try:
                b = cls.calculate(facts, fiscal_year=y)
                if b.owner_earnings > Decimal("0"):
                    oe_list.append(b.owner_earnings)
                    bridges.append(b)
            except Exception:
                continue

        if not oe_list:
            # Fallback to latest year
            return cls.calculate(facts, fiscal_year=latest_fiscal_year)

        avg_oe = sum(oe_list) / Decimal(str(len(oe_list)))
        latest_b = bridges[-1] if bridges else cls.calculate(facts, fiscal_year=latest_fiscal_year)

        desc = (
            f"Normalized {len(oe_list)}Y Mid-Cycle Owner Earnings = {avg_oe:,.0f} VND "
            f"(Averaged across {lookback_years}-year business cycle to remove commodity/cyclical distortion)."
        )
        return OwnerEarningsBridge(
            net_income=sum(b.net_income for b in bridges) / Decimal(str(len(bridges))),
            depreciation_amortization=latest_b.depreciation_amortization,
            maintenance_capex=latest_b.maintenance_capex,
            growth_capex_estimated=latest_b.growth_capex_estimated,
            working_capital_change=latest_b.working_capital_change,
            owner_earnings=avg_oe,
            formula_description=desc,
            source_fact_ids=latest_b.source_fact_ids,
        )
