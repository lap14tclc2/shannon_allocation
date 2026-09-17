from __future__ import annotations

import os

import pytest

from portfolio.automated_service import AutomatedPortfolioService
from portfolio.dividend_store import SqliteDividendService
from portfolio.domain import EventType, LedgerEvent
from portfolio.postgres import PostgresAuthStore, PostgresPortfolioStore


pytestmark = pytest.mark.skipif(
    not os.environ.get("QPORT_TEST_DATABASE_URL"),
    reason="QPORT_TEST_DATABASE_URL is required for the destructive PostgreSQL integration smoke to protect development data",
)


def test_postgres_auth_user_schema_and_operational_service(monkeypatch):
    test_db_url = os.environ.get("QPORT_TEST_DATABASE_URL")
    monkeypatch.setenv("DATABASE_URL", test_db_url)
    monkeypatch.setenv("QPORT_ALLOW_DATABASE_RESET", "1")
    monkeypatch.setenv("QPORT_ADMIN_PASSWORD", "ci-admin-password")

    auth = PostgresAuthStore()
    auth.reset_fresh_namespace()

    users = auth.list_users()
    assert len(users) == 1
    assert users[0]["role"] == "ADMIN"

    alice = auth.register("alice")
    bob = auth.register("bob")
    assert alice["id"] != bob["id"]

    logged_in, token = auth.login("ALICE")
    assert logged_in["id"] == alice["id"]
    assert auth.authenticate(token)["username"] == "alice"

    alice_store = PostgresPortfolioStore(alice["id"])
    service = AutomatedPortfolioService(store=alice_store)
    SqliteDividendService(alice_store, providers=[], stop_on_first_data=False)

    event_id = alice_store.append_event(
        LedgerEvent(
            event_type=EventType.CASH_DEPOSIT,
            event_date="2026-08-24",
            amount=1_000_000,
            note="postgres smoke",
            created_by="alice",
        )
    )
    assert event_id > 0
    assert len(alice_store.list_events()) == 1
    assert service.transactions()[0]["event_type"] == "CASH_DEPOSIT"

    bob_store = PostgresPortfolioStore(bob["id"])
    AutomatedPortfolioService(store=bob_store)
    assert bob_store.list_events() == []

    deleted = auth.delete_user(bob["id"])
    assert deleted["portfolio_data_removed"] is True
    assert auth.user_by_id(bob["id"]) is None

    auth.logout(token)
    assert auth.authenticate(token) is None
