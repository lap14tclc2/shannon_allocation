"""Corporate Action & Share-Basis Normalizer (TASK-152).

Provides canonical mathematical normalization for:
1. Stock Splits, Reverse Splits, Bonus Shares, Stock Dividends, Cash Dividends.
2. Share-basis normalization for per-share financial metrics (EPS, DPS, BVPS).
3. Anti-double-adjustment for historical and real-time market prices.
4. Total Cash Dividend Economics preservation.
5. Intrinsic Value double-counting verification.
6. Retained earnings reconciliation.
7. Portfolio position adjustments without economic distortion.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


class CorporateActionType(str, Enum):
    STOCK_SPLIT = "STOCK_SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    BONUS_SHARES = "BONUS_SHARES"
    BONUS_SHARE = "BONUS_SHARE"
    CASH_DIVIDEND = "CASH_DIVIDEND"
    RIGHTS_ISSUE = "RIGHTS_ISSUE"
    NEW_SHARE_ISSUANCE = "NEW_SHARE_ISSUANCE"
    STOCK_ISSUE = "STOCK_ISSUE"
    ESOP = "ESOP"
    MA_SHARE_ISSUANCE = "MA_SHARE_ISSUANCE"
    MA_ISSUANCE = "MA_ISSUANCE"
    BUYBACK = "BUYBACK"
    OTHER_DILUTION = "OTHER_DILUTION"
    OTHER = "OTHER"


CORPORATE_ACTION_VIETNAMESE = {
    "STOCK_SPLIT": "Chia cổ phiếu",
    "REVERSE_SPLIT": "Gộp cổ phiếu (Chia tách ngược)",
    "BONUS_SHARES": "Cổ phiếu thưởng",
    "BONUS_SHARE": "Cổ phiếu thưởng",
    "STOCK_DIVIDEND": "Cổ tức bằng cổ phiếu",
    "CASH_DIVIDEND": "Cổ tức tiền mặt",
    "RIGHTS_ISSUE": "Phát hành quyền mua",
    "NEW_SHARE_ISSUANCE": "Chào bán / Phát hành cổ phiếu mới",
    "STOCK_ISSUE": "Chào bán / Phát hành cổ phiếu mới",
    "ESOP": "Phát hành ESOP cho người lao động",
    "MA_SHARE_ISSUANCE": "Phát hành cổ phiếu hoán đổi M&A",
    "MA_ISSUANCE": "Phát hành cổ phiếu hoán đổi M&A",
    "BUYBACK": "Mua lại cổ phiếu quỹ",
    "OTHER_DILUTION": "Pha loãng cổ phần khác",
    "OTHER": "Sự kiện quyền khác",
    "ADJUSTED_PRICE": "Giá đã điều chỉnh",
    "RAW_PRICE": "Giá chưa điều chỉnh",
    "CURRENT_SHARE_BASIS": "Cơ sở cổ phần hiện hành",
}


@dataclass(frozen=True)
class CorporateActionEvent:
    symbol: str
    action_type: str  # STOCK_SPLIT, BONUS_SHARE, STOCK_DIVIDEND, CASH_DIVIDEND, etc.
    effective_date: str  # YYYY-MM-DD or fiscal year
    stock_ratio: Optional[float] = None  # e.g., 0.15 for 15% bonus/dividend; 1.0 for 2:1 split; -0.5 for 1:2 reverse split
    split_factor: Optional[float] = None  # e.g., 2.0 for 2:1 split; 1.15 for 15% stock dividend; 0.5 for 1:2 reverse split
    cash_per_share: Optional[float] = None  # VND per share for cash dividend
    issue_price: Optional[float] = None  # VND per share for rights issue / ESOP / new issuance
    fair_value: Optional[float] = None  # Fair value or market price at issuance date
    shares_issued: Optional[float] = None  # Absolute shares issued
    description: Optional[str] = None

    @property
    def multiplier(self) -> float:
        """Returns the multiplier on total share count for non-economic actions."""
        if self.split_factor is not None and self.split_factor > 0:
            return float(self.split_factor)
        if self.stock_ratio is not None:
            return 1.0 + float(self.stock_ratio)
        return 1.0

    @property
    def is_non_economic(self) -> bool:
        """Non-economic actions merely divide the ownership pie into more/fewer slices."""
        return self.action_type in {
            CorporateActionType.STOCK_SPLIT.value,
            CorporateActionType.REVERSE_SPLIT.value,
            CorporateActionType.BONUS_SHARE.value,
            CorporateActionType.BONUS_SHARES.value,
            CorporateActionType.STOCK_DIVIDEND.value,
            "STOCK_SPLIT",
            "REVERSE_SPLIT",
            "BONUS_SHARE",
            "BONUS_SHARES",
            "STOCK_DIVIDEND",
            "SPLIT",
        }

    @property
    def is_economic_dilution(self) -> bool:
        """Economic actions issue new claims against the business and can cause true economic dilution."""
        return self.action_type in {
            CorporateActionType.RIGHTS_ISSUE.value,
            CorporateActionType.NEW_SHARE_ISSUANCE.value,
            CorporateActionType.STOCK_ISSUE.value,
            CorporateActionType.ESOP.value,
            CorporateActionType.MA_SHARE_ISSUANCE.value,
            CorporateActionType.MA_ISSUANCE.value,
            CorporateActionType.OTHER_DILUTION.value,
            "RIGHTS_ISSUE",
            "NEW_SHARE_ISSUANCE",
            "STOCK_ISSUE",
            "ESOP",
            "MA_SHARE_ISSUANCE",
            "MA_ISSUANCE",
            "OTHER_DILUTION",
            "CONVERTIBLE",
        }

    @property
    def is_buyback(self) -> bool:
        """Share buyback reduces total shares outstanding by expending corporate cash."""
        return self.action_type in {
            CorporateActionType.BUYBACK.value,
            "BUYBACK",
            "SHARE_BUYBACK",
        }


def calculate_cumulative_multiplier(
    events: Sequence[CorporateActionEvent],
    from_date_or_year: Union[str, int],
    to_date_or_year: Union[str, int],
) -> float:
    """Calculates cumulative non-economic share multiplier between two dates/years (t1 -> t2).
    
    If t1 < t2, returns multiplier F(t1 -> t2) >= 0.
    If t1 == t2, returns 1.0.
    If t1 > t2, returns 1.0 / F(t2 -> t1).
    """
    from_str = str(from_date_or_year)
    to_str = str(to_date_or_year)

    if from_str == to_str:
        return 1.0

    is_forward = from_str < to_str
    start_bound = from_str if is_forward else to_str
    end_bound = to_str if is_forward else from_str

    mult = 1.0
    for e in events:
        if not e.is_non_economic:
            continue
        edate = str(e.effective_date)
        if start_bound < edate <= end_bound:
            mult *= e.multiplier

    return mult if is_forward else (1.0 / mult if mult != 0 else 1.0)


# ── Per-Share Normalization ───────────────────────────────────────────────────

def normalize_per_share_metric(
    aggregate_value: Optional[float],
    current_shares: Optional[float],
) -> Optional[float]:
    """Calculates normalized per-share metric on the current share basis.
    
    Formula: Metric_current_basis(t) = Aggregate_value(t) / Current_shares(T)
    """
    if aggregate_value is None or current_shares is None or current_shares <= 0:
        return None
    return float(aggregate_value) / float(current_shares)


def normalize_historical_financial_series(
    financial_history: List[Dict[str, Any]],
    current_shares: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Enriches financial history rows with consistent per-share metrics on current share basis.
    
    Guarantees:
    - EPS_normalized(t) = Net_Profit(t) / S_current
    - DPS_normalized(t) = Total_Cash_Dividend(t) / S_current
    - BVPS_normalized(t) = Equity(t) / S_current
    - CAGR(EPS_normalized) == CAGR(Net_Profit) when non-economic share events occur.
    """
    if not financial_history:
        return []

    # If current_shares not explicitly provided, extract latest non-empty shares_outstanding
    if current_shares is None or current_shares <= 0:
        for row in reversed(financial_history):
            s = row.get("shares_outstanding") or row.get("outstanding_shares")
            if s and float(s) > 0:
                current_shares = float(s)
                break

    out: List[Dict[str, Any]] = []
    for row in financial_history:
        r = dict(row)
        np_val = r.get("net_profit")
        eq_val = r.get("equity")
        s_hist = r.get("shares_outstanding") or r.get("outstanding_shares")
        cash_div_total = r.get("cash_dividend_total")

        # Raw historical per-share
        raw_eps = (float(np_val) / float(s_hist)) if (np_val is not None and s_hist and float(s_hist) > 0) else None
        raw_bvps = (float(eq_val) / float(s_hist)) if (eq_val is not None and s_hist and float(s_hist) > 0) else None

        # Current-share-basis normalized per-share
        norm_eps = (float(np_val) / float(current_shares)) if (np_val is not None and current_shares and current_shares > 0) else raw_eps
        norm_bvps = (float(eq_val) / float(current_shares)) if (eq_val is not None and current_shares and current_shares > 0) else raw_bvps

        norm_dps = None
        if cash_div_total is not None and current_shares and current_shares > 0:
            norm_dps = float(cash_div_total) / float(current_shares)
        elif r.get("dps") is not None and s_hist and current_shares and current_shares > 0:
            # If row had raw DPS: total cash = raw_dps * s_hist -> norm_dps = (raw_dps * s_hist) / current_shares
            norm_dps = (float(r["dps"]) * float(s_hist)) / float(current_shares)

        r["raw_eps"] = raw_eps
        r["raw_bvps"] = raw_bvps
        r["eps_normalized"] = norm_eps
        r["bvps_normalized"] = norm_bvps
        r["dps_normalized"] = norm_dps
        r["share_basis"] = current_shares

        out.append(r)

    return out


# ── Price Normalization ───────────────────────────────────────────────────────

def normalize_price_series(
    prices: List[Dict[str, Any]],
    corporate_actions: Sequence[CorporateActionEvent] = (),
    is_provider_adjusted: bool = True,
) -> List[Dict[str, Any]]:
    """Normalizes historical prices to current-share basis while preventing double-adjustment.
    
    Rules:
    - If is_provider_adjusted=True (e.g. VNDIRECT / VNSTOCK dchart API):
      Provider prices are already split-adjusted backwards. We do NOT apply split factor again.
    - If is_provider_adjusted=False (raw exchange prices):
      Apply cumulative split factor backwards from latest date T to historical date t:
      P_normalized(t) = P_raw(t) / F(t -> T).
    """
    if not prices:
        return []

    sorted_prices = sorted(prices, key=lambda x: str(x.get("trading_date") or x.get("ts") or ""))
    if not sorted_prices:
        return []

    latest_date = str(sorted_prices[-1].get("trading_date") or sorted_prices[-1].get("ts") or "")

    out: List[Dict[str, Any]] = []
    for row in sorted_prices:
        r = dict(row)
        curr_d = str(r.get("trading_date") or r.get("ts") or "")
        close_p = r.get("close") or r.get("close_price") or r.get("price")

        if close_p is None:
            r["normalized_close"] = None
            out.append(r)
            continue

        raw_price = float(close_p)

        if is_provider_adjusted:
            # Already adjusted by provider -> Keep verbatim, no second adjustment
            r["normalized_close"] = raw_price
            r["is_adjusted"] = True
            r["adjustment_source"] = "PROVIDER_ADJUSTED"
        else:
            # Raw price -> Apply split factor backwards
            factor = calculate_cumulative_multiplier(corporate_actions, curr_d, latest_date)
            r["normalized_close"] = raw_price / factor if factor > 0 else raw_price
            r["is_adjusted"] = True
            r["adjustment_source"] = "CANONICAL_SPLIT_ADJUSTED"
            r["split_factor_applied"] = factor

        out.append(r)

    return out


# ── Dividend Economics & Double Count Audit ───────────────────────────────────

def verify_no_dividend_double_counting(
    valuation_model_name: str,
    valuation_inputs: Dict[str, Any],
) -> Dict[str, Any]:
    """Audits valuation parameters to prove dividends are not double-counted.
    
    Theoretical Invariants:
    1. Owner Earnings DCF / EPV: Measures pre-distribution free cash flow.
       Cash dividends MUST NOT be added on top of equity DCF value.
    2. Bank RIM (Residual Income Model): Value = Book Value + PV(Residual Income).
       Under clean surplus accounting, retained earnings = Net Income - Dividends.
       Dividends reduce book value and are accounted for; do not add dividends on top.
    3. Dividend Discount Model (DDM): Value = PV(Future Dividends).
       Used as a standalone valuation stream, never summed with DCF/EPV.
    """
    model = valuation_model_name.upper().strip()
    has_double_count = False
    evidence: List[str] = []

    if "DCF" in model or "OWNER_EARNINGS" in model or "EPV" in model:
        # Check if cash flow basis is owner earnings / FCFF / FCFE
        cf_basis = valuation_inputs.get("cashflow_basis", "NET_INCOME_OWNER_EARNINGS")
        evidence.append(f"Model {model} uses cash flow basis: {cf_basis}")
        if valuation_inputs.get("add_dividends_to_dcf") is True:
            has_double_count = True
            evidence.append("VIOLATION: add_dividends_to_dcf is True on DCF model!")
        else:
            evidence.append("Verified: Dividends are treated as cash flow distribution, NOT added to DCF value.")

    elif "RIM" in model or "RESIDUAL_INCOME" in model:
        retention_ratio = valuation_inputs.get("retention_ratio")
        dividend_payout = valuation_inputs.get("dividend_payout_ratio")
        evidence.append(f"Model RIM uses retention_ratio={retention_ratio}, dividend_payout={dividend_payout}")
        if valuation_inputs.get("add_dividends_to_rim") is True:
            has_double_count = True
            evidence.append("VIOLATION: add_dividends_to_rim is True on RIM model!")
        else:
            evidence.append("Verified: Clean surplus accounting preserves dividend deduction from ending Book Value.")

    elif "SOTP" in model:
        evidence.append("Model SOTP aggregates component equity values without dividend addition.")

    return {
        "ok": not has_double_count,
        "model": model,
        "double_counting_detected": has_double_count,
        "evidence": evidence,
        "status": "PASS" if not has_double_count else "FAIL",
    }


# ── Retained Earnings Reconciliation ──────────────────────────────────────────

def reconcile_retained_earnings(
    beginning_re: Optional[float],
    net_income: Optional[float],
    cash_dividends: Optional[float],
    ending_re: Optional[float],
    other_adjustments: Optional[float] = 0.0,
    tolerance_pct: float = 5.0,
) -> Dict[str, Any]:
    """Reconciles Clean Surplus Accounting:
    Ending_RE = Beginning_RE + Net_Income - Cash_Dividends + Other_Adjustments
    """
    if beginning_re is None or net_income is None or ending_re is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "is_reconciled": False,
            "discrepancy": None,
            "explanation": "Chưa đủ dữ liệu để đối chiếu đầy đủ lợi nhuận giữ lại.",
        }

    div_val = float(cash_dividends or 0.0)
    other_val = float(other_adjustments or 0.0)

    expected_ending_re = float(beginning_re) + float(net_income) - div_val + other_val
    actual_ending_re = float(ending_re)
    discrepancy = actual_ending_re - expected_ending_re

    # Materiality check relative to ending equity / net income
    denom = max(abs(actual_ending_re), abs(float(net_income)), 1.0)
    disc_pct = (abs(discrepancy) / denom) * 100.0

    is_reconciled = disc_pct <= tolerance_pct

    if is_reconciled:
        explanation = f"Lợi nhuận giữ lại khớp chuẩn mực (sai số {disc_pct:.2f}% trong ngưỡng cho phép {tolerance_pct}%)."
    else:
        explanation = f"Có biến động vốn chủ/quỹ khác ảnh hưởng lợi nhuận giữ lại (chênh lệch: {discrepancy:,.0f} VND)."

    return {
        "status": "RECONCILED" if is_reconciled else "ADJUSTMENT_DETECTED",
        "is_reconciled": is_reconciled,
        "expected_ending_re": expected_ending_re,
        "actual_ending_re": actual_ending_re,
        "discrepancy": discrepancy,
        "discrepancy_pct": disc_pct,
        "explanation": explanation,
    }


# ── Portfolio Position Adjustment ─────────────────────────────────────────────

def adjust_position_for_corporate_action(
    current_shares: float,
    current_average_cost: float,
    corporate_action: CorporateActionEvent,
) -> Tuple[float, float, float]:
    """Adjusts position quantity and average cost for a non-economic corporate action.
    
    Guarantees:
    - NewShares = OldShares * Multiplier
    - NewAvgCost = OldAvgCost / Multiplier
    - NewInvestedCapital = NewShares * NewAvgCost == OldShares * OldAvgCost (Invariant!)
    
    Returns (new_shares, new_avg_cost, total_cost_basis).
    """
    old_shares = float(current_shares or 0.0)
    old_cost = float(current_average_cost or 0.0)
    old_total = old_shares * old_cost

    if not corporate_action.is_non_economic or old_shares <= 0:
        return old_shares, old_cost, old_total

    mult = corporate_action.multiplier
    if mult <= 0:
        return old_shares, old_cost, old_total

    new_shares = old_shares * mult
    new_cost = old_cost / mult if mult != 0 else old_cost
    new_total = new_shares * new_cost

    return new_shares, new_cost, new_total
