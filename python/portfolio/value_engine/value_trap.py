"""Buffett-Munger Value Trap Gate Evaluator (T07B-T07J)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

VALUE_TRAP_STATUSES = ("CLEAR", "WATCH", "HIGH_RISK", "INSUFFICIENT_DATA")
DETERIORATION_CLASSIFICATIONS = (
    "LIKELY_CYCLICAL",
    "POSSIBLY_STRUCTURAL",
    "STRUCTURAL_EVIDENCE",
    "UNKNOWN",
)


@dataclass
class ValueTrapAssessment:
    """Canonical Value Trap Gate output payload."""

    symbol: str
    status: str = "INSUFFICIENT_DATA"  # CLEAR, WATCH, HIGH_RISK, INSUFFICIENT_DATA

    earnings_quality: str = "UNKNOWN"  # CONFIRMED, PARTIAL, FAIL, UNKNOWN
    normalized_earnings_trend: str = "UNKNOWN"  # GROWING, STABLE, DECLINING, UNKNOWN
    cash_conversion_status: str = "UNKNOWN"  # CONFIRMED, DIVERGENT, UNKNOWN
    balance_sheet_status: str = "UNKNOWN"  # SAFE, ATTENTION, SOLVENCY_RISK, UNKNOWN
    return_on_capital_trend: str = "UNKNOWN"  # STABLE, DECLINING, UNKNOWN
    dilution_status: str = "UNKNOWN"  # OK, WATCH, DESTRUCTIVE, UNKNOWN
    capital_allocation_status: str = "UNKNOWN"  # PASS, WATCH, FAIL, UNKNOWN
    accounting_status: str = "UNKNOWN"  # PASS, FAIL, UNKNOWN
    bear_case_protection: str = "UNKNOWN"  # PROTECTED, UNPROTECTED, UNKNOWN

    deterioration_classification: str = "UNKNOWN"  # LIKELY_CYCLICAL, POSSIBLY_STRUCTURAL, STRUCTURAL_EVIDENCE, UNKNOWN

    structural_deterioration_flags: list[str] = field(default_factory=list)
    cyclical_deterioration_flags: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    confidence: str = "MEDIUM"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_value_trap(
    symbol: str,
    valuation_report: dict[str, Any] | None = None,
    financial_history: list[dict[str, Any]] | None = None,
) -> ValueTrapAssessment:
    """Evaluate Value Trap Gate before BUY / BUY_MORE decisions.

    Mandatory Invariant:
    If status == HIGH_RISK, BUY / BUY_MORE is PROHIBITED.
    """
    symbol_clean = symbol.strip().upper()
    val = valuation_report or {}
    history = financial_history or []

    structural_flags: list[str] = []
    cyclical_flags: list[str] = []
    missing: list[str] = []

    price = float(val.get("current_price") or val.get("price") or 0.0)
    bear_iv = val.get("bear_iv") or val.get("bear_case_iv")
    base_iv = val.get("base_iv") or val.get("intrinsic_value")
    hard_rejects = val.get("hard_rejects") or []

    # 1. Accounting Reliability Gate
    if "ACCOUNTING_UNRELIABLE" in hard_rejects:
        accounting_status = "FAIL"
        structural_flags.append("Báo cáo tài chính không tin cậy.")
    else:
        accounting_status = "PASS"

    # 2. Solvency Survival Gate
    if "SOLVENCY_RISK" in hard_rejects or "INSOLVENCY" in hard_rejects:
        balance_sheet_status = "SOLVENCY_RISK"
        structural_flags.append("Rủi ro mất khả năng thanh toán nợ.")
    else:
        balance_sheet_status = "SAFE"

    # 3. Cash Conversion Status (CFO vs Net Income)
    cfo_ratio = val.get("cfo_to_net_income") or val.get("cash_conversion_ratio")
    if cfo_ratio is not None:
        if cfo_ratio >= 0.8:
            cash_conversion_status = "CONFIRMED"
            earnings_quality = "CONFIRMED"
        elif cfo_ratio >= 0.5:
            cash_conversion_status = "DIVERGENT"
            earnings_quality = "PARTIAL"
            cyclical_flags.append(f"Dòng tiền CFO / Lợi nhuận ròng thấp ({cfo_ratio:.1f}).")
        else:
            cash_conversion_status = "DIVERGENT"
            earnings_quality = "FAIL"
            structural_flags.append(f"Dòng tiền CFO / Lợi nhuận ròng yếu nghiêm trọng ({cfo_ratio:.1f}).")
    else:
        cash_conversion_status = "UNKNOWN"
        earnings_quality = "PARTIAL"
        missing.append("CFO_NET_INCOME_RATIO")

    # 4. Bear Case Protection Gate
    if bear_iv is not None and price > 0:
        if price <= float(bear_iv):
            bear_case_protection = "PROTECTED"
        else:
            bear_case_protection = "UNPROTECTED"
            cyclical_flags.append(f"Giá thị trường ({price:,.0f}) cao hơn kịch bản Thận trọng (Bear IV: {float(bear_iv):,.0f}).")
    else:
        bear_case_protection = "UNKNOWN"

    # 5. Dilution Gate
    dilution_status_val = val.get("dilution_status")
    if dilution_status_val == "DESTRUCTIVE_DILUTION":
        dilution_status = "DESTRUCTIVE"
        structural_flags.append("Pha loãng cổ phiếu liên tục làm xói mòn EPS.")
    elif dilution_status_val in ("STABLE", "OK"):
        dilution_status = "OK"
    else:
        dilution_status = "UNKNOWN"

    # 6. Deterioration Classification
    if len(structural_flags) >= 2:
        deterioration_classification = "STRUCTURAL_EVIDENCE"
    elif len(structural_flags) == 1:
        deterioration_classification = "POSSIBLY_STRUCTURAL"
    elif len(cyclical_flags) > 0:
        deterioration_classification = "LIKELY_CYCLICAL"
    else:
        deterioration_classification = "UNKNOWN"

    # 7. Final Status Determination
    if accounting_status == "FAIL" or balance_sheet_status == "SOLVENCY_RISK" or deterioration_classification == "STRUCTURAL_EVIDENCE":
        status = "HIGH_RISK"
    elif len(structural_flags) > 0 or len(cyclical_flags) >= 2:
        status = "WATCH"
    elif len(missing) > 2:
        status = "INSUFFICIENT_DATA"
    else:
        status = "CLEAR"

    return ValueTrapAssessment(
        symbol=symbol_clean,
        status=status,
        earnings_quality=earnings_quality,
        normalized_earnings_trend="STABLE" if len(structural_flags) == 0 else "DECLINING",
        cash_conversion_status=cash_conversion_status,
        balance_sheet_status=balance_sheet_status,
        dilution_status=dilution_status,
        capital_allocation_status="FAIL" if dilution_status == "DESTRUCTIVE" else "PASS",
        accounting_status=accounting_status,
        bear_case_protection=bear_case_protection,
        deterioration_classification=deterioration_classification,
        structural_deterioration_flags=structural_flags,
        cyclical_deterioration_flags=cyclical_flags,
        missing_data=missing,
        confidence="HIGH" if len(missing) == 0 else "MEDIUM",
    )
