from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_valuation_has_no_ticker_profiles_or_generic_company_fallbacks():
    api = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    engine = (ROOT / "python" / "portfolio" / "value_engine" / "engine.py").read_text(encoding="utf-8")

    assert "PROFILES =" not in api
    assert "PROFILES_META" not in engine
    assert "SYMBOL_DIAGNOSTICS" not in engine
    assert '"valuation_snapshot"' in api
    assert "VALUATION_SYMBOL_MISMATCH" in api
    assert "QualityStatus.SINGLE_SOURCE" in api


def test_valuation_bypasses_browser_and_vercel_cache():
    client = (ROOT / "frontend" / "src" / "lib" / "api.js").read_text(encoding="utf-8")
    vercel = (ROOT / "vercel.json").read_text(encoding="utf-8")

    valuation_function = client.split("export const getValuationReport", 1)[1].split("export async function", 1)[0]
    assert "getJSONCached" not in valuation_function
    assert "getJSON(" in valuation_function
    assert "cache: 'no-store'" in client
    assert '"private, no-store, max-age=0"' in vercel


def test_vercel_runtime_installs_live_fundamental_provider():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    worker = (ROOT / "python" / "portfolio" / "vnstock_isolated.py").read_text(encoding="utf-8")

    assert '"vnstock>=4.0,<5"' in pyproject
    assert 'task == "valuation_snapshot"' in worker
    assert '"symbol": symbol' in worker
    assert '"fetched_at"' in worker
