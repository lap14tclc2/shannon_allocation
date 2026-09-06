"""Research storage (T11-T13 persistence).

Tables live in the ``qport_research`` schema (Postgres in production) and are
SQLite-compatible for hermetic tests. Keys are explicit ``run_id`` strings —
no auto-increment columns, so the DDL is dialect-portable.

Entities:
    research_factor_snapshots
    research_factor_outcomes
    research_benchmark_prices
    research_validation_runs
    research_walk_forward_windows
    research_factor_results

Every run records ``run_id``, ``factor_version``, ``data_hash``, ``created_at``
and provenance so results are reproducible.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

QPORT_RESEARCH_SCHEMA = "qport_research"

RESEARCH_DDL = """
CREATE TABLE IF NOT EXISTS research_factor_snapshots (
    run_id TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    universe_status TEXT NOT NULL DEFAULT 'CANDIDATE',
    value_factor DOUBLE PRECISION,
    quality_factor DOUBLE PRECISION,
    quality_tier TEXT,
    momentum_3m DOUBLE PRECISION,
    momentum_6m DOUBLE PRECISION,
    momentum_12m DOUBLE PRECISION,
    momentum_12_1 DOUBLE PRECISION,
    reversal_1m DOUBLE PRECISION,
    liquidity DOUBLE PRECISION,
    source_hash TEXT NOT NULL,
    factor_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(run_id, snapshot_date, symbol)
);
CREATE INDEX IF NOT EXISTS idx_research_snap_date
    ON research_factor_snapshots(snapshot_date, symbol);

CREATE TABLE IF NOT EXISTS research_factor_outcomes (
    run_id TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    horizon_sessions INTEGER NOT NULL,
    forward_stock_return DOUBLE PRECISION,
    forward_vnindex_return DOUBLE PRECISION,
    forward_excess_return DOUBLE PRECISION,
    source_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(run_id, snapshot_date, symbol, horizon_sessions)
);

CREATE TABLE IF NOT EXISTS research_benchmark_prices (
    benchmark TEXT NOT NULL,
    trading_date TEXT NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    data_quality TEXT NOT NULL DEFAULT 'VALID',
    PRIMARY KEY(benchmark, trading_date)
);

CREATE TABLE IF NOT EXISTS research_validation_runs (
    run_id TEXT NOT NULL PRIMARY KEY,
    factor TEXT NOT NULL,
    horizon_sessions INTEGER NOT NULL,
    benchmark TEXT NOT NULL,
    universe_definition TEXT NOT NULL DEFAULT '',
    cost_model_json TEXT NOT NULL DEFAULT '{}',
    data_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_walk_forward_windows (
    run_id TEXT NOT NULL,
    window_index INTEGER NOT NULL,
    train_start TEXT NOT NULL,
    train_end TEXT NOT NULL,
    valid_start TEXT NOT NULL,
    valid_end TEXT NOT NULL,
    PRIMARY KEY(run_id, window_index)
);

CREATE TABLE IF NOT EXISTS research_factor_results (
    run_id TEXT NOT NULL,
    factor TEXT NOT NULL,
    verdict TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(run_id, factor)
);
"""


def _sqlite_factory(path: str = ":memory:"):
    import sqlite3

    @contextmanager
    def _factory() -> Iterator:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    return _factory


def _postgres_factory():
    from ..postgres import _ensure_schema, _schema_connection

    _ensure_schema(QPORT_RESEARCH_SCHEMA)
    return lambda: _schema_connection(QPORT_RESEARCH_SCHEMA)


class ResearchStore:
    """Thin persistence layer over research tables.

    ``connection_factory`` is a zero-arg callable returning a context manager
    that yields a DB-API-compatible connection (Postgres compat or sqlite3).
    """

    def __init__(self, connection_factory=None) -> None:
        self._factory = connection_factory or _postgres_factory()

    @contextmanager
    def _connect(self) -> Iterator:
        with self._factory() as db:
            yield db

    def create_schema(self) -> None:
        with self._connect() as db:
            db.executescript(RESEARCH_DDL)

    # -- snapshots ----------------------------------------------------------
    def write_snapshots(self, run_id: str, rows: list[dict]) -> int:
        sql = (
            "INSERT INTO research_factor_snapshots "
            "(run_id, snapshot_date, symbol, universe_status, value_factor, "
            "quality_factor, quality_tier, momentum_3m, momentum_6m, "
            "momentum_12m, momentum_12_1, reversal_1m, liquidity, source_hash, "
            "factor_version, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (run_id, snapshot_date, symbol) "
            "DO UPDATE SET value_factor=excluded.value_factor, "
            "quality_factor=excluded.quality_factor, "
            "quality_tier=excluded.quality_tier, "
            "momentum_3m=excluded.momentum_3m, momentum_6m=excluded.momentum_6m, "
            "momentum_12m=excluded.momentum_12m, momentum_12_1=excluded.momentum_12_1, "
            "reversal_1m=excluded.reversal_1m, liquidity=excluded.liquidity, "
            "source_hash=excluded.source_hash, created_at=excluded.created_at"
        )
        params = [
            (run_id, r["snapshot_date"], r["symbol"], r.get("universe_status", "CANDIDATE"),
             r.get("value_factor"), r.get("quality_factor"), r.get("quality_tier"),
             r.get("momentum_3m"), r.get("momentum_6m"), r.get("momentum_12m"),
             r.get("momentum_12_1"), r.get("reversal_1m"), r.get("liquidity"),
             r["source_hash"], r["factor_version"], r["created_at"])
            for r in rows
        ]
        with self._connect() as db:
            db.executemany(sql, params)
        return len(params)

    def read_snapshots(self, run_id: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM research_factor_snapshots WHERE run_id = ? "
                "ORDER BY snapshot_date, symbol",
                (run_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # -- outcomes -----------------------------------------------------------
    def write_outcomes(self, run_id: str, rows: list[dict]) -> int:
        sql = (
            "INSERT INTO research_factor_outcomes "
            "(run_id, snapshot_date, symbol, horizon_sessions, "
            "forward_stock_return, forward_vnindex_return, forward_excess_return, "
            "source_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (run_id, snapshot_date, symbol, horizon_sessions) "
            "DO UPDATE SET forward_stock_return=excluded.forward_stock_return, "
            "forward_vnindex_return=excluded.forward_vnindex_return, "
            "forward_excess_return=excluded.forward_excess_return"
        )
        params = []
        for r in rows:
            for h in (21, 63, 126, 252):
                params.append((
                    run_id, r["snapshot_date"], r["symbol"], h,
                    r.get(f"forward_stock_return_{h}"),
                    r.get(f"forward_vnindex_return_{h}"),
                    r.get(f"forward_excess_return_{h}"),
                    r["source_hash"], r["created_at"],
                ))
        with self._connect() as db:
            db.executemany(sql, params)
        return len(params)

    # -- benchmark ----------------------------------------------------------
    def write_benchmark_prices(self, rows: list[dict]) -> int:
        sql = (
            "INSERT INTO research_benchmark_prices "
            "(benchmark, trading_date, close, source, fetched_at, data_quality) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (benchmark, trading_date) "
            "DO UPDATE SET close=excluded.close, source=excluded.source, "
            "fetched_at=excluded.fetched_at, data_quality=excluded.data_quality"
        )
        params = [
            (r["benchmark"], r["trading_date"], r["close"], r["source"],
             r.get("fetched_at", ""), r.get("data_quality", "VALID"))
            for r in rows
        ]
        with self._connect() as db:
            db.executemany(sql, params)
        return len(params)

    def read_benchmark_prices(self, benchmark: str = "VNINDEX") -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM research_benchmark_prices WHERE benchmark = ? "
                "ORDER BY trading_date",
                (benchmark,),
            ).fetchall()
        return [dict(r) for r in rows]

    # -- validation ---------------------------------------------------------
    def write_validation_run(self, run: dict) -> None:
        sql = (
            "INSERT INTO research_validation_runs "
            "(run_id, factor, horizon_sessions, benchmark, universe_definition, "
            "cost_model_json, data_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (run_id) DO UPDATE SET "
            "factor=excluded.factor, horizon_sessions=excluded.horizon_sessions"
        )
        with self._connect() as db:
            db.execute(sql, (
                run["run_id"], run["factor"], run["horizon_sessions"],
                run["benchmark"], run.get("universe_definition", ""),
                run.get("cost_model_json", "{}"), run["data_hash"],
                run["created_at"],
            ))

    def write_walk_forward_windows(self, run_id: str, windows: list[dict]) -> None:
        sql = (
            "INSERT INTO research_walk_forward_windows "
            "(run_id, window_index, train_start, train_end, valid_start, valid_end) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (run_id, window_index) DO UPDATE SET "
            "train_start=excluded.train_start, train_end=excluded.train_end, "
            "valid_start=excluded.valid_start, valid_end=excluded.valid_end"
        )
        params = [
            (run_id, i, w["train_start"], w["train_end"], w["valid_start"], w["valid_end"])
            for i, w in enumerate(windows)
        ]
        with self._connect() as db:
            db.executemany(sql, params)

    def write_factor_result(self, run_id: str, factor: str, verdict: str, metrics: dict) -> None:
        import json

        sql = (
            "INSERT INTO research_factor_results "
            "(run_id, factor, verdict, metrics_json, created_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (run_id, factor) DO UPDATE SET "
            "verdict=excluded.verdict, metrics_json=excluded.metrics_json"
        )
        from datetime import datetime, timezone

        with self._connect() as db:
            db.execute(sql, (
                run_id, factor, verdict, json.dumps(metrics, default=str),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ))