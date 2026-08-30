"""High-Quality Stock Screener Engine based on Buffett-Munger 100-point Quality Score."""
from __future__ import annotations

import time
import threading
from collections import defaultdict
from typing import Any, Dict, List, Optional

from .finance_catalog import _schema_connection, FINANCE_SCHEMA
from .value_engine.quality_scorer import QualityScorer, QualityTier
from .value_engine.archetypes import ArchetypeClassifier
from .value_engine.vi_labels import quality_tier_vi

_CACHE_LOCK = threading.Lock()
_SCORED_UNIVERSE_CACHE: List[Dict[str, Any]] = []
_LAST_COMPUTE_TIME: float = 0.0
_CACHE_TTL_SECONDS: float = 600.0  # 10 minutes cache


def _get_vietnamese_tier_label(tier_val: str) -> str:
    mapping = {
        "EXCEPTIONAL": "HẢO HẠNG",
        "HIGH_QUALITY": "CHẤT LƯỢNG CAO",
        "INVESTABLE": "ĐẦU TƯ ĐƯỢC",
        "WATCH": "THEO DÕI",
        "LOW_QUALITY": "CHẤT LƯỢNG THẤP",
    }
    return mapping.get(tier_val, tier_val)


def compute_all_screener_scores(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Compute and cache Quality Scores across the entire active universe."""
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
                """SELECT symbol, fiscal_year, line_item_code, value
                   FROM canonical_facts
                   WHERE period_type = 'FY' AND fiscal_quarter IS NULL
                   ORDER BY symbol, fiscal_year ASC"""
            ).fetchall()

            by_sym = defaultdict(lambda: defaultdict(dict))
            for r in fact_rows:
                sym = str(r["symbol"]).upper().strip()
                try:
                    fy = int(r["fiscal_year"])
                    code = str(r["line_item_code"])
                    val = float(r["value"])
                    by_sym[sym][fy][code] = val
                except (ValueError, TypeError):
                    continue

            price_map = {}
            try:
                db.execute(
                    """CREATE TABLE IF NOT EXISTS market_prices (
                           symbol TEXT,
                           trading_date TEXT,
                           close DOUBLE PRECISION,
                           source TEXT,
                           PRIMARY KEY (symbol, trading_date)
                       )"""
                )
                price_rows = db.execute(
                    """SELECT symbol, close FROM (
                           SELECT symbol, close, ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trading_date DESC) as rn
                           FROM market_prices
                       ) sub WHERE rn = 1"""
                ).fetchall()
                price_map = {str(r["symbol"]).upper().strip(): float(r["close"]) for r in price_rows if r.get("close")}
            except Exception:
                price_map = {}

        scored_items: List[Dict[str, Any]] = []
        for sym, (exch, name, ind) in secs.items():
            hist = by_sym.get(sym)
            if not hist:
                continue
            years = sorted(hist.keys())
            if len(years) < 2:
                continue

            financial_history = []
            for y in years:
                items = hist[y]
                np_val = items.get("IS.PROFIT.NET")
                eq_val = items.get("BS.EQUITY.TOTAL")
                cfo_val = items.get("CF.OPERATING.NET")
                capex_val = items.get("CF.CAPEX")
                debt_val = items.get("BS.DEBT.TOTAL")
                cash_val = items.get("BS.ASSETS.CASH_AND_EQUIVALENTS")
                rev_val = items.get("IS.REVENUE.NET")

                roe_val = round((np_val / eq_val * 100), 1) if (np_val and eq_val and eq_val > 0) else None
                cfo_scaled = cfo_val * 1e9 if cfo_val is not None else None
                np_scaled = np_val * 1e9 if np_val is not None else None
                conv = round((cfo_scaled / np_scaled * 100), 1) if (cfo_scaled and np_scaled and np_scaled > 0) else None

                financial_history.append({
                    "fiscal_year": y,
                    "net_profit": np_scaled,
                    "equity": eq_val * 1e9 if eq_val is not None else None,
                    "roe": roe_val,
                    "operating_cash_flow": cfo_scaled,
                    "free_cash_flow": (cfo_val - capex_val) * 1e9 if (cfo_val is not None and capex_val is not None) else None,
                    "cash_conversion_ratio": conv,
                    "total_debt": debt_val * 1e9 if debt_val is not None else None,
                    "cash_and_equivalents": cash_val * 1e9 if cash_val is not None else None,
                    "revenue": rev_val * 1e9 if rev_val is not None else None,
                })

            arch = ArchetypeClassifier.classify(sym, ind)

            recent_roes = [h["roe"] for h in financial_history[-5:] if h.get("roe") is not None]
            avg_roe_5y = round(sum(recent_roes) / len(recent_roes), 1) if recent_roes else None

            recent_convs = [h["cash_conversion_ratio"] for h in financial_history[-5:] if h.get("cash_conversion_ratio") is not None]
            avg_conv_5y = round(sum(recent_convs) / len(recent_convs), 1) if recent_convs else None

            latest_cfo = financial_history[-1].get("operating_cash_flow") or 0.0
            latest_debt = financial_history[-1].get("total_debt") or 0.0
            latest_cash = financial_history[-1].get("cash_and_equivalents") or 0.0
            net_debt = latest_debt - latest_cash

            try:
                scorecard = QualityScorer.evaluate(
                    archetype_prof=arch,
                    financial_history_10y=financial_history,
                    five_year_avg_roe=avg_roe_5y,
                    five_year_avg_cash_conversion=avg_conv_5y,
                    net_debt_vnd=net_debt,
                    latest_cfo=latest_cfo,
                    true_dilution_5y_pct=0.0,
                )
                scored_items.append({
                    "symbol": sym,
                    "exchange": exch,
                    "company_name": name,
                    "industry": ind,
                    "current_price": price_map.get(sym),
                    "total_score": scorecard.total_score,
                    "tier": scorecard.tier.value,
                    "tier_vi": _get_vietnamese_tier_label(scorecard.tier.value),
                    "moat_score": scorecard.moat_score,
                    "cash_quality_score": scorecard.cash_quality_score,
                    "capital_allocation_score": scorecard.capital_allocation_score,
                    "financial_strength_score": scorecard.financial_strength_score,
                    "predictability_score": scorecard.predictability_score,
                    "governance_score": scorecard.governance_score,
                    "avg_roe_5y": avg_roe_5y,
                    "latest_year": years[-1],
                    "archetype": arch.archetype.value,
                    "recommended_model": arch.recommended_model,
                    "hard_rejects": [r.value for r in scorecard.hard_rejects],
                })
            except Exception:
                continue

        _SCORED_UNIVERSE_CACHE = scored_items
        _LAST_COMPUTE_TIME = now
        return _SCORED_UNIVERSE_CACHE


def get_screener_results(
    min_score: int = 80,
    exchange: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "score",
    limit: int = 200,
) -> Dict[str, Any]:
    """Filter and sort scored universe according to user parameters."""
    universe = compute_all_screener_scores()
    filtered = universe

    # 1. Filter by min_score
    if min_score is not None and min_score > 0:
        filtered = [item for item in filtered if item["total_score"] >= min_score]

    # 2. Filter by exchange
    if exchange and exchange.upper() not in ("ALL", "TẤT CẢ", "*", ""):
        target_exch = exchange.upper().strip()
        filtered = [item for item in filtered if item["exchange"] == target_exch]

    # 3. Search query
    if search and search.strip():
        q = search.strip().lower()
        filtered = [
            item for item in filtered
            if q in item["symbol"].lower()
            or q in item["company_name"].lower()
            or q in item["industry"].lower()
        ]

    # 4. Sorting
    if sort_by == "roe":
        filtered = sorted(filtered, key=lambda x: (x["avg_roe_5y"] is not None, x["avg_roe_5y"] or 0), reverse=True)
    elif sort_by == "symbol":
        filtered = sorted(filtered, key=lambda x: x["symbol"])
    elif sort_by == "moat":
        filtered = sorted(filtered, key=lambda x: (x["moat_score"], x["total_score"]), reverse=True)
    else:  # default: score
        filtered = sorted(filtered, key=lambda x: (x["total_score"], x["avg_roe_5y"] or 0), reverse=True)

    total_screened = len(filtered)
    results = filtered[:limit]

    # Fetch missing prices for displayed results via VNDirect in parallel
    missing_symbols = [it["symbol"] for it in results if it.get("current_price") is None]
    if missing_symbols:
        import concurrent.futures
        from datetime import date, timedelta
        from .market_data import VndirectProvider, frame_to_price_rows

        provider = VndirectProvider()
        today = date.today().isoformat()
        start = (date.today() - timedelta(days=15)).isoformat()

        def _fetch(sym):
            try:
                df = provider.daily_history(sym, start, today)
                if not df.empty:
                    rows = frame_to_price_rows(sym, df, source="vndirect")
                    if rows:
                        return sym, float(rows[-1]["close"]), rows
            except Exception:
                pass
            return sym, None, []

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            fetched = list(ex.map(_fetch, missing_symbols[:50]))

        saved_rows = []
        for sym, close_val, rows in fetched:
            if close_val:
                for it in results:
                    if it["symbol"] == sym:
                        it["current_price"] = close_val
                if rows:
                    saved_rows.extend(rows)

        if saved_rows:
            try:
                with _schema_connection(FINANCE_SCHEMA) as db:
                    for r in saved_rows:
                        db.execute(
                            """INSERT INTO market_prices (symbol, trading_date, close, source)
                               VALUES (?, ?, ?, ?)
                               ON CONFLICT (symbol, trading_date) DO UPDATE SET close = EXCLUDED.close""",
                            [r["symbol"], r["trading_date"], r["close"], r["source"]]
                        )
            except Exception:
                pass

    return {
        "ok": True,
        "total_screened": total_screened,
        "universe_size": len(universe),
        "filters": {
            "min_score": min_score,
            "exchange": exchange or "ALL",
            "search": search or "",
            "sort_by": sort_by,
        },
        "items": results,
    }
