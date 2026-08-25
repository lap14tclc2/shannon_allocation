from __future__ import annotations

import os
import re
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from .auth import (
    AuthError,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    SESSION_DAYS,
    _hash_password,
    _iso,
    _now,
    _token_hash,
    _verify_password,
)
from .storage import PortfolioStore


DATABASE_URL_ENV = "DATABASE_URL"
AUTH_SCHEMA = "qport_auth"
USER_SCHEMA_PREFIX = "qport_user_"
MAX_PORTFOLIOS_PER_USER = 20
DEFAULT_PORTFOLIO_NAME = "Danh mục mặc định"
PORTFOLIO_SCHEMA_RE = re.compile(r"^qport_user_[0-9]+(?:_portfolio_[a-f0-9]{12})?$")


def database_url() -> str:
    value = str(os.environ.get(DATABASE_URL_ENV) or "").strip()
    if not value:
        raise RuntimeError(
            "DATABASE_URL is required for the Vercel/PostgreSQL runtime. "
            "Use a Neon/Supabase/PostgreSQL connection string."
        )
    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://") :]
    if not value.startswith(("postgresql://", "postgresql+")):
        raise RuntimeError("DATABASE_URL must be a PostgreSQL connection string.")
    return value


def user_schema(user_id: int) -> str:
    return f"{USER_SCHEMA_PREFIX}{int(user_id)}"


def portfolio_schema(user_id: int, token: str) -> str:
    value = f"{user_schema(user_id)}_portfolio_{str(token).lower()}"
    if not PORTFOLIO_SCHEMA_RE.fullmatch(value):
        raise ValueError("Invalid portfolio schema name.")
    return value


def _validate_portfolio_schema(user_id: int, schema_name: str) -> str:
    value = str(schema_name or "")
    prefix = user_schema(user_id)
    if not PORTFOLIO_SCHEMA_RE.fullmatch(value) or not (
        value == prefix or value.startswith(prefix + "_portfolio_")
    ):
        raise ValueError("Portfolio schema does not belong to this user.")
    return value


def _replace_qmark_placeholders(statement: str) -> str:
    """Translate SQLite DB-API qmark placeholders to psycopg placeholders.

    The existing QPort persistence layer uses ``?`` consistently. This small
    parser avoids replacing question marks that happen to occur inside quoted
    string literals.
    """
    out: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(statement):
        ch = statement[i]
        if quote:
            out.append(ch)
            if ch == quote:
                if i + 1 < len(statement) and statement[i + 1] == quote:
                    out.append(statement[i + 1])
                    i += 1
                else:
                    quote = None
            i += 1
            continue
        if ch in {"'", '"'}:
            quote = ch
            out.append(ch)
        elif ch == "?":
            out.append("%s")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _translate_statement(statement: str) -> str:
    text = statement.strip()
    if not text:
        return text

    # DDL compatibility for schemas created by the existing SQLite-oriented
    # modules. Keeping the existing table contracts lets the accounting/domain
    # layers remain unchanged during the hosting migration.
    text = re.sub(
        r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
        "BIGSERIAL PRIMARY KEY",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bAUTOINCREMENT\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bINTEGER\b", "BIGINT", text, flags=re.IGNORECASE)
    text = re.sub(r"\bREAL\b", "DOUBLE PRECISION", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+COLLATE\s+NOCASE\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bIFNULL\s*\(", "COALESCE(", text, flags=re.IGNORECASE)

    # SQLite's INSERT OR IGNORE maps directly to PostgreSQL conflict handling.
    if re.match(r"^INSERT\s+OR\s+IGNORE\s+INTO\b", text, flags=re.IGNORECASE):
        text = re.sub(
            r"^INSERT\s+OR\s+IGNORE\s+INTO\b",
            "INSERT INTO",
            text,
            flags=re.IGNORECASE,
        )
        if " ON CONFLICT " not in text.upper():
            text += " ON CONFLICT DO NOTHING"

    return _replace_qmark_placeholders(text)


def _split_script(script: str) -> list[str]:
    """Split simple schema scripts without breaking quoted semicolons."""
    statements: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(script):
        ch = script[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                if i + 1 < len(script) and script[i + 1] == quote:
                    buf.append(script[i + 1])
                    i += 1
                else:
                    quote = None
            i += 1
            continue
        if ch in {"'", '"'}:
            quote = ch
            buf.append(ch)
        elif ch == ";":
            statement = "".join(buf).strip()
            if statement:
                statements.append(statement)
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


class PostgresCursorCompat:
    def __init__(self, connection: psycopg.Connection, cursor, statement: str = "") -> None:
        self._connection = connection
        self._cursor = cursor
        self._statement = statement
        self._lastrowid = None

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        if self._lastrowid is not None:
            return self._lastrowid
        match = re.match(r"^\s*INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)", self._statement, re.IGNORECASE)
        if not match:
            return None
        table = match.group(1)
        try:
            with self._connection.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT currval(pg_get_serial_sequence(%s, 'id')) AS id",
                    (table,),
                )
                row = cur.fetchone()
            self._lastrowid = int(row["id"]) if row and row.get("id") is not None else None
        except Exception:
            self._lastrowid = None
        return self._lastrowid

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class PostgresConnectionCompat:
    """Tiny DB-API compatibility layer for QPort's existing store modules."""

    def __init__(self, connection: psycopg.Connection, schema: str) -> None:
        self._connection = connection
        self.schema = schema

    def execute(self, statement: str, params=()):
        pragma = re.match(
            r"^\s*PRAGMA\s+table_info\(([^)]+)\)\s*$",
            statement,
            flags=re.IGNORECASE,
        )
        if pragma:
            table = pragma.group(1).strip().strip("'\"")
            cur = self._connection.cursor(row_factory=dict_row)
            cur.execute(
                """
                SELECT column_name AS name, data_type AS type
                FROM information_schema.columns
                WHERE table_schema=%s AND table_name=%s
                ORDER BY ordinal_position
                """,
                (self.schema, table),
            )
            return PostgresCursorCompat(self._connection, cur, statement)

        translated = _translate_statement(statement)
        cur = self._connection.cursor(row_factory=dict_row)
        cur.execute(translated, tuple(params or ()))
        return PostgresCursorCompat(self._connection, cur, translated)

    def executemany(self, statement: str, rows):
        translated = _translate_statement(statement)
        cur = self._connection.cursor(row_factory=dict_row)
        cur.executemany(translated, rows)
        return PostgresCursorCompat(self._connection, cur, translated)

    def executescript(self, script: str):
        cursor = None
        for statement in _split_script(script):
            cursor = self.execute(statement)
        return cursor


@contextmanager
def _schema_connection(schema: str):
    conn = psycopg.connect(database_url(), row_factory=dict_row)
    try:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
        yield PostgresConnectionCompat(conn, schema)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_schema(schema: str) -> None:
    with psycopg.connect(database_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))


def drop_portfolio_schema(user_id: int, schema_name: str) -> bool:
    schema = _validate_portfolio_schema(user_id, schema_name)
    with psycopg.connect(database_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name=%s",
                (schema,),
            )
            existed = cur.fetchone() is not None
            cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
    return existed


def reset_portfolio_schema(user_id: int, schema_name: str) -> bool:
    schema = _validate_portfolio_schema(user_id, schema_name)
    existed = drop_portfolio_schema(user_id, schema)
    _ensure_schema(schema)
    return existed


def drop_user_schema(user_id: int) -> bool:
    """Drop every portfolio schema owned by a user, including the legacy default."""
    prefix = user_schema(user_id)
    with psycopg.connect(database_url(), autocommit=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name=%s OR schema_name LIKE %s",
                (prefix, prefix + "_portfolio_%"),
            )
            schemas = [row["schema_name"] for row in cur.fetchall()]
            for schema_name in schemas:
                _validate_portfolio_schema(user_id, schema_name)
                cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name)))
    return bool(schemas)


class PostgresPortfolioStore(PortfolioStore):
    """PortfolioStore contract backed by one isolated PostgreSQL schema per portfolio."""

    def __init__(self, user_id: int, schema_name: str | None = None) -> None:
        self.user_id = int(user_id)
        self.schema = _validate_portfolio_schema(
            self.user_id,
            schema_name or user_schema(self.user_id),
        )
        # ``path`` remains informational for code/tests that expose the backing
        # persistence location. It is never opened as a filesystem path here.
        self.path = Path(f"/{self.schema}.postgres")
        _ensure_schema(self.schema)
        self.initialize()

    @contextmanager
    def connect(self):
        with _schema_connection(self.schema) as db:
            yield db


class PostgresAuthStore:
    """PostgreSQL auth store preserving QPort's existing auth contract."""

    def __init__(self) -> None:
        self.schema = AUTH_SCHEMA
        self.path = Path("/qport_auth.postgres")
        self.user_data_dir = Path("/postgres-schemas")
        _ensure_schema(self.schema)
        self.initialize()

    @contextmanager
    def connect(self):
        with _schema_connection(self.schema) as db:
            yield db

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('USER','ADMIN')),
                    password_hash TEXT,
                    active_portfolio_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_qport_users_username_ci
                    ON users (LOWER(username));

                CREATE TABLE IF NOT EXISTS portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    schema_name TEXT NOT NULL UNIQUE,
                    is_default INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_portfolios_user_name_ci
                    ON portfolios(user_id, LOWER(name));
                CREATE UNIQUE INDEX IF NOT EXISTS idx_portfolios_one_default
                    ON portfolios(user_id) WHERE is_default=1;
                CREATE INDEX IF NOT EXISTS idx_portfolios_user
                    ON portfolios(user_id, id);

                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
                """
            )
            user_columns = {
                row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()
            }
            if "active_portfolio_id" not in user_columns:
                db.execute("ALTER TABLE users ADD COLUMN active_portfolio_id INTEGER")

            admin = db.execute("SELECT id FROM users WHERE role='ADMIN' LIMIT 1").fetchone()
            if admin is None:
                password = str(os.environ.get("QPORT_ADMIN_PASSWORD") or "").strip()
                if not password:
                    if os.environ.get("VERCEL"):
                        raise RuntimeError(
                            "QPORT_ADMIN_PASSWORD is required for the first Vercel deployment."
                        )
                    password = DEFAULT_ADMIN_PASSWORD
                now = _iso()
                db.execute(
                    "INSERT INTO users(username,role,password_hash,created_at,updated_at) VALUES (?,?,?,?,?)",
                    (DEFAULT_ADMIN_USERNAME, "ADMIN", _hash_password(password), now, now),
                )
        with self.connect() as db:
            existing_users = db.execute(
                "SELECT id FROM users WHERE role='USER' ORDER BY id"
            ).fetchall()
        for row in existing_users:
            self.ensure_default_portfolio(int(row["id"]))
        self.cleanup_expired_sessions()

    @staticmethod
    def normalize_username(username: str) -> str:
        from .auth import AuthStore

        return AuthStore.normalize_username(username)

    @staticmethod
    def _public_user(row) -> dict | None:
        if row is None:
            return None
        data = dict(row)
        return {
            "id": int(data["id"]),
            "username": data["username"],
            "role": data["role"],
            "active_portfolio_id": (
                int(data["active_portfolio_id"])
                if data.get("active_portfolio_id") is not None
                else None
            ),
            "created_at": data["created_at"],
        }

    @staticmethod
    def _public_portfolio(row) -> dict | None:
        if row is None:
            return None
        data = dict(row)
        return {
            "id": int(data["id"]),
            "user_id": int(data["user_id"]),
            "name": data["name"],
            "schema_name": data["schema_name"],
            "is_default": bool(data["is_default"]),
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
        }

    @staticmethod
    def normalize_portfolio_name(name: str) -> str:
        value = " ".join(str(name or "").strip().split())
        if not value:
            raise AuthError("PORTFOLIO_NAME_REQUIRED", "Portfolio name is required.", "name")
        if len(value) > 60:
            raise AuthError("PORTFOLIO_NAME_TOO_LONG", "Portfolio name must be at most 60 characters.", "name")
        return value

    def ensure_default_portfolio(self, user_id: int) -> dict:
        user_id = int(user_id)
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM portfolios WHERE user_id=? AND is_default=1 LIMIT 1",
                (user_id,),
            ).fetchone()
            if row is None:
                now = _iso()
                db.execute(
                    """
                    INSERT INTO portfolios(user_id,name,schema_name,is_default,created_at,updated_at)
                    VALUES (?,?,?,1,?,?)
                    ON CONFLICT DO NOTHING
                    """,
                    (user_id, DEFAULT_PORTFOLIO_NAME, user_schema(user_id), now, now),
                )
                row = db.execute(
                    "SELECT * FROM portfolios WHERE user_id=? AND is_default=1 LIMIT 1",
                    (user_id,),
                ).fetchone()
            user = db.execute(
                "SELECT active_portfolio_id FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
            if user and user.get("active_portfolio_id") is None:
                db.execute(
                    "UPDATE users SET active_portfolio_id=?,updated_at=? WHERE id=?",
                    (int(row["id"]), _iso(), user_id),
                )
        return self._public_portfolio(row)

    def list_portfolios(self, user_id: int) -> list[dict]:
        self.ensure_default_portfolio(user_id)
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM portfolios WHERE user_id=? ORDER BY is_default DESC, LOWER(name), id",
                (int(user_id),),
            ).fetchall()
        return [self._public_portfolio(row) for row in rows]

    def portfolio_for_user(self, user_id: int, portfolio_id: int) -> dict | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM portfolios WHERE id=? AND user_id=?",
                (int(portfolio_id), int(user_id)),
            ).fetchone()
        return self._public_portfolio(row)

    def active_portfolio(self, user_id: int) -> dict:
        default = self.ensure_default_portfolio(user_id)
        with self.connect() as db:
            user = db.execute(
                "SELECT active_portfolio_id FROM users WHERE id=?",
                (int(user_id),),
            ).fetchone()
        active_id = user.get("active_portfolio_id") if user else None
        active = self.portfolio_for_user(user_id, int(active_id)) if active_id is not None else None
        if active is None:
            self.select_portfolio(user_id, default["id"])
            return default
        return active

    def create_portfolio(self, user_id: int, name: str) -> dict:
        import secrets

        user_id = int(user_id)
        name = self.normalize_portfolio_name(name)
        if len(self.list_portfolios(user_id)) >= MAX_PORTFOLIOS_PER_USER:
            raise AuthError(
                "PORTFOLIO_LIMIT_REACHED",
                f"Each account may have at most {MAX_PORTFOLIOS_PER_USER} portfolios.",
                "name",
            )
        schema_name = portfolio_schema(user_id, secrets.token_hex(6))
        now = _iso()
        try:
            with self.connect() as db:
                cur = db.execute(
                    """
                    INSERT INTO portfolios(user_id,name,schema_name,is_default,created_at,updated_at)
                    VALUES (?,?,?,0,?,?)
                    """,
                    (user_id, name, schema_name, now, now),
                )
                row = db.execute("SELECT * FROM portfolios WHERE id=?", (int(cur.lastrowid),)).fetchone()
        except psycopg.IntegrityError as exc:
            raise AuthError("PORTFOLIO_NAME_TAKEN", "A portfolio with this name already exists.", "name") from exc
        try:
            PostgresPortfolioStore(user_id, schema_name)
        except Exception:
            with self.connect() as db:
                db.execute("DELETE FROM portfolios WHERE id=? AND user_id=?", (int(row["id"]), user_id))
            drop_portfolio_schema(user_id, schema_name)
            raise
        return self._public_portfolio(row)

    def rename_portfolio(self, user_id: int, portfolio_id: int, name: str) -> dict:
        name = self.normalize_portfolio_name(name)
        current = self.portfolio_for_user(user_id, portfolio_id)
        if current is None:
            raise AuthError("PORTFOLIO_NOT_FOUND", "Portfolio does not exist.", "portfolio_id")
        try:
            with self.connect() as db:
                db.execute(
                    "UPDATE portfolios SET name=?,updated_at=? WHERE id=? AND user_id=?",
                    (name, _iso(), int(portfolio_id), int(user_id)),
                )
                row = db.execute("SELECT * FROM portfolios WHERE id=?", (int(portfolio_id),)).fetchone()
        except psycopg.IntegrityError as exc:
            raise AuthError("PORTFOLIO_NAME_TAKEN", "A portfolio with this name already exists.", "name") from exc
        return self._public_portfolio(row)

    def select_portfolio(self, user_id: int, portfolio_id: int) -> dict:
        row = self.portfolio_for_user(user_id, portfolio_id)
        if row is None:
            raise AuthError("PORTFOLIO_NOT_FOUND", "Portfolio does not exist.", "portfolio_id")
        with self.connect() as db:
            db.execute(
                "UPDATE users SET active_portfolio_id=?,updated_at=? WHERE id=?",
                (int(portfolio_id), _iso(), int(user_id)),
            )
        return row

    def delete_portfolio(self, user_id: int, portfolio_id: int) -> dict:
        row = self.portfolio_for_user(user_id, portfolio_id)
        if row is None:
            raise AuthError("PORTFOLIO_NOT_FOUND", "Portfolio does not exist.", "portfolio_id")
        if row["is_default"]:
            raise AuthError(
                "DEFAULT_PORTFOLIO_DELETE_FORBIDDEN",
                "The default portfolio cannot be deleted. Clear its data instead.",
                "portfolio_id",
            )
        default = self.ensure_default_portfolio(user_id)
        with self.connect() as db:
            db.execute(
                "UPDATE users SET active_portfolio_id=?,updated_at=? WHERE id=? AND active_portfolio_id=?",
                (default["id"], _iso(), int(user_id), int(portfolio_id)),
            )
            db.execute(
                "DELETE FROM portfolios WHERE id=? AND user_id=?",
                (int(portfolio_id), int(user_id)),
            )
        removed = drop_portfolio_schema(user_id, row["schema_name"])
        return {**row, "portfolio_data_removed": removed, "next_active_portfolio_id": default["id"]}

    def user_by_username(self, username: str) -> dict | None:
        try:
            username = self.normalize_username(username)
        except AuthError:
            return None
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM users WHERE LOWER(username)=LOWER(?)",
                (username,),
            ).fetchone()
        return dict(row) if row else None

    def user_by_id(self, user_id: int) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM users WHERE id=?", (int(user_id),)).fetchone()
        return dict(row) if row else None

    def register(self, username: str) -> dict:
        username = self.normalize_username(username)
        if username.lower() == DEFAULT_ADMIN_USERNAME.lower():
            raise AuthError("USERNAME_RESERVED", "That username is reserved.", "username")
        now = _iso()
        try:
            with self.connect() as db:
                cur = db.execute(
                    "INSERT INTO users(username,role,password_hash,created_at,updated_at) VALUES (?, 'USER', NULL, ?, ?)",
                    (username, now, now),
                )
                user_id = int(cur.lastrowid)
                row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        except psycopg.IntegrityError as exc:
            if "idx_qport_users_username_ci" in str(exc) or "username" in str(exc).lower():
                raise AuthError("USERNAME_TAKEN", "Username is already registered.", "username") from exc
            raise
        # Preserve the legacy user schema as the default portfolio so existing
        # data migrates without copy/rewrite operations.
        PostgresPortfolioStore(int(row["id"]))
        self.ensure_default_portfolio(int(row["id"]))
        return self._public_user(self.user_by_id(int(row["id"])))

    def login(self, username: str, password: str | None = None) -> tuple[dict, str]:
        username = self.normalize_username(username)
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM users WHERE LOWER(username)=LOWER(?)",
                (username,),
            ).fetchone()
        if row is None:
            raise AuthError("USER_NOT_REGISTERED", "Username is not registered.", "username")
        if row["role"] == "ADMIN" and not _verify_password(str(password or ""), row["password_hash"]):
            raise AuthError("INVALID_ADMIN_PASSWORD", "Admin password is incorrect.", "password")
        token = self.create_session(int(row["id"]))
        return self._public_user(row), token

    def create_session(self, user_id: int) -> str:
        import secrets
        from datetime import timedelta

        token = secrets.token_urlsafe(32)
        now = _now()
        expires = now + timedelta(days=SESSION_DAYS)
        with self.connect() as db:
            db.execute(
                "INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES (?,?,?,?)",
                (_token_hash(token), int(user_id), _iso(now), _iso(expires)),
            )
        return token

    def authenticate(self, token: str | None) -> dict | None:
        if not token:
            return None
        with self.connect() as db:
            row = db.execute(
                """
                SELECT u.* FROM sessions s
                JOIN users u ON u.id=s.user_id
                WHERE s.token_hash=? AND s.expires_at>?
                """,
                (_token_hash(token), _iso()),
            ).fetchone()
        return self._public_user(row)

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))

    def cleanup_expired_sessions(self) -> int:
        with self.connect() as db:
            cur = db.execute("DELETE FROM sessions WHERE expires_at<=?", (_iso(),))
            return max(0, int(cur.rowcount or 0))

    def list_users(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM users ORDER BY role DESC, LOWER(username)"
            ).fetchall()
        return [self._public_user(row) for row in rows]

    def portfolio_schema(self, user_id: int) -> str:
        return user_schema(int(user_id))

    def portfolio_db_path(self, user_id: int) -> Path:
        # Compatibility only. Vercel runtime uses ``PostgresPortfolioStore``
        # directly and never opens this as a local SQLite file.
        return Path(f"/{self.portfolio_schema(user_id)}.postgres")

    def delete_user(self, user_id: int) -> dict:
        row = self.user_by_id(user_id)
        if row is None:
            raise AuthError("USER_NOT_FOUND", "User does not exist.", "user_id")
        if row["role"] == "ADMIN":
            raise AuthError("ADMIN_DELETE_FORBIDDEN", "The admin account cannot be removed.", "user_id")
        removed_data = drop_user_schema(int(row["id"]))
        with self.connect() as db:
            db.execute("DELETE FROM users WHERE id=?", (int(row["id"]),))
        return {
            "ok": True,
            "user": self._public_user(row),
            "portfolio_data_removed": removed_data,
            "persistence": "POSTGRESQL_SCHEMA",
        }

    def change_admin_password(self, admin_id: int, current_password: str, new_password: str) -> dict:
        row = self.user_by_id(admin_id)
        if row is None or row["role"] != "ADMIN":
            raise AuthError("ADMIN_REQUIRED", "Admin access is required.")
        if not _verify_password(str(current_password or ""), row["password_hash"]):
            raise AuthError("INVALID_ADMIN_PASSWORD", "Current admin password is incorrect.", "current_password")
        new_password = str(new_password or "")
        if len(new_password) < 6 or len(new_password) > 128:
            raise AuthError("INVALID_NEW_PASSWORD", "New password must be 6-128 characters.", "new_password")
        with self.connect() as db:
            db.execute(
                "UPDATE users SET password_hash=?,updated_at=? WHERE id=?",
                (_hash_password(new_password), _iso(), int(admin_id)),
            )
            db.execute("DELETE FROM sessions WHERE user_id=?", (int(admin_id),))
        return {"ok": True, "message": "Admin password updated. Please sign in again."}

    def reset_fresh_namespace(self) -> None:
        if os.environ.get("QPORT_ALLOW_DATABASE_RESET") != "1":
            raise RuntimeError("Set QPORT_ALLOW_DATABASE_RESET=1 before destructive PostgreSQL reset.")
        with psycopg.connect(database_url(), autocommit=True) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE %s",
                    (f"{USER_SCHEMA_PREFIX}%",),
                )
                schemas = [row["schema_name"] for row in cur.fetchall()]
                for schema_name in schemas:
                    cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name)))
                cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(AUTH_SCHEMA)))
        _ensure_schema(AUTH_SCHEMA)
        self.initialize()
