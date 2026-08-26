from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_risk_page_does_not_render_valuation_section():
    risk = (ROOT / "frontend" / "src" / "pages" / "RiskPage.jsx").read_text(encoding="utf-8")
    assert "risk-valuation-section" not in risk
    assert "getValuationReports" not in risk


def test_valuation_page_explains_models_and_database_source():
    page = (ROOT / "frontend" / "src" / "pages" / "ValuationPage.jsx").read_text(encoding="utf-8")
    assert "Owner Earnings" in page
    assert "Ba kịch bản DCF" in page
    assert "Reverse DCF" in page
    assert "Finance Data" in page
    assert "fallback" not in page.lower()
