"""
Internal Fundamental Financial Metrics Calculator (QFD-510).

Invariants enforced:
1. Rejects / Skips any calculation where input facts have QualityStatus CONFLICT or QUARANTINED.
2. Formats computed_at with exact UTC ISO-8601 timestamp.
3. Ratios explicitly versioned with formula code and input fact IDs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
    Deterministically compute key financial ratios from canonical facts.
    Strictly skips inputs with status CONFLICT or QUARANTINED (QFD-510).
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    
    # Filter facts by period and exclude CONFLICT / QUARANTINED / MISSING
    usable_facts: Dict[str, CanonicalFact] = {}
    for f in facts:
        if f.identity.fiscal_year == year and f.identity.fiscal_quarter == quarter:
            if f.quality_status not in (QualityStatus.CONFLICT, QualityStatus.QUARANTINED, QualityStatus.MISSING):
                if f.value is not None:
                    usable_facts[f.identity.line_item_code] = f

    metrics: Dict[str, ComputedMetric] = {}

    def get_fact(code: str) -> Optional[CanonicalFact]:
        return usable_facts.get(code)

    def make_metric(code: str, val: Decimal, required_codes: List[str], version: str = "1.0.0") -> Optional[ComputedMetric]:
        input_facts = [get_fact(c) for c in required_codes]
        if any(f is None for f in input_facts):
            return None  # Required input fact is missing or conflicted
        
        input_ids = [f.canonical_fact_id for f in input_facts if f]
        statuses = [f.quality_status for f in input_facts if f]
        
        if any(s == QualityStatus.SINGLE_SOURCE for s in statuses):
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
            computed_at=now_utc,
        )

    # 1. Normal Enterprise Metrics
    if entity_type == EntityType.NORMAL_ENTERPRISE:
        f_rev = get_fact("IS.REVENUE.NET")
        f_gp = get_fact("IS.PROFIT.GROSS")
        f_np = get_fact("IS.PROFIT.NET")
        f_eq = get_fact("BS.EQUITY.TOTAL")
        f_debt = get_fact("BS.DEBT.TOTAL")
        f_cf_ops = get_fact("CF.OPERATING.NET")
        f_capex = get_fact("CF.CAPEX")

        # Gross Margin = (Gross Profit / Net Revenue) * 100
        if f_rev and f_gp and f_rev.value != Decimal("0"):
            m = make_metric("RATIO.MARGIN.GROSS", (f_gp.value / f_rev.value) * Decimal("100"), ["IS.REVENUE.NET", "IS.PROFIT.GROSS"])
            if m: metrics[m.metric_code] = m

        # Net Margin = (Net Profit / Net Revenue) * 100
        if f_rev and f_np and f_rev.value != Decimal("0"):
            m = make_metric("RATIO.MARGIN.NET", (f_np.value / f_rev.value) * Decimal("100"), ["IS.REVENUE.NET", "IS.PROFIT.NET"])
            if m: metrics[m.metric_code] = m

        # ROE = (Net Profit / Equity) * 100
        if f_eq and f_np and f_eq.value != Decimal("0"):
            m = make_metric("RATIO.ROE", (f_np.value / f_eq.value) * Decimal("100"), ["IS.PROFIT.NET", "BS.EQUITY.TOTAL"])
            if m: metrics[m.metric_code] = m

        # Debt / Equity
        if f_eq and f_debt and f_eq.value != Decimal("0"):
            m = make_metric("RATIO.DEBT_TO_EQUITY", f_debt.value / f_eq.value, ["BS.DEBT.TOTAL", "BS.EQUITY.TOTAL"])
            if m: metrics[m.metric_code] = m

        # Free Cash Flow (FCF = Operating Cash Flow - Capex)
        if f_cf_ops and f_capex:
            m = make_metric("CF.FCF", f_cf_ops.value - f_capex.value, ["CF.OPERATING.NET", "CF.CAPEX"])
            if m: metrics[m.metric_code] = m

    # 2. Banking Metrics
    elif entity_type == EntityType.BANK:
        f_np = get_fact("IS.PROFIT.NET")
        f_eq = get_fact("BS.EQUITY.TOTAL")
        f_loans = get_fact("BS.BANK.LOANS_CUSTOMER")
        f_npl = get_fact("BS.BANK.NPL")

        if f_eq and f_np and f_eq.value != Decimal("0"):
            m = make_metric("RATIO.BANK.ROE", (f_np.value / f_eq.value) * Decimal("100"), ["IS.PROFIT.NET", "BS.EQUITY.TOTAL"])
            if m: metrics[m.metric_code] = m

        # NPL Ratio = NPL / Total Customer Loans
        if f_loans and f_npl and f_loans.value != Decimal("0"):
            m = make_metric("RATIO.BANK.NPL_RATIO", (f_npl.value / f_loans.value) * Decimal("100"), ["BS.BANK.NPL", "BS.BANK.LOANS_CUSTOMER"])
            if m: metrics[m.metric_code] = m

    # 3. Securities Metrics
    elif entity_type == EntityType.SECURITIES:
        f_np = get_fact("IS.PROFIT.NET")
        f_eq = get_fact("BS.EQUITY.TOTAL")
        f_margin = get_fact("BS.SEC.MARGIN_LOANS")

        if f_eq and f_np and f_eq.value != Decimal("0"):
            m = make_metric("RATIO.SEC.ROE", (f_np.value / f_eq.value) * Decimal("100"), ["IS.PROFIT.NET", "BS.EQUITY.TOTAL"])
            if m: metrics[m.metric_code] = m
        if f_eq and f_margin and f_eq.value != Decimal("0"):
            m = make_metric("RATIO.SEC.MARGIN_TO_EQUITY", f_margin.value / f_eq.value, ["BS.SEC.MARGIN_LOANS", "BS.EQUITY.TOTAL"])
            if m: metrics[m.metric_code] = m

    # 4. Insurance Metrics
    elif entity_type == EntityType.INSURANCE:
        f_prem_net = get_fact("IS.INS.PREMIUM_NET")
        f_claims = get_fact("IS.INS.CLAIMS_EXPENSE")
        if f_prem_net and f_claims and f_prem_net.value != Decimal("0"):
            m = make_metric("RATIO.INS.LOSS_RATIO", (f_claims.value / f_prem_net.value) * Decimal("100"), ["IS.INS.CLAIMS_EXPENSE", "IS.INS.PREMIUM_NET"])
            if m: metrics[m.metric_code] = m

    return metrics
