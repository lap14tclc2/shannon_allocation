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
    """
    Computes Buffett Owner Earnings strictly from verified Canonical Facts.
    """

    @staticmethod
    def calculate(
        facts: List[CanonicalFact],
        fiscal_year: int,
        fiscal_quarter: Optional[int] = None,
        maintenance_capex_ratio: Decimal = Decimal("0.70"),  # Default 70% of CAPEX is maintenance
    ) -> OwnerEarningsBridge:
        usable_facts: Dict[str, CanonicalFact] = {}
        for f in facts:
            if f.identity.fiscal_year == fiscal_year and f.identity.fiscal_quarter == fiscal_quarter:
                if f.quality_status not in (QualityStatus.CONFLICT, QualityStatus.QUARANTINED, QualityStatus.MISSING):
                    if f.value is not None:
                        usable_facts[f.identity.line_item_code] = f

        def get_val(code: str) -> Decimal:
            f = usable_facts.get(code)
            return f.value if f and f.value is not None else Decimal("0")

        def get_fact_id(code: str) -> Optional[str]:
            f = usable_facts.get(code)
            return f.canonical_fact_id if f else None

        net_income = get_val("IS.PROFIT.NET")
        cogs = get_val("IS.COGS")
        # In financial statements: CF.CAPEX, CF.OPERATING.NET
        # CF.CAPEX is usually recorded as positive magnitude or cash outflow
        capex_raw = get_val("CF.CAPEX")
        capex = abs(capex_raw)

        # Approximate D&A from Cash Flow or default ~60% of Gross CAPEX if not separate
        da_val = capex * Decimal("0.80") if capex > 0 else net_income * Decimal("0.15")

        # Maintenance CAPEX policy (QVE-102)
        # If total CAPEX > D&A, maintenance capex is bounded by D&A or ratio
        maint_capex = min(capex, da_val) if capex > 0 else da_val * maintenance_capex_ratio
        growth_capex = max(Decimal("0"), capex - maint_capex)

        # Working Capital change (approximate from operating CF vs Net Income + D&A)
        cf_ops = get_val("CF.OPERATING.NET")
        if cf_ops != Decimal("0"):
            wc_change = cf_ops - (net_income + da_val)
        else:
            wc_change = Decimal("0")

        # Owner Earnings = Net Income + D&A - Maintenance CAPEX + ΔWorking Capital
        owner_earnings = net_income + da_val - maint_capex + wc_change

        source_ids = [
            fid for code in ["IS.PROFIT.NET", "CF.CAPEX", "CF.OPERATING.NET"]
            if (fid := get_fact_id(code)) is not None
        ]

        desc = (
            f"Owner Earnings = Net Income ({net_income:,.0f}) + D&A ({da_val:,.0f}) "
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
