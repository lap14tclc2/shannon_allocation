"""Buffett-Munger 7-Dimension Business Review Evaluator (T07)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

DIMENSION_STATES = ("PASS", "WATCH", "FAIL", "UNKNOWN", "NOT_APPLICABLE")
AGGREGATE_STATUSES = ("BUSINESS_PASS", "BUSINESS_REVIEW", "BUSINESS_FAIL", "UNKNOWN")


@dataclass
class BusinessReviewResult:
    """Canonical 7-dimension Business Review output."""

    symbol: str

    understandability: str = "UNKNOWN"
    business_quality: str = "UNKNOWN"
    financial_strength: str = "UNKNOWN"
    earnings_durability: str = "UNKNOWN"
    moat: str = "UNKNOWN"
    management_capital_allocation: str = "UNKNOWN"
    accounting_reliability: str = "UNKNOWN"

    overall_status: str = "UNKNOWN"
    reasons: list[str] = field(default_factory=list)
    missing_dimensions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_business_review(
    symbol: str,
    valuation_report: dict[str, Any] | None = None,
    manual_qualitative_evidence: dict[str, Any] | None = None,
) -> BusinessReviewResult:
    """Evaluate 7 canonical dimensions for business quality.

    Dimensions:
    1. UNDERSTANDABILITY
    2. BUSINESS_QUALITY
    3. FINANCIAL_STRENGTH
    4. EARNINGS_DURABILITY
    5. MOAT
    6. MANAGEMENT_CAPITAL_ALLOCATION
    7. ACCOUNTING_RELIABILITY
    """
    symbol_clean = symbol.strip().upper()
    val = valuation_report or {}
    qual = manual_qualitative_evidence or {}

    reasons: list[str] = []
    missing: list[str] = []

    # 1. Understandability
    understandability = qual.get("understandability") or "PASS"  # Default PASS for listed universe unless flagged

    # 2. Business Quality
    quality_tier = val.get("quality_tier") or qual.get("quality_tier")
    if quality_tier == "HIGH_QUALITY":
        business_quality = "PASS"
    elif quality_tier in ("WATCH", "MEDIOCRE"):
        business_quality = "WATCH"
        reasons.append("Chất lượng doanh nghiệp trung bình / cần theo dõi.")
    elif quality_tier == "LOW_QUALITY":
        business_quality = "FAIL"
        reasons.append("Chất lượng doanh nghiệp kém.")
    else:
        business_quality = "UNKNOWN"
        missing.append("BUSINESS_QUALITY")

    # 3. Financial Strength
    fin_score = val.get("financial_strength_score") or val.get("financial_strength")
    hard_rejects = val.get("hard_rejects") or []
    if "SOLVENCY_RISK" in hard_rejects or fin_score == "FAIL":
        financial_strength = "FAIL"
        reasons.append("Rủi ro khả năng thanh toán / nợ cao.")
    elif isinstance(fin_score, (int, float)):
        if fin_score >= 60:
            financial_strength = "PASS"
        elif fin_score >= 40:
            financial_strength = "WATCH"
            reasons.append("Sức mạnh tài chính ở mức theo dõi.")
        else:
            financial_strength = "FAIL"
            reasons.append("Sức mạnh tài chính yếu.")
    else:
        financial_strength = "UNKNOWN"
        missing.append("FINANCIAL_STRENGTH")

    # 4. Earnings Durability
    owner_earnings = val.get("owner_earnings") or val.get("normalized_owner_earnings")
    if owner_earnings is not None:
        if owner_earnings > 0:
            earnings_durability = "PASS"
        else:
            earnings_durability = "WATCH"
            reasons.append("Lợi nhuận chủ sở hữu chưa dương hoặc biến động.")
    else:
        earnings_durability = "UNKNOWN"
        missing.append("EARNINGS_DURABILITY")

    # 5. Moat Assessment
    moat_val = qual.get("moat") or val.get("moat_strength")
    if moat_val in ("WIDE", "NARROW", "STRONG", "PASS"):
        moat = "PASS"
    elif moat_val in ("NONE", "WEAK", "FAIL"):
        moat = "WATCH"
        reasons.append("Lợi thế cạnh tranh yếu hoặc không rõ ràng.")
    else:
        moat = "UNKNOWN"
        missing.append("MOAT")

    # 6. Management / Capital Allocation
    mgt_val = qual.get("management_capital_allocation") or val.get("dilution_status")
    if mgt_val == "DESTRUCTIVE_DILUTION":
        management_capital_allocation = "FAIL"
        reasons.append("Pha loãng cổ phiếu phá hủy giá trị.")
    elif mgt_val in ("EXCELLENT", "GOOD", "PASS", "STABLE", "OK") or (quality_tier == "HIGH_QUALITY" and mgt_val is None):
        management_capital_allocation = "PASS"
    elif mgt_val in ("WATCH", "MODERATE"):
        management_capital_allocation = "WATCH"
    else:
        management_capital_allocation = "UNKNOWN"
        missing.append("MANAGEMENT_CAPITAL_ALLOCATION")


    # 7. Accounting Reliability
    acct_val = qual.get("accounting_reliability") or ("FAIL" if "ACCOUNTING_UNRELIABLE" in hard_rejects else "PASS")
    if acct_val == "FAIL":
        accounting_reliability = "FAIL"
        reasons.append("Báo cáo tài chính không tin cậy.")
    elif acct_val == "WATCH":
        accounting_reliability = "WATCH"
    else:
        accounting_reliability = "PASS"

    # Overall Status Aggregation
    fails = [business_quality, financial_strength, earnings_durability, management_capital_allocation, accounting_reliability]
    if "FAIL" in fails:
        overall_status = "BUSINESS_FAIL"
    elif "WATCH" in fails or "UNKNOWN" in fails:
        overall_status = "BUSINESS_REVIEW"
    elif all(d in ("PASS", "NOT_APPLICABLE") for d in fails):
        overall_status = "BUSINESS_PASS"
    else:
        overall_status = "UNKNOWN"

    return BusinessReviewResult(
        symbol=symbol_clean,
        understandability=understandability,
        business_quality=business_quality,
        financial_strength=financial_strength,
        earnings_durability=earnings_durability,
        moat=moat,
        management_capital_allocation=management_capital_allocation,
        accounting_reliability=accounting_reliability,
        overall_status=overall_status,
        reasons=reasons,
        missing_dimensions=missing,
    )
