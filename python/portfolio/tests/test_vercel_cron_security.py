from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.index import ApiError, _require_cron_authorization  # noqa: E402


class _Request:
    def __init__(self, authorization: str | None = None) -> None:
        self.headers = {}
        if authorization is not None:
            self.headers["authorization"] = authorization


def test_cron_rejects_when_secret_is_missing(monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)

    with pytest.raises(ApiError) as exc:
        _require_cron_authorization(_Request())

    assert exc.value.status == 503
    assert exc.value.payload["code"] == "CRON_NOT_CONFIGURED"


def test_cron_rejects_invalid_bearer_token(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "expected-secret")

    with pytest.raises(ApiError) as exc:
        _require_cron_authorization(_Request("Bearer wrong-secret"))

    assert exc.value.status == 401
    assert exc.value.payload["code"] == "CRON_UNAUTHORIZED"


def test_cron_accepts_matching_bearer_token(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "expected-secret")

    _require_cron_authorization(_Request("Bearer expected-secret"))
