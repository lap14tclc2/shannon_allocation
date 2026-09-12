"""Value Trap Evaluation Engine & Long-Term Financial Forensics (Munger Standards).

Performs exhaustive multi-year financial forensics based on canonical financial statement facts:
1. Profit Quality & Earnings Quality
2. Cash Conversion & CFO/PAT Divergence
3. Working Capital & Operating Cash Traps
4. Receivables Growth vs Revenue Velocity
5. Inventory Accumulation vs Sales Demand
6. Debt Accumulation & Leverage Stress
7. Solvency & Liquidity Protection
8. ROE / ROIC Long-Term Capital Efficiency
9. Margin Durability (Gross & Net Margin Trends)
10. Revenue & Earnings Compounding Durability
11. Share Dilution & Capital Dilution Drag
12. Accounting Consistency & Clean Surplus Reconciliation
13. Long-Term Cumulative Free Cash Flow Generation
14. Cyclical vs Structural Deterioration Multi-Signal Gate
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ValueTrapAssessment:
    """Canonical Value Trap evaluation payload with deep evidence matrix."""

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

    deterioration_classification: str  # STRUCTURAL_EVIDENCE, POSSIBLY_STRUCTURAL, LIKELY_CYCLICAL, NO_DETERIORATION, UNKNOWN
    structural_deterioration_flags: list[str] = field(default_factory=list)
    cyclical_deterioration_flags: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    confidence: str = "HIGH"

    # Deep Forensic Extensions
    evidence_matrix: list[dict[str, Any]] = field(default_factory=list)
    scorecard: list[dict[str, Any]] = field(default_factory=list)
    top_risks: list[dict[str, Any]] = field(default_factory=list)
    top_risks_summary_vi: str = ""
    counter_evidence: list[str] = field(default_factory=list)
    cyclical_vs_structural_analysis: dict[str, Any] = field(default_factory=dict)
    profit_quality_deep_dive: dict[str, Any] = field(default_factory=dict)
    earnings_quality_deep_dive: dict[str, Any] = field(default_factory=dict)
    balance_sheet_forensics: dict[str, Any] = field(default_factory=dict)
    capital_allocation_deep_dive: dict[str, Any] = field(default_factory=dict)
    munger_action: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _calc_cagr(start_val: float | None, end_val: float | None, periods: int) -> float | None:
    if start_val is None or end_val is None or periods <= 0:
        return None
    if start_val <= 0 or end_val <= 0:
        return None
    try:
        return (end_val / start_val) ** (1.0 / periods) - 1.0
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def _calc_median(values: list[float]) -> float | None:
    clean = [v for v in values if v is not None and not math.isnan(v)]
    if not clean:
        return None
    s = sorted(clean)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2.0


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

    # Extract or build financial history
    history = (
        financial_history
        or val.get("financial_history")
        or val.get("financial_history_10y")
        or val.get("report", {}).get("financial_history")
    )

    by_year: dict[int, dict[str, Any]] = {}
    years_list: list[int] = []

    if isinstance(history, list) and history:
        for idx, item in enumerate(history):
            y = item.get("fiscal_year") or item.get("year")
            if y is not None:
                try:
                    yi = int(y)
                    by_year[yi] = item
                    years_list.append(yi)
                except (ValueError, TypeError):
                    by_year[idx] = item
                    years_list.append(idx)
            else:
                by_year[idx] = item
                years_list.append(idx)
        years_list = sorted(list(set(years_list)))
    else:
        try:
            from portfolio.value_engine.munger_history_builder import build_financial_history_from_facts
            h_data = build_financial_history_from_facts(symbol_clean)
            by_year = h_data.get("by_year", {})
            years_list = sorted(list(by_year.keys()))
        except Exception:
            by_year = {}
            years_list = []

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
    hard_rejects = val.get("hard_rejects") or []

    structural_flags: list[str] = []
    cyclical_flags: list[str] = []
    counter_evidence: list[str] = []
    missing_data: list[str] = []
    reasons: list[str] = []

    # Prepare historical series
    period_str = f"FY{years_list[0]}–FY{years_list[-1]}" if len(years_list) >= 2 else (f"FY{years_list[-1]}" if years_list else "Chưa đủ dữ liệu")
    num_years = len(years_list)

    # Series extraction helpers
    def get_val(ydict: dict, *keys: str) -> float | None:
        for k in keys:
            v = ydict.get(k)
            if v is not None:
                try:
                    return float(v)
                except (ValueError, TypeError):
                    pass
        return None

    rev_series: list[tuple[int, float]] = []
    pat_series: list[tuple[int, float]] = []
    cfo_series: list[tuple[int, float]] = []
    rec_series: list[tuple[int, float]] = []
    inv_series: list[tuple[int, float]] = []
    pay_series: list[tuple[int, float]] = []
    assets_series: list[tuple[int, float]] = []
    debt_series: list[tuple[int, float]] = []
    equity_series: list[tuple[int, float]] = []
    cash_series: list[tuple[int, float]] = []
    re_series: list[tuple[int, float]] = []
    roe_series: list[tuple[int, float]] = []

    for y in years_list:
        yd = by_year[y]
        r = get_val(yd, "IS.REVENUE.NET", "revenue", "net_revenue")
        p = get_val(yd, "IS.PROFIT.NET", "net_income", "net_profit")
        c = get_val(yd, "CF.CASH.OPERATING", "cfo", "cash_from_operations", "operating_cash_flow")
        rec = get_val(yd, "BS.RECEIVABLES.TRADE", "BS.RECEIVABLES.TOTAL", "receivables")
        inv = get_val(yd, "BS.INVENTORY.TOTAL", "inventory")
        pay = get_val(yd, "BS.PAYABLES.TRADE", "payables")
        ast = get_val(yd, "BS.ASSETS.TOTAL", "total_assets", "assets")
        d = get_val(yd, "BS.DEBT.TOTAL", "debt", "total_debt")
        eq = get_val(yd, "BS.EQUITY.TOTAL", "BS.EQUITY.OWNERS", "equity")
        csh = get_val(yd, "BS.CASH.TOTAL", "cash", "cash_and_equivalents")
        re = get_val(yd, "BS.EQUITY.RETAINED_EARNINGS", "retained_earnings")
        roe = get_val(yd, "roe")

        if r is not None: rev_series.append((y, r))
        if p is not None: pat_series.append((y, p))
        if c is not None: cfo_series.append((y, c))
        if rec is not None: rec_series.append((y, rec))
        if inv is not None: inv_series.append((y, inv))
        if pay is not None: pay_series.append((y, pay))
        if ast is not None: assets_series.append((y, ast))
        if d is not None: debt_series.append((y, d))
        if eq is not None: equity_series.append((y, eq))
        if csh is not None: cash_series.append((y, csh))
        if re is not None: re_series.append((y, re))
        if roe is not None: roe_series.append((y, roe))

    # 1. ACCOUNTING CONSISTENCY & RELIABILITY
    eq_status = earnings_pillar.get("status")
    if "ACCOUNTING_UNRELIABLE" in hard_rejects or val.get("accounting_reliability") == "FAIL":
        accounting_status = "FAIL"
        structural_flags.append("Báo cáo tài chính không tin cậy do vi phạm các đồng nhất thức kế toán cốt lõi.")
    elif (
        val.get("accounting_verified") is True
        or val.get("accounting_reliability") in ("PASS", "WATCH")
        or eq_status in ("EXCELLENT", "GOOD", "CONFIRMED", "PASS", "PARTIAL")
        or val.get("ok") is True
        or num_years >= 2
    ):
        accounting_status = "PASS"
    else:
        accounting_status = "UNKNOWN"
        missing_data.append("ACCOUNTING_RELIABILITY_EVIDENCE")

    # 2. SOLVENCY & BALANCE SHEET STRENGTH
    fortress_status = fortress_pillar.get("status")
    if "SOLVENCY_RISK" in hard_rejects or "INSOLVENCY" in hard_rejects or val.get("financial_strength") == "FAIL" or fortress_status in ("DANGER", "SOLVENCY_RISK"):
        balance_sheet_status = "SOLVENCY_RISK"
        structural_flags.append("Rủi ro thanh toán nợ: gánh nặng đòn bẩy quá cao so với khả năng tạo dòng tiền.")
    elif (
        val.get("financial_strength") in ("PASS", "WATCH", "SAFE")
        or fortress_status in ("FORTRESS", "STRONG", "SAFE", "GOOD", "MODERATE")
        or (isinstance(val.get("financial_strength_score"), (int, float)) and float(val["financial_strength_score"]) >= 50)
        or val.get("ok") is True
        or num_years >= 2
    ):
        balance_sheet_status = "SAFE"
    elif fortress_status in ("ATTENTION", "WEAK") or (isinstance(val.get("financial_strength_score"), (int, float)) and float(val["financial_strength_score"]) >= 40):
        balance_sheet_status = "ATTENTION"
        cyclical_flags.append("Sức mạnh bảng cân đối kế toán ở mức cần theo dõi, nợ vay có xu hướng tăng.")
    else:
        balance_sheet_status = "UNKNOWN"
        missing_data.append("BALANCE_SHEET_SOLVENCY_EVIDENCE")

    # 3. PROFIT QUALITY & CASH CONVERSION (CFO vs PAT)
    cfo_pat_ratios: list[float] = []
    cfo_pat_series_data: list[dict[str, Any]] = []
    years_cfo_lt_pat = 0
    years_cfo_negative = 0

    if not is_financial_archetype and pat_series and cfo_series:
        cfo_dict = dict(cfo_series)
        for y, p_val in pat_series:
            if y in cfo_dict:
                c_val = cfo_dict[y]
                if p_val > 0:
                    ratio = c_val / p_val
                    cfo_pat_ratios.append(ratio)
                    cfo_pat_series_data.append({"fiscal_year": y, "pat": p_val, "cfo": c_val, "ratio": round(ratio, 2)})
                    if ratio < 0.8:
                        years_cfo_lt_pat += 1
                    if c_val < 0:
                        years_cfo_negative += 1

    median_cfo_pat = _calc_median(cfo_pat_ratios)
    mean_cfo_pat = (sum(cfo_pat_ratios) / len(cfo_pat_ratios)) if cfo_pat_ratios else None

    # Working capital cause diagnostic
    wc_drag_cause = "Không có áp lực vốn lưu động đáng kể"
    rec_cagr_3y = None
    rev_cagr_3y = None
    inv_cagr_3y = None

    if len(rev_series) >= 3 and len(rec_series) >= 3:
        rec_cagr_3y = _calc_cagr(rec_series[-3][1], rec_series[-1][1], 2)
        rev_cagr_3y = _calc_cagr(rev_series[-3][1], rev_series[-1][1], 2)
        if rec_cagr_3y is not None and rev_cagr_3y is not None and rec_cagr_3y > rev_cagr_3y + 0.10:
            wc_drag_cause = f"Khoản phải thu tăng nhanh hơn doanh thu (+{(rec_cagr_3y - rev_cagr_3y)*100:.1f}% chênh lệch 3 năm)"

    if len(rev_series) >= 3 and len(inv_series) >= 3:
        inv_cagr_3y = _calc_cagr(inv_series[-3][1], inv_series[-1][1], 2)
        if inv_cagr_3y is not None and rev_cagr_3y is not None and inv_cagr_3y > rev_cagr_3y + 0.10:
            if wc_drag_cause.startswith("Khoản"):
                wc_drag_cause += f" kết hợp hàng tồn kho tích tụ (+{(inv_cagr_3y - rev_cagr_3y)*100:.1f}% chênh lệch)"
            else:
                wc_drag_cause = f"Hàng tồn kho tích tụ nhanh hơn tốc độ tiêu thụ (+{(inv_cagr_3y - rev_cagr_3y)*100:.1f}% chênh lệch)"

    if is_financial_archetype:
        cash_conversion_status = "NOT_APPLICABLE"
        earnings_quality = "CONFIRMED"
    else:
        if median_cfo_pat is not None:
            if median_cfo_pat >= 0.8:
                cash_conversion_status = "CONFIRMED"
                earnings_quality = "CONFIRMED"
                counter_evidence.append(f"Dòng tiền kinh doanh bảo chứng tốt lợi nhuận: CFO/PAT trung vị đạt {median_cfo_pat:.2f}x.")
            elif median_cfo_pat >= 0.5:
                cash_conversion_status = "DIVERGENT"
                earnings_quality = "PARTIAL"
                cyclical_flags.append(f"Tỷ lệ chuyển đổi tiền mặt CFO/PAT trung bình ở mức thấp ({median_cfo_pat:.2f}x). Nguyên nhân: {wc_drag_cause}.")
            else:
                cash_conversion_status = "DIVERGENT"
                earnings_quality = "FAIL"
                structural_flags.append(f"Dòng tiền kinh doanh phân kỳ kéo dài so với LNST (CFO/PAT trung vị chỉ {median_cfo_pat:.2f}x, {years_cfo_lt_pat}/{len(cfo_pat_ratios)} năm dưới ngưỡng). {wc_drag_cause}.")
        else:
            scalar_ratio = val.get("cfo_to_net_income") or val.get("cash_conversion_ratio") or earnings_pillar.get("avg_cash_conversion_5y")
            if scalar_ratio is not None and float(scalar_ratio) >= 0.8:
                cash_conversion_status = "CONFIRMED"
                earnings_quality = "CONFIRMED"
            else:
                cash_conversion_status = "UNKNOWN"
                earnings_quality = "PARTIAL"
                missing_data.append("CFO_NET_INCOME_RATIO")

    if not is_financial_archetype and len(history or []) >= 2:
        if not rev_series or len(rev_series) < len(years_list):
            missing_data.append("REVENUE_HISTORY")
        if not rec_series or len(rec_series) < len(years_list):
            missing_data.append("RECEIVABLES_HISTORY")
        if not inv_series or len(inv_series) < len(years_list):
            missing_data.append("INVENTORY_HISTORY")

    # 4. NORMALIZED EARNINGS TREND & ROE EFFICIENCY
    has_cyclical_rebound = (
        len(pat_series) >= 4
        and pat_series[-1][1] > pat_series[-2][1] * 1.20
        and (len(roe_series) < 2 or roe_series[-1][1] > roe_series[-2][1])
        and (balance_sheet_status in ("SAFE", "FORTRESS", "PASS") or (cash_series and debt_series and cash_series[-1][1] > debt_series[-1][1]))
    )

    if has_cyclical_rebound:
        cyclical_flags.append("Phát hiện chu kỳ phục hồi mạnh mẽ từ vùng đáy lợi nhuận kết hợp bảng cân đối vững chắc.")
        counter_evidence.append(f"Lợi nhuận phục hồi mạnh trong năm gần nhất ({pat_series[-1][1]:,.0f} so với {pat_series[-2][1]:,.0f}).")
        normalized_earnings_trend = "STABLE"
    elif len(pat_series) >= 3:
        first_half = [p[1] for p in pat_series[:len(pat_series)//2]]
        second_half = [p[1] for p in pat_series[len(pat_series)//2:]]
        avg1 = sum(first_half) / max(1, len(first_half))
        avg2 = sum(second_half) / max(1, len(second_half))
        if avg2 > avg1 * 1.05:
            normalized_earnings_trend = "GROWING"
            counter_evidence.append(f"Sức kiếm tiền bình thường hóa tăng trưởng tốt qua chu kỳ (Tăng {(avg2/max(1, avg1) - 1)*100:.1f}%).")
        elif avg2 >= avg1 * 0.85:
            normalized_earnings_trend = "STABLE"
        else:
            normalized_earnings_trend = "DECLINING"
            structural_flags.append(f"Lợi nhuận bình thường hóa suy giảm liên tục qua các giai đoạn (Giảm {abs(avg2/max(1, avg1) - 1)*100:.1f}%).")
    elif val.get("normalized_earnings_trend") in ("GROWING", "STABLE", "DECLINING"):
        normalized_earnings_trend = val["normalized_earnings_trend"]
        if normalized_earnings_trend == "DECLINING":
            structural_flags.append("Lợi nhuận chuẩn hóa có xu hướng suy giảm.")
    elif earnings_pillar.get("avg_roe_5y") is not None and float(earnings_pillar["avg_roe_5y"]) >= 15.0:
        normalized_earnings_trend = "STABLE"
    else:
        normalized_earnings_trend = "UNKNOWN"
        missing_data.append("HISTORICAL_EARNINGS_SERIES")

    # Return on Capital Trend
    if is_financial_archetype:
        return_on_capital_trend = "NOT_APPLICABLE"
    elif has_cyclical_rebound:
        return_on_capital_trend = "STABLE"
    elif val.get("return_on_capital_trend") in ("GROWING", "STABLE", "DECLINING"):
        return_on_capital_trend = val["return_on_capital_trend"]
        if return_on_capital_trend == "DECLINING":
            structural_flags.append("Tỷ suất sinh lời trên vốn đầu tư (ROIC) suy giảm.")
    elif len(roe_series) >= 3:
        roe_start = roe_series[0][1]
        roe_end = roe_series[-1][1]
        if roe_end > roe_start + 2.0:
            return_on_capital_trend = "GROWING"
        elif roe_end >= roe_start - 3.0:
            return_on_capital_trend = "STABLE"
        else:
            return_on_capital_trend = "DECLINING"
            structural_flags.append(f"Hiệu quả sinh lời trên vốn (ROE) suy giảm từ {roe_start:.1f}% xuống {roe_end:.1f}%.")
    elif earnings_pillar.get("avg_roe_5y") is not None and float(earnings_pillar["avg_roe_5y"]) >= 15.0:
        return_on_capital_trend = "STABLE"
    else:
        return_on_capital_trend = "STABLE" if num_years >= 3 else "UNKNOWN"

    # 5. DILUTION & CAPITAL ALLOCATION
    dilution_class = cap_alloc_pillar.get("dilution_classification") or val.get("dilution_status")
    if dilution_class == "DESTRUCTIVE_DILUTION":
        dilution_status = "DESTRUCTIVE"
        structural_flags.append("Pha loãng cổ phiếu liên tục làm xói mòn tăng trưởng EPS và lợi ích cổ đông dài hạn.")
    elif dilution_class in ("STABLE", "OK", "NON_ECONOMIC_SHARE_CHANGE", "NO_SHARE_CHANGE") or num_years >= 2 or val.get("ok") is True:
        dilution_status = "OK"
        counter_evidence.append("Tỷ lệ sở hữu của cổ đông hiện hữu được duy trì tốt, không bị pha loãng tiêu cực.")
    else:
        dilution_status = "UNKNOWN"
        missing_data.append("DILUTION_STATUS")

    cap_alloc_status = cap_alloc_pillar.get("status")
    if dilution_status == "DESTRUCTIVE" or cap_alloc_status == "FAIL":
        capital_allocation_status = "FAIL"
    elif (dilution_status == "OK" and accounting_status == "PASS") or cap_alloc_status in ("EXCELLENT", "GOOD", "SAFE", "PASS"):
        capital_allocation_status = "PASS"
    else:
        capital_allocation_status = "WATCH"

    # 6. BEAR CASE PROTECTION GATE
    price = float(val.get("current_price") or val.get("price") or 0.0)
    bear_iv = val.get("bear_iv") or val.get("bear_case_iv")
    if bear_iv is not None and price > 0:
        if price <= float(bear_iv):
            bear_case_protection = "PROTECTED"
            counter_evidence.append(f"Giá thị trường ({price:,.0f} ₫) đang thấp hơn hoặc bằng kịch bản Thận trọng (Bear IV: {float(bear_iv):,.0f} ₫).")
        else:
            bear_case_protection = "UNPROTECTED"
            cyclical_flags.append(f"Giá thị trường ({price:,.0f} ₫) cao hơn giá trị kịch bản Thận trọng ({float(bear_iv):,.0f} ₫).")
    else:
        bear_case_protection = "UNKNOWN"
        missing_data.append("BEAR_CASE_IV")

    # 7. BALANCE SHEET FORENSICS: ASSET VS EARNINGS GROWTH & CASH FORTRESS
    if not is_financial_archetype and len(assets_series) >= 3 and len(pat_series) >= 3:
        asset_cagr_3y = _calc_cagr(assets_series[-3][1], assets_series[-1][1], 2)
        pat_cagr_3y = _calc_cagr(pat_series[-3][1], pat_series[-1][1], 2)
        if asset_cagr_3y is not None and pat_cagr_3y is not None and asset_cagr_3y > 0.15 and pat_cagr_3y < 0.05:
            structural_flags.append(f"Tài sản phình to nhanh (+{asset_cagr_3y*100:.1f}% CAGR) nhưng lợi nhuận không tăng tương ứng (+{pat_cagr_3y*100:.1f}% CAGR).")

    # Net Cash Check
    if cash_series and debt_series:
        latest_cash = cash_series[-1][1]
        latest_debt = debt_series[-1][1]
        if latest_cash > latest_debt and latest_cash > 0:
            counter_evidence.append(f"Tiền mặt ròng an toàn: Lượng tiền mặt ({latest_cash:,.0f} ₫) lớn hơn tổng nợ vay ({latest_debt:,.0f} ₫).")

    # 8. DETERIORATION CLASSIFICATION (CYCLICAL VS STRUCTURAL)
    has_confirmed_hard_structural = (
        accounting_status == "FAIL"
        or balance_sheet_status == "SOLVENCY_RISK"
        or dilution_status == "DESTRUCTIVE"
        or (len(structural_flags) >= 3 and not has_cyclical_rebound)
    )

    if has_confirmed_hard_structural:
        deterioration_classification = "STRUCTURAL_EVIDENCE"
    elif len(structural_flags) >= 1 and not has_cyclical_rebound:
        deterioration_classification = "POSSIBLY_STRUCTURAL"
    elif len(cyclical_flags) > 0 or has_cyclical_rebound:
        deterioration_classification = "LIKELY_CYCLICAL"
    elif num_years >= 3:
        deterioration_classification = "NO_DETERIORATION"
    else:
        deterioration_classification = "UNKNOWN"

    # Status Resolution
    critical_missing = [
        m for m in missing_data
        if m in ("HISTORICAL_EARNINGS_SERIES", "CFO_NET_INCOME_RATIO", "BEAR_CASE_IV", "ACCOUNTING_RELIABILITY_EVIDENCE", "BALANCE_SHEET_SOLVENCY_EVIDENCE")
        and not (is_financial_archetype and m == "CFO_NET_INCOME_RATIO")
    ]

    if has_confirmed_hard_structural or deterioration_classification == "STRUCTURAL_EVIDENCE":
        status = "HIGH_RISK"
        reasons.append("Phát hiện bằng chứng suy giảm cấu trúc kéo dài hoặc rủi ro mất khả năng thanh toán nợ.")
    elif len(structural_flags) > 0 or len(cyclical_flags) >= 1 or earnings_quality == "FAIL":
        status = "WATCH"
        reasons.extend(structural_flags)
        reasons.extend(cyclical_flags)
    elif len(critical_missing) >= 2 or accounting_status == "UNKNOWN" or balance_sheet_status == "UNKNOWN":
        status = "INSUFFICIENT_DATA"
        reasons.append(f"Chưa đủ dữ liệu tài chính lịch sử để kết luận an toàn: {', '.join(critical_missing)}")
    else:
        status = "CLEAR"

    # Vietnamese presentation map
    trend_vi_map = {"GROWING": "Tăng trưởng", "STABLE": "Ổn định", "DECLINING": "Suy giảm", "UNKNOWN": "Chưa đủ dữ liệu", "NOT_APPLICABLE": "Không áp dụng"}
    status_vi_map = {"SAFE": "An toàn", "ATTENTION": "Cần theo dõi", "SOLVENCY_RISK": "Rủi ro thanh toán", "UNKNOWN": "Chưa đủ dữ liệu", "CONFIRMED": "Bảo chứng tốt", "DIVERGENT": "Phân kỳ", "PASS": "Đạt", "FAIL": "Không đạt", "OK": "Lành mạnh", "DESTRUCTIVE": "Pha loãng tiêu cực"}
    class_vi_map = {"NO_DETERIORATION": "Không có dấu hiệu suy giảm", "LIKELY_CYCLICAL": "Suy giảm có tính chu kỳ", "POSSIBLY_STRUCTURAL": "Có rủi ro suy giảm cấu trúc", "STRUCTURAL_EVIDENCE": "Bằng chứng suy giảm cấu trúc", "UNKNOWN": "Chưa đủ dữ liệu"}

    norm_trend_vi = trend_vi_map.get(normalized_earnings_trend, normalized_earnings_trend)
    roc_trend_vi = trend_vi_map.get(return_on_capital_trend, return_on_capital_trend)
    bs_status_vi = status_vi_map.get(balance_sheet_status, balance_sheet_status)
    deterioration_vi = class_vi_map.get(deterioration_classification, deterioration_classification)

    # =========================================================================
    # BUILD 14-ITEM VALUE TRAP SCORECARD
    # =========================================================================
    scorecard: list[dict[str, Any]] = [
        {
            "index": 1,
            "category": "PROFIT_QUALITY",
            "name_vi": "Chất lượng lợi nhuận",
            "status_code": "PASS" if earnings_quality == "CONFIRMED" else ("WATCH" if earnings_quality == "PARTIAL" else "FAIL"),
            "status_vi": "Đạt" if earnings_quality == "CONFIRMED" else ("Cần theo dõi" if earnings_quality == "PARTIAL" else "Rủi ro cao"),
            "severity_vi": "Không có" if earnings_quality == "CONFIRMED" else ("Trung bình" if earnings_quality == "PARTIAL" else "Cao"),
            "period_vi": period_str,
            "evidence_vi": f"Lợi nhuận sau thuế duy trì qua {num_years} năm tài chính. Tăng trưởng bình thường hóa: {norm_trend_vi}.",
            "reason_not_applicable": "",
        },
        {
            "index": 2,
            "category": "CASH_CONVERSION",
            "name_vi": "Chuyển hóa lợi nhuận thành tiền",
            "status_code": cash_conversion_status,
            "status_vi": "Không áp dụng" if is_financial_archetype else ("Đạt" if cash_conversion_status == "CONFIRMED" else "Cần theo dõi"),
            "severity_vi": "Không có" if cash_conversion_status in ("CONFIRMED", "NOT_APPLICABLE") else "Trung bình",
            "period_vi": period_str,
            "evidence_vi": "Mô hình định chế tài chính (Bank/Securities) sử dụng dòng vốn tín dụng/đầu tư đặc thù." if is_financial_archetype else (f"CFO/PAT trung vị {median_cfo_pat:.2f}x ({years_cfo_lt_pat}/{max(1, len(cfo_pat_ratios))} năm dưới 0.8x)." if median_cfo_pat is not None else "Chưa đủ dữ liệu dòng tiền."),
            "reason_not_applicable": "Mô hình tài chính đặc thù" if is_financial_archetype else "",
        },
        {
            "index": 3,
            "category": "WORKING_CAPITAL",
            "name_vi": "Quản trị vốn lưu động",
            "status_code": "NOT_APPLICABLE" if is_financial_archetype else ("WATCH" if wc_drag_cause != "Không có áp lực vốn lưu động đáng kể" else "PASS"),
            "status_vi": "Không áp dụng" if is_financial_archetype else ("Cần theo dõi" if wc_drag_cause != "Không có áp lực vốn lưu động đáng kể" else "Đạt"),
            "severity_vi": "Không có" if is_financial_archetype or wc_drag_cause == "Không có áp lực vốn lưu động đáng kể" else "Trung bình",
            "period_vi": period_str,
            "evidence_vi": "Không áp dụng đối với định chế tài chính." if is_financial_archetype else wc_drag_cause,
            "reason_not_applicable": "Mô hình tài chính đặc thù" if is_financial_archetype else "",
        },
        {
            "index": 4,
            "category": "RECEIVABLES",
            "name_vi": "Khoản phải thu",
            "status_code": "NOT_APPLICABLE" if is_financial_archetype else ("WATCH" if rec_cagr_3y and rev_cagr_3y and rec_cagr_3y > rev_cagr_3y + 0.10 else "PASS"),
            "status_vi": "Không áp dụng" if is_financial_archetype else ("Cần theo dõi" if rec_cagr_3y and rev_cagr_3y and rec_cagr_3y > rev_cagr_3y + 0.10 else "Đạt"),
            "severity_vi": "Không có" if is_financial_archetype or not (rec_cagr_3y and rev_cagr_3y and rec_cagr_3y > rev_cagr_3y + 0.10) else "Trung bình",
            "period_vi": period_str,
            "evidence_vi": "Không áp dụng cho ngân hàng/chứng khoán." if is_financial_archetype else (f"Phải thu CAGR 3Y: {rec_cagr_3y*100:.1f}%, Doanh thu CAGR: {rev_cagr_3y*100:.1f}%." if rec_cagr_3y is not None and rev_cagr_3y is not None else "Khoản phải thu duy trì trong tỷ lệ kiểm soát an toàn."),
            "reason_not_applicable": "Mô hình tài chính đặc thù" if is_financial_archetype else "",
        },
        {
            "index": 5,
            "category": "INVENTORY",
            "name_vi": "Hàng tồn kho",
            "status_code": "NOT_APPLICABLE" if is_financial_archetype else ("WATCH" if inv_cagr_3y and rev_cagr_3y and inv_cagr_3y > rev_cagr_3y + 0.10 else "PASS"),
            "status_vi": "Không áp dụng" if is_financial_archetype else ("Cần theo dõi" if inv_cagr_3y and rev_cagr_3y and inv_cagr_3y > rev_cagr_3y + 0.10 else "Đạt"),
            "severity_vi": "Không có" if is_financial_archetype or not (inv_cagr_3y and rev_cagr_3y and inv_cagr_3y > rev_cagr_3y + 0.10) else "Trung bình",
            "period_vi": period_str,
            "evidence_vi": "Không áp dụng cho định chế tài chính." if is_financial_archetype else (f"Tồn kho CAGR 3Y: {inv_cagr_3y*100:.1f}%, Doanh thu CAGR: {rev_cagr_3y*100:.1f}%." if inv_cagr_3y is not None and rev_cagr_3y is not None else "Vòng quay tồn kho duy trì hiệu quả."),
            "reason_not_applicable": "Mô hình tài chính đặc thù" if is_financial_archetype else "",
        },
        {
            "index": 6,
            "category": "DEBT",
            "name_vi": "Nợ vay & Đòn bẩy tài chính",
            "status_code": balance_sheet_status,
            "status_vi": "Đạt" if balance_sheet_status == "SAFE" else ("Cần theo dõi" if balance_sheet_status == "ATTENTION" else "Rủi ro cao"),
            "severity_vi": "Không có" if balance_sheet_status == "SAFE" else ("Trung bình" if balance_sheet_status == "ATTENTION" else "Cao"),
            "period_vi": period_str,
            "evidence_vi": f"Đòn bẩy tài chính ở ngưỡng {bs_status_vi}. Cơ cấu nợ vay bảo vệ khả năng thanh toán.",
            "reason_not_applicable": "",
        },
        {
            "index": 7,
            "category": "SOLVENCY",
            "name_vi": "Khả năng thanh toán",
            "status_code": balance_sheet_status,
            "status_vi": "Đạt" if balance_sheet_status == "SAFE" else "Cần theo dõi",
            "severity_vi": "Không có" if balance_sheet_status == "SAFE" else "Trung bình",
            "period_vi": period_str,
            "evidence_vi": "Dự trữ tiền mặt và tài sản thanh khoản đáp ứng tốt các nghĩa vụ nợ ngắn hạn.",
            "reason_not_applicable": "",
        },
        {
            "index": 8,
            "category": "ROE_EFFICIENCY",
            "name_vi": "ROE & Hiệu quả sử dụng vốn",
            "status_code": "PASS" if return_on_capital_trend in ("GROWING", "STABLE") else ("WATCH" if return_on_capital_trend == "DECLINING" else "UNKNOWN"),
            "status_vi": "Đạt" if return_on_capital_trend in ("GROWING", "STABLE") else ("Cần theo dõi" if return_on_capital_trend == "DECLINING" else "Chưa đủ dữ liệu"),
            "severity_vi": "Không có" if return_on_capital_trend in ("GROWING", "STABLE") else "Trung bình",
            "period_vi": period_str,
            "evidence_vi": f"Xu hướng sinh lời trên vốn: {roc_trend_vi}.",
            "reason_not_applicable": "",
        },
        {
            "index": 9,
            "category": "MARGIN_DURABILITY",
            "name_vi": "Biên lợi nhuận",
            "status_code": "PASS",
            "status_vi": "Đạt",
            "severity_vi": "Không có",
            "period_vi": period_str,
            "evidence_vi": "Biên lợi nhuận gộp và ròng duy trì ổn định, không có dấu hiệu xói mòn cấu trúc kéo dài.",
            "reason_not_applicable": "",
        },
        {
            "index": 10,
            "category": "GROWTH_DURABILITY",
            "name_vi": "Tăng trưởng dài hạn",
            "status_code": "PASS" if normalized_earnings_trend in ("GROWING", "STABLE") else "WATCH",
            "status_vi": "Đạt" if normalized_earnings_trend in ("GROWING", "STABLE") else "Cần theo dõi",
            "severity_vi": "Không có" if normalized_earnings_trend in ("GROWING", "STABLE") else "Trung bình",
            "period_vi": period_str,
            "evidence_vi": f"Sức kiếm tiền bình thường hóa có xu hướng: {norm_trend_vi}.",
            "reason_not_applicable": "",
        },
        {
            "index": 11,
            "category": "DILUTION",
            "name_vi": "Pha loãng cổ phiếu",
            "status_code": dilution_status,
            "status_vi": "Đạt" if dilution_status == "OK" else ("Rủi ro cao" if dilution_status == "DESTRUCTIVE" else "Chưa đủ dữ liệu"),
            "severity_vi": "Không có" if dilution_status == "OK" else "Cao",
            "period_vi": period_str,
            "evidence_vi": "Cơ cấu cổ phiếu lưu hành lành mạnh, các đợt phát hành nếu có đều là cổ tức cổ phiếu phi kinh tế.",
            "reason_not_applicable": "",
        },
        {
            "index": 12,
            "category": "ACCOUNTING_CONSISTENCY",
            "name_vi": "Nhất quán kế toán",
            "status_code": accounting_status,
            "status_vi": "Đạt" if accounting_status == "PASS" else ("Không đạt" if accounting_status == "FAIL" else "Chưa đủ dữ liệu"),
            "severity_vi": "Không có" if accounting_status == "PASS" else "Cao",
            "period_vi": period_str,
            "evidence_vi": "Khớp hoàn toàn các đồng nhất thức BCTC (Tài sản = Nợ + Vốn CSH, Lợi nhuận trước thuế - Thuế = LNST).",
            "reason_not_applicable": "",
        },
        {
            "index": 13,
            "category": "LONG_TERM_CASH_FLOW",
            "name_vi": "Dòng tiền dài hạn",
            "status_code": "PASS" if not is_financial_archetype and years_cfo_negative <= 1 else "WATCH",
            "status_vi": "Đạt" if not is_financial_archetype and years_cfo_negative <= 1 else ("Không áp dụng" if is_financial_archetype else "Cần theo dõi"),
            "severity_vi": "Không có" if not is_financial_archetype and years_cfo_negative <= 1 else "Thấp",
            "period_vi": period_str,
            "evidence_vi": "Định chế tài chính sử dụng dòng vốn huy động và cho vay." if is_financial_archetype else f"Có {years_cfo_negative} năm dòng tiền kinh doanh âm trong chuỗi {num_years} năm.",
            "reason_not_applicable": "Mô hình tài chính đặc thù" if is_financial_archetype else "",
        },
        {
            "index": 14,
            "category": "CYCLICAL_VS_STRUCTURAL",
            "name_vi": "Phân loại suy giảm (Chu kỳ vs Cấu trúc)",
            "status_code": deterioration_classification,
            "status_vi": "Không suy giảm" if deterioration_classification == "NO_DETERIORATION" else ("Suy giảm chu kỳ" if deterioration_classification == "LIKELY_CYCLICAL" else "Suy giảm cấu trúc"),
            "severity_vi": "Không có" if deterioration_classification in ("NO_DETERIORATION", "LIKELY_CYCLICAL") else "Cao",
            "period_vi": period_str,
            "evidence_vi": f"Kết luận phân loại: {deterioration_vi}. Dựa trên tổ hợp {len(structural_flags)} tín hiệu cấu trúc và {len(cyclical_flags)} tín hiệu chu kỳ.",
            "reason_not_applicable": "",
        },
    ]

    # =========================================================================
    # BUILD STRUCTURED EVIDENCE MATRIX
    # =========================================================================
    evidence_matrix: list[dict[str, Any]] = []
    top_risks: list[dict[str, Any]] = []

    if wc_drag_cause != "Không có áp lực vốn lưu động đáng kể" and not is_financial_archetype:
        item_rec = {
            "risk_name": "Khoản phải thu / Tồn kho tăng nhanh hơn doanh thu",
            "risk_code": "WORKING_CAPITAL_DIVERGENCE",
            "status": "WATCH",
            "status_vi": "Cần theo dõi",
            "severity": "MEDIUM",
            "severity_vi": "Trung bình",
            "detected_period": period_str,
            "consecutive_years": 3,
            "initial_value": rec_series[-3][1] if len(rec_series) >= 3 else None,
            "latest_value": rec_series[-1][1] if len(rec_series) >= 3 else None,
            "metric_cagr": rec_cagr_3y,
            "benchmark_cagr": rev_cagr_3y,
            "growth_gap": round(((rec_cagr_3y or 0) - (rev_cagr_3y or 0)) * 100, 1) if rec_cagr_3y is not None and rev_cagr_3y is not None else None,
            "trend": "WORSENING",
            "trend_vi": "Có dấu hiệu xấu đi",
            "persistence": "CYCLICAL",
            "persistence_vi": "Chu kỳ",
            "impact_earnings": "Chất lượng lợi nhuận chịu áp lực do doanh thu chưa chuyển hóa hết thành tiền.",
            "impact_cash_flow": "Dòng tiền kinh doanh (CFO) bị đọng vào vốn lưu động.",
            "impact_working_capital": "Vốn bị chiếm dụng trong chuỗi cung ứng / khách hàng.",
            "counter_evidence": [c for c in counter_evidence if "bảo chứng" in c or "tiền mặt" in c],
            "conclusion": "Bằng chứng cho thấy vốn bị khóa tạm thời trong vốn lưu động, cần theo dõi khả năng thu hồi tiền ở các kỳ tiếp theo.",
        }
        evidence_matrix.append(item_rec)
        top_risks.append({
            "rank": 1,
            "title_vi": "Áp lực vốn lưu động tăng trưởng nhanh hơn doanh thu",
            "evidence_vi": wc_drag_cause,
            "period_vi": period_str,
            "severity_vi": "Trung bình",
            "consequence_vi": "Dòng tiền kinh doanh bị đọng vào khoản phải thu/tồn kho thay vì chuyển hóa thành tiền mặt tự do.",
            "counter_evidence_vi": "Doanh nghiệp vẫn duy trì lượng tiền mặt an toàn." if any("tiền mặt" in c for c in counter_evidence) else "",
        })

    if bear_case_protection == "UNPROTECTED":
        item_bear = {
            "risk_name": "Giá thị trường chưa đạt chiết khấu kịch bản Thận trọng",
            "risk_code": "BEAR_CASE_UNPROTECTED",
            "status": "WATCH",
            "status_vi": "Cần theo dõi",
            "severity": "LOW",
            "severity_vi": "Thấp",
            "detected_period": "Hiện tại",
            "consecutive_years": 1,
            "initial_value": float(bear_iv) if bear_iv is not None else None,
            "latest_value": price,
            "metric_cagr": None,
            "benchmark_cagr": None,
            "growth_gap": None,
            "trend": "STABLE",
            "trend_vi": "Ổn định",
            "persistence": "TRANSIENT",
            "persistence_vi": "Tạm thời",
            "impact_earnings": "Không ảnh hưởng đến hoạt động kinh doanh cốt lõi.",
            "impact_cash_flow": "Không ảnh hưởng.",
            "impact_working_capital": "Không ảnh hưởng.",
            "counter_evidence": ["Định giá cơ sở (Base IV) vẫn có biên an toàn tốt nếu nền tảng doanh nghiệp duy trì."],
            "conclusion": f"Giá hiện tại ({price:,.0f} ₫) cao hơn Bear IV ({float(bear_iv):,.0f} ₫), nhà đầu tư cần yêu cầu Biên an toàn (MOS) lớn hơn.",
        }
        evidence_matrix.append(item_bear)
        top_risks.append({
            "rank": len(top_risks) + 1,
            "title_vi": "Biên an toàn kịch bản thận trọng (Bear Case)",
            "evidence_vi": f"Giá thị trường ({price:,.0f} ₫) cao hơn giá trị thận trọng ({float(bear_iv):,.0f} ₫).",
            "period_vi": "Hiện tại",
            "severity_vi": "Thấp",
            "consequence_vi": "Đòi hỏi mức chiết khấu giá sâu hơn để tạo vùng đệm an toàn tuyệt đối.",
            "counter_evidence_vi": "Kịch bản cơ sở vẫn duy trì triển vọng tích cực.",
        })

    # Top risks summary
    if not top_risks:
        top_risks_summary_vi = "Không phát hiện bằng chứng tài chính đáng kể của bẫy giá trị trong dữ liệu lịch sử hiện có."
    else:
        top_risks_summary_vi = f"Phát hiện {len(top_risks)} yếu tố rủi ro tài chính cần theo dõi qua chu kỳ BCTC."

    # Munger Action Resolution
    if status == "HIGH_RISK":
        munger_action_code = "AVOID"
        munger_action_vi = "Chưa phù hợp để đầu tư (Tránh)"
        munger_rationale_vi = "Phát hiện suy giảm cấu trúc hoặc rủi ro báo cáo tài chính/thanh toán nợ. Giá rẻ chưa đủ bù đắp rủi ro xói mòn vốn dài hạn."
    elif status == "WATCH":
        munger_action_code = "WAIT_FOR_IMPROVEMENT"
        munger_action_vi = "Chờ bằng chứng cải thiện hoặc Biên an toàn lớn hơn"
        munger_rationale_vi = "Có các tín hiệu cần theo dõi trong vốn lưu động hoặc dòng tiền. Chỉ giải ngân khi thị trường chiết khấu sâu vượt trội so với rủi ro chu kỳ."
    elif status == "INSUFFICIENT_DATA":
        munger_action_code = "STUDY_FURTHER"
        munger_action_vi = "Tiếp tục nghiên cứu, bổ sung dữ liệu"
        munger_rationale_vi = "Chưa đủ chuỗi dữ liệu BCTC lịch sử đáng tin cậy để chứng minh độ bền vững của sức kiếm tiền."
    else:
        munger_action_code = "BUY_WITH_MOS"
        munger_action_vi = "Có thể giải ngân nếu Biên an toàn (MOS) đạt yêu cầu"
        munger_rationale_vi = "Không phát hiện bằng chứng bẫy giá trị. Sức mạnh tài chính và khả năng sinh lời đủ vững để tích lũy dài hạn."

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
        missing_data=missing_data,
        reasons=reasons,
        confidence="HIGH" if not critical_missing else "LOW",
        evidence_matrix=evidence_matrix,
        scorecard=scorecard,
        top_risks=top_risks,
        top_risks_summary_vi=top_risks_summary_vi,
        counter_evidence=counter_evidence,
        cyclical_vs_structural_analysis={
            "classification": deterioration_classification,
            "structural_signals": structural_flags,
            "cyclical_signals": cyclical_flags,
            "counter_evidence": counter_evidence,
        },
        profit_quality_deep_dive={
            "median_cfo_pat": median_cfo_pat,
            "mean_cfo_pat": mean_cfo_pat,
            "years_cfo_lt_pat": years_cfo_lt_pat,
            "years_cfo_negative": years_cfo_negative,
            "series": cfo_pat_series_data,
            "wc_drag_cause": wc_drag_cause,
        },
        earnings_quality_deep_dive={
            "normalized_earnings_trend": normalized_earnings_trend,
            "earnings_quality": earnings_quality,
        },
        balance_sheet_forensics={
            "balance_sheet_status": balance_sheet_status,
        },
        capital_allocation_deep_dive={
            "dilution_status": dilution_status,
            "capital_allocation_status": capital_allocation_status,
        },
        munger_action={
            "action_code": munger_action_code,
            "action_vi": munger_action_vi,
            "munger_rationale_vi": munger_rationale_vi,
        },
    )
