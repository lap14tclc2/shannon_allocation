from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .domain import EventType, LedgerEvent


def default_db_path() -> Path:
    here = Path(__file__).resolve().parents[1]
    return Path(os.environ.get("PORTFOLIO_DB", here / "data" / "portfolio.sqlite3"))


class PortfolioStore:
    """SQLite persistence for immutable ledger events and derived daily snapshots.

    The public API intentionally has no update/delete method for ledger events.
    Corrections should be represented by compensating events rather than history
    mutation.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS ledger_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    symbol TEXT,
                    quantity REAL NOT NULL DEFAULT 0,
                    price REAL NOT NULL DEFAULT 0,
                    fee REAL NOT NULL DEFAULT 0,
                    tax REAL NOT NULL DEFAULT 0,
                    amount REAL NOT NULL DEFAULT 0,
                    ratio REAL NOT NULL DEFAULT 0,
                    note TEXT NOT NULL DEFAULT '',
                    created_by TEXT NOT NULL DEFAULT 'local',
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_ledger_date
                    ON ledger_events(event_date, id);
                CREATE INDEX IF NOT EXISTS idx_ledger_symbol
                    ON ledger_events(symbol, event_date, id);

                CREATE TABLE IF NOT EXISTS market_prices (
                    symbol TEXT NOT NULL,
                    trading_date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL NOT NULL,
                    volume REAL,
                    source TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    is_final INTEGER NOT NULL DEFAULT 1,
                    data_quality TEXT NOT NULL DEFAULT 'VALID',
                    PRIMARY KEY(symbol, trading_date)
                );
                CREATE INDEX IF NOT EXISTS idx_price_date
                    ON market_prices(trading_date, symbol);

                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_date TEXT NOT NULL UNIQUE,
                    cash REAL NOT NULL,
                    equity_value REAL NOT NULL,
                    nav REAL NOT NULL,
                    external_flow REAL NOT NULL DEFAULT 0,
                    daily_pnl REAL,
                    daily_return REAL,
                    twr_index REAL NOT NULL DEFAULT 1,
                    total_pnl REAL,
                    current_drawdown REAL,
                    max_drawdown REAL,
                    volatility_63 REAL,
                    volatility_252 REAL,
                    hhi REAL,
                    max_position_weight REAL,
                    data_quality TEXT NOT NULL,
                    official INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS snapshot_positions (
                    snapshot_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    shares REAL NOT NULL,
                    average_cost REAL NOT NULL,
                    price REAL,
                    cost_value REAL NOT NULL DEFAULT 0,
                    market_value REAL NOT NULL,
                    weight REAL NOT NULL,
                    unrealized_pnl REAL NOT NULL,
                    unrealized_return REAL,
                    risk_contribution REAL,
                    erc_reference_weight REAL,
                    status TEXT NOT NULL DEFAULT 'HOLD',
                    PRIMARY KEY(snapshot_id, symbol),
                    FOREIGN KEY(snapshot_id) REFERENCES portfolio_snapshots(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS reference_weights (
                    symbol TEXT PRIMARY KEY,
                    weight REAL NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

            # Existing databases created before cost_value was exposed need a
            # non-destructive schema upgrade. Snapshots are derived data, while
            # the ledger remains immutable source-of-truth data.
            columns = {
                row["name"] for row in db.execute("PRAGMA table_info(snapshot_positions)").fetchall()
            }
            if "cost_value" not in columns:
                db.execute(
                    "ALTER TABLE snapshot_positions ADD COLUMN cost_value REAL NOT NULL DEFAULT 0"
                )

            # One-time repair for the original provider-unit bug. VNDIRECT and
            # vnstock bars such as 22.75/72.0 mean 22,750/72,000 VND. Canonical
            # persisted prices are absolute VND. If legacy rows are repaired,
            # previously-derived snapshots are invalidated rather than silently
            # preserving wrong NAV/P&L history; a normal daily sync regenerates
            # the current snapshot from the immutable ledger and corrected data.
            marker = db.execute(
                "SELECT value FROM app_meta WHERE key = 'price_units_vnd_v1'"
            ).fetchone()
            if marker is None:
                cur = db.execute(
                    """
                    UPDATE market_prices
                    SET
                        open = CASE WHEN open IS NOT NULL AND ABS(open) < 1000 THEN open * 1000 ELSE open END,
                        high = CASE WHEN high IS NOT NULL AND ABS(high) < 1000 THEN high * 1000 ELSE high END,
                        low = CASE WHEN low IS NOT NULL AND ABS(low) < 1000 THEN low * 1000 ELSE low END,
                        close = close * 1000
                    WHERE LOWER(source) IN ('vndirect', 'vnstock')
                      AND close > 0 AND close < 1000
                    """
                )
                migrated = max(0, int(cur.rowcount or 0))
                if migrated:
                    db.execute("DELETE FROM snapshot_positions")
                    db.execute("DELETE FROM portfolio_snapshots")
                db.execute(
                    "INSERT INTO app_meta(key, value) VALUES ('price_units_vnd_v1', ?)",
                    (f"migrated:{migrated}",),
                )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def append_event(self, event: LedgerEvent) -> int:
        with self.connect() as db:
            return self.insert_event(db, event)

    def insert_event(self, db, event: LedgerEvent) -> int:
        """Insert one event using an existing transaction.

        Application services use this method for atomic multi-row imports.  The
        normal public append path remains immutable and intentionally exposes no
        update/delete operation for ledger rows.
        """
        cur = db.execute(
            """
            INSERT INTO ledger_events (
                event_type, event_date, symbol, quantity, price, fee, tax,
                amount, ratio, note, created_by, created_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_type.value,
                event.event_date,
                event.symbol.upper() if event.symbol else None,
                float(event.quantity or 0),
                float(event.price or 0),
                float(event.fee or 0),
                float(event.tax or 0),
                float(event.amount or 0),
                float(event.ratio or 0),
                event.note or "",
                event.created_by or "local",
                event.created_at or self._now(),
                json.dumps(event.metadata or {}, ensure_ascii=False),
            ),
        )
        return int(cur.lastrowid)

    def list_events(self, start: str | None = None, end: str | None = None) -> list[LedgerEvent]:
        sql = "SELECT * FROM ledger_events WHERE 1=1"
        args: list[object] = []
        if start:
            sql += " AND event_date >= ?"
            args.append(start)
        if end:
            sql += " AND event_date <= ?"
            args.append(end)
        sql += " ORDER BY event_date, id"
        with self.connect() as db:
            rows = db.execute(sql, args).fetchall()
        return [self._event_from_row(r) for r in rows]

    def events_after(self, date_exclusive: str | None, end_inclusive: str) -> list[LedgerEvent]:
        sql = "SELECT * FROM ledger_events WHERE event_date <= ?"
        args: list[object] = [end_inclusive]
        if date_exclusive:
            sql += " AND event_date > ?"
            args.append(date_exclusive)
        sql += " ORDER BY event_date, id"
        with self.connect() as db:
            rows = db.execute(sql, args).fetchall()
        return [self._event_from_row(r) for r in rows]

    @staticmethod
    def _event_from_row(row) -> LedgerEvent:
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except Exception:
            metadata = {}
        return LedgerEvent(
            id=int(row["id"]),
            event_type=EventType(row["event_type"]),
            event_date=row["event_date"],
            symbol=row["symbol"],
            quantity=float(row["quantity"] or 0),
            price=float(row["price"] or 0),
            fee=float(row["fee"] or 0),
            tax=float(row["tax"] or 0),
            amount=float(row["amount"] or 0),
            ratio=float(row["ratio"] or 0),
            note=row["note"] or "",
            created_by=row["created_by"] or "local",
            created_at=row["created_at"],
            metadata=metadata,
        )

    def upsert_market_prices(self, rows: Iterable[dict]) -> None:
        now = self._now()
        data = []
        for r in rows:
            if r.get("close") is None:
                continue
            data.append(
                (
                    str(r["symbol"]).upper(),
                    str(r["trading_date"]),
                    r.get("open"), r.get("high"), r.get("low"), float(r["close"]),
                    r.get("volume"), str(r.get("source") or "unknown"),
                    str(r.get("fetched_at") or now),
                    1 if r.get("is_final", True) else 0,
                    str(r.get("data_quality") or "VALID"),
                )
            )
        if not data:
            return
        with self.connect() as db:
            db.executemany(
                """
                INSERT INTO market_prices (
                    symbol, trading_date, open, high, low, close, volume, source,
                    fetched_at, is_final, data_quality
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, trading_date) DO UPDATE SET
                    open=excluded.open, high=excluded.high, low=excluded.low,
                    close=excluded.close, volume=excluded.volume,
                    source=excluded.source, fetched_at=excluded.fetched_at,
                    is_final=excluded.is_final, data_quality=excluded.data_quality
                """,
                data,
            )

    def latest_price(self, symbol: str, on_or_before: str | None = None) -> dict | None:
        sql = "SELECT * FROM market_prices WHERE symbol = ?"
        args: list[object] = [symbol.upper()]
        if on_or_before:
            sql += " AND trading_date <= ?"
            args.append(on_or_before)
        sql += " ORDER BY trading_date DESC LIMIT 1"
        with self.connect() as db:
            row = db.execute(sql, args).fetchone()
        return dict(row) if row else None

    def latest_prices(self, symbols: Iterable[str], on_or_before: str | None = None) -> dict[str, dict]:
        symbol_list = [str(s).upper().strip() for s in symbols if str(s).strip()]
        if not symbol_list:
            return {}
        placeholders = ", ".join(["?"] * len(symbol_list))
        sql = f"SELECT * FROM market_prices WHERE symbol IN ({placeholders})"
        args: list[object] = list(symbol_list)
        if on_or_before:
            sql += " AND trading_date <= ?"
            args.append(on_or_before)
        # One batched query instead of one connection + query per symbol.
        sql += " ORDER BY trading_date DESC"
        with self.connect() as db:
            rows = db.execute(sql, args).fetchall()
        out: dict[str, dict] = {}
        for row in rows:
            out.setdefault(str(row["symbol"]).upper(), dict(row))

        # Fallback to PostgreSQL catalog for symbols missing in local sqlite
        missing = [s for s in symbol_list if s not in out]
        if missing:
            try:
                from portfolio.finance_catalog import _schema_connection, FINANCE_SCHEMA
                with _schema_connection(FINANCE_SCHEMA) as db:
                    ph = ",".join("%s" for _ in missing)
                    pg_sql = f"""
                        SELECT DISTINCT ON (symbol) symbol, trading_date, open, high, low, close, volume
                        FROM market_prices
                        WHERE symbol IN ({ph})
                    """
                    if on_or_before:
                        pg_sql += f" AND trading_date <= '{on_or_before}'"
                    pg_sql += " ORDER BY symbol, trading_date DESC"
                    pg_rows = db.execute(pg_sql, tuple(missing)).fetchall()
                    if pg_rows:
                        upsert_rows = []
                        for r in pg_rows:
                            sym = str(r["symbol"]).upper()
                            p_row = {
                                "symbol": sym,
                                "trading_date": str(r["trading_date"]),
                                "open": float(r["open"]) if r.get("open") is not None else float(r["close"]),
                                "high": float(r["high"]) if r.get("high") is not None else float(r["close"]),
                                "low": float(r["low"]) if r.get("low") is not None else float(r["close"]),
                                "close": float(r["close"]),
                                "volume": float(r["volume"]) if r.get("volume") is not None else 0.0,
                                "source": "postgres_catalog",
                            }
                            upsert_rows.append(p_row)
                            out[sym] = p_row
                        if upsert_rows:
                            self.upsert_market_prices(upsert_rows)
            except Exception:
                pass

        return out

    def price_history(self, symbol: str, limit: int = 252, end: str | None = None) -> list[dict]:
        sql = "SELECT * FROM market_prices WHERE symbol = ?"
        args: list[object] = [symbol.upper()]
        if end:
            sql += " AND trading_date <= ?"
            args.append(end)
        sql += " ORDER BY trading_date DESC LIMIT ?"
        args.append(int(limit))
        with self.connect() as db:
            rows = db.execute(sql, args).fetchall()
        return [dict(r) for r in reversed(rows)]

    def price_histories(self, symbols: Iterable[str], limit: int = 252, end: str | None = None) -> dict[str, list[dict]]:
        """Batch price history load for many symbols with one query."""
        symbol_list = [str(s).upper().strip() for s in symbols if str(s).strip()]
        if not symbol_list:
            return {}
        placeholders = ", ".join(["?"] * len(symbol_list))
        sql = f"SELECT * FROM market_prices WHERE symbol IN ({placeholders})"
        args: list[object] = list(symbol_list)
        if end:
            sql += " AND trading_date <= ?"
            args.append(end)
        sql += " ORDER BY trading_date DESC LIMIT ?"
        args.append(int(limit))
        with self.connect() as db:
            rows = db.execute(sql, args).fetchall()
        out: dict[str, list[dict]] = {s: [] for s in symbol_list}
        for row in rows:
            out[str(row["symbol"]).upper()].append(dict(row))
        for symbol in symbol_list:
            out[symbol].reverse()
        return out

    def market_price_count(self, symbol: str) -> int:
        with self.connect() as db:
            row = db.execute(
                "SELECT COUNT(*) AS n FROM market_prices WHERE symbol = ?",
                (symbol.upper(),),
            ).fetchone()
        return int(row["n"] if row else 0)

    def save_snapshot(self, snapshot: dict, positions: list[dict]) -> int:
        with self.connect() as db:
            existing = db.execute(
                "SELECT id FROM portfolio_snapshots WHERE snapshot_date = ?",
                (snapshot["snapshot_date"],),
            ).fetchone()
            values = (
                float(snapshot.get("cash", 0)),
                float(snapshot.get("equity_value", 0)),
                float(snapshot.get("nav", 0)),
                float(snapshot.get("external_flow", 0)),
                snapshot.get("daily_pnl"),
                snapshot.get("daily_return"),
                float(snapshot.get("twr_index", 1)),
                snapshot.get("total_pnl"),
                snapshot.get("current_drawdown"),
                snapshot.get("max_drawdown"),
                snapshot.get("volatility_63"),
                snapshot.get("volatility_252"),
                snapshot.get("hhi"),
                snapshot.get("max_position_weight"),
                str(snapshot.get("data_quality") or "MISSING"),
                1 if snapshot.get("official") else 0,
                str(snapshot.get("created_at") or self._now()),
            )
            if existing:
                sid = int(existing["id"])
                db.execute(
                    """
                    UPDATE portfolio_snapshots SET
                        cash=?, equity_value=?, nav=?, external_flow=?, daily_pnl=?,
                        daily_return=?, twr_index=?, total_pnl=?, current_drawdown=?,
                        max_drawdown=?, volatility_63=?, volatility_252=?, hhi=?,
                        max_position_weight=?, data_quality=?, official=?, created_at=?
                    WHERE id=?
                    """,
                    (*values, sid),
                )
                db.execute("DELETE FROM snapshot_positions WHERE snapshot_id = ?", (sid,))
            else:
                cur = db.execute(
                    """
                    INSERT INTO portfolio_snapshots (
                        snapshot_date, cash, equity_value, nav, external_flow,
                        daily_pnl, daily_return, twr_index, total_pnl,
                        current_drawdown, max_drawdown, volatility_63,
                        volatility_252, hhi, max_position_weight, data_quality,
                        official, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (snapshot["snapshot_date"], *values),
                )
                sid = int(cur.lastrowid)

            db.executemany(
                """
                INSERT INTO snapshot_positions (
                    snapshot_id, symbol, shares, average_cost, price, cost_value,
                    market_value, weight, unrealized_pnl, unrealized_return,
                    risk_contribution, erc_reference_weight, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        sid, p["symbol"], float(p.get("shares", 0)),
                        float(p.get("average_cost", 0)), p.get("price"),
                        float(p.get("cost_value", 0)), float(p.get("market_value", 0)),
                        float(p.get("weight", 0)), float(p.get("unrealized_pnl", 0)),
                        p.get("unrealized_return"), p.get("risk_contribution"),
                        p.get("erc_reference_weight"), str(p.get("status") or "HOLD"),
                    )
                    for p in positions
                ],
            )
            return sid

    def _snapshot_from_row(self, db, row) -> dict:
        out = dict(row)
        positions = db.execute(
            "SELECT * FROM snapshot_positions WHERE snapshot_id = ? ORDER BY market_value DESC",
            (row["id"],),
        ).fetchall()
        out["positions"] = [dict(p) for p in positions]
        out["official"] = bool(out.get("official"))
        return out

    def latest_snapshot(self, official_only: bool = False) -> dict | None:
        sql = "SELECT * FROM portfolio_snapshots"
        if official_only:
            sql += " WHERE official = 1"
        sql += " ORDER BY snapshot_date DESC LIMIT 1"
        with self.connect() as db:
            row = db.execute(sql).fetchone()
            return self._snapshot_from_row(db, row) if row else None

    def list_snapshots(self, limit: int = 500, official_only: bool = False) -> list[dict]:
        sql = "SELECT * FROM portfolio_snapshots"
        if official_only:
            sql += " WHERE official = 1"
        sql += " ORDER BY snapshot_date DESC LIMIT ?"
        with self.connect() as db:
            rows = db.execute(sql, (int(limit),)).fetchall()
            if not rows:
                return []
            ids = [int(r["id"]) for r in rows]
            placeholders = ", ".join(["?"] * len(ids))
            pos_rows = db.execute(
                f"SELECT * FROM snapshot_positions WHERE snapshot_id IN ({placeholders}) ORDER BY market_value DESC",
                ids,
            ).fetchall()
        positions_by_snapshot: dict[int, list[dict]] = {}
        for p in pos_rows:
            positions_by_snapshot.setdefault(int(p["snapshot_id"]), []).append(dict(p))
        out = []
        for row in rows:
            snapshot = dict(row)
            snapshot["positions"] = positions_by_snapshot.get(int(row["id"]), [])
            snapshot["official"] = bool(snapshot.get("official"))
            out.append(snapshot)
        return out

    def set_reference_weights(self, weights: dict[str, float]) -> None:
        total = sum(float(v) for v in weights.values())
        if weights and abs(total - 1.0) > 1e-6:
            raise ValueError("Reference weights must sum to 1.0")
        now = self._now()
        with self.connect() as db:
            db.execute("DELETE FROM reference_weights")
            db.executemany(
                "INSERT INTO reference_weights(symbol, weight, updated_at) VALUES (?, ?, ?)",
                [(s.upper(), float(w), now) for s, w in sorted(weights.items())],
            )

    def get_reference_weights(self) -> dict[str, float]:
        with self.connect() as db:
            rows = db.execute("SELECT symbol, weight FROM reference_weights ORDER BY symbol").fetchall()
        return {r["symbol"]: float(r["weight"]) for r in rows}

    def set_meta(self, key: str, value: str) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO app_meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        with self.connect() as db:
            row = db.execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
