from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_portfolio_exposes_concise_professional_fund_manager_review():
    page = (FRONTEND / "pages" / "PortfolioPage.jsx").read_text(encoding="utf-8")
    review = (FRONTEND / "components" / "FundManagerReview.jsx").read_text(encoding="utf-8")
    assert "FundManagerReview" in page
    assert "fund-manager-review.css" in page
    assert "Professional judgment" in review
    assert "Fund manager review" in review
    assert "Manager assessment" in review
    assert "What I would monitor" in review
    assert "View detailed risk analysis" in review


def test_review_uses_portfolio_level_evidence_without_becoming_a_metric_dashboard():
    source = (FRONTEND / "components" / "FundManagerReview.jsx").read_text(encoding="utf-8")
    for token in (
        "dashboard.portfolio",
        "dashboard.risk",
        "dashboard.performance_summary",
        "dashboard.market_data",
        "official_snapshot_count",
        "return_observations",
        "largest_risk_contribution",
        "current_drawdown",
    ):
        assert token in source

    for advanced_or_operational_token in (
        "getPortfolioOperations",
        "tax_lots",
        "cash_dividend_tax",
        "daily_cvar_95",
        "equity_hhi",
        "erc_reference_weights",
        "ReviewRow",
        "fm-review-grid",
    ):
        assert advanced_or_operational_token not in source


def test_review_reduces_confidence_when_evidence_is_not_ready():
    source = (FRONTEND / "components" / "FundManagerReview.jsx").read_text(encoding="utf-8")
    assert "coverage >= 0.90" in source
    assert "returnObs >= 20" in source
    assert "snapshots >= 20" in source
    assert "EVIDENCE BUILDING" in source
    assert "I would not make a strong risk judgment yet" in source
    assert "Performance history is still too short" in source


def test_review_is_judgment_and_monitoring_only_not_an_auto_trade_surface():
    source = (FRONTEND / "components" / "FundManagerReview.jsx").read_text(encoding="utf-8")
    assert "This review does not create BUY/SELL actions." in source
    assert "investment thesis" in source
    assert "What I would monitor" in source
    assert 'href="/risk"' in source
    assert "createPortfolioTransaction" not in source
    assert "updatePortfolioTransaction" not in source
    assert "deletePortfolioTransaction" not in source


def test_review_uses_readable_non_tiny_typography_and_simple_layout():
    css = (FRONTEND / "fund-manager-review.css").read_text(encoding="utf-8")
    assert "font-size: 14px" in css
    assert "font-size: 15px" in css
    assert "font-size: 12.5px" in css
    assert "order: 35" in css
    assert ".fm-manager-assessment" in css
    assert ".fm-manager-summary" in css
    assert ".fm-review-grid" not in css
