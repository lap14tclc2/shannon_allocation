"""Multi-Year FY Financial History Builder & Indicator Extraction (Task 136).

Builds structured multi-year FY financial history from PostgreSQL canonical facts
or pre-loaded historical records. Computes 1Y, 3Y, 5Y, 10Y, and full-history statistics.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from portfolio.finance_catalog import _schema_connection, FINANCE_SCHEMA
from .munger_models import HistoryDepthClass


def classify_history_depth(years: int) -> str:
    if years < 3:
        return HistoryDepthClass.INSUFFICIENT_HISTORY.value
    elif years in (3, 4):
        return HistoryDepthClass.LIMITED.value
    elif years in (5, 6):
        return HistoryDepthClass.USABLE.value
    elif years in (7, 8, 9):
        return HistoryDepthClass.STRONG.value
    else:
        return HistoryDepthClass.DEEP_HISTORY.value


def calculate_cagr(start_val: Optional[float], end_val: Optional[float], years: int) -> Optional[float]:
    if start_val is None or end_val is None or years <= 0:
        return None
    if start_val <= 0 or end_val <= 0:
        return None
    try:
        return (end_val / start_val) ** (1.0 / years) - 1.0
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def calculate_median(values: List[float]) -> Optional[float]:
    clean = [v for v in values if v is not None and not math.isnan(v)]
    if not clean:
        return None
    sorted_v = sorted(clean)
    n = len(sorted_v)
    mid = n // 2
    if n % 2 == 1:
        return float(sorted_v[mid])
    else:
        return float((sorted_v[mid - 1] + sorted_v[mid]) / 2.0)


def load_raw_canonical_facts_db(symbol: str) -> List[Dict[str, Any]]:
    """Load all FY canonical facts for a symbol from PostgreSQL qport_finance.canonical_facts."""
    ticker = symbol.strip().upper()
    try:
        with _schema_connection(FINANCE_SCHEMA) as db:
            rows = db.execute(
                """
                SELECT symbol, statement_type, line_item_code, period_type, fiscal_year, provider, value, quality_status, observed_at
                FROM canonical_facts
                WHERE symbol = %s AND (period_type = 'FY' OR period_type IS NULL)
                ORDER BY fiscal_year ASC, line_item_code ASC
                """,
                (ticker,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        print(f"DEBUG load_raw_canonical_facts_db error for {ticker}: {exc}")
        return []


def build_financial_history_from_facts(
    symbol: str,
    raw_facts: Optional[List[Dict[str, Any]]] = None,
    existing_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build structured multi-year financial history dictionary.

    Returns:
      {
        "symbol": symbol,
        "years": sorted_fy_years,
        "history_start": min_fy,
        "history_end": max_fy,
        "history_years": len(years),
        "history_depth": depth_class,
        "provider": primary_provider,
        "by_year": { fy: { metric_key: val } },
        "series": { metric_key: [ (fy, val) ] },
      }
    """
    ticker = symbol.strip().upper()
    if existing_history and len(existing_history) >= 2:
        # Construct from existing financial_history format
        by_year: Dict[int, Dict[str, Any]] = {}
        for h in existing_history:
            fy = int(h.get("fiscal_year") or 0)
            if fy > 0:
                by_year[fy] = dict(h)
        years = sorted(by_year.keys())
        min_fy = years[0] if years else 0
        max_fy = years[-1] if years else 0
        depth = classify_history_depth(len(years))
        
        # Build series
        series: Dict[str, List[tuple[int, float]]] = {}
        all_keys = set()
        for ydict in by_year.values():
            all_keys.update(ydict.keys())
        for k in all_keys:
            if k in ("fiscal_year", "symbol", "provider"):
                continue
            s_list = []
            for y in years:
                val = by_year[y].get(k)
                if val is not None and isinstance(val, (int, float)) and not math.isnan(val):
                    s_list.append((y, float(val)))
            series[k] = s_list

        return {
            "symbol": ticker,
            "years": years,
            "history_start": min_fy,
            "history_end": max_fy,
            "history_years": len(years),
            "history_depth": depth,
            "provider": by_year.get(max_fy, {}).get("provider", "ssi"),
            "by_year": by_year,
            "series": series,
        }

    facts = raw_facts if raw_facts is not None else load_raw_canonical_facts_db(ticker)
    if not facts:
        return {
            "symbol": ticker,
            "years": [],
            "history_start": 0,
            "history_end": 0,
            "history_years": 0,
            "history_depth": HistoryDepthClass.INSUFFICIENT_HISTORY.value,
            "provider": "unknown",
            "by_year": {},
            "series": {},
        }

    # Deterministic provider resolution: SSI primary per (code, fy) if present, TCBS fallback otherwise
    fact_map: Dict[tuple[str, int], Dict[str, Any]] = {}
    for f in facts:
        fy = f.get("fiscal_year")
        if not fy or not isinstance(fy, int) or fy <= 1900:
            continue
        code = str(f.get("line_item_code") or "").upper()
        p = f.get("provider", "unknown")
        key = (code, fy)

        # SSI primary priority over TCBS
        if key not in fact_map or p == "ssi":
            fact_map[key] = f

    effective_facts = list(fact_map.values())
    ssi_count = sum(1 for f in effective_facts if f.get("provider") == "ssi")
    provider = "ssi" if ssi_count > 0 else (facts[0].get("provider") if facts else "unknown")

    by_year: Dict[int, Dict[str, Any]] = {}
    for f in effective_facts:
        fy = f.get("fiscal_year")
        code = str(f.get("line_item_code") or "").upper()
        p = f.get("provider", "ssi")
        val = f.get("value")
        if val is None:
            continue
        try:
            fval = float(val)
        except (ValueError, TypeError):
            continue

        # Scale TCBS monetary facts (stored in billions) to exact VND if needed
        if p == "tcbs" and "SHARES" not in code and abs(fval) < 1e7 and fval != 0:
            fval = fval * 1e9

        if fy not in by_year:
            by_year[fy] = {"fiscal_year": fy, "provider": provider}

        by_year[fy][code] = fval

        # Map canonical aliases to user-friendly keys
        if code in ("IS.REVENUE.TOTAL", "IS.REVENUE.NET"):
            by_year[fy]["revenue"] = fval
        elif code in ("IS.PROFIT.NET", "IS.NET_INCOME"):
            by_year[fy]["net_profit"] = fval
            by_year[fy]["net_income"] = fval
        elif code == "IS.PROFIT.OPERATING":
            by_year[fy]["operating_profit"] = fval
        elif code == "IS.PROFIT.GROSS":
            by_year[fy]["gross_profit"] = fval
        elif code == "CF.OPERATING.NET":
            by_year[fy]["operating_cash_flow"] = fval
            by_year[fy]["cfo"] = fval
        elif code == "CF.CAPEX":
            by_year[fy]["capex"] = abs(fval)
        elif code == "BS.ASSETS.CASH_AND_EQUIVALENTS":
            by_year[fy]["cash"] = fval
        elif code == "BS.DEBT.TOTAL":
            by_year[fy]["total_debt"] = fval
        elif code in ("BS.EQUITY.TOTAL", "BS.EQUITY.OWNERS"):
            by_year[fy]["equity"] = fval
        elif code in ("IS.SHARES.OUTSTANDING", "BS.SHARES.OUTSTANDING"):
            by_year[fy]["outstanding_shares"] = fval
        elif code in ("BS.RECEIVABLES.TRADE.NET", "BS.ASSETS.RECEIVABLES_TRADE"):
            by_year[fy]["trade_receivables"] = fval
        elif code in ("BS.ASSETS.RECEIVABLES", "BS.ASSETS.SHORT_TERM_RECEIVABLES", "BS.RECEIVABLES.TOTAL"):
            by_year[fy]["total_receivables"] = fval
        elif code == "BS.ADVANCES.SUPPLIERS":
            by_year[fy]["advances_to_suppliers"] = fval
        elif code == "BS.RECEIVABLES.OTHER":
            by_year[fy]["other_receivables"] = fval
        elif code == "BS.RECEIVABLES.PROVISION":
            by_year[fy]["receivables_provision"] = fval
        elif code == "BS.ASSETS.INVENTORY":
            by_year[fy]["inventory"] = fval
        elif code == "BS.ASSETS.TOTAL":
            by_year[fy]["total_assets"] = fval
        elif code == "BS.LIABILITIES.TOTAL":
            by_year[fy]["total_liabilities"] = fval
        elif code == "IS.INTEREST_EXPENSE":
            by_year[fy]["interest_expense"] = abs(fval)
        elif code == "CF.OPERATING.DEPRECIATION":
            by_year[fy]["depreciation"] = fval

    # Explicit Priority & Semantic Conflict Resolution for Receivables across all years
    for fy, ydict in by_year.items():
        trade_rec = ydict.get("trade_receivables")
        tot_rec = ydict.get("total_receivables")

        if trade_rec is not None and tot_rec is not None and trade_rec > tot_rec + 1.0:
            ydict["receivables_source_type"] = "CONFLICT"
            ydict["receivables_semantic_status"] = "DATA_CONFLICT"
            ydict["receivables"] = None
        elif trade_rec is not None:
            ydict["receivables"] = trade_rec
            ydict["receivables_source_type"] = "TRADE_NET"
            ydict["receivables_semantic_status"] = "DATA_VALID"
        elif tot_rec is not None:
            ydict["receivables"] = tot_rec
            ydict["receivables_source_type"] = "TOTAL_PROXY"
            ydict["receivables_semantic_status"] = "DATA_WARNING"
        else:
            ydict["receivables"] = None
            ydict["receivables_source_type"] = "MISSING"
            ydict["receivables_semantic_status"] = "DATA_INVALID"

    years = sorted(by_year.keys())
    min_fy = years[0] if years else 0
    max_fy = years[-1] if years else 0
    depth = classify_history_depth(len(years))

    series: Dict[str, List[tuple[int, float]]] = {}
    all_keys = set()
    for ydict in by_year.values():
        all_keys.update(ydict.keys())
    for k in all_keys:
        if k in ("fiscal_year", "symbol", "provider"):
            continue
        s_list = []
        for y in years:
            val = by_year[y].get(k)
            if val is not None and isinstance(val, (int, float)) and not math.isnan(val):
                s_list.append((y, float(val)))
        series[k] = s_list

    return {
        "symbol": ticker,
        "years": years,
        "history_start": min_fy,
        "history_end": max_fy,
        "history_years": len(years),
        "history_depth": depth,
        "provider": provider,
        "by_year": by_year,
        "series": series,
    }
