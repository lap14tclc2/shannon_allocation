from __future__ import annotations

from pathlib import Path

import pytest

from portfolio.auth import AuthError, AuthStore, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.storage import PortfolioStore


def test_default_admin_requires_default_password(tmp_path):
    auth = AuthStore(tmp_path / "auth.sqlite3", tmp_path / "users")
    with pytest.raises(AuthError) as exc:
        auth.login(DEFAULT_ADMIN_USERNAME, "wrong")
    assert exc.value.code == "INVALID_ADMIN_PASSWORD"

    admin, token = auth.login(DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD)
    assert admin["role"] == "ADMIN"
    assert auth.authenticate(token)["username"] == DEFAULT_ADMIN_USERNAME


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
    admin, token = auth.login("admin", "abc123")

    with pytest.raises(AuthError) as exc:
        auth.change_admin_password(admin["id"], "bad", "new-pass-123")
    assert exc.value.code == "INVALID_ADMIN_PASSWORD"

    auth.change_admin_password(admin["id"], "abc123", "new-pass-123")
    assert auth.authenticate(token) is None

    with pytest.raises(AuthError):
        auth.login("admin", "abc123")
    relogin, new_token = auth.login("admin", "new-pass-123")
    assert relogin["role"] == "ADMIN"
    assert auth.authenticate(new_token)["id"] == admin["id"]


def test_admin_account_cannot_be_deleted(tmp_path):
    auth = AuthStore(tmp_path / "auth.sqlite3", tmp_path / "users")
    admin = auth.user_by_username("admin")
    with pytest.raises(AuthError) as exc:
        auth.delete_user(admin["id"])
    assert exc.value.code == "ADMIN_DELETE_FORBIDDEN"
