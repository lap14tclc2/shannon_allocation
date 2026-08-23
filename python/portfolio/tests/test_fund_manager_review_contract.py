from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_portfolio_exposes_concise_professional_fund_manager_review():
    page = (FRONTEND / "pages" / "PortfolioPage.jsx").read_text(encoding="utf-8")
    review = (FRONTEND / "components" / "FundManagerReview.jsx").read_text(encoding="utf-8")
    assert "FundManagerReview" in page
    assert "fund-manager-review.css" in page
    assert "Experienced portfolio-manager view" in review
    assert "Fund manager review" in review
    assert "Manager view" in review
    assert "What I would watch next" in review
    assert "See detailed risk analysis" in review
    assert "See performance history" in review


def test_review_uses_only_evidence_needed_for_professional_judgment():
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
        "dividend_income",
    ):
        assert token in source

    # Detailed quant/operations belong on Risk or advanced operational routes,
    # not in the normal-user manager review.
    for advanced_or_operational_token in (
        "getPortfolioOperations",
        "tax_lots",
        "cash_dividend_tax",
        "daily_cvar_95",
        "equity_hhi",
        "erc_reference_weights",
        "ReviewRow",
        "fm-review-grid",
        "covariance",
    ):
        assert advanced_or_operational_token not in source


def test_review_reduces_confidence_when_evidence_is_not_ready():
    source = (FRONTEND / "components" / "FundManagerReview.jsx").read_text(encoding="utf-8")
    assert "coverage >= 0.90" in source
    assert "observations >= 20" in source
    assert "snapshots >= 20" in source
    assert "EVIDENCE BUILDING" in source
    assert "market-risk evidence is still maturing" in source
    assert "Tracked performance is still young" in source


def test_review_is_judgment_and_monitoring_only_not_an_auto_trade_surface():
    source = (FRONTEND / "components" / "FundManagerReview.jsx").read_text(encoding="utf-8")
    assert "Portfolio oversight only" in source
    assert "investment thesis" in source
    assert "What I would watch next" in source
    assert 'href="/risk"' in source
    assert 'href="/performance"' in source
    assert "createPortfolioTransaction" not in source
    assert "updatePortfolioTransaction" not in source
    assert "deletePortfolioTransaction" not in source


def test_review_uses_readable_simple_three_lens_layout():
    css = (FRONTEND / "fund-manager-review.css").read_text(encoding="utf-8")
    assert "font-size: 13.5px" in css
    assert "font-size: 15px" in css
    assert "font-size: 16px" in css
    assert "order: 35" in css
    assert ".fm-manager-verdict" in css
    assert ".fm-manager-lenses" in css
    assert "grid-template-columns: repeat(3" in css
    assert ".fm-review-grid" not in css
