from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_portfolio_exposes_professional_fund_manager_review():
    page = (FRONTEND / "pages" / "PortfolioPage.jsx").read_text(encoding="utf-8")
    review = (FRONTEND / "components" / "FundManagerReview.jsx").read_text(encoding="utf-8")
    assert "FundManagerReview" in page
    assert "fund-manager-review.css" in page
    assert "Professional portfolio review" in review
    assert "Fund manager review" in review
    assert "Manager commentary" in review
    assert "Monitoring priorities" in review


def test_review_aggregates_portfolio_risk_performance_income_and_operations():
    source = (FRONTEND / "components" / "FundManagerReview.jsx").read_text(encoding="utf-8")
    for token in (
        "dashboard.portfolio",
        "dashboard.risk",
        "dashboard.performance_summary",
        "dashboard.market_data",
        "getPortfolioOperations",
        "tax_lots",
        "exceptions",
        "cash_dividend_tax",
        "net_dividend_income",
        "official_snapshot_count",
        "return_observations",
        "largest_risk_contribution",
        "daily_cvar_95",
    ):
        assert token in source


def test_review_reduces_confidence_when_evidence_is_not_ready():
    source = (FRONTEND / "components" / "FundManagerReview.jsx").read_text(encoding="utf-8")
    assert "coverage >= 0.90" in source
    assert "returnObs >= 20" in source
    assert "snapshots >= 20" in source
    assert "EVIDENCE BUILDING" in source
    assert "Risk conclusions remain provisional" in source
    assert "Tracked performance is still immature" in source


def test_review_is_monitoring_only_not_an_auto_trade_surface():
    source = (FRONTEND / "components" / "FundManagerReview.jsx").read_text(encoding="utf-8")
    assert "It does not create trades." in source
    assert "automatic sell rule" in source
    assert "Monitoring priorities" in source
    assert "createPortfolioTransaction" not in source
    assert "updatePortfolioTransaction" not in source
    assert "deletePortfolioTransaction" not in source


def test_review_uses_readable_non_tiny_typography():
    css = (FRONTEND / "fund-manager-review.css").read_text(encoding="utf-8")
    assert "font-size: 13.5px" in css
    assert "font-size: 15px" in css
    assert "font-size: 12.5px" in css
    assert "order: 35" in css
