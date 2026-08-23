from __future__ import annotations

import sys
from pathlib import Path

import portfolio.vnstock_isolated as vi


def test_vnstock_worker_can_use_configured_external_python(tmp_path, monkeypatch):
    worker = tmp_path / "fake_worker.py"
    worker.write_text(
        "import json,sys\n"
        "req=json.loads(sys.stdin.read())\n"
        "print(json.dumps({'status':'success','provider':'vnstock','api_variant':'fake_reference','python_version':sys.version.split()[0],'data':[{'task':req['task']}] }))\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("QPORT_VNSTOCK_PYTHON", sys.executable)
    monkeypatch.setattr(vi, "_WORKER_PATH", worker)
    vi._HEALTH_CACHE.clear()

    result = vi.run_vnstock_task("events", {"symbols": ["FPT"], "start": "2026-01-01", "end": "2026-12-31"}, max_attempts=1)
    assert result["provider"] == "vnstock"
    assert result["data"][0]["task"] == "events"
    assert Path(result["worker_python"]).resolve() == Path(sys.executable).resolve()

    health = vi.vnstock_runtime_health("reference", cache_seconds=0)
    assert health["available"] is True
    assert health["api_variant"] == "fake_reference"
    assert Path(health["worker_python"]).resolve() == Path(sys.executable).resolve()


def test_vnstock_health_rejects_missing_configured_interpreter(tmp_path, monkeypatch):
    missing = tmp_path / "missing-python.exe"
    monkeypatch.setenv("QPORT_VNSTOCK_PYTHON", str(missing))
    vi._HEALTH_CACHE.clear()
    health = vi.vnstock_runtime_health("reference", cache_seconds=0)
    assert health["available"] is False
    assert "does not exist" in str(health["error"])
    assert str(missing) in str(health["worker_python"])
