from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "abc123"
SESSION_DAYS = 30
PBKDF2_ITERATIONS = 200_000


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).isoformat(timespec="seconds")


def _hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str | None) -> bool:
    try:
        scheme, iterations, salt_hex, expected_hex = str(encoded or "").split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            str(password or "").encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), expected_hex)
    except Exception:
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


class AuthError(ValueError):
    def __init__(self, code: str, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.field = field

    def as_dict(self) -> dict:
        return {"error": str(self), "code": self.code, "field": self.field}


class AuthStore:
    """Small local auth database plus one isolated portfolio SQLite DB per user.

    The authenticated identity database is intentionally separate from portfolio
    databases. Normal users authenticate by unique username only. The built-in
    admin account requires a password. Deleting a normal user removes the auth
    row, active sessions and that user's entire portfolio database.

    The default storage namespace is ``python/data/auth-v1``. The previous
    single-user ``python/data/portfolio.sqlite3`` database is deliberately not
    reused, giving the authentication migration a fresh clean data namespace.
    Environment variables can override both locations for tests/deployment.
    """

    def __init__(self, path: str | Path | None = None, user_data_dir: str | Path | None = None) -> None:
        python_dir = Path(__file__).resolve().parents[1]
        namespace = Path(os.environ.get("QPORT_AUTH_NAMESPACE", python_dir / "data" / "auth-v1"))
        self.path = Path(path or os.environ.get("QPORT_AUTH_DB", namespace / "auth.sqlite3"))
        self.user_data_dir = Path(user_data_dir or os.environ.get("QPORT_USER_DATA_DIR", namespace / "users"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    role TEXT NOT NULL CHECK(role IN ('USER','ADMIN')),
                    password_hash TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

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
            admin = db.execute("SELECT id FROM users WHERE role='ADMIN' LIMIT 1").fetchone()
            if admin is None:
                now = _iso()
                db.execute(
                    "INSERT INTO users(username,role,password_hash,created_at,updated_at) VALUES (?,?,?,?,?)",
                    (DEFAULT_ADMIN_USERNAME, "ADMIN", _hash_password(DEFAULT_ADMIN_PASSWORD), now, now),
                )
        self.cleanup_expired_sessions()

    @staticmethod
    def normalize_username(username: str) -> str:
        value = str(username or "").strip()
        if not value:
            raise AuthError("USERNAME_REQUIRED", "Username is required.", "username")
        if not USERNAME_RE.fullmatch(value):
            raise AuthError(
                "INVALID_USERNAME",
                "Username may contain only letters, numbers, dot, underscore or dash (max 32 characters).",
                "username",
            )
        return value

    @staticmethod
    def _public_user(row) -> dict | None:
        if row is None:
            return None
        return {
            "id": int(row["id"]),
            "username": row["username"],
            "role": row["role"],
            "created_at": row["created_at"],
        }

    def user_by_username(self, username: str) -> dict | None:
        try:
            username = self.normalize_username(username)
        except AuthError:
            return None
        with self.connect() as db:
            row = db.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone()
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
                row = db.execute("SELECT * FROM users WHERE id=?", (int(cur.lastrowid),)).fetchone()
        except sqlite3.IntegrityError:
            raise AuthError("USERNAME_TAKEN", "Username is already registered.", "username")
        return self._public_user(row)

    def login(self, username: str, password: str | None = None) -> tuple[dict, str]:
        username = self.normalize_username(username)
        with self.connect() as db:
            row = db.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone()
        if row is None:
            raise AuthError("USER_NOT_REGISTERED", "Username is not registered.", "username")
        if row["role"] == "ADMIN" and not _verify_password(str(password or ""), row["password_hash"]):
            raise AuthError("INVALID_ADMIN_PASSWORD", "Admin password is incorrect.", "password")
        token = self.create_session(int(row["id"]))
        return self._public_user(row), token

    def create_session(self, user_id: int) -> str:
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
        now = _iso()
        with self.connect() as db:
            row = db.execute(
                """
                SELECT u.* FROM sessions s
                JOIN users u ON u.id=s.user_id
                WHERE s.token_hash=? AND s.expires_at>?
                """,
                (_token_hash(token), now),
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
            rows = db.execute("SELECT * FROM users ORDER BY role DESC, username COLLATE NOCASE").fetchall()
        return [self._public_user(row) for row in rows]

    def portfolio_db_path(self, user_id: int) -> Path:
        return self.user_data_dir / f"user-{int(user_id)}.sqlite3"

    def delete_user(self, user_id: int) -> dict:
        row = self.user_by_id(user_id)
        if row is None:
            raise AuthError("USER_NOT_FOUND", "User does not exist.", "user_id")
        if row["role"] == "ADMIN":
            raise AuthError("ADMIN_DELETE_FORBIDDEN", "The admin account cannot be removed.", "user_id")
        db_path = self.portfolio_db_path(int(row["id"]))
        with self.connect() as db:
            db.execute("DELETE FROM users WHERE id=?", (int(row["id"]),))
        removed_data = False
        if db_path.exists():
            db_path.unlink()
            removed_data = True
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(db_path) + suffix)
            if sidecar.exists():
                sidecar.unlink()
        return {"ok": True, "user": self._public_user(row), "portfolio_data_removed": removed_data}

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
            # Password rotation invalidates every other admin session.
            db.execute("DELETE FROM sessions WHERE user_id=?", (int(admin_id),))
        return {"ok": True, "message": "Admin password updated. Please sign in again."}

    def reset_fresh_namespace(self) -> None:
        """Destructive test/development helper. Never called automatically at runtime."""
        if self.path.exists():
            self.path.unlink()
        if self.user_data_dir.exists():
            shutil.rmtree(self.user_data_dir)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.initialize()
