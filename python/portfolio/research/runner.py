"""End-to-end factor research runner on real QPort data.

Pipeline: universe -> fetch real OHLCV + VNINDEX -> PIT factor snapshots ->
forward benchmark-relative outcomes -> IC/quantile/walk-forward/sealed-OOS
validation -> deterministic report.

Real-data only. No synthetic data is used for research evidence.
"""
from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Callable

import pandas as pd

from ..finance_catalog import FINANCE_SCHEMA, _schema_connection
from .factors import price_factors_from_frame
from .outcomes import build_outcomes
from .pit import DEFAULT_LAGS, facts_from_canonical, get_facts_as_of
from .snapshots import SnapshotDeps, build_snapshots
from .store import ResearchStore
from .validation import ResearchCostModel, validate_factor
from .valuation_adapter import canonical_pit_quality, canonical_pit_valuator
from .walk_forward import ResearchConfig

FACTORS: dict[str, str] = {
    "value_factor": "VALUE_SAFETY",
    "quality_factor": "QUALITY",
    "momentum_3m": "MOMENTUM_3M",
    "momentum_6m": "MOMENTUM_6M",
    "momentum_12m": "MOMENTUM_12M",
    "momentum_12_1": "MOMENTUM_12_1",
    "reversal_1m": "REVERSAL_1M",
}
HORIZONS = (21, 63, 126, 252)
PRICE_START = "2016-01-01"
_TICKER_RE = re.compile(r"^[A-Z]{3,4}$")
_VALID_EXCHANGES = {"HOSE", "HNX", "UPCOM"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_universe(
    *,
    top_n: int = 150,
    min_recent_bars: int = 20,
    connection=None,
) -> tuple[list[str], dict]:
    """Conservative liquid VN common-equity universe from existing infra.

    Filters: HOSE/HNX/UPCOM, 3-4 letter ticker (excludes warrants/derivatives),
    >= ``min_recent_bars`` stored bars (the finance DB stores ~2 months of
    recent prices), ranked by average daily traded value over those stored bars.
    """
    def q(sql, params=()):
        if connection is not None:
            return connection.execute(sql, params).fetchall()
        with _schema_connection(FINANCE_SCHEMA) as db:
            return db.execute(sql, params).fetchall()

    rows = q(
        "SELECT s.symbol, s.exchange, s.company_name, "
        "       COUNT(m.trading_date) AS bars, "
        "       AVG(m.close * COALESCE(m.volume, 0)) AS avg_turnover_20d "
        "FROM securities s "
        "LEFT JOIN market_prices m ON m.symbol = s.symbol "
        "WHERE s.is_active = 1 "
        "GROUP BY s.symbol, s.exchange, s.company_name "
        "ORDER BY avg_turnover_20d DESC"
    )
    universe: list[str] = []
    stats = {"total_candidates": len(rows), "excluded_reason": {}, "by_exchange": {}}
    for row in rows:
        symbol = str(row["symbol"] or "").upper()
        exchange = str(row["exchange"] or "").upper()
        bars = int(row["bars"] or 0)
        if exchange not in _VALID_EXCHANGES:
            stats["excluded_reason"]["exchange"] = stats["excluded_reason"].get("exchange", 0) + 1
            continue
        if not _TICKER_RE.match(symbol):
            stats["excluded_reason"]["ticker_pattern"] = stats["excluded_reason"].get("ticker_pattern", 0) + 1
            continue
        if bars < min_recent_bars:
            stats["excluded_reason"]["insufficient_recent_bars"] = stats["excluded_reason"].get("insufficient_recent_bars", 0) + 1
            continue
        stats["by_exchange"][exchange] = stats["by_exchange"].get(exchange, 0) + 1
        universe.append(symbol)
        if len(universe) >= top_n:
            break
    return universe, stats


def fetch_and_persist_prices(
    store: ResearchStore,
    symbols: list[str],
    *,
    start: str = PRICE_START,
    end: str | None = None,
    provider=None,
    delay: float = 0.05,
) -> dict:
    """Fetch real historical OHLCV (VNDIRECT) and VNINDEX, persist to research store."""
    from ..market_data import VndirectProvider, frame_to_price_rows
    from .benchmark import VNIndexBenchmark

    provider = provider or VndirectProvider()
    end = end or date.today().isoformat()
    benchmark = VNIndexBenchmark(market=provider)
    store.create_schema()

    bench_df = benchmark.history(start, end)
    bench_rows = [{
        "benchmark": "VNINDEX", "trading_date": str(idx.date()),
        "close": float(row["close"]), "source": "vndirect",
        "fetched_at": _now(), "data_quality": "VALID",
    } for idx, row in bench_df.iterrows()]
    store.write_benchmark_prices(bench_rows)

    fetched: list[str] = []
    failed: dict[str, str] = {}
    for index, symbol in enumerate(symbols):
        try:
            df = provider.daily_history(symbol, start, end)
            if df.empty:
                raise RuntimeError("empty history")
            rows = frame_to_price_rows(symbol, df, source="vndirect")
            store.write_stock_prices(symbol, rows)
            fetched.append(symbol)
        except Exception as exc:  # noqa: BLE001
            failed[symbol] = str(exc)[:120]
        if delay and index % 20 == 19:
            time.sleep(delay)
        if index and index % 50 == 0:
            print(f"[research] fetched {index}/{len(symbols)}", flush=True)

    return {
        "benchmark_symbols": ["VNINDEX"],
        "benchmark_rows": len(bench_rows),
        "benchmark_span": {"start": start, "end": end},
        "universe_requested": len(symbols),
        "fetched": len(fetched),
        "failed": failed,
        "fetched_symbols": fetched,
    }


def research_deps(
    store: ResearchStore,
    *,
    lags: dict[str, int] | None = None,
    facts_cache: dict | None = None,
    price_cache: dict | None = None,
) -> tuple[SnapshotDeps, dict]:
    """Build snapshot deps backed by the finance DB + research store (cached)."""
    from ..finance_catalog import FINANCE_SCHEMA

    lags = lags or DEFAULT_LAGS
    facts_cache = facts_cache if facts_cache is not None else {}
    price_cache = price_cache if price_cache is not None else {}
    sector_cache: dict[str, tuple[str, str]] = {}

    def facts_for(symbol: str) -> list[dict]:
        if symbol not in facts_cache:
            with _schema_connection(FINANCE_SCHEMA) as db:
                facts_cache[symbol] = facts_from_canonical(symbol, connection=db)
        return facts_cache[symbol]

    def sector_for(symbol: str) -> tuple[str, str]:
        if symbol not in sector_cache:
            try:
                with _schema_connection(FINANCE_SCHEMA) as db:
                    row = db.execute(
                        "SELECT industry, company_name FROM securities WHERE symbol = ?",
                        (symbol,),
                    ).fetchone()
                sector_cache[symbol] = (
                    str(row["industry"] or "") if row else "",
                    str(row["company_name"] or "") if row else "",
                )
            except Exception:  # noqa: BLE001
                sector_cache[symbol] = ("", "")
        return sector_cache[symbol]

    def fact_provider(symbol: str, as_of: str) -> list[dict]:
        return get_facts_as_of(facts_for(symbol), as_of, lags=lags)

    def price_provider(symbol: str, as_of: str) -> pd.DataFrame:
        if symbol not in price_cache:
            price_cache[symbol] = store.read_stock_price_frame(symbol)
        frame = price_cache[symbol]
        if frame is None or frame.empty:
            return pd.DataFrame(columns=["close"])
        return frame[frame.index <= pd.Timestamp(as_of)]

    def valuator(facts, price):
        if not facts or price is None:
            return None, None
        sector, name = sector_for(str(facts[0].get("symbol") or "X").upper())
        return canonical_pit_valuator(facts, price, sector=sector, company_name=name)

    def quality(facts):
        if not facts:
            return None, None
        sector, name = sector_for(str(facts[0].get("symbol") or "X").upper())
        return canonical_pit_quality(facts, sector=sector, company_name=name)

    deps = SnapshotDeps(
        fact_provider=fact_provider,
        price_provider=price_provider,
        pit_valuator=valuator,
        pit_quality=quality,
        lags=lags,
    )
    return deps, {"facts_cache": facts_cache, "price_cache": price_cache}


def monthly_snapshot_dates(benchmark_frame: pd.DataFrame, start: str, end: str) -> list[str]:
    """Last trading day of each month within [start, end] from the benchmark calendar."""
    frame = benchmark_frame.copy()
    frame.index = pd.to_datetime(frame.index)
    frame = frame[(frame.index >= pd.Timestamp(start)) & (frame.index <= pd.Timestamp(end))]
    if frame.empty:
        return []
    dates = frame.groupby(frame.index.to_period("M"))["close"].idxmax().sort_index()
    return [str(d.date()) for d in dates]


def run_full_research(
    *,
    top_n: int = 150,
    min_recent_bars: int = 30,
    price_start: str = PRICE_START,
    research_start: str = "2019-01-31",
    snapshot_end: str = "2024-12-31",
    research_end: str = "2025-12-31",
    sealed_oos_start: str = "2024-01-01",
    sealed_oos_end: str = "2025-12-31",
    train_years: int = 4,
    validation_years: int = 1,
    store: ResearchStore | None = None,
    price_provider=None,
) -> dict:
    """Run the end-to-end real research pipeline. Returns run_id + results."""
    store = store or ResearchStore()
    store.create_schema()

    # 1. Universe.
    universe, universe_stats = build_universe(top_n=top_n, min_recent_bars=min_recent_bars)

    # 2. Real prices + benchmark.
    price_coverage = fetch_and_persist_prices(
        store, universe, start=price_start, provider=price_provider,
    )
    usable = [s for s in universe if s in set(price_coverage["fetched_symbols"])]
    benchmark_frame = store.read_benchmark_frame("VNINDEX")

    # 3. Snapshots on a monthly grid.
    snapshot_dates = monthly_snapshot_dates(benchmark_frame, research_start, snapshot_end)
    deps, _cache = research_deps(store)
    snapshots = build_snapshots(
        deps, symbols=usable, snapshot_dates=snapshot_dates,
        universe_status_fn=lambda sym, d: "IN_UNIVERSE",
    )

    import uuid
    run_id = f"res-{uuid.uuid4().hex[:10]}"
    store.write_snapshots(run_id, snapshots)

    # 4. Forward outcomes.
    def full_price(symbol: str) -> pd.DataFrame:
        return store.read_stock_price_frame(symbol)

    outcome_rows = build_outcomes(full_price, benchmark_frame, snapshots, horizons=HORIZONS)
    store.write_outcomes(run_id, outcome_rows)

    # 5. Validation per factor x horizon.
    config = ResearchConfig(
        research_start=research_start,
        research_end=research_end,
        train_years=train_years,
        validation_years=validation_years,
        sealed_oos_start=sealed_oos_start,
        sealed_oos_end=sealed_oos_end,
    )
    cost_model = ResearchCostModel()
    results: list[dict] = []
    for factor_key, factor_name in FACTORS.items():
        for horizon in HORIZONS:
            excess_key = f"forward_excess_return_{horizon}"
            result = validate_factor(
                outcome_rows,
                factor_key=factor_key,
                factor_name=factor_name,
                excess_key=excess_key,
                config=config,
                cost_model=cost_model,
            )
            result["benchmark"] = "VNINDEX"
            result["run_id"] = run_id
            store.write_factor_result(run_id, f"{factor_name}_{horizon}", result["verdict"], result)
            results.append(result)

    return {
        "run_id": run_id,
        "universe": usable,
        "universe_stats": universe_stats,
        "price_coverage": price_coverage,
        "snapshot_dates": snapshot_dates,
        "snapshot_count": len(snapshots),
        "outcome_count": len(outcome_rows),
        "config": {
            "research_start": research_start,
            "research_end": research_end,
            "train_years": train_years,
            "validation_years": validation_years,
            "sealed_oos_start": sealed_oos_start,
            "sealed_oos_end": sealed_oos_end,
        },
        "cost_model": cost_model.to_dict(),
        "results": results,
    }


def summarize_results(results: list[dict]) -> list[dict]:
    rows = []
    for r in results:
        ic = r.get("rank_ic") or {}
        rows.append({
            "factor": r["factor"],
            "horizon": r["horizon_sessions"],
            "observations": r["observations"],
            "mean_ic": ic.get("mean_ic"),
            "positive_ratio": ic.get("positive_ic_ratio"),
            "gross_spread": r.get("gross_spread"),
            "after_cost_spread": r.get("after_cost_spread"),
            "sealed_oos_mean_ic": r.get("sealed_oos_mean_ic"),
            "verdict": r["verdict"],
        })
    return rows