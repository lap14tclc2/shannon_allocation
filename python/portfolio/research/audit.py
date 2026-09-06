"""Data readiness audit for the real QPort finance database.

Reports actual coverage so research never proceeds silently on poor data.
"""
from __future__ import annotations


def audit_finance_data(connection=None) -> dict:
    """Audit qport_finance coverage. ``connection`` optional (Postgres default)."""
    from ..finance_catalog import FINANCE_SCHEMA, _schema_connection

    def q(sql, params=()):
        if connection is not None:
            return connection.execute(sql, params).fetchall()
        with _schema_connection(FINANCE_SCHEMA) as db:
            return db.execute(sql, params).fetchall()

    securities = int(q("SELECT COUNT(*) AS n FROM securities")[0]["n"])
    facts = int(q("SELECT COUNT(*) AS n FROM canonical_facts")[0]["n"])
    docs = int(q("SELECT COUNT(*) AS n FROM documents")[0]["n"])

    fy = q("SELECT MIN(fiscal_year) AS mn, MAX(fiscal_year) AS mx FROM canonical_facts")[0]
    pe = q("SELECT MIN(period_end) AS mn, MAX(period_end) AS mx FROM canonical_facts")[0]

    # Stored price coverage.
    price_span = q("SELECT MIN(trading_date) AS mn, MAX(trading_date) AS mx FROM market_prices")[0]
    price_symbols = int(q("SELECT COUNT(DISTINCT symbol) AS n FROM market_prices")[0]["n"])
    bars_dist = q(
        "SELECT CASE WHEN bars < 20 THEN '<20' WHEN bars < 60 THEN '20-60' "
        "WHEN bars < 260 THEN '60-260' ELSE '>=260' END AS bucket, COUNT(*) AS n "
        "FROM (SELECT symbol, COUNT(*) AS bars FROM market_prices GROUP BY symbol) t "
        "GROUP BY bucket ORDER BY bucket"
    )
    ok_260 = int(q(
        "SELECT COUNT(*) AS n FROM (SELECT symbol FROM market_prices GROUP BY symbol HAVING COUNT(*) >= 260) t"
    )[0]["n"])

    # PIT publication metadata coverage.
    try:
        pub_count = int(q(
            "SELECT COUNT(*) AS n FROM canonical_facts WHERE published_at IS NOT NULL"
        )[0]["n"])
    except Exception:  # column absent -> no verified metadata
        pub_count = 0

    # Documents: fetched_at present (always) but no verified publication date.
    doc_fetched = int(q("SELECT COUNT(*) AS n FROM documents WHERE fetched_at IS NOT NULL")[0]["n"])

    return {
        "securities": securities,
        "securities_by_exchange": [dict(r) for r in q(
            "SELECT exchange, COUNT(*) AS n FROM securities GROUP BY exchange ORDER BY exchange"
        )],
        "canonical_facts": facts,
        "canonical_facts_fiscal_years": {"min": fy["mn"], "max": fy["mx"]},
        "canonical_facts_period_end": {"min": pe["mn"], "max": pe["mx"]},
        "documents": docs,
        "documents_with_fetched_at": doc_fetched,
        "verified_publication_facts": pub_count,
        "inferred_publication_facts": max(0, facts - pub_count),
        "stored_ohlcv": {
            "symbols": price_symbols,
            "span": {"min": price_span["mn"], "max": price_span["mx"]},
            "bars_distribution": [dict(r) for r in bars_dist],
            "symbols_with_ge_260_bars": ok_260,
        },
        "historical_ohlcv_in_db": ok_260 > 0,
        "survivorship": {
            "status": "SURVIVORSHIP_BIAS_NOT_FULLY_CONTROLLED",
            "detail": "Historical universe membership is not reconstructible from current data; "
                      "securities table reflects the current (surviving) listing set.",
        },
    }


def audit_benchmark(provider=None) -> dict:
    """Empirically verify VNINDEX is fetchable (do not assume semantics)."""
    from ..research.benchmark import VNIndexBenchmark

    bench = VNIndexBenchmark(market=provider) if provider else VNIndexBenchmark()
    return bench.verify("2023-01-01", "2023-12-31")