from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from portfolio.risk import portfolio_risk

REPO_DIR = Path(__file__).resolve().parents[3]
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def test_risk_engine_produces_real_portfolio_evidence_when_history_is_sufficient():
    start = date(2025, 1, 1)
    histories = {"AAA": [], "BBB": []}
    price_a = 100.0
    price_b = 80.0
    for i in range(320):
        day = (start + timedelta(days=i)).isoformat()
        # Deterministic non-flat paths with related but non-identical movement.
        price_a *= 1.0 + (0.004 if i % 5 in {0, 1, 2} else -0.0025)
        price_b *= 1.0 + (0.003 if i % 7 in {0, 1, 2, 3} else -0.002)
        histories["AAA"].append({"trading_date": day, "close": price_a})
        histories["BBB"].append({"trading_date": day, "close": price_b})

    positions = [
        {"symbol": "AAA", "market_value": 600_000_000, "weight": 0.60},
        {"symbol": "BBB", "market_value": 400_000_000, "weight": 0.40},
    ]
    risk = portfolio_risk(positions, histories)

    assert risk["status"] == "VALID"
    assert risk["quality"]["coverage_weight"] == 1.0
    assert risk["volatility_63"] is not None
    assert risk["volatility_252"] is not None
    assert risk["average_correlation"] is not None
    assert risk["diversification_ratio"] is not None
    assert risk["daily_var_95"] is not None
    assert risk["daily_cvar_95"] is not None
    assert risk["return_observations"] >= 20
    assert set(risk["risk_contributions"]) == {"AAA", "BBB"}


def test_portfolio_assessment_exposes_backend_risk_and_performance_evidence():
    source = (FRONTEND_SRC / "components" / "PortfolioAssessmentEnhancer.jsx").read_text(encoding="utf-8")
    for token in (
        "Risk coverage",
        "Portfolio return observations",
        "Effective / actual positions",
        "Equity HHI",
        "Diversification ratio",
        "63D / 252D volatility",
        "Average correlation",
        "Daily VaR / CVaR 95%",
        "Since-inception TWR",
        "Current / max drawdown",
        "Performance history",
    ):
        assert token in source
    assert "createPortal" in source
    assert "portfolio-assessment-card" in source


def test_received_dividend_section_disappears_when_ledger_has_no_receipts():
    panel = (FRONTEND_SRC / "components" / "ReceivedDividendsPanel.jsx").read_text(encoding="utf-8")
    page = (FRONTEND_SRC / "pages" / "PortfolioPage.jsx").read_text(encoding="utf-8")
    assert "if (loading) return null" in panel
    assert "if (!error && groups.length === 0) return null" in panel
    assert 'className="page portfolio-received-supplement"' in panel
    assert 'className="page portfolio-received-supplement"' not in page


def test_performance_history_derives_multiple_windows_and_drawdown_anatomy():
    source = (FRONTEND_SRC / "components" / "PerformanceHistoryPanel.jsx").read_text(encoding="utf-8")
    wrapper = (FRONTEND_SRC / "pages" / "PerformancePageV2.jsx").read_text(encoding="utf-8")
    client = (FRONTEND_SRC / "entry-client.jsx").read_text(encoding="utf-8")
    ssr = (FRONTEND_SRC / "ssr-entry.jsx").read_text(encoding="utf-8")

    assert "chainReturn" in source
    assert "annualizedVol" in source
    assert "drawdownEpisode" in source
    assert "monthlyReturns" in source
    for window in ("'5D'", "'21D'", "'63D'", "'126D'", "'252D'"):
        assert window in source
    assert "Peak before max drawdown" in source
    assert "Recovery date" in source
    assert "Current underwater duration" in source
    assert "Recent monthly TWR" in source
    assert "hasTrackedSeries" in wrapper
    assert "PerformancePageV2.jsx" in client
    assert "PerformancePageV2.jsx" in ssr


def test_existing_risk_page_is_not_only_a_summary_card():
    source = (FRONTEND_SRC / "pages" / "RiskPage.jsx").read_text(encoding="utf-8")
    for token in (
        "Risk interpretation",
        "Concentration & diversification",
        "Tail-risk diagnostics",
        "Risk contribution HHI",
        "Historical daily CVaR 95%",
        "Downside volatility",
        "ERC capital reference",
        "Data readiness",
    ):
        assert token in source
