"""Munger Liquidity Gate & Market Trading Evaluator (Task 162).

Evaluates real trading liquidity from PostgreSQL canonical market_prices:
1. 20-session & 60-session Average Trading Volume
2. 20-session & 60-session Average Trading Value (Turnover in Billion VND)
3. Trading-day coverage percentage (Active days / total window days)
4. Liquidity Classification:
   - LIQUIDITY_STRONG -> "Thanh khoản tốt"
   - LIQUIDITY_ACCEPTABLE -> "Thanh khoản đủ"
   - LIQUIDITY_WEAK -> "Thanh khoản thấp"
   - LIQUIDITY_INSUFFICIENT_DATA -> "Chưa đủ dữ liệu thanh khoản"
5. Actionable investment liquidity commentary & synthesis with Munger quality and MOS.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

LIQUIDITY_CLASSIFICATION_MAP = {
    "LIQUIDITY_STRONG": "Thanh khoản tốt",
    "LIQUIDITY_ACCEPTABLE": "Thanh khoản đủ",
    "LIQUIDITY_WEAK": "Thanh khoản thấp",
    "LIQUIDITY_INSUFFICIENT_DATA": "Chưa đủ dữ liệu thanh khoản",
}
LIQUIDITY_CLASSIFICATION_VI = LIQUIDITY_CLASSIFICATION_MAP



def classify_liquidity(
    avg_val_20d_billion: Optional[float],
    avg_vol_20d: Optional[float],
    coverage_pct: Optional[float],
    trading_days: int,
) -> Tuple[str, str, str]:
    """Classify trading liquidity into deterministic tiers with investor commentary."""
    if trading_days < 3 or avg_val_20d_billion is None or coverage_pct is None:
        return (
            "LIQUIDITY_INSUFFICIENT_DATA",
            "Chưa đủ dữ liệu thanh khoản",
            "Chưa đủ dữ liệu giao dịch lịch sử để đánh giá thanh khoản.",
        )

    # 1. Strong Liquidity: >= 10 Billion VND/day and >= 85% coverage
    if (avg_val_20d_billion >= 10.0 or (avg_vol_20d and avg_vol_20d >= 500_000)) and coverage_pct >= 85.0:
        return (
            "LIQUIDITY_STRONG",
            "Thanh khoản tốt",
            "Cổ phiếu có thanh khoản dồi dào, thuận lợi cho việc giải ngân và tái cấu trúc vị thế quy mô lớn.",
        )

    # 2. Acceptable Liquidity: >= 1.0 Billion VND/day and >= 60% coverage
    if (avg_val_20d_billion >= 1.0 or (avg_vol_20d and avg_vol_20d >= 50_000)) and coverage_pct >= 60.0:
        return (
            "LIQUIDITY_ACCEPTABLE",
            "Thanh khoản đủ",
            "Thanh khoản đáp ứng yêu cầu giao dịch bình thường, có thể giải ngân theo từng đợt.",
        )

    # 3. Weak Liquidity: < 1.0 Billion VND/day or < 60% coverage
    return (
        "LIQUIDITY_WEAK",
        "Thanh khoản thấp",
        "Thanh khoản thấp, cần thận trọng khi xây dựng hoặc thoát vị thế để tránh rủi ro trượt giá.",
    )


def evaluate_symbol_liquidity(symbol: str) -> Dict[str, Any]:
    """Evaluate 20D and 60D liquidity from PostgreSQL qport_finance.market_prices."""
    ticker = str(symbol or "").strip().upper()
    if not ticker:
        return {
            "symbol": ticker,
            "classification": "LIQUIDITY_INSUFFICIENT_DATA",
            "classification_vi": "Chưa đủ dữ liệu thanh khoản",
            "commentary_vi": "Chưa đủ dữ liệu giao dịch lịch sử để đánh giá thanh khoản.",
            "latest_price": None,
            "avg_volume_20d": None,
            "avg_trading_value_20d_billion": None,
            "avg_volume_60d": None,
            "avg_trading_value_60d_billion": None,
            "trading_day_coverage_pct": None,
            "trading_days_observed": 0,
            "data_status": "INSUFFICIENT_DATA",
        }

    try:
        from ..finance_catalog import _schema_connection, FINANCE_SCHEMA

        with _schema_connection(FINANCE_SCHEMA) as db:
            rows = db.execute(
                """
                SELECT trading_date, close, volume
                FROM market_prices
                WHERE symbol = %s
                ORDER BY trading_date DESC
                LIMIT 60
                """,
                (ticker,),
            ).fetchall()

        if not rows:
            return {
                "symbol": ticker,
                "classification": "LIQUIDITY_INSUFFICIENT_DATA",
                "classification_vi": "Chưa đủ dữ liệu thanh khoản",
                "commentary_vi": "Chưa có dữ liệu thị giá và khối lượng giao dịch trong hệ thống.",
                "latest_price": None,
                "avg_volume_20d": None,
                "avg_trading_value_20d_billion": None,
                "avg_volume_60d": None,
                "avg_trading_value_60d_billion": None,
                "trading_day_coverage_pct": None,
                "trading_days_observed": 0,
                "data_status": "INSUFFICIENT_DATA",
            }

        latest_price = float(rows[0]["close"]) if rows[0].get("close") is not None else None

        # 20-day metrics
        rows_20 = rows[:20]
        vols_20 = [float(r["volume"] or 0) for r in rows_20]
        vals_20 = [(float(r["close"] or 0) * float(r["volume"] or 0)) for r in rows_20]
        active_days_20 = sum(1 for v in vols_20 if v > 0)

        avg_vol_20 = sum(vols_20) / len(vols_20) if vols_20 else 0.0
        avg_val_20_billion = (sum(vals_20) / len(vals_20)) / 1e9 if vals_20 else 0.0
        cov_20 = (active_days_20 / len(vols_20)) * 100.0 if vols_20 else 0.0

        # 60-day metrics
        vols_60 = [float(r["volume"] or 0) for r in rows]
        vals_60 = [(float(r["close"] or 0) * float(r["volume"] or 0)) for r in rows]
        avg_vol_60 = sum(vols_60) / len(vols_60) if vols_60 else avg_vol_20
        avg_val_60_billion = (sum(vals_60) / len(vals_60)) / 1e9 if vals_60 else avg_val_20_billion

        code, vi_label, comment = classify_liquidity(
            avg_val_20d_billion=avg_val_20_billion,
            avg_vol_20d=avg_vol_20,
            coverage_pct=cov_20,
            trading_days=len(rows_20),
        )

        return {
            "symbol": ticker,
            "classification": code,
            "classification_vi": vi_label,
            "commentary_vi": comment,
            "latest_price": latest_price,
            "avg_volume_20d": round(avg_vol_20, 0),
            "avg_trading_value_20d_billion": round(avg_val_20_billion, 2),
            "avg_volume_60d": round(avg_vol_60, 0),
            "avg_trading_value_60d_billion": round(avg_val_60_billion, 2),
            "trading_day_coverage_pct": round(cov_20, 1),
            "trading_days_observed": len(rows_20),
            "data_status": "AVAILABLE",
        }
    except Exception as exc:
        logger.warning(f"Error evaluating liquidity for {ticker}: {exc}")
        return {
            "symbol": ticker,
            "classification": "LIQUIDITY_INSUFFICIENT_DATA",
            "classification_vi": "Chưa đủ dữ liệu thanh khoản",
            "commentary_vi": "Chưa đủ dữ liệu thanh khoản để đánh giá.",
            "latest_price": None,
            "avg_volume_20d": None,
            "avg_trading_value_20d_billion": None,
            "avg_volume_60d": None,
            "avg_trading_value_60d_billion": None,
            "trading_day_coverage_pct": None,
            "trading_days_observed": 0,
            "data_status": "INSUFFICIENT_DATA",
        }


def synthesize_munger_screening_conclusion_vi(
    quality_tier: str,
    compounder_class: str,
    mos: Optional[float],
    req_mos: Optional[float],
    vt_status: str,
    liquidity_code: str,
    hard_failures_count: int = 0,
) -> str:
    """Synthesize holistic conclusion combining Quality, Valuation, Value Trap & Liquidity."""
    is_high_quality = quality_tier in ("EXCEPTIONAL", "HIGH_QUALITY") or compounder_class in ("COMPOUNDER", "POTENTIAL_COMPOUNDER")
    is_mos_qualified = mos is not None and req_mos is not None and mos >= req_mos
    is_liquidity_ok = liquidity_code in ("LIQUIDITY_STRONG", "LIQUIDITY_ACCEPTABLE")

    if hard_failures_count > 0 or vt_status == "HIGH_RISK":
        return "Rủi ro tài chính / bẫy giá trị cao, không phù hợp đầu tư"

    if is_high_quality and is_mos_qualified and is_liquidity_ok:
        return "Đạt tiêu chuẩn Munger — thanh khoản tốt"

    if is_high_quality and is_mos_qualified and not is_liquidity_ok:
        return "Đạt tiêu chuẩn tài chính nhưng thanh khoản thấp, cần thận trọng khi giải ngân"

    if is_high_quality and not is_mos_qualified and is_liquidity_ok:
        return "Doanh nghiệp tốt nhưng giá chưa đủ hấp dẫn, tiếp tục theo dõi"

    if is_high_quality and not is_mos_qualified and not is_liquidity_ok:
        return "Doanh nghiệp chất lượng tốt, thị giá chưa đạt MOS và thanh khoản hạn chế"

    if not is_high_quality and is_mos_qualified:
        return "Định giá hấp dẫn nhưng chất lượng tài chính chưa đạt chuẩn Munger"

    if vt_status == "WATCH":
        return "Có rủi ro chu kỳ BCTC cần theo dõi thêm"

    return "Chưa đủ điều kiện đầu tư dài hạn theo tiêu chuẩn Munger"
