from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from portfolio.auth import (
    AUTH_SECURITY_VERSION,
    MIN_ADMIN_PASSWORD_LENGTH,
    AuthError,
    AuthStore,
    DEFAULT_ADMIN_USERNAME,
    _hash_password,
)
from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.storage import PortfolioStore


def test_admin_requires_explicit_secure_bootstrap(tmp_path):
    auth = AuthStore(tmp_path / "auth.sqlite3", tmp_path / "users")
    assert auth.admin_configured() is False

    with pytest.raises(AuthError) as exc:
        auth.login(DEFAULT_ADMIN_USERNAME, "not-configured")
    assert exc.value.code == "ADMIN_NOT_CONFIGURED"

    password = "S3cure-admin-password!"
    auth.bootstrap_admin_password(password)
    assert auth.admin_configured() is True
    admin, token = auth.login(DEFAULT_ADMIN_USERNAME, password)
    assert admin["role"] == "ADMIN"
    assert auth.authenticate(token)["username"] == DEFAULT_ADMIN_USERNAME


def test_admin_bootstrap_rejects_weak_password(tmp_path):
    auth = AuthStore(tmp_path / "auth.sqlite3", tmp_path / "users")
    with pytest.raises(AuthError) as exc:
        auth.bootstrap_admin_password("short")
    assert exc.value.code == "INVALID_NEW_PASSWORD"
    assert MIN_ADMIN_PASSWORD_LENGTH >= 12


def test_security_version_migration_invalidates_pre_v2_admin_credentials_and_sessions(tmp_path):
    path = tmp_path / "auth.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                role TEXT NOT NULL,
                password_hash TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            """
        )
        db.execute(
            "INSERT INTO users(username,role,password_hash,created_at,updated_at) VALUES ('admin','ADMIN',?,'2026-01-01','2026-01-01')",
            (_hash_password("previously-configured-password"),),
        )
        db.execute(
            "INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES ('stale',1,'2026-01-01','2099-01-01')"
        )

    auth = AuthStore(path, tmp_path / "users")
    assert auth.admin_configured() is False
    with auth.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM sessions WHERE user_id=1").fetchone()[0] == 0
        version = db.execute("SELECT value FROM auth_meta WHERE key='security_version'").fetchone()[0]
    assert version == AUTH_SECURITY_VERSION


def test_normal_user_registers_unique_username_and_logs_in_without_password(tmp_path):
    auth = AuthStore(tmp_path / "auth.sqlite3", tmp_path / "users")
    alice = auth.register("alice")
    assert alice["role"] == "USER"

    with pytest.raises(AuthError) as exc:
        auth.register("ALICE")
    assert exc.value.code == "USERNAME_TAKEN"

    user, token = auth.login("Alice")
    assert user["id"] == alice["id"]
    assert auth.authenticate(token)["username"] == "alice"


def test_user_portfolio_databases_are_physically_isolated(tmp_path):
    auth = AuthStore(tmp_path / "auth.sqlite3", tmp_path / "users")
    alice = auth.register("alice")
    bob = auth.register("bob")

    alice_store = PortfolioStore(auth.portfolio_db_path(alice["id"]))
    bob_store = PortfolioStore(auth.portfolio_db_path(bob["id"]))
    alice_service = CorrectablePortfolioService(store=alice_store)
    bob_service = CorrectablePortfolioService(store=bob_store)

    alice_service.append_event(
        {"event_type":"CASH_DEPOSIT", "event_date":"2026-08-23", "amount":1_000_000},
        created_by="alice",
    )

    assert len(alice_service.transactions()) == 1
    assert alice_service.transactions()[0]["created_by"] == "alice"
    assert bob_service.transactions() == []
    assert alice_store.path != bob_store.path


def test_admin_delete_user_removes_sessions_and_portfolio_database(tmp_path):
    auth = AuthStore(tmp_path / "auth.sqlite3", tmp_path / "users")
    user = auth.register("delete-me")
    _, token = auth.login("delete-me")
    db_path = auth.portfolio_db_path(user["id"])
    PortfolioStore(db_path)
    assert db_path.exists()
    assert auth.authenticate(token) is not None

    result = auth.delete_user(user["id"])
    assert result["ok"] is True
    assert not db_path.exists()
    assert auth.authenticate(token) is None
    assert auth.user_by_id(user["id"]) is None


def test_admin_password_update_requires_current_password_and_invalidates_sessions(tmp_path):
    auth = AuthStore(tmp_path / "auth.sqlite3", tmp_path / "users")
    first = "S3cure-admin-password!"
    second = "Another-secure-pass!"
    auth.bootstrap_admin_password(first)
    admin, token = auth.login("admin", first)

    with pytest.raises(AuthError) as exc:
        auth.change_admin_password(admin["id"], "bad", second)
    assert exc.value.code == "INVALID_ADMIN_PASSWORD"

    auth.change_admin_password(admin["id"], first, second)
    assert auth.authenticate(token) is None

    with pytest.raises(AuthError):
        auth.login("admin", first)
    relogin, new_token = auth.login("admin", second)
    assert relogin["role"] == "ADMIN"
    assert auth.authenticate(new_token)["id"] == admin["id"]


def test_admin_account_cannot_be_deleted(tmp_path):
    auth = AuthStore(tmp_path / "auth.sqlite3", tmp_path / "users")
    admin = auth.user_by_username("admin")
    with pytest.raises(AuthError) as exc:
        auth.delete_user(admin["id"])
    assert exc.value.code == "ADMIN_DELETE_FORBIDDEN"
