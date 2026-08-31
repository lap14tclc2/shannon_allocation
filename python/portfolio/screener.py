"""High-Quality Stock Screener Engine based on Buffett-Munger Margin of Safety & Quality Score."""
from __future__ import annotations

import time
import threading
from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .finance_catalog import _schema_connection, FINANCE_SCHEMA
from .financial_data.models import (
    CanonicalFact,
    ConsolidationScope,
    EntityType,
    FactIdentityKey,
    PeriodType,
    QualityStatus,
    StatementType,
)
from .value_engine import ValuationEngine
from .value_engine.dilution import classify_share_change
from .value_engine.quality_scorer import QualityScorer, QualityTier
from .value_engine.archetypes import ArchetypeClassifier, EconomicArchetype
from .value_engine.vi_labels import quality_tier_vi, hard_reject_vi, verdict_vi
from .market_data import canonical_vnd_price

_CACHE_LOCK = threading.Lock()
_SCORED_UNIVERSE_CACHE: List[Dict[str, Any]] = []
_LAST_COMPUTE_TIME: float = 0.0
_CACHE_TTL_SECONDS: float = 600.0  # 10 minutes cache

# user-test.md §19 + user yêu cầu: giá phải AUTO-FETCH mỗi lần vào page.
# In-memory cache ngắn (3 phút) tránh quá tải provider khi reload/filter liên tục;
# mỗi lần vào page thật sự (cách nhau > TTL) vẫn fetch giá mới nhất.
_PRICE_FETCH_CACHE: Dict[str, tuple[float, float, float, int, list]] = {}
_PRICE_FETCH_CACHE_TTL: float = 180.0
_PRICE_CACHE_LOCK = threading.Lock()
_PRICE_FETCH_DAYS = 30


def _fetch_latest_prices(
    symbols: List[str],
    start: str,
    today: str,
    max_workers: int = 10,
) -> Dict[str, tuple[float, float, int, list]]:
    """Fetch giá mới nhất + thanh khoản 20D cho list symbols (threaded, có cache).

    Trả {symbol: (latest_close, t_20d_billion, v_20d, price_rows)}.
    Dùng chung cho auto-refresh mỗi request và auto-backfill universe.
    """
    import concurrent.futures
    from .market_data import VndirectProvider, frame_to_price_rows

    provider = VndirectProvider()
    now = time.time()

    def _fetch(sym):
        with _PRICE_CACHE_LOCK:
            cached = _PRICE_FETCH_CACHE.get(sym)
            if cached and (now - cached[0]) < _PRICE_FETCH_CACHE_TTL:
                return sym, cached[1], cached[2], cached[3], cached[4]
        try:
            df = provider.daily_history(sym, start, today)
            if not df.empty:
                df["price_vnd"] = [canonical_vnd_price(c, "vndirect") for c in df["close"]]
                df["turnover_vnd"] = df["volume"] * df["price_vnd"]
                t_20d = float(df["turnover_vnd"].tail(20).mean() / 1e9)
                v_20d = int(df["volume"].tail(20).mean())
                latest_close = float(df["price_vnd"].iloc[-1])
                rows = frame_to_price_rows(sym, df, source="vndirect")
                with _PRICE_CACHE_LOCK:
                    _PRICE_FETCH_CACHE[sym] = (now, latest_close, t_20d, v_20d, rows)
                return sym, latest_close, t_20d, v_20d, rows
        except Exception:
            pass
        return sym, None, 0.0, 0, []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        fetched = list(ex.map(_fetch, symbols))
    return {sym: (close, t_20d, v_20d, rows) for sym, close, t_20d, v_20d, rows in fetched}


def _persist_price_rows(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    try:
        with _schema_connection(FINANCE_SCHEMA) as db:
            for r in rows:
                db.execute(
                    """INSERT INTO market_prices (symbol, trading_date, close, volume, source)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT (symbol, trading_date)
                       DO UPDATE SET close = EXCLUDED.close, volume = EXCLUDED.volume, source = EXCLUDED.source""",
                    [r["symbol"], r["trading_date"], r["close"], r.get("volume"), r["source"]],
                )
    except Exception:
        pass


def _apply_refreshed_price(item: Dict[str, Any], close_val: float) -> None:
    """Cập nhật MOS / buffett-qualified / pe / pb theo giá mới nhất (auto-fetch)."""
    old_price = item.get("current_price")
    item["current_price"] = close_val
    if item.get("intrinsic_value") and item["intrinsic_value"] > 0:
        item["margin_of_safety"] = round(((item["intrinsic_value"] - close_val) / item["intrinsic_value"]) * 100.0, 1)
        item["is_positive_mos"] = item["margin_of_safety"] > 0
        item["is_buffett_qualified"] = item["margin_of_safety"] >= item.get("required_mos", 25.0)
    elif item.get("diagnostic_intrinsic_value") and item["diagnostic_intrinsic_value"] > 0:
        item["diagnostic_mos"] = round(((item["diagnostic_intrinsic_value"] - close_val) / item["diagnostic_intrinsic_value"]) * 100.0, 1)
    # PE/PB scale theo tỷ lệ giá (EPS/BVPS không đổi trong ngắn hạn).
    if old_price and old_price > 0 and close_val > 0:
        ratio = close_val / old_price
        if item.get("pe") is not None:
            item["pe"] = round(float(item["pe"]) * ratio, 1)
        if item.get("pb") is not None:
            item["pb"] = round(float(item["pb"]) * ratio, 2)


def _get_vietnamese_tier_label(tier_val: str) -> str:
    mapping = {
        "EXCEPTIONAL": "HẢO HẠNG",
        "HIGH_QUALITY": "CHẤT LƯỢNG CAO",
        "INVESTABLE": "ĐẦU TƯ ĐƯỢC",
        "WATCH": "THEO DÕI",
        "LOW_QUALITY": "CHẤT LƯỢNG THẤP",
    }
    return mapping.get(tier_val, tier_val)


def _get_vietnamese_valuation_status(status_val: str) -> str:
    # user-test.md: dùng mapping canonical từ Value Engine (vi_labels.verdict_vi)
    # thay vì mapping local trùng — tránh screener và detail lệch nhãn tiếng Việt.
    return verdict_vi(status_val)


# user-test.md: latest-year facts phải khớp CHÍNH XÁC bộ fact mà detail endpoint
# (`app/main.py` -> `valuation_snapshot_from_catalog`) nạp vào Value Engine —
# tức chỉ các code snapshot cung cấp. Đặc biệt KHÔNG gồm IS.REVENUE.NET cho năm
# hiện tại (là lý do mid-cycle normalization của detail dùng 9 năm, không 10).
_LATEST_YEAR_FACT_CODES = {
    "IS.PROFIT.NET",
    "IS.PROFIT.OPERATING",
    "BS.DEBT.TOTAL",
    "BS.ASSETS.CASH_AND_EQUIVALENTS",
    "BS.EQUITY.TOTAL",
    "CF.OPERATING.DEPRECIATION",
    "CF.CAPEX",
    "CF.OPERATING.NET",
    "IS.SHARES.OUTSTANDING",
}
_BILLION = Decimal("1000000000")


def _build_engine_inputs(
    sym: str,
    name: str,
    ind: str,
    hist: Dict[int, Dict[str, Decimal]],
    years: List[int],
    latest_year: int,
    fact_meta: Dict[Any, Dict[str, str]],
    price_map: Dict[str, float],
    div_by_sym: Dict[str, List[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    """Build `ValuationEngine.evaluate` inputs exactly like the detail endpoint.

    Mirrors `app/main.py` `/api/portfolio/valuation/{symbol}`: latest-year facts
    chỉ gồm bộ code snapshot cung cấp (user-test.md: KHÔNG gồm IS.REVENUE.NET cho
    năm hiện tại), các năm còn lại đầy đủ; `financial_history` kèm shares; dilution
    classification thật từ `dividend_canonical`. Kết quả report phải khớp canonical.
    """
    curr_price = price_map.get(sym)
    if not curr_price:
        return None
    latest_items = hist.get(latest_year, {})
    shares_val = latest_items.get("IS.SHARES.OUTSTANDING")
    if shares_val is None or shares_val <= 0:
        return None
    price_d = Decimal(str(curr_price))
    shares_d = Decimal(str(shares_val))

    facts: List[CanonicalFact] = []
    for y in years:
        items = hist[y]
        for code, val in items.items():
            if y == latest_year and code not in _LATEST_YEAR_FACT_CODES:
                continue
            st = StatementType.INCOME_STATEMENT if code.startswith("IS.") else (
                StatementType.BALANCE_SHEET if code.startswith("BS.") else StatementType.CASH_FLOW
            )
            val_dec = Decimal(str(val))
            fact_val = val_dec if code == "IS.SHARES.OUTSTANDING" or abs(val_dec) >= _BILLION else val_dec * _BILLION
            meta = fact_meta.get((sym, y, code)) or {}
            observed_at = str(meta.get("observed_at") or "2026-08-31T00:00:00Z")
            facts.append(CanonicalFact(
                canonical_fact_id=f"db-{sym.lower()}-{code.lower().replace('.', '-')}-{y}",
                identity=FactIdentityKey(
                    security_id=f"sec-{sym.lower()}",
                    statement_type=st,
                    period_end=f"{y}-12-31",
                    period_type=PeriodType.FY,
                    fiscal_year=y,
                    fiscal_quarter=None,
                    consolidation_scope=ConsolidationScope.CONSOLIDATED,
                    line_item_code=code,
                    currency="VND",
                ),
                value=fact_val,
                quality_status=QualityStatus.SINGLE_SOURCE,
                decision_id=f"db-{sym.lower()}-{y}",
                winning_candidate_id=f"finance-db-{sym.lower()}-{code.lower()}-{y}",
                candidate_ids=[],
                observed_at=observed_at,
                valid_from=observed_at,
                reason="Validated Finance DB canonical fact.",
            ))

    financial_history: List[Dict[str, Any]] = []
    for y in years:
        items = hist[y]
        np_val = items.get("IS.PROFIT.NET")
        eq_val = items.get("BS.EQUITY.TOTAL")
        cfo_val = items.get("CF.OPERATING.NET")
        capex_val = items.get("CF.CAPEX")
        debt_val = items.get("BS.DEBT.TOTAL")
        cash_val = items.get("BS.ASSETS.CASH_AND_EQUIVALENTS")
        rev_val = items.get("IS.REVENUE.NET")
        shares_y = items.get("IS.SHARES.OUTSTANDING")

        np_s = float(np_val * _BILLION) if np_val is not None else None
        eq_s = float(eq_val * _BILLION) if eq_val is not None else None
        cfo_s = float(cfo_val * _BILLION) if cfo_val is not None else None
        capex_s = float(abs(capex_val) * _BILLION) if capex_val is not None else None
        roe_h = round((float(np_val) / float(eq_val) * 100), 1) if (np_val is not None and eq_val and eq_val > 0) else None
        conv = round((cfo_s / np_s * 100), 1) if (cfo_s is not None and np_s and np_s > 0) else None
        financial_history.append({
            "fiscal_year": y,
            "revenue": float(rev_val * _BILLION) if rev_val is not None else None,
            "net_profit": np_s,
            "equity": eq_s,
            "roe": roe_h,
            "operating_cash_flow": cfo_s,
            "free_cash_flow": (cfo_s - capex_s) if (cfo_s is not None and capex_s is not None) else None,
            "cash_conversion_ratio": conv,
            "shares_outstanding": float(shares_y) if shares_y is not None else None,
            "total_debt": float(debt_val * _BILLION) if debt_val is not None else None,
            "cash_and_equivalents": float(cash_val * _BILLION) if cash_val is not None else None,
        })

    np_latest = latest_items.get("IS.PROFIT.NET")
    eq_latest = latest_items.get("BS.EQUITY.TOTAL")
    eps = (np_latest * _BILLION / shares_d) if (np_latest is not None and np_latest > 0) else None
    bvps = (eq_latest * _BILLION / shares_d) if (eq_latest is not None and eq_latest > 0) else None
    pe = (price_d / eps) if (eps is not None and eps > 0) else None
    pb = (price_d / bvps) if (bvps is not None and bvps > 0) else None
    roe = (np_latest / eq_latest * Decimal("100")) if (np_latest is not None and eq_latest and eq_latest > 0) else None
    fundamentals = {
        "sector": ind,
        "eps": float(eps) if eps is not None else None,
        "bvps": float(bvps) if bvps is not None else None,
        "pe": float(pe) if pe is not None else None,
        "pb": float(pb) if pb is not None else None,
        "roe": float(roe) if roe is not None else None,
    }

    is_bank = any(token in f"{ind} {name}".lower() for token in ("bank", "ngân hàng"))
    is_securities = any(token in f"{ind} {name}".lower() for token in ("chứng khoán", "securities", "broker", "môi giới"))
    is_insurance = any(token in f"{ind} {name}".lower() for token in ("bảo hiểm", "insurance"))
    is_financial = is_bank or is_securities or is_insurance

    recent_convs = [h["cash_conversion_ratio"] for h in financial_history[-5:] if h.get("cash_conversion_ratio") is not None]
    avg_conv_5y = round(sum(recent_convs) / len(recent_convs), 1) if recent_convs else None
    recent_roes = [h["roe"] for h in financial_history[-5:] if h.get("roe") is not None]
    avg_roe_5y = round(sum(recent_roes) / len(recent_roes), 1) if recent_roes else None

    latest_hist = financial_history[-1] if financial_history else {}
    latest_debt = latest_hist.get("total_debt") or 0
    latest_cash = latest_hist.get("cash_and_equivalents") or 0
    net_debt_calc = 0.0 if is_financial else max(0.0, float(latest_debt - latest_cash))
    latest_cfo = latest_hist.get("operating_cash_flow") or 0
    if is_financial:
        debt_payback_years = None
    elif net_debt_calc > 0 and latest_cfo and latest_cfo > 0:
        debt_payback_years = round(net_debt_calc / latest_cfo, 1)
    else:
        debt_payback_years = 0.0
    op_profit = latest_items.get("IS.PROFIT.OPERATING")
    deprec = latest_items.get("CF.OPERATING.DEPRECIATION")
    ebitda_billion = (float(op_profit) if op_profit is not None else 0.0) + (float(deprec) if deprec is not None else 0.0)
    ebitda_vnd = ebitda_billion * 1e9 if ebitda_billion and ebitda_billion > 0 else 0.0
    net_debt_to_ebitda = None
    if not is_financial and net_debt_calc > 0 and ebitda_vnd > 0:
        ratio = net_debt_calc / ebitda_vnd
        if 0.0 <= ratio < 100.0:
            net_debt_to_ebitda = round(ratio, 2)

    shares_series = [(h["fiscal_year"], h["shares_outstanding"]) for h in financial_history if h.get("shares_outstanding") is not None]
    dilution = None
    if len(shares_series) >= 5 and shares_series[-5][1] and shares_series[-1][1] and shares_series[-5][1] > 0:
        s_old = shares_series[-5][1]
        s_new = shares_series[-1][1]
        start_year = shares_series[-5][0]
        events = [
            e for e in div_by_sym.get(sym, [])
            if e.get("effective_event_date") and e["effective_event_date"] >= f"{start_year}-01-01"
        ]
        dilution = classify_share_change(shares_old=s_old, shares_new=s_new, non_economic_events=events, economic_events=[])

    value_investor_pillars = {
        "earnings_quality": {"avg_cash_conversion_5y": None if is_financial else avg_conv_5y},
        "financial_fortress": {
            "net_debt_vnd": net_debt_calc,
            "debt_payback_years": debt_payback_years,
            "net_debt_to_ebitda": net_debt_to_ebitda,
        },
        "capital_allocation": {
            "avg_roe_5y": avg_roe_5y,
            "confirmed_economic_dilution_5y_pct": dilution["confirmed_economic_dilution_pct"] if dilution else None,
            "unexplained_share_change_5y_pct": dilution["unexplained_share_change_pct"] if dilution else None,
            "non_economic_share_change_5y_pct": dilution["non_economic_share_change_pct"] if dilution else None,
            "raw_share_change_5y_pct": dilution["raw_share_change_pct"] if dilution else None,
            "dilution_classification": dilution["classification"] if dilution else None,
        },
    }

    return {
        "facts": facts,
        "financial_history": financial_history,
        "fundamentals": fundamentals,
        "value_investor_pillars": value_investor_pillars,
        "entity_type": EntityType.BANK if is_bank else EntityType.NORMAL_ENTERPRISE,
        "current_market_price": price_d,
        "shares_outstanding": shares_d,
        "diluted_shares_estimate": shares_d,
        "fiscal_year": latest_year,
        "latest_items": latest_items,
    }


def _fallback_quality_scorecard(
    arch: Any,
    financial_history: List[Dict[str, Any]],
    inputs: Dict[str, Any],
) -> Optional[Any]:
    """QualityScorer fallback dùng đúng inputs canonical khi engine không chạy được."""
    latest_hist = financial_history[-1] if financial_history else {}
    latest_cfo = latest_hist.get("operating_cash_flow") or 0
    latest_debt = latest_hist.get("total_debt") or 0
    latest_cash = latest_hist.get("cash_and_equivalents") or 0
    net_debt = latest_debt - latest_cash
    if not latest_cfo or latest_cfo <= 0:
        latest_cfo = float(inputs["current_market_price"] * inputs["shares_outstanding"] * Decimal("0.1"))
    cap_alloc = inputs["value_investor_pillars"]["capital_allocation"]
    try:
        return QualityScorer.evaluate(
            archetype_prof=arch,
            financial_history_10y=financial_history,
            five_year_avg_roe=cap_alloc.get("avg_roe_5y"),
            five_year_avg_cash_conversion=inputs["value_investor_pillars"]["earnings_quality"].get("avg_cash_conversion_5y"),
            net_debt_vnd=net_debt,
            latest_cfo=latest_cfo,
            true_dilution_5y_pct=cap_alloc.get("confirmed_economic_dilution_5y_pct") or 0.0,
            dilution_classification=cap_alloc.get("dilution_classification"),
        )
    except Exception:
        return None


def _quality_blocked_warning(total_score: int, hard_reject_codes: List[str]) -> str:
    if hard_reject_codes:
        reasons_vi = "; ".join(hard_reject_vi(code) for code in hard_reject_codes)
        return (
            f"KHÔNG đạt tiêu chuẩn Buffett/Munger — {reasons_vi}. "
            f"Điểm Chất lượng {total_score}/100. Không tính Biên An Toàn (MOS) / Giá trị Thực."
        )
    return (
        f"Điểm Chất lượng quá thấp ({total_score}/100 — {quality_tier_vi('LOW_QUALITY')}): "
        f"không đạt tiêu chuẩn Buffett/Munger. Không tính Biên An Toàn (MOS) / Giá trị Thực; khuyến nghị tránh xa."
    )


def compute_all_screener_scores(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Compute and cache Quality Scores and Buffett Margin of Safety across the active universe."""
    global _SCORED_UNIVERSE_CACHE, _LAST_COMPUTE_TIME

    now = time.time()
    with _CACHE_LOCK:
        if not force_refresh and _SCORED_UNIVERSE_CACHE and (now - _LAST_COMPUTE_TIME < _CACHE_TTL_SECONDS):
            return _SCORED_UNIVERSE_CACHE

        with _schema_connection(FINANCE_SCHEMA) as db:
            sec_rows = db.execute(
                "SELECT symbol, exchange, company_name, industry FROM securities ORDER BY symbol"
            ).fetchall()
            secs = {
                str(r["symbol"]).upper().strip(): (
                    str(r["exchange"] or "HOSE").upper().strip(),
                    str(r["company_name"] or "").strip(),
                    str(r["industry"] or "Chưa phân loại").strip(),
                )
                for r in sec_rows
            }

            fact_rows = db.execute(
                """SELECT symbol, fiscal_year, line_item_code, value, quality_status, observed_at
                   FROM canonical_facts
                   WHERE period_type = 'FY' AND fiscal_quarter IS NULL
                   ORDER BY symbol, fiscal_year ASC"""
            ).fetchall()

            by_sym = defaultdict(lambda: defaultdict(dict))
            fact_meta = {}
            for r in fact_rows:
                sym = str(r["symbol"]).upper().strip()
                try:
                    fy = int(r["fiscal_year"])
                    code = str(r["line_item_code"])
                    val = Decimal(str(r["value"]))
                    by_sym[sym][fy][code] = val
                    fact_meta[(sym, fy, code)] = {
                        "quality_status": str(r["quality_status"] or "SINGLE_SOURCE"),
                        "observed_at": str(r["observed_at"] or "2026-08-31T00:00:00Z"),
                    }
                except (ValueError, TypeError):
                    continue

            price_map = {}
            turnover_map = {}
            volume_map = {}
            try:
                db.execute(
                    """CREATE TABLE IF NOT EXISTS market_prices (
                           symbol TEXT,
                           trading_date TEXT,
                           close DOUBLE PRECISION,
                           volume DOUBLE PRECISION,
                           source TEXT,
                           PRIMARY KEY (symbol, trading_date)
                       )"""
                )
                try:
                    db.execute("ALTER TABLE market_prices ADD COLUMN IF NOT EXISTS volume DOUBLE PRECISION")
                except Exception:
                    pass

                price_rows = db.execute(
                    """SELECT symbol, close FROM (
                           SELECT symbol, close, ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trading_date DESC) as rn
                           FROM market_prices
                       ) sub WHERE rn = 1"""
                ).fetchall()
                price_map = {str(r["symbol"]).upper().strip(): float(r["close"]) for r in price_rows if r.get("close")}

                liq_rows = db.execute(
                    """SELECT symbol,
                              AVG(CASE WHEN close < 1000 THEN close * 1000 ELSE close END * COALESCE(volume, 0)) / 1e9 as avg_turnover_billion,
                              AVG(COALESCE(volume, 0)) as avg_vol
                       FROM (
                           SELECT symbol, close, volume, ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trading_date DESC) as rn
                           FROM market_prices
                       ) sub WHERE rn <= 20
                       GROUP BY symbol"""
                ).fetchall()
                for r in liq_rows:
                    sym_key = str(r["symbol"]).upper().strip()
                    turnover_map[sym_key] = round(float(r["avg_turnover_billion"] or 0), 2)
                    volume_map[sym_key] = int(r["avg_vol"] or 0)
            except Exception:
                price_map = {}

            div_by_sym = defaultdict(list)
            try:
                div_rows = db.execute(
                    """SELECT symbol, stock_ratio, effective_event_date
                       FROM dividend_canonical
                       WHERE dividend_type = 'STOCK_DIVIDEND'"""
                ).fetchall()
                for r in div_rows:
                    sym_key = str(r["symbol"]).upper().strip()
                    if r["stock_ratio"]:
                        div_by_sym[sym_key].append({
                            "action_type": "STOCK_DIVIDEND",
                            "stock_ratio": float(r["stock_ratio"]),
                            "effective_event_date": str(r["effective_event_date"] or ""),
                        })
            except Exception:
                pass

        # Auto-backfill giá (bounded per compute) cho mã có BCTC nhưng chưa có giá —
        # đảm bảo universe tự hoàn thiện (không phụ thuộc backfill thủ công).
        missing_price = [
            sym for sym in by_sym
            if len([y for y in by_sym[sym] if by_sym[sym][y]]) >= 2 and sym not in price_map
        ][:40]
        if missing_price:
            from datetime import date, timedelta
            start = (date.today() - timedelta(days=_PRICE_FETCH_DAYS)).isoformat()
            today = date.today().isoformat()
            fetched = _fetch_latest_prices(missing_price, start, today, max_workers=10)
            auto_rows = []
            for sym, (close_val, t_20d, v_20d, rows) in fetched.items():
                if close_val:
                    price_map[sym] = close_val
                    turnover_map[sym] = round(t_20d, 2)
                    volume_map[sym] = v_20d
                    auto_rows.extend(rows)
            if auto_rows:
                _persist_price_rows(auto_rows)

        scored_items: List[Dict[str, Any]] = []
        for sym, (exch, name, ind) in secs.items():
            hist = by_sym.get(sym)
            if not hist:
                continue
            years = sorted(hist.keys())
            if len(years) < 2:
                continue

            arch = ArchetypeClassifier.classify(sym, ind)
            recommended_model = arch.recommended_model
            archetype_code = arch.archetype.value

            # user-test.md: screener KHÔNG còn engine định giá riêng. Dựng inputs
            # GIỐNG HỆT detail endpoint (`app/main.py`) và gọi canonical
            # `ValuationEngine.evaluate`; đọc public_base_iv/public_mos/required_mos/
            # valuation_pill trực tiếp từ `ValuationReport`.
            inputs = _build_engine_inputs(
                sym=sym,
                name=name,
                ind=ind,
                hist=hist,
                years=years,
                latest_year=years[-1],
                fact_meta=fact_meta,
                price_map=price_map,
                div_by_sym=div_by_sym,
            )
            if inputs is None:
                # Không có giá thị trường hoặc số cổ phiếu -> không thể định giá.
                continue

            financial_history = inputs["financial_history"]
            recent_roes = [h["roe"] for h in financial_history[-5:] if h.get("roe") is not None]
            avg_roe_5y = round(sum(recent_roes) / len(recent_roes), 1) if recent_roes else None

            report = None
            try:
                report = ValuationEngine.evaluate(
                    symbol=sym,
                    facts=inputs["facts"],
                    current_market_price=inputs["current_market_price"],
                    shares_outstanding=inputs["shares_outstanding"],
                    diluted_shares_estimate=inputs["diluted_shares_estimate"],
                    fiscal_year=inputs["fiscal_year"],
                    entity_type=inputs["entity_type"],
                    fundamentals=inputs["fundamentals"],
                    financial_history=financial_history,
                    value_investor_pillars=inputs["value_investor_pillars"],
                )
            except Exception:
                report = None

            if report is not None:
                quality = report.quality_scorecard
                model_status = report.model_status
                valuation_gap = " ".join(report.missing_data) if report.missing_data else None
                public_iv = report.public_base_iv
                public_mos = report.public_mos
                req_mos = (report.margin_of_safety_analysis or {}).get("required_mos_pct")
                val_status = report.valuation_pill
                valuation_warning = report.valuation_warning
                data_status = report.data_status
                regime_status = report.regime_status
                numeric_confidence = report.numeric_confidence
                fb = report.fallback_valuation or {}
                diagnostic_iv = fb.get("base_iv") if not public_iv else None
                diagnostic_mos = fb.get("margin_of_safety_pct") if not public_mos else None
                hard_reject_codes = list(quality.get("hard_rejects") or [])
            else:
                # Fallback: engine không chạy được (thiếu required facts). Giữ
                # điểm chất lượng + trạng thái model theo archetype, KHÔNG có
                # public valuation — mã rơi vào section "Thiếu dữ liệu".
                data_status = "INSUFFICIENT"
                regime_status = "SINGLE_REGIME"
                numeric_confidence = "MEDIUM"
                scorecard = _fallback_quality_scorecard(
                    arch=arch,
                    financial_history=financial_history,
                    inputs=inputs,
                )
                if scorecard is None:
                    continue
                quality = {
                    "total_score": scorecard.total_score,
                    "tier": scorecard.tier.value,
                    "moat_score": scorecard.moat_score,
                    "cash_quality_score": scorecard.cash_quality_score,
                    "capital_allocation_score": scorecard.capital_allocation_score,
                    "financial_strength_score": scorecard.financial_strength_score,
                    "predictability_score": scorecard.predictability_score,
                    "governance_score": scorecard.governance_score,
                    "hard_rejects": [r.value for r in scorecard.hard_rejects],
                }
                model_status = "MODEL_INCOMPLETE"
                valuation_gap = "BCTC chưa đủ dữ liệu cần thiết để chạy mô hình định giá (required facts)."
                if arch.archetype == EconomicArchetype.ARCHETYPE_UNKNOWN:
                    model_status = "ARCHETYPE_UNKNOWN"
                    valuation_gap = "Chưa xác định được bản chất kinh tế / mô hình định giá (thiếu thông tin phân loại ngành)."
                elif recommended_model in ("RESERVE_NAV", "FLEET_NAV", "AIRLINE_EBITDAR", "MID_CYCLE_FCFF", "RNAV", "SOTP", "LEASE_CASHFLOW_DCF"):
                    valuation_gap = "Thiếu dữ liệu mô hình đặc thù."
                elif recommended_model == "CONCESSION_DCF" and arch.archetype == EconomicArchetype.AIRPORT_INFRASTRUCTURE:
                    model_status = "MODEL_ESTIMATED"
                    valuation_gap = "Mô hình Ước tính (giả định chưa có nguồn)."
                public_iv = None
                public_mos = None
                req_mos = None
                val_status = model_status if model_status in (
                    "MODEL_INCOMPLETE", "MODEL_ESTIMATED", "ARCHETYPE_UNKNOWN",
                    "ARCHETYPE_UNSUPPORTED", "FALLBACK_MODEL_ONLY",
                ) else "MODEL_INCOMPLETE"
                valuation_warning = None
                hard_reject_codes = quality["hard_rejects"]
                if hard_reject_codes or quality["tier"] == QualityTier.LOW_QUALITY.value:
                    val_status = "AVOID_QUALITY"
                    valuation_warning = _quality_blocked_warning(quality["total_score"], hard_reject_codes)
                diagnostic_iv = None
                diagnostic_mos = None

            is_qualified = public_mos is not None and req_mos is not None and public_mos >= req_mos
            is_positive = public_mos is not None and public_mos > 0

            latest_items = inputs["latest_items"]
            np_latest = latest_items.get("IS.PROFIT.NET")
            eq_latest = latest_items.get("BS.EQUITY.TOTAL")
            shares_latest = latest_items.get("IS.SHARES.OUTSTANDING")
            pe_val = round(float(inputs["current_market_price"]) / float(np_latest * _BILLION / shares_latest), 1) if (np_latest and shares_latest and np_latest > 0) else None
            pb_val = round(float(inputs["current_market_price"]) / float((eq_latest * _BILLION) / shares_latest), 2) if (eq_latest and shares_latest and eq_latest > 0) else None

            scored_items.append({
                "symbol": sym,
                "exchange": exch,
                "company_name": name,
                "industry": ind,
                "current_price": float(inputs["current_market_price"]),
                "intrinsic_value": round(float(public_iv), 1) if public_iv is not None else None,
                "margin_of_safety": round(float(public_mos), 1) if public_mos is not None else None,
                "diagnostic_intrinsic_value": round(float(diagnostic_iv), 1) if diagnostic_iv is not None else None,
                "diagnostic_mos": round(float(diagnostic_mos), 1) if diagnostic_mos is not None else None,
                "required_mos": float(req_mos) if req_mos is not None else None,
                "valuation_status": val_status,
                "valuation_status_vi": _get_vietnamese_valuation_status(val_status),
                "valuation_warning": valuation_warning,
                "is_buffett_qualified": is_qualified,
                "is_positive_mos": is_positive,
                "avg_turnover_20d_billion": turnover_map.get(sym, 0.0),
                "avg_volume_20d": volume_map.get(sym, 0),
                "pe": pe_val,
                "pb": pb_val,
                "total_score": quality["total_score"],
                "tier": quality["tier"],
                "tier_vi": _get_vietnamese_tier_label(quality["tier"]),
                "moat_score": quality["moat_score"],
                "cash_quality_score": quality["cash_quality_score"],
                "capital_allocation_score": quality["capital_allocation_score"],
                "financial_strength_score": quality["financial_strength_score"],
                "predictability_score": quality["predictability_score"],
                "governance_score": quality["governance_score"],
                "avg_roe_5y": avg_roe_5y,
                "latest_year": inputs["fiscal_year"],
                "archetype": archetype_code,
                "recommended_model": recommended_model,
                "model_status": model_status,
                "valuation_gap": valuation_gap,
                "hard_rejects": hard_reject_codes,
                "data_status": data_status,
                "regime_status": regime_status,
                "numeric_confidence": numeric_confidence,
                "validation_confidence": getattr(report, "validation_confidence", None),
            })

        _SCORED_UNIVERSE_CACHE = scored_items
        _LAST_COMPUTE_TIME = now
        return _SCORED_UNIVERSE_CACHE


def get_screener_results(
    mos_filter: Optional[str] = "buffett_qualified",
    min_liquidity: Optional[float] = 10.0,
    min_score: Optional[int] = None,
    exchange: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "mos",
    limit: int = 200,
) -> Dict[str, Any]:
    """Filter and sort universe according to Buffett Margin of Safety, Liquidity, and user parameters."""
    universe = compute_all_screener_scores()
    filtered = universe

    # 1. Filter by Buffett Margin of Safety (Rule #1: Never lose money)
    if mos_filter == "buffett_qualified":
        filtered = [item for item in filtered if item.get("is_buffett_qualified")]
    elif mos_filter == "positive":
        filtered = [item for item in filtered if item.get("is_positive_mos")]
    elif mos_filter == "undervalued":
        # user-test.md: status giờ là canonical ValuationPill từ Value Engine.
        filtered = [item for item in filtered if item.get("valuation_status") in (
            "HIGH_CONVICTION_VALUE", "ATTRACTIVE", "FAIRLY_VALUED",
            "DEEP_VALUE", "UNDERVALUED", "FAIR_VALUE",
        )]

    # 2. Fetch latest prices & 20-day liquidity for candidate items missing recent liquidity
    candidate_symbols = [it["symbol"] for it in filtered if it.get("avg_turnover_20d_billion", 0) == 0][:60]
    if candidate_symbols:
        from datetime import date, timedelta
        start = (date.today() - timedelta(days=_PRICE_FETCH_DAYS)).isoformat()
        today = date.today().isoformat()
        fetched = _fetch_latest_prices(candidate_symbols, start, today, max_workers=10)
        saved_rows = []
        for sym, (close_val, t_20d, v_20d, rows) in fetched.items():
            for it in filtered:
                if it["symbol"] == sym:
                    it["avg_turnover_20d_billion"] = round(t_20d, 2)
                    it["avg_volume_20d"] = v_20d
                    if close_val:
                        _apply_refreshed_price(it, close_val)
            if rows:
                saved_rows.extend(rows)
        if saved_rows:
            _persist_price_rows(saved_rows)

    # 3. Filter by Liquidity (min_liquidity in billion VND/day)
    if min_liquidity is not None and min_liquidity > 0:
        filtered = [item for item in filtered if (item.get("avg_turnover_20d_billion") or 0) >= min_liquidity]

    # 4. Filter by min_score if specified
    if min_score is not None and min_score > 0:
        filtered = [item for item in filtered if item["total_score"] >= min_score]

    # 5. Filter by exchange
    if exchange and exchange.upper() not in ("ALL", "TẤT CẢ", "*", ""):
        target_exch = exchange.upper().strip()
        filtered = [item for item in filtered if item["exchange"] == target_exch]

    # 6. Search query
    if search and search.strip():
        q = search.strip().lower()
        filtered = [
            item for item in filtered
            if q in item["symbol"].lower()
            or q in item["company_name"].lower()
            or q in item["industry"].lower()
        ]

    # 7. Sorting
    if sort_by == "mos":
        filtered = sorted(
            filtered,
            key=lambda x: (x["margin_of_safety"] is not None, x["margin_of_safety"] or -999, x["total_score"]),
            reverse=True,
        )
    elif sort_by == "liquidity":
        filtered = sorted(
            filtered,
            key=lambda x: (x.get("avg_turnover_20d_billion") or 0, x["margin_of_safety"] or -999),
            reverse=True,
        )
    elif sort_by == "score":
        filtered = sorted(
            filtered,
            key=lambda x: (x["total_score"], x["margin_of_safety"] or -999),
            reverse=True,
        )
    elif sort_by == "roe":
        filtered = sorted(
            filtered,
            key=lambda x: (x["avg_roe_5y"] is not None, x["avg_roe_5y"] or 0),
            reverse=True,
        )
    elif sort_by == "moat":
        filtered = sorted(
            filtered,
            key=lambda x: (x["moat_score"], x["total_score"]),
            reverse=True,
        )
    elif sort_by == "symbol":
        filtered = sorted(filtered, key=lambda x: x["symbol"])
    else:  # default: mos
        filtered = sorted(
            filtered,
            key=lambda x: (x["margin_of_safety"] is not None, x["margin_of_safety"] or -999, x["total_score"]),
            reverse=True,
        )

    total_screened = len(filtered)
    # user yêu cầu: giá phải AUTO-FETCH mỗi lần vào page — fetch giá mới nhất cho
    # các mã sẽ hiển thị, cập nhật MOS/PE/PB và persist (cache 180s tránh quá tải).
    # KHÔNG ghi đè avg_turnover ở bước này (liquidity filter đã chạy với giá trị cached).
    display_symbols = [it["symbol"] for it in filtered[:limit]]
    if display_symbols:
        from datetime import date, timedelta
        start = (date.today() - timedelta(days=_PRICE_FETCH_DAYS)).isoformat()
        today = date.today().isoformat()
        fetched = _fetch_latest_prices(display_symbols, start, today, max_workers=10)
        saved_rows = []
        for it in filtered[:limit]:
            res = fetched.get(it["symbol"])
            if not res:
                continue
            close_val, t_20d, v_20d, rows = res
            if close_val:
                _apply_refreshed_price(it, close_val)
            if rows:
                saved_rows.extend(rows)
        if saved_rows:
            _persist_price_rows(saved_rows)

    results = filtered[:limit]

    return {
        "ok": True,
        "total_screened": total_screened,
        "universe_size": len(universe),
        "filters": {
            "mos_filter": mos_filter,
            "min_liquidity": min_liquidity,
            "min_score": min_score,
            "exchange": exchange or "ALL",
            "search": search or "",
            "sort_by": sort_by,
        },
        "items": results,
    }
