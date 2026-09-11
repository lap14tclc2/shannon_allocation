from __future__ import annotations

import re
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from portfolio.financial_data.models import (
    CanonicalFact,
    ConsolidationScope,
    EntityType,
    FactIdentityKey,
    PeriodType,
    QualityStatus,
    StatementType,
)
from portfolio.finance_catalog import (
    _schema_connection,
    FINANCE_SCHEMA,
    valuation_snapshot_from_catalog,
)
from portfolio.value_engine import ValuationEngine
from portfolio.value_engine.dilution import classify_share_change


def normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def field(rows: list[dict], *aliases: str, reverse: bool = False):
    wanted = [normalized_key(alias) for alias in aliases]
    source = list(reversed(rows or [])) if reverse else list(rows or [])
    for row in source:
        if not isinstance(row, dict):
            continue
        normalized = {normalized_key(key): value for key, value in row.items()}
        for alias in wanted:
            for key, value in normalized.items():
                if value is not None and value != "" and (key == alias or key.endswith(alias)):
                    return value
    return None


def number(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        parsed = Decimal(str(value).replace(",", ""))
        return parsed if parsed.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def build_canonical_valuation(
    symbol: str,
    store: Any | None = None,
    market_price: float | None = None,
) -> dict[str, Any]:
    """Single canonical valuation application builder.

    Guarantees: same symbol + same Finance DB facts + same market price
    => same ValuationReport and structured metrics.
    """
    ticker = str(symbol or "").upper().strip()
    if not re.fullmatch(r"[A-Z0-9]{3,10}", ticker):
        return {
            "ok": False,
            "symbol": ticker,
            "code": "INVALID_TICKER",
            "error": "Invalid stock symbol.",
            "quality_tier": "UNKNOWN",
            "financial_history": [],
            "financial_history_10y": [],
        }

    current_price_val = market_price
    if (current_price_val is None or current_price_val <= 0) and store is not None:
        latest_row = store.latest_price(ticker)
        current_price_val = latest_row.get("close") if latest_row else None
        if current_price_val is None or current_price_val <= 0:
            try:
                today_str = store.today_vn() if hasattr(store, "today_vn") else date.today().isoformat()
                today_d = date.fromisoformat(today_str)
                start_str = (today_d - timedelta(days=30)).isoformat()
                from portfolio.market_data import AutoMarketData, frame_to_price_rows
                market_data = AutoMarketData()
                df = market_data.daily_history(ticker, start_str, today_str)
                if not df.empty:
                    price_rows = frame_to_price_rows(ticker, df, source="vndirect")
                    if price_rows:
                        store.upsert_market_prices(price_rows)
                        current_price_val = price_rows[-1].get("close")
            except Exception:
                pass

    snapshot = valuation_snapshot_from_catalog(ticker, current_price_val)
    if not snapshot.get("ok"):
        return {
            "ok": False,
            "symbol": ticker,
            "code": snapshot.get("code", "FINANCE_DATA_INCOMPLETE"),
            "error": snapshot.get("message", "Finance data incomplete."),
            "quality_tier": "UNKNOWN",
            "financial_history": [],
            "financial_history_10y": [],
            "missing": snapshot.get("missing", []),
        }

    income = list(snapshot.get("income_statement") or [])
    balance = list(snapshot.get("balance_sheet") or [])
    cash_flow = list(snapshot.get("cash_flow") or [])
    ratios = list(snapshot.get("ratios") or [])
    profile = list(snapshot.get("profile") or [])
    prices = list(snapshot.get("prices") or [])
    fetched_at = str(snapshot.get("fetched_at") or datetime.now(timezone.utc).isoformat())

    current_price_dec = number(field(prices, "close", "close_price", reverse=True)) or (Decimal(str(current_price_val)) if current_price_val else None)
    net_income = number(field(income, "net_profit", "net_profit_after_tax", "profit_after_tax", "net_income"))
    operating_profit = number(field(income, "operating_profit", "profit_from_operation"))
    total_debt = number(field(balance, "total_debt", "debt", "borrowings"))
    short_debt = number(field(balance, "short_term_borrowings", "short_term_debt"))
    long_debt = number(field(balance, "long_term_borrowings", "long_term_debt"))
    cash = number(field(balance, "cash_and_cash_equivalents", "cash", "cash_equivalents"))
    short_investments = number(field(balance, "short_term_investments", "short_term_investment"))
    equity = number(field(balance, "equity", "owners_equity", "owner_equity"))
    depreciation = number(field(cash_flow, "depreciation", "depreciation_amortization"))
    capex = number(field(cash_flow, "capex", "purchase_of_fixed_assets", "fixed_asset_purchases"))
    operating_cash = number(field(cash_flow, "operating_cash_flow", "net_cash_from_operating_activities"))

    eps = number(field(ratios, "eps", "earning_per_share"))
    bvps = number(field(ratios, "bvps", "book_value_per_share"))
    pe = number(field(ratios, "pe", "price_to_earnings"))
    pb = number(field(ratios, "pb", "price_to_book"))
    roe = number(field(ratios, "roe", "return_on_equity"))
    dividend_yield = number(field(ratios, "dividend_yield", "cash_dividend_yield"))
    shares = number(field(ratios, "outstanding_share", "outstanding_shares", "shares_outstanding"))

    BANK_TICKERS = {"ACB", "VCB", "BID", "CTG", "MBB", "TCB", "VPB", "STB", "HDB", "TPB", "VIB", "MSB", "LPB", "EIB", "OCB", "SSB", "BAB", "NAB", "BVB", "ABB", "PGB", "SGB"}
    sector = field(profile, "industry", "industry_name", "sector", "icb_name3", "icb_name2")
    company_type = str(field(profile, "company_type", "type", "industry") or "")
    sec_str = f"{sector or ''} {company_type}".lower()
    is_bank = ticker in BANK_TICKERS or any(token in sec_str for token in ("bank", "ngân hàng", "ngn hng", "ngan hang"))
    entity_type = EntityType.BANK if is_bank else EntityType.NORMAL_ENTERPRISE

    if current_price_dec is None or current_price_dec <= 0 or net_income is None or shares is None or shares <= 0:
        return {
            "ok": False,
            "symbol": ticker,
            "code": "VALUATION_DATA_INCOMPLETE",
            "error": f"BCTC mới nhất của {ticker} chưa đủ lợi nhuận và số cổ phiếu lưu hành để định giá.",
            "quality_tier": "UNKNOWN",
            "financial_history": [],
            "financial_history_10y": [],
        }

    fiscal_year_raw = number(snapshot.get("fiscal_year"))
    fiscal_quarter_raw = number(snapshot.get("fiscal_quarter"))
    if fiscal_year_raw is None or not 2000 <= fiscal_year_raw <= 2200:
        return {
            "ok": False,
            "symbol": ticker,
            "code": "VALUATION_DATA_INCOMPLETE",
            "error": "Finance DB thiếu kỳ báo cáo hợp lệ.",
            "quality_tier": "UNKNOWN",
            "financial_history": [],
            "financial_history_10y": [],
        }
    fiscal_year = int(fiscal_year_raw)
    fiscal_quarter = int(fiscal_quarter_raw) if fiscal_quarter_raw and 1 <= fiscal_quarter_raw <= 4 else None
    period_end = str(snapshot.get("period_end") or f"{fiscal_year}-12-31")

    facts: list[CanonicalFact] = []

    def add_fact(code: str, statement_type: StatementType, value: Decimal | None, period_type: PeriodType) -> None:
        if value is None:
            return
        fact_val = value if code == "IS.SHARES.OUTSTANDING" or abs(value) >= Decimal("1000000000") else value * Decimal("1000000000")
        fact_id = f"db-{ticker.lower()}-{code.lower().replace('.', '-')}-{fetched_at[:19]}"
        facts.append(CanonicalFact(
            canonical_fact_id=fact_id,
            identity=FactIdentityKey(
                security_id=f"sec-{ticker.lower()}",
                statement_type=statement_type,
                period_end=period_end,
                period_type=period_type,
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code=code,
                currency="VND",
            ),
            value=fact_val,
            quality_status=QualityStatus.SINGLE_SOURCE,
            decision_id=f"db-{ticker.lower()}-{fetched_at[:19]}",
            winning_candidate_id=f"finance-db-{ticker.lower()}-{code.lower()}",
            candidate_ids=[],
            observed_at=fetched_at,
            valid_from=fetched_at,
            reason=f"Validated Finance DB fact from {snapshot.get('provider')}",
        ))

    add_fact("IS.PROFIT.NET", StatementType.INCOME_STATEMENT, net_income, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)
    add_fact("IS.PROFIT.OPERATING", StatementType.INCOME_STATEMENT, operating_profit, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)
    add_fact("BS.DEBT.TOTAL", StatementType.BALANCE_SHEET, total_debt, PeriodType.INSTANT)
    add_fact("BS.LIABILITIES.SHORT_TERM_BORROWINGS", StatementType.BALANCE_SHEET, short_debt, PeriodType.INSTANT)
    add_fact("BS.LIABILITIES.LONG_TERM_BORROWINGS", StatementType.BALANCE_SHEET, long_debt, PeriodType.INSTANT)
    add_fact("BS.ASSETS.CASH_AND_EQUIVALENTS", StatementType.BALANCE_SHEET, cash, PeriodType.INSTANT)
    add_fact("BS.ASSETS.SHORT_TERM_INVESTMENTS", StatementType.BALANCE_SHEET, short_investments, PeriodType.INSTANT)
    add_fact("BS.EQUITY.TOTAL", StatementType.BALANCE_SHEET, equity, PeriodType.INSTANT)
    add_fact("CF.OPERATING.DEPRECIATION", StatementType.CASH_FLOW, depreciation, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)
    add_fact("CF.CAPEX", StatementType.CASH_FLOW, capex, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)
    add_fact("CF.OPERATING.NET", StatementType.CASH_FLOW, operating_cash, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)
    add_fact("IS.SHARES.OUTSTANDING", StatementType.INCOME_STATEMENT, shares, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)

    scaled_net_income = net_income * Decimal("1000000000") if net_income is not None and abs(net_income) < Decimal("1000000000") else net_income
    scaled_equity = equity * Decimal("1000000000") if equity is not None and abs(equity) < Decimal("1000000000") else equity

    if bvps is None and scaled_equity is not None and shares > 0:
        bvps = scaled_equity / shares
    if eps is None and scaled_net_income is not None and shares > 0:
        eps = scaled_net_income / shares
    if pe is None and current_price_dec is not None and eps is not None and eps > 0:
        pe = current_price_dec / eps
    if pb is None and current_price_dec is not None and bvps is not None and bvps > 0:
        pb = current_price_dec / bvps
    if roe is None and scaled_net_income is not None and scaled_equity is not None and scaled_equity > 0:
        roe = (scaled_net_income / scaled_equity) * Decimal("100")

    def percent(value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return value * Decimal("100") if abs(value) <= Decimal("1") else value

    financial_history: list[dict[str, Any]] = []
    with _schema_connection(FINANCE_SCHEMA) as db:
        hist_rows = db.execute(
            """SELECT fiscal_year, line_item_code, value, provider
               FROM canonical_facts
               WHERE symbol = ? AND period_type = 'FY' AND fiscal_quarter IS NULL
               ORDER BY fiscal_year ASC, CASE WHEN lower(provider) = 'ssi' THEN 1 WHEN lower(provider) = 'tcbs' THEN 2 ELSE 3 END ASC""",
            (ticker,),
        ).fetchall()
        by_year: dict[int, dict[str, Decimal]] = {}
        for r in hist_rows:
            y_int = int(r["fiscal_year"])
            code_str = str(r["line_item_code"])
            val_dec = Decimal(str(r["value"]))
            
            # Provider precedence: ssi first, then tcbs. Only set if code_str not yet present for that year.
            if code_str not in by_year.setdefault(y_int, {}):
                by_year[y_int][code_str] = val_dec

            if y_int != fiscal_year:
                st_type = StatementType.INCOME_STATEMENT if code_str.startswith("IS.") else (StatementType.BALANCE_SHEET if code_str.startswith("BS.") else StatementType.CASH_FLOW)
                fact_val = val_dec if code_str == "IS.SHARES.OUTSTANDING" or abs(val_dec) >= Decimal("1000000000") else val_dec * Decimal("1000000000")
                facts.append(CanonicalFact(
                    canonical_fact_id=f"db-{ticker.lower()}-{code_str.lower().replace('.', '-')}-{y_int}",
                    identity=FactIdentityKey(
                        security_id=f"sec-{ticker.lower()}",
                        statement_type=st_type,
                        period_end=f"{y_int}-12-31",
                        period_type=PeriodType.FY,
                        fiscal_year=y_int,
                        fiscal_quarter=None,
                        consolidation_scope=ConsolidationScope.CONSOLIDATED,
                        line_item_code=code_str,
                        currency="VND",
                    ),
                    value=fact_val,
                    quality_status=QualityStatus.SINGLE_SOURCE,
                    decision_id=f"db-{ticker.lower()}-{y_int}",
                    winning_candidate_id=f"finance-db-{ticker.lower()}-{code_str.lower()}-{y_int}",
                    candidate_ids=[],
                    observed_at=fetched_at,
                    valid_from=fetched_at,
                    reason=f"Validated Finance DB historical fact {y_int}",
                ))

        for y in sorted(by_year.keys()):
            items = by_year[y]
            np_val = items.get("IS.PROFIT.NET")
            eq_val = items.get("BS.EQUITY.TOTAL")
            cfo_val = items.get("CF.OPERATING.NET")
            capex_val = items.get("CF.CAPEX")
            shares_val = items.get("IS.SHARES.OUTSTANDING")
            debt_val = items.get("BS.DEBT.TOTAL")
            cash_val = items.get("BS.ASSETS.CASH_AND_EQUIVALENTS")
            rev_val = items.get("IS.REVENUE.TOTAL") or items.get("IS.REVENUE.NET")
            rec_val = items.get("BS.ASSETS.RECEIVABLES_SHORT_TERM") or items.get("BS.ASSETS.SHORT_TERM")
            inv_val = items.get("BS.ASSETS.INVENTORY")

            np_scaled = float(np_val * Decimal("1000000000")) if np_val is not None else None
            eq_scaled = float(eq_val * Decimal("1000000000")) if eq_val is not None else None
            cfo_scaled = float(cfo_val * Decimal("1000000000")) if cfo_val is not None else None
            capex_scaled = float(abs(capex_val) * Decimal("1000000000")) if capex_val is not None else None
            fcf_scaled = (cfo_scaled - capex_scaled) if (cfo_scaled is not None and capex_scaled is not None) else None
            debt_scaled = float(debt_val * Decimal("1000000000")) if debt_val is not None else None
            cash_scaled = float(cash_val * Decimal("1000000000")) if cash_val is not None else None
            rec_scaled = float(rec_val * Decimal("1000000000")) if rec_val is not None else None
            inv_scaled = float(inv_val * Decimal("1000000000")) if inv_val is not None else None
            shares_count = float(shares_val) if shares_val is not None else None

            roe_hist = round((float(np_val) / float(eq_val) * 100), 1) if (np_val is not None and eq_val and eq_val > Decimal("0")) else None
            conversion_hist = round((cfo_scaled / np_scaled * 100), 1) if (cfo_scaled is not None and np_scaled and np_scaled > 0) else None

            financial_history.append({
                "fiscal_year": y,
                "revenue": float(rev_val * Decimal("1000000000")) if rev_val is not None else None,
                "net_profit": np_scaled,
                "equity": eq_scaled,
                "roe": roe_hist,
                "operating_cash_flow": cfo_scaled,
                "free_cash_flow": fcf_scaled,
                "cash_conversion_ratio": conversion_hist,
                "shares_outstanding": shares_count,
                "total_debt": debt_scaled,
                "cash_and_equivalents": cash_scaled,
                "receivables": rec_scaled,
                "inventory": inv_scaled,
            })

    np_series = [(h["fiscal_year"], h["net_profit"]) for h in financial_history if h.get("net_profit") is not None]
    cagr_5y = None
    if len(np_series) >= 5 and np_series[-5][1] and np_series[-1][1] and np_series[-5][1] > 0 and np_series[-1][1] > 0:
        y_start, v_start = np_series[-5]
        y_end, v_end = np_series[-1]
        span = y_end - y_start
        if span > 0:
            cagr_5y = round(((v_end / v_start) ** (1.0 / span) - 1.0) * 100, 1)

    recent_conversions = [h["cash_conversion_ratio"] for h in financial_history[-5:] if h.get("cash_conversion_ratio") is not None]
    avg_cash_conversion_5y = round(sum(recent_conversions) / len(recent_conversions), 1) if recent_conversions else None
    latest_conversion = financial_history[-1].get("cash_conversion_ratio") if financial_history else None

    recent_roes = [h["roe"] for h in financial_history[-5:] if h.get("roe") is not None]
    avg_roe_5y = round(sum(recent_roes) / len(recent_roes), 1) if recent_roes else None

    is_securities = any(token in f"{sector or ''} {company_type}".lower() for token in ("chứng khoán", "securities", "broker", "môi giới"))
    is_insurance = any(token in f"{sector or ''} {company_type}".lower() for token in ("bảo hiểm", "insurance"))
    is_financial = is_bank or is_securities or is_insurance

    if is_financial:
        earnings_quality = {
            "latest_cash_conversion": None,
            "avg_cash_conversion_5y": None,
            "avg_roe_5y": avg_roe_5y,
            "status": "EXCELLENT" if (avg_roe_5y and avg_roe_5y >= 15) else ("GOOD" if (avg_roe_5y and avg_roe_5y >= 12) else "WATCH"),
            "diagnosis": "Chất lượng thu nhập tổ chức tài chính dựa trên tỷ suất Sinh lời trên Vốn.",
        }
    else:
        status = "WATCH"
        diag = "Lợi nhuận có độ trễ hoặc thâm dụng vốn lưu động."
        if avg_cash_conversion_5y is not None:
            if avg_cash_conversion_5y > 200.0:
                status = "GOOD"
                diag = f"Tỷ lệ CFO/LNST ({avg_cash_conversion_5y:.1f}%) rất cao do mẫu số lợi nhuận thấp."
            elif 80.0 <= avg_cash_conversion_5y <= 140.0:
                status = "EXCELLENT"
                diag = f"Dòng tiền kinh doanh dồi dào, lợi nhuận chuyển hóa thành tiền mặt cao ({avg_cash_conversion_5y:.1f}%)."
            elif (70.0 <= avg_cash_conversion_5y < 80.0) or (140.0 < avg_cash_conversion_5y <= 200.0):
                status = "GOOD"
                diag = f"Chuyển hóa dòng tiền tốt ({avg_cash_conversion_5y:.1f}%)."
            else:
                status = "WATCH"
                diag = f"Chuyển hóa dòng tiền thấp ({avg_cash_conversion_5y:.1f}%)."

        earnings_quality = {
            "latest_cash_conversion": latest_conversion,
            "avg_cash_conversion_5y": avg_cash_conversion_5y,
            "status": status,
            "diagnosis": diag,
        }

    latest_hist = financial_history[-1] if financial_history else {}
    latest_debt = latest_hist.get("total_debt") or 0
    latest_cash = latest_hist.get("cash_and_equivalents") or 0
    net_debt_calc = 0.0 if is_financial else max(0.0, float(latest_debt - latest_cash))
    latest_cfo = latest_hist.get("operating_cash_flow") or 0
    debt_payback_years = None if is_financial else (round(net_debt_calc / latest_cfo, 1) if (net_debt_calc > 0 and latest_cfo and latest_cfo > 0) else 0.0)

    ebitda_est_billion = (float(operating_profit) if operating_profit is not None else 0.0) + (float(depreciation) if depreciation is not None else 0.0)
    ebitda_est_vnd = ebitda_est_billion * 1e9 if ebitda_est_billion and ebitda_est_billion > 0 else 0.0
    net_debt_to_ebitda = None
    if not is_financial and net_debt_calc > 0 and ebitda_est_vnd > 0:
        ratio = net_debt_calc / ebitda_est_vnd
        if 0.0 <= ratio < 100.0:
            net_debt_to_ebitda = round(ratio, 2)

    fortress_status = "FORTRESS" if (is_financial or net_debt_calc == 0) else ("STRONG" if (debt_payback_years is not None and debt_payback_years < 3.0) else "MODERATE")
    fortress_diag = "Cơ cấu tài chính chuẩn mực." if is_financial else ("Pháo đài tiền mặt ròng dồi dào." if net_debt_calc == 0 else f"Khả năng hoàn trả nợ ({debt_payback_years} năm).")

    shares_series = [(h["fiscal_year"], h["shares_outstanding"]) for h in financial_history if h.get("shares_outstanding") is not None]
    share_dilution_5y = None
    dilution = None
    true_dilution_diag = "Tỷ lệ sở hữu của cổ đông hiện hữu được duy trì tốt."
    if len(shares_series) >= 5 and shares_series[-5][1] and shares_series[-1][1] and shares_series[-5][1] > 0:
        s_old = shares_series[-5][1]
        s_new = shares_series[-1][1]
        start_year = shares_series[-5][0]
        with _schema_connection(FINANCE_SCHEMA) as db:
            stock_div_rows = db.execute(
                """SELECT stock_ratio FROM dividend_canonical
                   WHERE symbol = ? AND dividend_type = 'STOCK_DIVIDEND'
                   AND effective_event_date >= ?""",
                (ticker, f"{start_year}-01-01"),
            ).fetchall()
        non_economic_events = [
            {"action_type": "STOCK_DIVIDEND", "stock_ratio": float(r["stock_ratio"])}
            for r in stock_div_rows
            if r["stock_ratio"]
        ]
        dilution = classify_share_change(
            shares_old=s_old,
            shares_new=s_new,
            non_economic_events=non_economic_events,
            economic_events=[],
        )
        share_dilution_5y = dilution["confirmed_economic_dilution_pct"]
        if dilution["classification"] == "EXCESSIVE_DILUTION":
            true_dilution_diag = f"Có phát hành thêm/ESOP gây pha loãng kinh tế ({dilution['confirmed_economic_dilution_pct']}%)."
        elif dilution["classification"] == "UNEXPLAINED_SHARE_CHANGE":
            true_dilution_diag = f"Tăng vốn cổ phần chưa giải thích ({dilution['unexplained_share_change_pct']}%)."

    cap_allocation_uncertain = bool(
        dilution and dilution["classification"] == "UNEXPLAINED_SHARE_CHANGE"
        and (dilution.get("unexplained_share_change_pct") or 0) >= 5.0
    )
    if cap_allocation_uncertain:
        cap_status = "UNCERTAIN"
    elif avg_roe_5y and avg_roe_5y >= 18 and (share_dilution_5y is None or share_dilution_5y < 5):
        cap_status = "EXCELLENT"
    elif avg_roe_5y and avg_roe_5y >= 13:
        cap_status = "GOOD"
    else:
        cap_status = "WATCH"

    latest_equity_vnd = float(latest_hist.get("equity") or 0)
    total_debt_vnd = float(latest_hist.get("total_debt") or 0)
    total_cash_vnd = float(latest_hist.get("cash_and_equivalents") or 0)
    debt_to_equity_ratio = round(total_debt_vnd / latest_equity_vnd, 2) if latest_equity_vnd > 0 else None

    value_investor_pillars = {
        "earnings_quality": earnings_quality,
        "financial_fortress": {
            "net_debt_vnd": net_debt_calc,
            "total_debt_vnd": total_debt_vnd,
            "total_cash_vnd": total_cash_vnd,
            "total_equity_vnd": latest_equity_vnd,
            "debt_to_equity_ratio": debt_to_equity_ratio,
            "debt_payback_years": debt_payback_years,
            "net_debt_to_ebitda": net_debt_to_ebitda,
            "status": fortress_status,
            "diagnosis": fortress_diag,
        },
        "capital_allocation": {
            "avg_roe_5y": avg_roe_5y,
            "share_dilution_5y_pct": share_dilution_5y,
            "economic_dilution_5y_pct": dilution["confirmed_economic_dilution_pct"] if dilution else None,
            "confirmed_economic_dilution_5y_pct": dilution["confirmed_economic_dilution_pct"] if dilution else None,
            "unexplained_share_change_5y_pct": dilution["unexplained_share_change_pct"] if dilution else None,
            "non_economic_share_change_5y_pct": dilution["non_economic_share_change_pct"] if dilution else None,
            "raw_share_change_5y_pct": dilution["raw_share_change_pct"] if dilution else None,
            "dilution_classification": dilution["classification"] if dilution else None,
            "dilution_breakdown": dilution or None,
            "status": cap_status,
            "diagnosis": true_dilution_diag,
        },
    }

    try:
        report = ValuationEngine.evaluate(
            symbol=ticker,
            facts=facts,
            current_market_price=current_price_dec,
            shares_outstanding=shares,
            diluted_shares_estimate=shares,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            entity_type=entity_type,
            fundamentals={
                "sector": sector,
                "eps": eps,
                "bvps": bvps,
                "pe": pe,
                "pb": pb,
                "roe": percent(roe),
                "dividend_yield": percent(dividend_yield),
                "source": snapshot.get("provider"),
                "as_of": fetched_at,
            },
            financial_history=financial_history,
            value_investor_pillars=value_investor_pillars,
        )
    except ValueError as err:
        return {
            "ok": False,
            "symbol": ticker,
            "code": "VALUATION_EVALUATION_ERROR",
            "error": str(err),
            "quality_tier": "UNKNOWN",
            "financial_history": financial_history,
            "financial_history_10y": financial_history,
        }

    rep_dict = asdict(report)
    curr_price_float = float(current_price_dec)

    bear_iv_val = float(report.public_bear_iv) if report.public_bear_iv is not None else None
    base_iv_val = float(report.base_iv) if report.base_iv is not None else (float(report.public_base_iv) if report.public_base_iv is not None else None)
    bull_iv_val = float(report.public_bull_iv) if report.public_bull_iv is not None else None
    if (bear_iv_val is None or bull_iv_val is None or base_iv_val is None) and report.scenarios:
        for k, v in report.scenarios.items():
            k_name = k.name if hasattr(k, "name") else str(k)
            if k_name.upper() == "BEAR" and bear_iv_val is None:
                bear_iv_val = float(v.intrinsic_value_per_share) if v and getattr(v, "intrinsic_value_per_share", None) is not None else None
            elif k_name.upper() == "BASE" and base_iv_val is None:
                base_iv_val = float(v.intrinsic_value_per_share) if v and getattr(v, "intrinsic_value_per_share", None) is not None else None
            elif k_name.upper() == "BULL" and bull_iv_val is None:
                bull_iv_val = float(v.intrinsic_value_per_share) if v and getattr(v, "intrinsic_value_per_share", None) is not None else None

    actual_mos = float(report.public_mos) if report.public_mos is not None else (float(report.margin_of_safety_pct) if report.margin_of_safety_pct is not None else None)
    if actual_mos is None and base_iv_val is not None and base_iv_val > 0 and curr_price_float > 0:
        actual_mos = float(round((Decimal(str(base_iv_val)) - Decimal(str(curr_price_float))) / Decimal(str(base_iv_val)) * Decimal("100"), 2))
    req_mos = float(report.margin_of_safety_analysis.get("required_margin_of_safety_pct") or 25.0) if isinstance(report.margin_of_safety_analysis, dict) else 25.0
    quality_score = report.quality_scorecard.get("total_score") if isinstance(report.quality_scorecard, dict) else (report.assessment.quality_score if getattr(report, "assessment", None) else 0)
    quality_tier = report.quality_scorecard.get("tier") if isinstance(report.quality_scorecard, dict) else (str(report.assessment.quality_tier.value if hasattr(report.assessment.quality_tier, "value") else report.assessment.quality_tier) if getattr(report, "assessment", None) else "UNKNOWN")
    val_conf = str(report.confidence_level.value if hasattr(report.confidence_level, "value") else report.confidence_level)
    hard_rejects = [str(r.value if hasattr(r, "value") else r) for r in (getattr(report, "hard_rejects", None) or (report.margin_of_safety_analysis.get("hard_rejects") if isinstance(report.margin_of_safety_analysis, dict) else []))]

    from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
    munger_analysis = build_munger_financial_analysis(ticker, existing_history=financial_history).to_dict()

    return {
        "ok": True,
        "symbol": ticker,
        "is_bank": is_bank,
        "archetype": "BANK" if is_bank else "ENTERPRISE",
        "current_price": curr_price_float,
        "price": curr_price_float,
        "bear_iv": bear_iv_val,
        "base_iv": base_iv_val,
        "bull_iv": bull_iv_val,
        "actual_mos_pct": actual_mos,
        "required_mos_pct": req_mos,
        "quality_score": quality_score,
        "quality_tier": quality_tier,
        "valuation_confidence": val_conf,
        "model_status": report.model_status,
        "hard_rejects": hard_rejects,
        "financial_history": financial_history,          # ONE internal domain field
        "financial_history_10y": financial_history,      # compatibility alias
        "cagr_5y_net_profit": cagr_5y,
        "value_investor_pillars": value_investor_pillars,
        "munger_analysis": munger_analysis,
        "report": {
            **rep_dict,
            "financial_history": financial_history,
            "financial_history_10y": financial_history,
            "cagr_5y_net_profit": cagr_5y,
            "value_investor_pillars": value_investor_pillars,
            "munger_analysis": munger_analysis,
        },
        "valuation_snapshot": snapshot,
        "data_freshness": {
            "cache": "DATABASE",
            "fetched_at": fetched_at,
            "provider": snapshot.get("provider"),
            "api_variant": snapshot.get("api_variant"),
            "symbol_verified": True,
        },
    }
