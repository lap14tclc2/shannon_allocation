"""
Internal Fundamental Financial Metrics Calculator (QFD-510).

Computes core metrics directly from standardized canonical facts:
- Profitability: Gross Margin, Operating Margin, Net Margin, ROE
- Leverage: Debt-to-Equity, Total Debt / Total Assets
- Cash Flow: Free Cash Flow (FCF = Operating Cash Flow - Capex)
- Banking metrics: Net Interest Margin (NII / Earning Assets), NPL ratio
- Securities metrics: Margin Loan ratio
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional
from .models import CanonicalFact, EntityType, QualityStatus


@dataclass
class ComputedMetric:
    metric_code: str
    symbol: str
    fiscal_year: int
    fiscal_quarter: Optional[int]
    value: Decimal
    formula_version: str
    input_fact_ids: List[str]
    quality_status: QualityStatus
    computed_at: str


def compute_metrics(
    facts: List[CanonicalFact],
    symbol: str,
    year: int,
    quarter: Optional[int],
    entity_type: EntityType = EntityType.NORMAL_ENTERPRISE,
) -> Dict[str, ComputedMetric]:
    """
    Deterministically compute key financial ratios from a set of canonical facts.
    """
    # Index facts by line item code
    facts_by_code: Dict[str, CanonicalFact] = {
        f.identity.line_item_code: f
        for f in facts
        if f.identity.fiscal_year == year and f.identity.fiscal_quarter == quarter
    }

    metrics: Dict[str, ComputedMetric] = {}

    def get_val(code: str) -> Optional[Decimal]:
        f = facts_by_code.get(code)
        return f.value if f else None

    def make_metric(code: str, val: Decimal, input_codes: List[str], version: str = "1.0.0") -> ComputedMetric:
        input_facts = [facts_by_code[c] for c in input_codes if c in facts_by_code]
        input_ids = [f.canonical_fact_id for f in input_facts]
        # Aggregate quality status
        statuses = [f.quality_status for f in input_facts]
        if any(s == QualityStatus.CONFLICT for s in statuses):
            agg_status = QualityStatus.CONFLICT
        elif any(s == QualityStatus.SINGLE_SOURCE for s in statuses):
            agg_status = QualityStatus.SINGLE_SOURCE
        else:
            agg_status = QualityStatus.CROSS_SOURCE_VERIFIED

        return ComputedMetric(
            metric_code=code,
            symbol=symbol,
            fiscal_year=year,
            fiscal_quarter=quarter,
            value=val,
            formula_version=f"qfd-metric-{code.lower()}@{version}",
            input_fact_ids=input_ids,
            quality_status=agg_status,
            computed_at="",
        )

    # 1. Normal Enterprise Metrics
    if entity_type == EntityType.NORMAL_ENTERPRISE:
        rev = get_val("IS.REVENUE.NET")
        cogs = get_val("IS.COGS")
        gp = get_val("IS.PROFIT.GROSS")
        np = get_val("IS.PROFIT.NET")
        eq = get_val("BS.EQUITY.TOTAL")
        debt = get_val("BS.DEBT.TOTAL")
        cf_ops = get_val("CF.OPERATING.NET")
        capex = get_val("CF.CAPEX")

        # Gross Margin = (Gross Profit / Net Revenue) * 100
        if rev and rev != Decimal("0") and gp is not None:
            metrics["RATIO.MARGIN.GROSS"] = make_metric("RATIO.MARGIN.GROSS", (gp / rev) * Decimal("100"), ["IS.REVENUE.NET", "IS.PROFIT.GROSS"])
        elif rev and rev != Decimal("0") and cogs is not None:
            calc_gp = rev - cogs
            metrics["RATIO.MARGIN.GROSS"] = make_metric("RATIO.MARGIN.GROSS", (calc_gp / rev) * Decimal("100"), ["IS.REVENUE.NET", "IS.COGS"])

        # Net Margin = (Net Profit / Net Revenue) * 100
        if rev and rev != Decimal("0") and np is not None:
            metrics["RATIO.MARGIN.NET"] = make_metric("RATIO.MARGIN.NET", (np / rev) * Decimal("100"), ["IS.REVENUE.NET", "IS.PROFIT.NET"])

        # ROE = (Net Profit / Equity) * 100
        if eq and eq != Decimal("0") and np is not None:
            metrics["RATIO.ROE"] = make_metric("RATIO.ROE", (np / eq) * Decimal("100"), ["IS.PROFIT.NET", "BS.EQUITY.TOTAL"])

        # Debt / Equity
        if eq and eq != Decimal("0") and debt is not None:
            metrics["RATIO.DEBT_TO_EQUITY"] = make_metric("RATIO.DEBT_TO_EQUITY", debt / eq, ["BS.DEBT.TOTAL", "BS.EQUITY.TOTAL"])

        # Free Cash Flow (FCF = Operating Cash Flow - Capex)
        if cf_ops is not None and capex is not None:
            metrics["CF.FCF"] = make_metric("CF.FCF", cf_ops - capex, ["CF.OPERATING.NET", "CF.CAPEX"])

    # 2. Banking Metrics
    elif entity_type == EntityType.BANK:
        np = get_val("IS.PROFIT.NET")
        eq = get_val("BS.EQUITY.TOTAL")
        nii = get_val("IS.BANK.NII")
        loans = get_val("BS.BANK.LOANS_CUSTOMER")
        npl = get_val("BS.BANK.NPL")

        if eq and eq != Decimal("0") and np is not None:
            metrics["RATIO.BANK.ROE"] = make_metric("RATIO.BANK.ROE", (np / eq) * Decimal("100"), ["IS.PROFIT.NET", "BS.EQUITY.TOTAL"])

        # NPL Ratio = NPL / Total Customer Loans
        if loans and loans != Decimal("0") and npl is not None:
            metrics["RATIO.BANK.NPL_RATIO"] = make_metric("RATIO.BANK.NPL_RATIO", (npl / loans) * Decimal("100"), ["BS.BANK.NPL", "BS.BANK.LOANS_CUSTOMER"])

    # 3. Securities Metrics
    elif entity_type == EntityType.SECURITIES:
        np = get_val("IS.PROFIT.NET")
        eq = get_val("BS.EQUITY.TOTAL")
        margin = get_val("BS.SEC.MARGIN_LOANS")

        if eq and eq != Decimal("0") and np is not None:
            metrics["RATIO.SEC.ROE"] = make_metric("RATIO.SEC.ROE", (np / eq) * Decimal("100"), ["IS.PROFIT.NET", "BS.EQUITY.TOTAL"])
        if eq and eq != Decimal("0") and margin is not None:
            metrics["RATIO.SEC.MARGIN_TO_EQUITY"] = make_metric("RATIO.SEC.MARGIN_TO_EQUITY", margin / eq, ["BS.SEC.MARGIN_LOANS", "BS.EQUITY.TOTAL"])

    return metrics
