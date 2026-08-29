from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_risk_page_does_not_render_valuation_section():
    risk = (ROOT / "frontend" / "src" / "pages" / "RiskPage.jsx").read_text(encoding="utf-8")
    assert "risk-valuation-section" not in risk
    assert "getValuationReports" not in risk


def test_valuation_page_explains_models_and_database_source():
    page = (ROOT / "frontend" / "src" / "pages" / "ValuationPage.jsx").read_text(encoding="utf-8")
    # Pure-Vietnamese narrative (task 043): no raw English model jargon exposed.
    assert "Owner Earnings" not in page
    assert "Reverse DCF" not in page
    # Vietnamese explanations of the valuation models are present.
    assert "Lợi nhuận Thực" in page
    assert "Kịch bản" in page
    assert "Chiết khấu" in page
    assert "fallback" not in page.lower()


def test_capital_allocation_uncertainty_is_explicit_in_ui():
    page = (ROOT / "frontend" / "src" / "pages" / "ValuationPage.jsx").read_text(encoding="utf-8")
    assert "UNCERTAIN" in page
    assert "Chưa xác minh" in page
    assert "N/A ·" in page
    assert "chưa giải thích" in page
