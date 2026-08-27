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
        # The maintenance/growth split is only a bounded interpretation of two
        # reported cash-flow facts, never a synthetic percentage fallback.
        maint_capex = min(capex, abs(da_val))
        growth_capex = max(Decimal("0"), capex - maint_capex)
        cf_ops = usable_facts["CF.OPERATING.NET"].value
        wc_change = cf_ops - (net_income + da_val)
        owner_earnings = net_income + da_val - maint_capex + wc_change

        source_ids = [usable_facts[code].canonical_fact_id for code in required_codes]
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
