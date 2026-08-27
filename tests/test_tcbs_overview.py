from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from portfolio import finance_catalog  # noqa: E402


def test_tcbs_overview_uses_bearer_token_from_environment(monkeypatch):
    monkeypatch.setenv("TCBS_BEARER_TOKEN", "test-token")

    headers = finance_catalog._tcbs_overview_headers()

    assert headers["Authorization"] == "Bearer test-token"


def test_tcbs_overview_requires_local_token(monkeypatch):
    monkeypatch.delenv("TCBS_BEARER_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="TCBS_BEARER_TOKEN"):
        finance_catalog._tcbs_overview_headers()


def test_tcbs_overview_uses_ticker_endpoint(monkeypatch):
    monkeypatch.setenv("TCBS_BEARER_TOKEN", "test-token")
    calls = []

    def fake_url_json(url, **_kwargs):
        calls.append(url)
        return 200, '{"ticker":"VNM","exchange":"HOSE","industry":"Food & Beverage"}'

    monkeypatch.setattr(finance_catalog, "_url_json", fake_url_json)

    overview = finance_catalog._load_tcbs_overview("VNM")

    assert overview["exchange"] == "HOSE"
    assert calls == [
        "https://apipubaws.tcbs.com.vn/tcanalysis/v1/ticker/VNM/overview",
    ]
