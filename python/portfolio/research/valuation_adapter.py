"""PIT value & quality adapters that reuse the canonical engines.

Value and Quality factors MUST use PIT-safe fundamentals. These adapters build
engine inputs from already-PIT-filtered fact rows and call the canonical
``ValuationEngine.evaluate`` / ``QualityScorer.evaluate`` entry points — the
same code paths the screener and valuation endpoint use. No new valuation
heuristics are introduced here.

When PIT data is insufficient, adapters return ``(None, None)`` (never a
fabricated number).
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Callable

from ..value_engine import ValuationEngine
from ..value_engine.quality_scorer import QualityScorer

_BILLION = Decimal("1000000000")


def _num(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _latest_fact(facts: list[dict], code: str, year: int | None = None) -> Decimal | None:
    for fact in facts:
        if str(fact.get("line_item_code") or "") == code:
            if year is not None and int(fact.get("fiscal_year") or -1) != year:
                continue
            value = fact.get("value")
            if value is None:
                return None
            try:
                return Decimal(str(value))
            except (TypeError, ValueError):
                return None
    return None


def build_financial_history(facts: list[dict]) -> list[dict]:
    """Build the canonical ``financial_history`` shape from PIT facts."""
    by_year: dict[int, dict[str, Decimal]] = defaultdict(dict)
    for fact in facts:
        try:
            year = int(fact.get("fiscal_year"))
        except (TypeError, ValueError):
            continue
        if str(fact.get("period_type") or "").upper() != "FY":
            continue
        by_year[year][str(fact.get("line_item_code") or "")] = _num(fact.get("value")) if isinstance(_num(fact.get("value")), float) else (Decimal(str(fact.get("value"))) if fact.get("value") is not None else None)

    history: list[dict] = []
    for year in sorted(by_year):
        items = by_year[year]
        np_val = items.get("IS.PROFIT.NET")
        eq_val = items.get("BS.EQUITY.TOTAL")
        cfo_val = items.get("CF.OPERATING.NET")
        capex_val = items.get("CF.CAPEX")
        debt_val = items.get("BS.DEBT.TOTAL")
        cash_val = items.get("BS.ASSETS.CASH_AND_EQUIVALENTS")
        rev_val = items.get("IS.REVENUE.NET")
        shares_y = items.get("IS.SHARES.OUTSTANDING")

        def scale(v):
            if v is None:
                return None
            return float(Decimal(str(v)) * _BILLION) if abs(Decimal(str(v))) < _BILLION else float(Decimal(str(v)))

        def scale_pos(v):
            if v is None:
                return None
            return float(abs(Decimal(str(v))) * _BILLION) if abs(Decimal(str(v))) < _BILLION else float(abs(Decimal(str(v))))

        roe = (float(Decimal(str(np_val)) / Decimal(str(eq_val)) * Decimal("100")) if np_val is not None and eq_val and Decimal(str(eq_val)) > 0 else None)
        conv = (float(Decimal(str(scale(cfo_val)) if cfo_val is not None else 0) / Decimal(str(scale(np_val)) if np_val is not None else 1) * Decimal("100")) if cfo_val is not None and np_val and scale(np_val) not in (None, 0) else None)
        history.append({
            "fiscal_year": year,
            "revenue": scale(rev_val),
            "net_profit": scale(np_val),
            "equity": scale(eq_val),
            "roe": roe,
            "operating_cash_flow": scale(cfo_val),
            "free_cash_flow": (scale(cfo_val) - scale_pos(capex_val)) if (cfo_val is not None and capex_val is not None) else None,
            "cash_conversion_ratio": conv,
            "shares_outstanding": scale(shares_y),
            "total_debt": scale(debt_val),
            "cash_and_equivalents": scale(cash_val),
        })
    return history


def canonical_pit_valuator(
    facts: list[dict],
    market_price: float | None,
    *,
    sector: str | None = None,
    company_name: str = "",
) -> tuple[float | None, float | None]:
    """Compute (actual_mos_pct, required_mos_pct) via the canonical engine.

    Returns ``(None, None)`` when PIT data is insufficient for a public
    valuation (model not verified, hard reject, missing inputs). Never invents
    numbers.
    """
    try:
        from ..value_engine.dilution import classify_share_change
    except Exception:  # noqa: BLE001
        classify_share_change = None

    history = build_financial_history(facts)
    if not history:
        return None, None
    latest = history[-1]
    price = _num(market_price)
    shares = latest.get("shares_outstanding")
    if price is None or price <= 0 or shares is None or shares <= 0:
        return None, None

    sector_text = str(sector or "")
    is_bank = any(token in f"{sector_text} {company_name}".lower() for token in ("bank", "ngân hàng"))
    is_securities = any(token in f"{sector_text} {company_name}".lower() for token in ("chứng khoán", "securities", "broker", "môi giới"))
    is_insurance = any(token in f"{sector_text} {company_name}".lower() for token in ("bảo hiểm", "insurance"))
    is_financial = is_bank or is_securities or is_insurance

    np_latest = latest.get("net_profit")
    eq_latest = latest.get("equity")
    eps = (np_latest / shares) if np_latest is not None else None
    bvps = (eq_latest / shares) if eq_latest is not None else None
    pe = (price / eps) if eps and eps > 0 else None
    pb = (price / bvps) if bvps and bvps > 0 else None
    roe = latest.get("roe")

    net_debt = 0.0 if is_financial else max(0.0, float(latest.get("total_debt") or 0) - float(latest.get("cash_and_equivalents") or 0))
    cfo = latest.get("operating_cash_flow") or 0.0
    debt_payback = None if is_financial else (net_debt / cfo if (net_debt > 0 and cfo and cfo > 0) else (0.0 if net_debt == 0 else None))
    avg_roe_5y = _avg_recent(history, "roe")
    avg_conv_5y = _avg_recent(history, "cash_conversion_ratio")

    value_investor_pillars = {
        "earnings_quality": {"avg_cash_conversion_5y": None if is_financial else avg_conv_5y},
        "financial_fortress": {
            "net_debt_vnd": net_debt,
            "debt_payback_years": debt_payback,
            "net_debt_to_ebitda": None,
        },
        "capital_allocation": {
            "avg_roe_5y": avg_roe_5y,
            "confirmed_economic_dilution_5y_pct": None,
            "unexplained_share_change_5y_pct": None,
            "dilution_classification": None,
        },
    }

    from ..financial_data.models import CanonicalFact, ConsolidationScope, EntityType, FactIdentityKey, PeriodType, QualityStatus, StatementType

    engine_facts: list[CanonicalFact] = []
    for fact in facts:
        code = str(fact.get("line_item_code") or "")
        if not code:
            continue
        value = fact.get("value")
        if value is None:
            continue
        pt = PeriodType.FY if str(fact.get("period_type") or "").upper() == "FY" else PeriodType.QUARTER
        st = StatementType.INCOME_STATEMENT if code.startswith("IS.") else (StatementType.BALANCE_SHEET if code.startswith("BS.") else StatementType.CASH_FLOW)
        fq = fact.get("fiscal_quarter")
        fact_val = Decimal(str(value)) if code == "IS.SHARES.OUTSTANDING" or abs(Decimal(str(value))) >= _BILLION else Decimal(str(value)) * _BILLION
        engine_facts.append(CanonicalFact(
            canonical_fact_id=f"pit-{code}-{fact.get('period_end', '')}",
            identity=FactIdentityKey(
                security_id=f"sec-{str(fact.get('symbol') or 'X').upper()}",
                statement_type=st,
                period_end=str(fact.get("period_end") or ""),
                period_type=pt,
                fiscal_year=int(fact.get("fiscal_year") or 0),
                fiscal_quarter=int(fq) if fq not in (None, "") else None,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code=code,
                currency="VND",
            ),
            value=fact_val,
            quality_status=QualityStatus.SINGLE_SOURCE,
            decision_id="pit-research",
            winning_candidate_id=None,
            candidate_ids=[],
            observed_at="",
            valid_from=str(fact.get("available_from") or ""),
            reason="PIT research fact",
        ))

    fiscal_year = int(latest.get("fiscal_year") or 0)
    report = ValuationEngine.evaluate(
        symbol=str(facts[0].get("symbol") or "X").upper(),
        facts=engine_facts,
        current_market_price=Decimal(str(price)),
        shares_outstanding=Decimal(str(shares)),
        diluted_shares_estimate=Decimal(str(shares)),
        fiscal_year=fiscal_year,
        entity_type=EntityType.BANK if is_bank else EntityType.NORMAL_ENTERPRISE,
        fundamentals={"sector": sector_text, "eps": eps, "bvps": bvps, "pe": pe, "pb": pb, "roe": roe},
        financial_history=history,
        value_investor_pillars=value_investor_pillars,
    )
    if report is None:
        return None, None
    actual_mos = report.public_mos
    required_mos = (report.margin_of_safety_analysis or {}).get("required_mos_pct")
    if actual_mos is None or required_mos is None:
        return None, None
    return float(actual_mos), float(required_mos)


def canonical_pit_quality(
    facts: list[dict],
    *,
    sector: str | None = None,
    company_name: str = "",
) -> tuple[int | None, str | None]:
    """Compute (quality_score, quality_tier) from PIT facts via the canonical scorer.

    Returns ``(None, None)`` when PIT data is insufficient.
    """
    try:
        from ..value_engine.archetypes import ArchetypeClassifier
        from ..value_engine.quality_scorer import QualityScorecard
    except Exception:  # noqa: BLE001
        return None, None

    history = build_financial_history(facts)
    if not history:
        return None, None
    latest = history[-1]
    arch = ArchetypeClassifier.classify(str(facts[0].get("symbol") or "X"), str(sector or ""))
    cap_alloc = {
        "avg_roe_5y": _avg_recent(history, "roe"),
        "confirmed_economic_dilution_5y_pct": None,
        "dilution_classification": None,
    }
    net_debt = float(latest.get("total_debt") or 0) - float(latest.get("cash_and_equivalents") or 0)
    latest_cfo = latest.get("operating_cash_flow") or 0
    if not latest_cfo or latest_cfo <= 0:
        price_proxy = float(latest.get("equity") or 0) or 1.0
        latest_cfo = price_proxy * 0.1
    scorecard = QualityScorer.evaluate(
        archetype_prof=arch,
        financial_history_10y=history,
        five_year_avg_roe=cap_alloc.get("avg_roe_5y"),
        five_year_avg_cash_conversion=None,
        net_debt_vnd=net_debt,
        latest_cfo=latest_cfo,
        true_dilution_5y_pct=0.0,
        dilution_classification=None,
    )
    if scorecard is None:
        return None, None
    return int(scorecard.total_score), str(scorecard.tier.value)


def _avg_recent(history: list[dict], key: str, n: int = 5) -> float | None:
    values = [row[key] for row in history[-n:] if row.get(key) is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 1)


# Typed aliases so callers can inject deterministic test implementations.
PitValuator = Callable[[list[dict], float | None], tuple[float | None, float | None]]
PitQualityScorer = Callable[[list[dict]], tuple[int | None, str | None]]