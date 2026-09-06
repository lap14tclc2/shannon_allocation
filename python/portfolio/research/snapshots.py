"""T11 — Reproducible factor snapshot builder.

A snapshot captures one symbol's factor values on one snapshot_date using ONLY
information available as of that date:

- fundamentals filtered by ``available_from <= snapshot_date`` (PIT);
- OHLCV sliced to ``<= snapshot_date`` (no future candles);
- value/quality via the canonical engines on PIT facts.

Reproducibility: every snapshot records ``source_hash`` (SHA-256 over the exact
input facts + price tail used). Same inputs -> same hash -> same snapshot.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import pandas as pd

from .factors import price_factors_from_frame, value_factor
from .pit import DEFAULT_LAGS, get_facts_as_of
from .valuation_adapter import PitQualityScorer, PitValuator

FACTOR_VERSION = "1.0.0"


@dataclass(frozen=True)
class SnapshotDeps:
    """Injected providers so the builder is testable without a live DB."""

    fact_provider: Callable[[str, str], list[dict]]
    price_provider: Callable[[str, str], pd.DataFrame]
    pit_valuator: PitValuator
    pit_quality: PitQualityScorer
    lags: dict[str, int] | None = None

    @classmethod
    def production(cls, market=None, sector_fn=None) -> "SnapshotDeps":
        """Production defaults backed by canonical facts + stored market prices.

        ``sector_fn`` maps a symbol to (sector, company_name) for the canonical
        engine; defaults to reading the finance securities table.
        """
        from ..finance_catalog import FINANCE_SCHEMA, _schema_connection
        from ..postgres import _ensure_schema
        from .pit import facts_from_canonical, get_facts_as_of
        from .valuation_adapter import canonical_pit_quality, canonical_pit_valuator

        _ensure_schema(FINANCE_SCHEMA)

        def fact_provider(symbol: str, as_of: str) -> list[dict]:
            with _schema_connection(FINANCE_SCHEMA) as db:
                raw = facts_from_canonical(symbol, connection=db)
            return get_facts_as_of(raw, as_of, lags=DEFAULT_LAGS)

        def price_provider(symbol: str, as_of: str) -> pd.DataFrame:
            # Production prices come from the finance-schema market_prices table
            # (persisted by the screener). Synthetic providers are used in tests.
            with _schema_connection(FINANCE_SCHEMA) as db:
                rows = db.execute(
                    "SELECT trading_date, close, volume FROM market_prices "
                    "WHERE symbol = ? AND trading_date <= ? ORDER BY trading_date",
                    (str(symbol).upper(), as_of),
                ).fetchall()
            if not rows:
                return pd.DataFrame(columns=["close"])
            frame = pd.DataFrame([dict(r) for r in rows])
            frame["trading_date"] = pd.to_datetime(frame["trading_date"])
            return frame.set_index("trading_date").sort_index()

        def meta(symbol: str) -> tuple[str, str]:
            if sector_fn:
                return sector_fn(symbol)
            try:
                with _schema_connection(FINANCE_SCHEMA) as db:
                    row = db.execute(
                        "SELECT industry, company_name FROM securities WHERE symbol = ?",
                        (str(symbol).upper(),),
                    ).fetchone()
                if row:
                    return str(row["industry"] or ""), str(row["company_name"] or "")
            except Exception:  # noqa: BLE001
                pass
            return "", ""

        def valuator(facts, market_price):
            if market_price is None:
                return None, None
            sector, name = meta(str(facts[0].get("symbol") or "X").upper()) if facts else ("", "")
            return canonical_pit_valuator(facts, market_price, sector=sector, company_name=name)

        def quality(facts):
            if not facts:
                return None, None
            sector, name = meta(str(facts[0].get("symbol") or "X").upper())
            return canonical_pit_quality(facts, sector=sector, company_name=name)

        return cls(
            fact_provider=fact_provider,
            price_provider=price_provider,
            pit_valuator=valuator,
            pit_quality=quality,
        )


def _source_hash(facts: list[dict], price_tail: pd.DataFrame) -> str:
    payload = {
        "facts": [
            {
                "code": f.get("line_item_code"),
                "period_end": f.get("period_end"),
                "period_type": f.get("period_type"),
                "fiscal_year": f.get("fiscal_year"),
                "fiscal_quarter": f.get("fiscal_quarter"),
                "value": str(f.get("value")),
                "available_from": f.get("available_from"),
            }
            for f in facts
        ],
        "price_tail": [
            {"date": str(idx.date()), "close": float(row["close"])}
            for idx, row in price_tail.tail(300).iterrows()
            if pd.notna(row.get("close"))
        ],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _market_price(frame: pd.DataFrame) -> float | None:
    if frame is None or frame.empty or "close" not in frame.columns:
        return None
    close = pd.to_numeric(frame["close"], errors="coerce").dropna()
    if close.empty:
        return None
    return float(close.iloc[-1])


def build_snapshot_row(
    deps: SnapshotDeps,
    *,
    symbol: str,
    snapshot_date: str,
    factor_version: str = FACTOR_VERSION,
    universe_status: str = "CANDIDATE",
) -> dict:
    """Build one deterministic factor-snapshot row for ``(symbol, snapshot_date)``.

    Facts are PIT-filtered to ``available_from <= snapshot_date``; prices are
    sliced to ``<= snapshot_date``. Missing factor values stay None (never 0).
    """
    symbol = str(symbol).upper()
    facts = get_facts_as_of(
        deps.fact_provider(symbol, snapshot_date),
        snapshot_date,
        lags=deps.lags,
    )
    prices = deps.price_provider(symbol, snapshot_date)
    if prices is not None and not prices.empty:
        prices = prices[prices.index <= pd.Timestamp(snapshot_date)]

    price = _market_price(prices)
    actual_mos, required_mos = deps.pit_valuator(facts, price)
    quality_score, quality_tier = deps.pit_quality(facts)

    price_factors = price_factors_from_frame(prices) if (prices is not None and not prices.empty) else {}

    row = {
        "snapshot_date": snapshot_date,
        "symbol": symbol,
        "universe_status": universe_status,
        "value_factor": value_factor(actual_mos, required_mos),
        "quality_factor": quality_score if quality_score is not None else None,
        "quality_tier": quality_tier,
        "momentum_3m": price_factors.get("momentum_3m"),
        "momentum_6m": price_factors.get("momentum_6m"),
        "momentum_12m": price_factors.get("momentum_12m"),
        "momentum_12_1": price_factors.get("momentum_12_1"),
        "reversal_1m": price_factors.get("reversal_1m"),
        "liquidity": price_factors.get("liquidity"),
        "source_hash": _source_hash(facts, prices if prices is not None else pd.DataFrame()),
        "factor_version": factor_version,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return row


def build_snapshots(
    deps: SnapshotDeps,
    *,
    symbols: list[str],
    snapshot_dates: list[str],
    factor_version: str = FACTOR_VERSION,
    universe_status_fn: Callable[[str, str], str] | None = None,
) -> list[dict]:
    """Build snapshots for all (symbol, snapshot_date) pairs deterministically."""
    rows: list[dict] = []
    for date_value in snapshot_dates:
        for symbol in symbols:
            status = universe_status_fn(symbol, date_value) if universe_status_fn else "CANDIDATE"
            rows.append(build_snapshot_row(
                deps, symbol=symbol, snapshot_date=date_value,
                factor_version=factor_version, universe_status=status,
            ))
    return rows