#!/usr/bin/env python3
"""One-time QPort SQLite -> PostgreSQL migration.

The Vercel architecture keeps the current isolation model by mapping each old
``user-N.sqlite3`` file to a PostgreSQL schema named ``qport_user_N``. The auth
database maps to ``qport_auth``.

Usage:
    DATABASE_URL='postgresql://...' python scripts/migrate_sqlite_to_postgres.py

Use ``--replace`` only when intentionally replacing an earlier migration target.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import defaultdict, deque
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from portfolio.automated_service import AutomatedPortfolioService  # noqa: E402
from portfolio.dividend_store import SqliteDividendService  # noqa: E402
from portfolio.postgres import (  # noqa: E402
    AUTH_SCHEMA,
    PostgresAuthStore,
    PostgresPortfolioStore,
    _translate_statement,
    database_url,
    user_schema,
)


def source_tables(db: sqlite3.Connection) -> list[str]:
    return [
        row["name"]
        for row in db.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%' AND sql IS NOT NULL
            ORDER BY name
            """
        ).fetchall()
    ]


def dependency_order(db: sqlite3.Connection, tables: list[str]) -> list[str]:
    table_set = set(tables)
    dependencies: dict[str, set[str]] = {table: set() for table in tables}
    reverse: dict[str, set[str]] = defaultdict(set)
    for table in tables:
        for row in db.execute(f'PRAGMA foreign_key_list("{table}")').fetchall():
            parent = str(row["table"])
            if parent in table_set and parent != table:
                dependencies[table].add(parent)
                reverse[parent].add(table)

    ready = deque(sorted(table for table, deps in dependencies.items() if not deps))
    ordered: list[str] = []
    while ready:
        table = ready.popleft()
        ordered.append(table)
        for child in sorted(reverse.get(table, ())):
            dependencies[child].discard(table)
            if not dependencies[child] and child not in ordered and child not in ready:
                ready.append(child)
    # No cycles are expected in QPort, but preserve deterministic progress if a
    # future schema introduces one. PostgreSQL DDL creation will surface it.
    ordered.extend(sorted(set(tables) - set(ordered)))
    return ordered


def schema_exists(schema_name: str) -> bool:
    with psycopg.connect(database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name=%s",
                (schema_name,),
            )
            return cur.fetchone() is not None


def prepare_schema(schema_name: str, *, replace: bool) -> None:
    exists = schema_exists(schema_name)
    if exists and not replace:
        raise RuntimeError(
            f"Target schema {schema_name!r} already exists. "
            "Use --replace only if you intentionally want to overwrite it."
        )
    with psycopg.connect(database_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            if exists:
                cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema_name)))
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))


def create_tables(source: sqlite3.Connection, schema_name: str, tables: list[str]) -> None:
    pending = {
        table: source.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()["sql"]
        for table in tables
    }
    # Dependency order already covers QPort's foreign keys. The retry loop makes
    # this tolerant of SQLite returning a different sqlite_master order.
    ordered = dependency_order(source, tables)
    with psycopg.connect(database_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema_name)))
            remaining = list(ordered)
            last_errors: dict[str, str] = {}
            while remaining:
                progressed = False
                next_remaining = []
                for table in remaining:
                    try:
                        cur.execute(_translate_statement(pending[table]))
                        progressed = True
                    except psycopg.errors.UndefinedTable as exc:
                        last_errors[table] = str(exc)
                        next_remaining.append(table)
                    except psycopg.errors.DuplicateTable:
                        progressed = True
                if not next_remaining:
                    break
                if not progressed:
                    details = "; ".join(f"{k}: {v}" for k, v in last_errors.items())
                    raise RuntimeError(f"Could not create dependent tables in {schema_name}: {details}")
                remaining = next_remaining


def create_indexes(source: sqlite3.Connection, schema_name: str) -> None:
    rows = source.execute(
        """
        SELECT name, sql FROM sqlite_master
        WHERE type='index' AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    with psycopg.connect(database_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema_name)))
            for row in rows:
                try:
                    cur.execute(_translate_statement(row["sql"]))
                except psycopg.errors.DuplicateObject:
                    pass


def copy_rows(source: sqlite3.Connection, schema_name: str, tables: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    ordered = dependency_order(source, tables)
    with psycopg.connect(database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema_name)))
            for table in ordered:
                columns = [row["name"] for row in source.execute(f'PRAGMA table_info("{table}")').fetchall()]
                rows = source.execute(f'SELECT * FROM "{table}"').fetchall()
                counts[table] = len(rows)
                if not rows or not columns:
                    continue
                insert = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                    sql.Identifier(table),
                    sql.SQL(", ").join(sql.Identifier(column) for column in columns),
                    sql.SQL(", ").join(sql.Placeholder() for _ in columns),
                )
                cur.executemany(insert, [tuple(row[column] for column in columns) for row in rows])
        conn.commit()
    return counts


def reset_sequences(schema_name: str, tables: list[str]) -> None:
    with psycopg.connect(database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema_name)))
            for table in tables:
                cur.execute(
                    """
                    SELECT column_default FROM information_schema.columns
                    WHERE table_schema=%s AND table_name=%s AND column_name='id'
                    """,
                    (schema_name, table),
                )
                meta = cur.fetchone()
                if not meta or not str(meta.get("column_default") or "").startswith("nextval("):
                    continue
                cur.execute(sql.SQL("SELECT MAX(id) AS max_id FROM {}").format(sql.Identifier(table)))
                row = cur.fetchone()
                max_id = int(row["max_id"] or 0)
                if max_id <= 0:
                    continue
                qualified = f"{schema_name}.{table}"
                cur.execute("SELECT pg_get_serial_sequence(%s, 'id') AS sequence", (qualified,))
                seq = cur.fetchone()["sequence"]
                if seq:
                    cur.execute("SELECT setval(%s, %s, true)", (seq, max_id))
        conn.commit()


def migrate_database(source_path: Path, schema_name: str, *, replace: bool) -> dict:
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    source = sqlite3.connect(source_path)
    source.row_factory = sqlite3.Row
    try:
        tables = source_tables(source)
        prepare_schema(schema_name, replace=replace)
        create_tables(source, schema_name, tables)
        counts = copy_rows(source, schema_name, tables)
        create_indexes(source, schema_name)
        reset_sequences(schema_name, tables)
        return {"schema": schema_name, "tables": counts, "rows": sum(counts.values())}
    finally:
        source.close()


def source_user_ids(auth_path: Path) -> list[int]:
    db = sqlite3.connect(auth_path)
    db.row_factory = sqlite3.Row
    try:
        return [
            int(row["id"])
            for row in db.execute("SELECT id FROM users WHERE role='USER' ORDER BY id").fetchall()
        ]
    finally:
        db.close()


def post_migration_upgrade(user_ids: list[int]) -> None:
    # Re-apply current non-destructive schema upgrades after copying any older
    # local database. Dividend/institutional schemas share the same user schema.
    auth = PostgresAuthStore()
    with auth.connect() as db:
        # Existing browser sessions point at localhost and are not useful on the
        # new deployment domain. Force a clean login on Vercel.
        db.execute("DELETE FROM sessions")
    for user_id in user_ids:
        store = PostgresPortfolioStore(user_id)
        service = AutomatedPortfolioService(store=store)
        SqliteDividendService(service.store, stop_on_first_data=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate QPort auth + per-user SQLite files to PostgreSQL schemas")
    parser.add_argument(
        "--namespace",
        type=Path,
        default=ROOT / "python" / "data" / "auth-v1",
        help="Existing auth-v1 directory containing auth.sqlite3 and users/",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Drop existing qport_auth/qport_user_* target schemas before migration",
    )
    args = parser.parse_args()

    # Fail before touching data if DATABASE_URL is absent/invalid.
    database_url()
    auth_path = args.namespace / "auth.sqlite3"
    users_dir = args.namespace / "users"
    if not auth_path.exists():
        raise SystemExit(f"Auth database not found: {auth_path}")

    ids = source_user_ids(auth_path)
    report = [migrate_database(auth_path, AUTH_SCHEMA, replace=args.replace)]
    for user_id in ids:
        source_path = users_dir / f"user-{user_id}.sqlite3"
        if source_path.exists():
            report.append(migrate_database(source_path, user_schema(user_id), replace=args.replace))
        else:
            prepare_schema(user_schema(user_id), replace=args.replace)

    post_migration_upgrade(ids)
    print("QPort PostgreSQL migration complete")
    for item in report:
        print(f"- {item['schema']}: {item['rows']} rows across {len(item['tables'])} tables")
    print(f"- users migrated: {len(ids)}")
    print("- sessions cleared: sign in again on the Vercel domain")


if __name__ == "__main__":
    main()
