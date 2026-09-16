"""Munger Long-Term Investment Candidate Discovery Engine (Task 158).

Discovers and ranks companies across the universe that meet Warren Buffett & Charlie Munger's
long-term investing standards:
1. QUALITY (Moat, ROE, Margin Stability)
2. DURABILITY (Earnings Volatility, Normalization)
3. FINANCIAL STRENGTH (Cash Fortress, Safe Solvency, D/E)
4. ACCOUNTING CONSISTENCY (Zero Statement Fabrication)
5. CAPITAL ALLOCATION & DILUTION (No destructive equity dilution)
6. VALUE TRAP RISK (Zero structural deterioration, healthy working capital)
7. VALUATION & MARGIN OF SAFETY (Base IV, Bear IV, Required MOS)

Sole evidence source: Canonical SSI Annual Financial Statements in PostgreSQL.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

from .archetypes import ArchetypeClassifier, EconomicArchetype
from .munger_analyzer import build_munger_financial_analysis
from .munger_models import CompounderClassification, FindingSeverity
from .value_trap import evaluate_value_trap

logger = logging.getLogger(__name__)

_CANDIDATE_LOCK = threading.Lock()
_COMPUTATION_CONDITION = threading.Condition(_CANDIDATE_LOCK)
_CACHED_CANDIDATES: List[Dict[str, Any]] = []
_LAST_COMPUTE_TIME: float = 0.0
_CANDIDATE_CACHE_TTL: float = 1800.0  # 30 minutes cache
_IS_COMPUTING: bool = False


def _generate_candidate_rationale_vi(
    symbol: Optional[str] = None,
    quality_tier: Optional[str] = None,
    roe: Optional[float] = None,
    pat_cagr: Optional[float] = None,
    cfo_pat: Optional[float] = None,
    vt_status: str = "CLEAR",
    mos: Optional[float] = None,
    req_mos: Optional[float] = None,
    is_financial: bool = False,
    top_warning_vi: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Generate professional semantic Vietnamese explanation of why company is recommended."""
    reasons = []

    # 1. Profitability & Quality
    if roe is not None and roe >= 20.0:
        reasons.append(f"Hiệu quả sinh lời trên vốn (ROE trung vị {roe:.1f}%) duy trì ở mức vượt trội")
    elif roe is not None and roe >= 14.0:
        reasons.append(f"Hiệu quả sinh lời trên vốn (ROE {roe:.1f}%) ổn định trên mức trung bình thị trường")

    # 2. Growth
    if pat_cagr is not None and pat_cagr >= 0.15:
        reasons.append(f"lợi nhuận sau thuế tăng trưởng bền vững (+{pat_cagr*100:.1f}% CAGR)")
    elif pat_cagr is not None and pat_cagr > 0.0:
        reasons.append(f"lợi nhuận duy trì tăng trưởng dương (+{pat_cagr*100:.1f}% CAGR)")

    # 3. Cash flow conversion
    if not is_financial:
        if cfo_pat is not None and cfo_pat >= 0.85:
            reasons.append("chất lượng chuyển hóa lợi nhuận thành dòng tiền tự do (CFO/PAT) lành mạnh")
        elif cfo_pat is not None and cfo_pat < 0.60:
            reasons.append("dòng tiền kinh doanh chịu áp lực đọng vốn tạm thời")

    # 4. Value trap & Solvency
    if vt_status == "CLEAR":
        reasons.append("chưa phát hiện bằng chứng bẫy giá trị hay suy giảm cấu trúc tài chính")
    elif vt_status == "WATCH":
        reasons.append("có một số tín hiệu chu kỳ cần theo dõi chặt chẽ")

    base_text = ", ".join(reasons)
    if not base_text:
        base_text = "Nền tảng tài chính và chất lượng kinh doanh đáp ứng các tiêu chuẩn cơ bản"

    # Capitalize only the first character without lowercasing acronyms (ROE, CAGR, CFO/PAT)
    formatted_base = base_text[0].upper() + base_text[1:] if base_text else ""

    # Valuation context
    if mos is not None and req_mos is not None:
        if mos >= req_mos:
            val_context = f" Đặc biệt, thị giá đang chiết khấu hấp dẫn với Biên an toàn thực tế đạt {mos:.1f}% (vượt mức yêu cầu {req_mos:.0f}%)."
        else:
            val_context = f" Tuy nhiên, Biên an toàn hiện tại ({mos:.1f}%) chưa đạt mức chiết khấu yêu cầu ({req_mos:.0f}%), nhà đầu tư nên kiên nhẫn chờ điểm mua tối ưu."
    else:
        val_context = " Cần đối chiếu thêm giá trị nội tại cơ sở để xác định điểm giải ngân an toàn."

    return f"{formatted_base}.{val_context}"


_build_recommendation_reason_vi = _generate_candidate_rationale_vi


def _evaluate_candidate_symbol(sym: str) -> Optional[Dict[str, Any]]:
    """Evaluate a single symbol against Munger candidate standards and attach liquidity assessment."""
    try:
        from ..canonical_valuation import build_canonical_valuation
        from .value_trap import evaluate_value_trap

        val = build_canonical_valuation(sym, compute_munger=True)
        if not val.get("ok"):
            return None

        munger = val.get("munger_analysis", {})
        quality_tier = val.get("quality_tier", "UNKNOWN")
        compounder_class = munger.get("compounder_classification", "UNKNOWN")
        overall_quality = munger.get("overall_financial_quality", {})

        # Munger Filtering Gates (Never compromise on quality / integrity)
        accounting_status = overall_quality.get("accounting_consistency", "UNKNOWN")
        solvency_status = overall_quality.get("balance_sheet", "UNKNOWN")
        dilution_status = overall_quality.get("dilution", "UNKNOWN")
        history_years = munger.get("history_years", 0)

        # Hard Reject: Accounting Failure, Solvency Collapse, Destructive Dilution, Insufficient History
        if accounting_status == "FAIL":
            return None
        if solvency_status in ("FAIL", "SOLVENCY_RISK"):
            return None
        if dilution_status == "FAIL" or dilution_status == "DESTRUCTIVE":
            return None
        if history_years < 2:
            return None

        # Evaluate Value Trap
        vt = evaluate_value_trap(sym, valuation_report=val)
        if vt.status == "HIGH_RISK" or vt.deterioration_classification == "STRUCTURAL_EVIDENCE":
            return None

        # Extract Financial Metrics
        growth_metrics = munger.get("growth_analysis", {}).get("metrics", {})
        prof_metrics = munger.get("profitability_analysis", {}).get("metrics", {})
        eq_metrics = munger.get("earnings_quality", {}).get("metrics", {})
        bs_metrics = munger.get("balance_sheet_strength", {}).get("metrics", {})

        roe_val = prof_metrics.get("median_roe")
        if roe_val is not None:
            roe_pct = round(float(roe_val) * 100, 1)
        else:
            roe_pct = None

        pat_cagr = growth_metrics.get("net_profit_cagr")
        cfo_pat_val = eq_metrics.get("avg_cfo_pat")
        cfo_pat = round(float(cfo_pat_val), 2) if cfo_pat_val is not None else None
        de_ratio = bs_metrics.get("latest_debt_equity")

        is_fin = munger.get("archetype") in ("BANK", "SECURITIES")

        # Filter minimum acceptable quality threshold for Munger candidates
        is_quality_qualified = (
            quality_tier in ("EXCEPTIONAL", "HIGH_QUALITY", "INVESTABLE")
            or compounder_class in ("COMPOUNDER", "POTENTIAL_COMPOUNDER", "CONSISTENT_GROWER")
            or (roe_pct is not None and roe_pct >= 14.0 and (pat_cagr is None or pat_cagr >= 0.05))
        )

        if not is_quality_qualified:
            return None

        current_price = val.get("current_price")
        base_iv = val.get("base_iv")
        bear_iv = val.get("bear_iv")
        actual_mos = val.get("actual_mos_pct")
        req_mos = val.get("required_mos_pct", 25.0)

        # Top Warning
        findings = munger.get("all_findings", [])
        crit_findings = [f for f in findings if f.get("severity") in ("CRITICAL", "HIGH", "MEDIUM")]
        if crit_findings:
            top_f = crit_findings[0]
            top_warning_vi = top_f.get("explanation") or top_f.get("impact") or "Cần theo dõi chu kỳ kinh doanh"
        elif vt.top_risks:
            top_warning_vi = vt.top_risks[0].get("title_vi", "Không có rủi ro trọng yếu")
        else:
            top_warning_vi = "Không có cảnh báo tài chính trọng yếu"

        # Decision state
        decision_state = munger.get("long_term_decision", {}).get("state") or val.get("verdict") or "HOLD"

        # Candidate Category Labeling
        if quality_tier == "EXCEPTIONAL" or compounder_class == "COMPOUNDER":
            candidate_tier_code = "EXCEPTIONAL"
            candidate_tier_vi = "Chất lượng xuất sắc"
            rank_score = 100
        elif quality_tier == "HIGH_QUALITY" or compounder_class == "POTENTIAL_COMPOUNDER":
            candidate_tier_code = "HIGH_QUALITY"
            candidate_tier_vi = "Chất lượng cao"
            rank_score = 80
        else:
            candidate_tier_code = "INVESTABLE"
            candidate_tier_vi = "Đáng xem xét"
            rank_score = 60

        # Score boosts for ROE, clean Value Trap, and MOS
        if roe_pct is not None:
            if roe_pct >= 25.0:
                rank_score += 25
            elif roe_pct >= 18.0:
                rank_score += 15
            elif roe_pct >= 14.0:
                rank_score += 8

        if vt.status == "CLEAR":
            rank_score += 15

        if actual_mos is not None and req_mos is not None:
            if actual_mos >= req_mos:
                rank_score += 30
            elif actual_mos > 0:
                rank_score += 10

        if cfo_pat is not None and cfo_pat >= 1.0:
            rank_score += 10

        if pat_cagr is not None and pat_cagr >= 0.15:
            rank_score += 10

        # Construct Vietnamese synthesis rationale
        rationale_vi = _build_recommendation_reason_vi(
            roe=roe_pct,
            pat_cagr=pat_cagr,
            cfo_pat=cfo_pat,
            is_financial=is_fin,
            vt_status=vt.status,
            mos=actual_mos,
            req_mos=req_mos,
        )

        # Evaluate real market liquidity from qport_finance.market_prices
        from .liquidity_evaluator import evaluate_symbol_liquidity, synthesize_munger_screening_conclusion_vi
        liq = evaluate_symbol_liquidity(sym)
        liq_code = liq.get("classification", "LIQUIDITY_INSUFFICIENT_DATA")

        # Hard Reject: Illiquid stocks with trading value < 5.0 Billion VND/day
        avg_val_20b = liq.get("avg_trading_value_20d_billion")
        if avg_val_20b is not None and avg_val_20b < 5.0:
            return None

        hard_failures_count = len([f for f in crit_findings if f.get("severity") in ("CRITICAL", "HIGH") and f.get("status") == "FAIL"])
        synthesis_conclusion = synthesize_munger_screening_conclusion_vi(
            quality_tier=quality_tier,
            compounder_class=compounder_class,
            mos=actual_mos,
            req_mos=req_mos,
            vt_status=vt.status,
            liquidity_code=liq_code,
            hard_failures_count=hard_failures_count,
        )

        # Boost score if liquidity is strong or acceptable
        if liq_code == "LIQUIDITY_STRONG":
            rank_score += 10
        elif liq_code == "LIQUIDITY_ACCEPTABLE":
            rank_score += 5

        is_mos_pass = bool(actual_mos is not None and req_mos is not None and actual_mos >= req_mos)
        mos_code = "MOS_QUALIFIED" if is_mos_pass else ("MOS_NEGATIVE" if (actual_mos is not None and actual_mos < 0) else "MOS_BELOW_REQUIRED")
        mos_status_vi = "Đạt biên an toàn (Xem xét mua)" if is_mos_pass else ("Thị giá cao hơn giá trị thực (Tiếp tục theo dõi)" if (actual_mos is not None and actual_mos < 0) else "Chưa đạt biên an toàn (Tiếp tục theo dõi)")
        price_status_vi = "Đạt biên an toàn" if is_mos_pass else ("Chưa hấp dẫn (Cao hơn định giá)" if (actual_mos is not None and actual_mos < 0) else "Chờ chiết khấu thêm")

        return {
            "symbol": sym,
            "company_name": val.get("company_name") or f"Doanh nghiệp {sym}",
            "archetype": munger.get("archetype", "NORMAL_ENTERPRISE"),
            "archetype_vi": "Ngân hàng" if is_fin and munger.get("archetype") == "BANK" else ("Chứng khoán" if is_fin else "Doanh nghiệp sản xuất / kinh doanh"),
            "quality_tier": quality_tier,
            "quality_tier_vi": candidate_tier_vi,
            "candidate_tier_code": candidate_tier_code,
            "compounder_classification": compounder_class,
            "current_price": current_price,
            "base_iv": base_iv,
            "bear_iv": bear_iv,
            "actual_mos_pct": actual_mos,
            "required_mos_pct": req_mos,
            "is_mos_qualified": is_mos_pass,
            "mos_status_code": mos_code,
            "mos_status_vi": mos_status_vi,
            "price_status_vi": price_status_vi,
            "value_trap_status": vt.status,
            "value_trap_status_vi": "Chưa thấy dấu hiệu bẫy giá trị" if vt.status == "CLEAR" else "Có rủi ro cần theo dõi",
            "deterioration_classification": vt.deterioration_classification,
            "roe_pct": roe_pct,
            "net_profit_cagr": pat_cagr,
            "net_profit_cagr_pct": round(pat_cagr * 100, 1) if pat_cagr is not None else None,
            "cfo_to_pat": cfo_pat if not is_fin else None,
            "cfo_to_pat_display": f"{cfo_pat:.2f}x" if cfo_pat is not None and not is_fin else ("Không áp dụng (Bank/Securities)" if is_fin else "Chưa đủ dữ liệu"),
            "debt_to_equity": round(float(de_ratio), 2) if de_ratio is not None and not is_fin else None,
            "debt_to_equity_display": f"{float(de_ratio):.2f}x" if de_ratio is not None and not is_fin else ("Không áp dụng" if is_fin else "An toàn"),
            "liquidity": {
                "classification": liq.get("classification"),
                "classification_vi": liq.get("classification_vi"),
                "commentary_vi": liq.get("commentary_vi"),
                "avg_volume_20d": liq.get("avg_volume_20d"),
                "avg_trading_value_20d_billion": liq.get("avg_trading_value_20d_billion"),
                "avg_volume_60d": liq.get("avg_volume_60d"),
                "avg_trading_value_60d_billion": liq.get("avg_trading_value_60d_billion"),
                "trading_day_coverage_pct": liq.get("trading_day_coverage_pct"),
                "trading_days_observed": liq.get("trading_days_observed"),
                "data_status": liq.get("data_status"),
            },
            "liquidity_classification": liq.get("classification"),
            "liquidity_classification_vi": liq.get("classification_vi"),
            "synthesis_conclusion_vi": synthesis_conclusion,
            "top_warning_vi": top_warning_vi,
            "decision": decision_state,
            "decision_vi": "Có thể xem xét mua" if decision_state in ("BUY", "BUY_MORE", "BUY_UNDER_MOS") else ("Có thể xem xét mua (Cần theo dõi rủi ro)" if decision_state in ("CONDITIONAL_BUY", "BUY_WATCH") else ("Theo dõi (Chờ biên an toàn)" if decision_state == "WAIT_FOR_MOS" else "Tiếp tục nắm giữ / Theo dõi")),
            "recommendation_reason_vi": rationale_vi,
            "rank_score": rank_score,
            "history_years": history_years,
            "data_source": "Nguồn BCTC: SSI (Chuẩn hóa)",
            "updated_at": val.get("valuation_date") or time.strftime("%Y-%m-%d"),
        }
    except Exception as exc:
        logger.warning(f"Error evaluating candidate {sym}: {exc}")
        return None


def compute_all_munger_candidates(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Scan universe and compute ranked list of Buffett-Munger long-term investment candidates."""
    global _CACHED_CANDIDATES, _LAST_COMPUTE_TIME, _IS_COMPUTING

    now = time.time()
    with _CANDIDATE_LOCK:
        # 1. Fast path: fresh cache
        if not force_refresh and _CACHED_CANDIDATES and (now - _LAST_COMPUTE_TIME) < _CANDIDATE_CACHE_TTL:
            return _CACHED_CANDIDATES

        # 2. Concurrency guard: if another thread is already computing
        if _IS_COMPUTING:
            # Stale-while-revalidate: if we have existing cached candidates, return immediately
            if _CACHED_CANDIDATES:
                return _CACHED_CANDIDATES
            # Cold start: wait until the active computation finishes
            while _IS_COMPUTING:
                _COMPUTATION_CONDITION.wait(timeout=1.0)
            if _CACHED_CANDIDATES:
                return _CACHED_CANDIDATES

        _IS_COMPUTING = True

    try:
        from ..finance_catalog import FINANCE_SCHEMA, _schema_connection

        # 3. Fetch symbols pre-filtered by liquidity in PostgreSQL (>= 3.0 billion VND/day gives buffer for >=5.0B rule)
        # This reduces evaluation universe from 1,495 penny/delisted stocks down to ~200 liquid stocks (7.5x faster).
        try:
            with _schema_connection(FINANCE_SCHEMA) as db:
                rows = db.execute(
                    """
                    WITH recent_dates AS (
                        SELECT DISTINCT trading_date 
                        FROM market_prices 
                        ORDER BY trading_date DESC 
                        LIMIT 20
                    ),
                    liquid_symbols AS (
                        SELECT symbol
                        FROM market_prices
                        WHERE trading_date IN (SELECT trading_date FROM recent_dates)
                        GROUP BY symbol
                        HAVING AVG(close * volume) / 1e9 >= 3.0
                    )
                    SELECT s.symbol 
                    FROM canonical_facts s
                    JOIN liquid_symbols l ON s.symbol = l.symbol
                    WHERE s.period_type = 'FY'
                    GROUP BY s.symbol
                    HAVING count(*) >= 8
                    ORDER BY s.symbol;
                    """
                ).fetchall()
            symbols = [str(r["symbol"]).upper().strip() for r in rows if r.get("symbol")]
        except Exception as exc:
            logger.warning(f"Error fetching canonical facts symbols: {exc}")
            symbols = ["FPT", "DGC", "ACB", "VIX", "VNM", "MWG", "HPG", "MBB", "TCB", "VCB", "REE"]

        # Ensure essential watchlist & holding symbols are always evaluated
        essential_symbols = [
            "FPT", "DGC", "ACB", "VIX", "VNM", "MWG", "HPG", "MBB", "TCB", "VCB", "REE",
            "TLG", "TPB", "PNJ", "MSN", "GAS", "VHM", "VIC", "SSI", "VND", "HCM"
        ]
        for s in essential_symbols:
            if s not in symbols:
                symbols.append(s)

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            results = list(executor.map(_evaluate_candidate_symbol, symbols))

        candidates = [r for r in results if r is not None]

        # Sort candidates: Rank Score descending (Quality -> Durability -> Financial Strength -> MOS -> Liquidity)
        candidates.sort(key=lambda c: c["rank_score"], reverse=True)

        with _CANDIDATE_LOCK:
            _CACHED_CANDIDATES = candidates
            _LAST_COMPUTE_TIME = time.time()
            return _CACHED_CANDIDATES
    finally:
        with _CANDIDATE_LOCK:
            _IS_COMPUTING = False
            _COMPUTATION_CONDITION.notify_all()


def warm_munger_candidates_cache_async() -> None:
    """Trigger background computation to warm candidate cache without blocking server startup."""
    import threading
    t = threading.Thread(target=compute_all_munger_candidates, kwargs={"force_refresh": False}, daemon=True)
    t.start()


def get_munger_candidates(
    tier: Optional[str] = "all",
    liquidity: Optional[str] = "all",
    search: Optional[str] = None,
    min_val_billion: Optional[float] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Get filtered Munger candidate list for frontend presentation."""
    all_candidates = compute_all_munger_candidates()
    filtered = all_candidates

    if tier and tier.lower() not in ("all", "tat_ca", "tất cả", "*", ""):
        t_code = tier.upper().strip()
        filtered = [c for c in filtered if c["candidate_tier_code"] == t_code or c["quality_tier"] == t_code]

    if liquidity and liquidity.lower() not in ("all", "tat_ca", "tất cả", "*", ""):
        l_code = liquidity.upper().strip()
        if not l_code.startswith("LIQUIDITY_"):
            l_code = f"LIQUIDITY_{l_code}"
        filtered = [c for c in filtered if c.get("liquidity_classification") == l_code]

    try:
        min_val = float(min_val_billion) if min_val_billion is not None else 5.0
        filtered = [
            c for c in filtered
            if (c.get("liquidity", {}).get("avg_trading_value_20d_billion") or 0.0) >= min_val
        ]
    except (ValueError, TypeError):
        pass

    if search and search.strip():
        q = search.strip().lower()
        filtered = [c for c in filtered if q in c["symbol"].lower() or q in c["company_name"].lower()]

    total_count = len(filtered)
    items = filtered[:limit]

    return {
        "ok": True,
        "total": total_count,
        "count": len(items),
        "candidates": items,
        "top_candidates": all_candidates[:8],
        "summary": {
            "total_universe_evaluated": len(all_candidates),
            "exceptional_count": sum(1 for c in all_candidates if c["candidate_tier_code"] == "EXCEPTIONAL"),
            "high_quality_count": sum(1 for c in all_candidates if c["candidate_tier_code"] == "HIGH_QUALITY"),
            "investable_count": sum(1 for c in all_candidates if c["candidate_tier_code"] == "INVESTABLE"),
            "mos_qualified_count": sum(1 for c in all_candidates if c.get("is_mos_qualified")),
            "strong_liquidity_count": sum(1 for c in all_candidates if c.get("liquidity_classification") == "LIQUIDITY_STRONG"),
            "acceptable_liquidity_count": sum(1 for c in all_candidates if c.get("liquidity_classification") == "LIQUIDITY_ACCEPTABLE"),
        },
    }
