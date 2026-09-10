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
    If status == WATCH, BUY / BUY_MORE is PROHIBITED.
    If status == INSUFFICIENT_DATA, BUY / BUY_MORE is PROHIBITED by default.
    BUY / BUY_MORE requires status == CLEAR.
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

    is_bank = (
        bool(val.get("is_bank"))
        or val.get("archetype") == "BANK"
        or "BANK" in str(val.get("sector") or "").upper()
    )

    # 1. Accounting Reliability Gate
    if "ACCOUNTING_UNRELIABLE" in hard_rejects or val.get("accounting_reliability") == "FAIL":
        accounting_status = "FAIL"
        structural_flags.append("Báo cáo tài chính không tin cậy.")
    elif val.get("accounting_verified") is True or val.get("accounting_reliability") == "PASS":
        accounting_status = "PASS"
    else:
        accounting_status = "UNKNOWN"
        missing.append("ACCOUNTING_RELIABILITY_EVIDENCE")

    # 2. Solvency Survival Gate
    if "SOLVENCY_RISK" in hard_rejects or "INSOLVENCY" in hard_rejects or val.get("financial_strength") == "FAIL":
        balance_sheet_status = "SOLVENCY_RISK"
        structural_flags.append("Rủi ro mất khả năng thanh toán nợ.")
    elif val.get("financial_strength") == "PASS" or (isinstance(val.get("financial_strength_score"), (int, float)) and float(val["financial_strength_score"]) >= 60):
        balance_sheet_status = "SAFE"
    elif isinstance(val.get("financial_strength_score"), (int, float)) and float(val["financial_strength_score"]) >= 40:
        balance_sheet_status = "ATTENTION"
        cyclical_flags.append("Sức mạnh bảng cân đối kế toán ở mức theo dõi.")
    else:
        balance_sheet_status = "UNKNOWN"
        missing.append("BALANCE_SHEET_SOLVENCY_EVIDENCE")

    # 3. Normalized Earnings Trend (Process financial_history)
    earnings_series: list[float] = []
    if history:
        for p in history:
            val_p = p.get("owner_earnings") or p.get("net_income") or p.get("net_profit") or p.get("operating_profit")
            if val_p is not None:
                try:
                    earnings_series.append(float(val_p))
                except (ValueError, TypeError):
                    pass

    if len(earnings_series) >= 3:
        # Check trend over history
        first_half_avg = sum(earnings_series[:len(earnings_series)//2]) / max(1, len(earnings_series)//2)
        second_half_avg = sum(earnings_series[len(earnings_series)//2:]) / max(1, len(earnings_series) - len(earnings_series)//2)
        if second_half_avg > first_half_avg * 1.05:
            normalized_earnings_trend = "GROWING"
        elif second_half_avg >= first_half_avg * 0.85:
            normalized_earnings_trend = "STABLE"
        else:
            normalized_earnings_trend = "DECLINING"
            structural_flags.append("Lợi nhuận chuẩn hóa suy giảm liên tục qua các kỳ.")
    elif val.get("normalized_earnings_trend") in ("GROWING", "STABLE", "DECLINING"):
        normalized_earnings_trend = val["normalized_earnings_trend"]
        if normalized_earnings_trend == "DECLINING":
            structural_flags.append("Lợi nhuận chuẩn hóa có xu hướng suy giảm.")
    else:
        normalized_earnings_trend = "UNKNOWN"
        missing.append("HISTORICAL_EARNINGS_SERIES")

    # 4. Cash Conversion & Earnings Quality (Multi-year CFO vs Net Income)
    cfo_ratios: list[float] = []
    if history:
        for p in history:
            cfo = p.get("cfo") or p.get("cash_from_operations") or p.get("operating_cash_flow")
            ni = p.get("net_income") or p.get("net_profit")
            if cfo is not None and ni is not None and float(ni) > 0:
                try:
                    cfo_ratios.append(float(cfo) / float(ni))
                except (ValueError, TypeError, ZeroDivisionError):
                    pass

    if cfo_ratios:
        avg_cfo_ratio = sum(cfo_ratios) / len(cfo_ratios)
    else:
        scalar_ratio = val.get("cfo_to_net_income") or val.get("cash_conversion_ratio")
        avg_cfo_ratio = float(scalar_ratio) if scalar_ratio is not None else None

    if avg_cfo_ratio is not None:
        if avg_cfo_ratio >= 0.8:
            cash_conversion_status = "CONFIRMED"
            earnings_quality = "CONFIRMED"
        elif avg_cfo_ratio >= 0.5:
            cash_conversion_status = "DIVERGENT"
            earnings_quality = "PARTIAL"
            cyclical_flags.append(f"Tỷ lệ chuyển đổi dòng tiền CFO/Lợi nhuận ròng trung bình thấp ({avg_cfo_ratio:.2f}).")
        else:
            cash_conversion_status = "DIVERGENT"
            earnings_quality = "FAIL"
            structural_flags.append(f"Dòng tiền kinh doanh phân kỳ nghiêm trọng so với lợi nhuận báo cáo ({avg_cfo_ratio:.2f}).")
    else:
        cash_conversion_status = "UNKNOWN"
        earnings_quality = "PARTIAL"
        missing.append("CFO_NET_INCOME_RATIO")

    # 5. ROIC / Return on Capital Trend
    if is_bank:
        return_on_capital_trend = "NOT_APPLICABLE"
    else:
        roic_val = val.get("return_on_capital_trend") or val.get("roic_trend")
        if roic_val in ("STABLE", "DECLINING", "GROWING"):
            return_on_capital_trend = roic_val
            if roic_val == "DECLINING":
                structural_flags.append("Tỷ suất sinh lời trên vốn đầu tư (ROIC) suy giảm.")
        else:
            return_on_capital_trend = "UNKNOWN"
            missing.append("ROIC_HISTORICAL_SERIES")

    # 6. Receivables / Inventory Growth Divergence
    if history and len(history) >= 2 and not is_bank:
        latest = history[-1]
        prev = history[0]

        rev_latest = latest.get("revenue")
        rev_prev = prev.get("revenue")
        rec_latest = latest.get("receivables")
        rec_prev = prev.get("receivables")
        inv_latest = latest.get("inventory")
        inv_prev = prev.get("inventory")

        if rev_latest is None or rev_prev is None:
            missing.append("REVENUE_HISTORY")
        if rec_latest is None or rec_prev is None:
            missing.append("RECEIVABLES_HISTORY")
        if inv_latest is None or inv_prev is None:
            missing.append("INVENTORY_HISTORY")

        if rev_latest is not None and rev_prev is not None and float(rev_prev) > 0:
            rev_growth = (float(rev_latest) - float(rev_prev)) / float(rev_prev)

            if rec_latest is not None and rec_prev is not None and float(rec_prev) > 0:
                rec_growth = (float(rec_latest) - float(rec_prev)) / float(rec_prev)
                if rec_growth > rev_growth + 0.15 and rec_growth > 0.10:
                    cyclical_flags.append("Phải thu tăng trưởng nhanh hơn đáng kể so với doanh thu.")
                    if earnings_quality == "CONFIRMED":
                        earnings_quality = "PARTIAL"

            if inv_latest is not None and inv_prev is not None and float(inv_prev) > 0:
                inv_growth = (float(inv_latest) - float(inv_prev)) / float(inv_prev)
                if inv_growth > rev_growth + 0.15 and inv_growth > 0.10:
                    cyclical_flags.append("Tồn kho tích tụ nhanh hơn tốc độ tăng trưởng doanh thu.")
                    if earnings_quality == "CONFIRMED":
                        earnings_quality = "PARTIAL"

    # 7. Bear Case Protection Gate
    if bear_iv is not None and price > 0:
        if price <= float(bear_iv):
            bear_case_protection = "PROTECTED"
        else:
            bear_case_protection = "UNPROTECTED"
            cyclical_flags.append(f"Giá thị trường ({price:,.0f}) cao hơn kịch bản Thận trọng (Bear IV: {float(bear_iv):,.0f}).")
    else:
        bear_case_protection = "UNKNOWN"
        missing.append("BEAR_CASE_IV")

    # 8. Dilution Gate
    dilution_status_val = val.get("dilution_status")
    if dilution_status_val == "DESTRUCTIVE_DILUTION":
        dilution_status = "DESTRUCTIVE"
        structural_flags.append("Pha loãng cổ phiếu liên tục làm xói mòn EPS.")
    elif dilution_status_val in ("STABLE", "OK"):
        dilution_status = "OK"
    else:
        dilution_status = "UNKNOWN"
        missing.append("DILUTION_STATUS")

    # 9. Capital Allocation Status
    if dilution_status == "DESTRUCTIVE":
        capital_allocation_status = "FAIL"
    elif dilution_status == "OK" and accounting_status == "PASS":
        capital_allocation_status = "PASS"
    else:
        capital_allocation_status = "WATCH"

    # 10. Deterioration Classification
    has_confirmed_hard_structural = (
        accounting_status == "FAIL"
        or balance_sheet_status == "SOLVENCY_RISK"
        or dilution_status == "DESTRUCTIVE"
        or val.get("confirmed_permanent_impairment") is True
        or val.get("confirmed_hard_structural") is True
    )

    if has_confirmed_hard_structural:
        deterioration_classification = "STRUCTURAL_EVIDENCE"
    elif len(structural_flags) >= 1 or earnings_quality == "FAIL":
        deterioration_classification = "POSSIBLY_STRUCTURAL"
    elif len(cyclical_flags) > 0:
        deterioration_classification = "LIKELY_CYCLICAL"
    else:
        deterioration_classification = "UNKNOWN"

    # 11. Final Status Determination
    critical_missing = [
        m for m in missing
        if m in ("HISTORICAL_EARNINGS_SERIES", "CFO_NET_INCOME_RATIO", "BEAR_CASE_IV", "ACCOUNTING_RELIABILITY", "SOLVENCY_RISK")
    ]

    if has_confirmed_hard_structural or deterioration_classification == "STRUCTURAL_EVIDENCE":
        status = "HIGH_RISK"
    elif len(structural_flags) > 0 or len(cyclical_flags) >= 2 or earnings_quality == "FAIL":
        status = "WATCH"
    elif len(critical_missing) >= 2 or accounting_status == "UNKNOWN" or balance_sheet_status == "UNKNOWN":
        status = "INSUFFICIENT_DATA"
    else:
        status = "CLEAR"

    return ValueTrapAssessment(
        symbol=symbol_clean,
        status=status,
        earnings_quality=earnings_quality,
        normalized_earnings_trend=normalized_earnings_trend,
        cash_conversion_status=cash_conversion_status,
        balance_sheet_status=balance_sheet_status,
        return_on_capital_trend=return_on_capital_trend,
        dilution_status=dilution_status,
        capital_allocation_status=capital_allocation_status,
        accounting_status=accounting_status,
        bear_case_protection=bear_case_protection,
        deterioration_classification=deterioration_classification,
        structural_deterioration_flags=structural_flags,
        cyclical_deterioration_flags=cyclical_flags,
        missing_data=missing,
        confidence="HIGH" if len(missing) == 0 else "MEDIUM" if len(missing) <= 2 else "LOW",
    )

