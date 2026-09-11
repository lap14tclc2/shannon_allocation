"""Value Trap Evaluation Engine.

Evaluates structural vs cyclical deterioration risks to prevent buying value traps.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ValueTrapAssessment:
    """Canonical Value Trap evaluation payload."""

    symbol: str
    status: str  # CLEAR, WATCH, HIGH_RISK, INSUFFICIENT_DATA
    earnings_quality: str  # CONFIRMED, PARTIAL, FAIL
    normalized_earnings_trend: str  # GROWING, STABLE, DECLINING, UNKNOWN
    cash_conversion_status: str  # CONFIRMED, DIVERGENT, UNKNOWN, NOT_APPLICABLE
    balance_sheet_status: str  # SAFE, ATTENTION, SOLVENCY_RISK, UNKNOWN
    return_on_capital_trend: str  # GROWING, STABLE, DECLINING, UNKNOWN, NOT_APPLICABLE
    dilution_status: str  # OK, DESTRUCTIVE, UNKNOWN
    capital_allocation_status: str  # PASS, WATCH, FAIL
    accounting_status: str  # PASS, FAIL, UNKNOWN
    bear_case_protection: str  # PROTECTED, UNPROTECTED, UNKNOWN

    deterioration_classification: str  # STRUCTURAL_EVIDENCE, POSSIBLY_STRUCTURAL, LIKELY_CYCLICAL, UNKNOWN
    structural_deterioration_flags: list[str] = field(default_factory=list)
    cyclical_deterioration_flags: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    confidence: str = "HIGH"

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
    history = (
        financial_history
        or val.get("financial_history")
        or val.get("financial_history_10y")
        or val.get("report", {}).get("financial_history")
        or []
    )

    structural_flags: list[str] = []
    cyclical_flags: list[str] = []
    missing: list[str] = []
    reasons: list[str] = []

    price = float(val.get("current_price") or val.get("price") or 0.0)
    bear_iv = val.get("bear_iv") or val.get("bear_case_iv")
    base_iv = val.get("base_iv") or val.get("intrinsic_value")
    hard_rejects = val.get("hard_rejects") or []

    BANK_TICKERS = {"ACB", "VCB", "BID", "CTG", "MBB", "TCB", "VPB", "STB", "HDB", "TPB", "VIB", "MSB", "LPB", "EIB", "OCB", "SSB", "BAB", "NAB", "BVB", "ABB", "PGB", "SGB"}
    SECURITIES_TICKERS = {"VIX", "SSI", "VND", "HCM", "VCI", "MBS", "SHS", "CTS", "FTS", "BSI", "ORS", "AGR", "VDS", "TCBS"}
    is_bank = (
        bool(val.get("is_bank"))
        or val.get("archetype") == "BANK"
        or symbol_clean in BANK_TICKERS
        or "BANK" in str(val.get("sector") or "").upper()
        or "NGÂN HÀNG" in str(val.get("sector") or "").upper()
    )
    is_securities = (
        bool(val.get("is_securities"))
        or val.get("archetype") == "SECURITIES"
        or symbol_clean in SECURITIES_TICKERS
        or "CHỨNG KHOÁN" in str(val.get("sector") or "").upper()
    )
    is_financial_archetype = is_bank or is_securities

    pillars = val.get("value_investor_pillars") or val.get("report", {}).get("value_investor_pillars") or {}
    fortress_pillar = pillars.get("financial_fortress") or {}
    earnings_pillar = pillars.get("earnings_quality") or {}
    cap_alloc_pillar = pillars.get("capital_allocation") or {}

    # 1. Accounting Reliability Gate
    eq_status = earnings_pillar.get("status")
    if "ACCOUNTING_UNRELIABLE" in hard_rejects or val.get("accounting_reliability") == "FAIL":
        accounting_status = "FAIL"
        structural_flags.append("Báo cáo tài chính không tin cậy.")
    elif (
        val.get("accounting_verified") is True
        or val.get("accounting_reliability") in ("PASS", "WATCH")
        or eq_status in ("EXCELLENT", "GOOD", "CONFIRMED", "PASS", "PARTIAL")
        or val.get("ok") is True
        or len(history) > 0
    ):
        accounting_status = "PASS"
    else:
        accounting_status = "UNKNOWN"
        missing.append("ACCOUNTING_RELIABILITY_EVIDENCE")

    # 2. Solvency Survival Gate
    fortress_status = fortress_pillar.get("status")
    if "SOLVENCY_RISK" in hard_rejects or "INSOLVENCY" in hard_rejects or val.get("financial_strength") == "FAIL" or fortress_status in ("DANGER", "SOLVENCY_RISK"):
        balance_sheet_status = "SOLVENCY_RISK"
        structural_flags.append("Rủi ro mất khả năng thanh toán nợ.")
    elif (
        val.get("financial_strength") in ("PASS", "WATCH", "SAFE")
        or fortress_status in ("FORTRESS", "STRONG", "SAFE", "GOOD", "MODERATE")
        or (isinstance(val.get("financial_strength_score"), (int, float)) and float(val["financial_strength_score"]) >= 50)
        or val.get("ok") is True
        or len(history) > 0
    ):
        balance_sheet_status = "SAFE"
    elif fortress_status in ("ATTENTION", "WEAK") or (isinstance(val.get("financial_strength_score"), (int, float)) and float(val["financial_strength_score"]) >= 40):
        balance_sheet_status = "ATTENTION"
        cyclical_flags.append("Sức mạnh bảng cân đối kế toán ở mức theo dõi.")
    else:
        balance_sheet_status = "UNKNOWN"
        missing.append("BALANCE_SHEET_SOLVENCY_EVIDENCE")

    # 3. Normalized Earnings Trend (Process financial_history)
    earnings_series: list[float] = []
    if history:
        for p in history:
            val_p = p.get("owner_earnings") if p.get("owner_earnings") is not None else (p.get("net_income") if p.get("net_income") is not None else p.get("net_profit"))
            if val_p is not None:
                try:
                    earnings_series.append(float(val_p))
                except (ValueError, TypeError):
                    pass

    if len(earnings_series) >= 3:
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
    elif earnings_pillar.get("avg_roe_5y") is not None and float(earnings_pillar["avg_roe_5y"]) >= 15.0:
        normalized_earnings_trend = "STABLE"
    else:
        normalized_earnings_trend = "UNKNOWN"
        missing.append("HISTORICAL_EARNINGS_SERIES")

    # 4. Cash Conversion & Earnings Quality (NOT_APPLICABLE for Bank & Securities)
    if is_financial_archetype:
        cash_conversion_status = "NOT_APPLICABLE"
        earnings_quality = "CONFIRMED"
    else:
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
            scalar_ratio = val.get("cfo_to_net_income") or val.get("cash_conversion_ratio") or earnings_pillar.get("avg_cash_conversion_5y")
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

    # 5. ROIC / Return on Capital Trend (NOT_APPLICABLE for Bank & Securities)
    if is_financial_archetype:
        return_on_capital_trend = "NOT_APPLICABLE"
    else:
        roic_val = val.get("return_on_capital_trend") or val.get("roic_trend")
        if roic_val in ("STABLE", "DECLINING", "GROWING"):
            return_on_capital_trend = roic_val
            if roic_val == "DECLINING":
                structural_flags.append("Tỷ suất sinh lời trên vốn đầu tư (ROIC) suy giảm.")
        elif earnings_pillar.get("avg_roe_5y") is not None and float(earnings_pillar["avg_roe_5y"]) >= 15.0:
            return_on_capital_trend = "STABLE"
        elif len(history) >= 3:
            return_on_capital_trend = "STABLE"
        else:
            return_on_capital_trend = "UNKNOWN"
            missing.append("ROIC_HISTORICAL_SERIES")

    # 6. Receivables / Inventory Growth Divergence (NOT_APPLICABLE for Bank & Securities)
    if history and len(history) >= 2 and not is_financial_archetype:
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
    dilution_class = cap_alloc_pillar.get("dilution_classification") or val.get("dilution_status")
    if dilution_class == "DESTRUCTIVE_DILUTION":
        dilution_status = "DESTRUCTIVE"
        structural_flags.append("Pha loãng cổ phiếu liên tục làm xói mòn EPS.")
    elif dilution_class in ("STABLE", "OK", "NON_ECONOMIC_SHARE_CHANGE", "NO_SHARE_CHANGE") or len(history) >= 2 or val.get("ok") is True:
        dilution_status = "OK"
    else:
        dilution_status = "UNKNOWN"
        missing.append("DILUTION_STATUS")

    # 9. Capital Allocation Status
    cap_alloc_status = cap_alloc_pillar.get("status")
    if dilution_status == "DESTRUCTIVE" or cap_alloc_status == "FAIL":
        capital_allocation_status = "FAIL"
    elif (dilution_status == "OK" and accounting_status == "PASS") or cap_alloc_status in ("EXCELLENT", "GOOD", "SAFE", "PASS"):
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
        if m in ("HISTORICAL_EARNINGS_SERIES", "CFO_NET_INCOME_RATIO", "BEAR_CASE_IV", "ACCOUNTING_RELIABILITY_EVIDENCE", "BALANCE_SHEET_SOLVENCY_EVIDENCE")
        and not (is_financial_archetype and m == "CFO_NET_INCOME_RATIO")
    ]

    if has_confirmed_hard_structural or deterioration_classification == "STRUCTURAL_EVIDENCE":
        status = "HIGH_RISK"
        reasons.append("Phát hiện suy giảm cấu trúc hoặc rủi ro mất khả năng thanh toán/báo cáo tài chính.")
    elif len(structural_flags) > 0 or len(cyclical_flags) >= 1 or earnings_quality == "FAIL":
        status = "WATCH"
        if len(cyclical_flags) > 0:
            reasons.extend(cyclical_flags)

    elif len(critical_missing) >= 2 or accounting_status == "UNKNOWN" or balance_sheet_status == "UNKNOWN":
        status = "INSUFFICIENT_DATA"
        reasons.append(f"Thiếu dữ liệu quan trọng: {', '.join(critical_missing)}")
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
        reasons=reasons,
        confidence="HIGH" if not critical_missing else "LOW",
    )
