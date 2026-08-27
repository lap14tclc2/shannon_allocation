from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from portfolio.finance_catalog import _tcbs_universe_config  # noqa: E402


def test_tcbs_universe_uses_environment_credentials(monkeypatch):
    monkeypatch.setenv("TCBS_UNIVERSE_URL", "https://example.test/universe")
    monkeypatch.setenv("TCBS_BEARER_TOKEN", "test-token")

    url, headers = _tcbs_universe_config()

    assert url == "https://example.test/universe"
    assert headers["Authorization"] == "Bearer test-token"


@pytest.mark.parametrize("name", ["TCBS_UNIVERSE_URL", "TCBS_BEARER_TOKEN"])
def test_tcbs_universe_requires_both_environment_values(monkeypatch, name):
    monkeypatch.setenv("TCBS_UNIVERSE_URL", "https://example.test/universe")
    monkeypatch.setenv("TCBS_BEARER_TOKEN", "test-token")
    monkeypatch.delenv(name)

    with pytest.raises(RuntimeError):
        _tcbs_universe_config()
