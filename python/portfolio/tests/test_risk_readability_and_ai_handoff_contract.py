from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_risk_page_is_plain_language_first_with_progressive_disclosure():
    page = (FRONTEND / "pages" / "RiskPage.jsx").read_text(encoding="utf-8")

    for phrase in (
        "Is the portfolio too concentrated?",
        "Do the holdings move together?",
        "Is price movement getting stronger?",
        "How bad have bad days been?",
        "Which holding drives the most risk?",
        "Can I trust these conclusions yet?",
        "Who drives your risk?",
        "Technical details & methodology",
    ):
        assert phrase in page

    assert "<details className=\"card risk-technical-details\">" in page
    assert "Risk Score" not in page
    assert "73/100" not in page


def test_technical_risk_evidence_and_erc_are_preserved_but_advanced():
    page = (FRONTEND / "pages" / "RiskPage.jsx").read_text(encoding="utf-8")

    for phrase in (
        "Equity HHI",
        "Historical daily VaR 95%",
        "Historical daily CVaR 95%",
        "Downside volatility",
        "ERC capital reference",
        "diagnostic capital reference only",
        "does not set portfolio targets",
    ):
        assert phrase in page


def test_risk_readability_styles_are_loaded_after_general_accessibility():
    entry = (FRONTEND / "entry-client.jsx").read_text(encoding="utf-8")
    assert "import './risk-readable.css';" in entry
    assert entry.index("import './accessibility-polish.css';") < entry.index("import './risk-readable.css';")

    css = (FRONTEND / "risk-readable.css").read_text(encoding="utf-8")
    assert ".risk-plain-grid" in css
    assert ".risk-technical-details" in css
    assert "font-size: 14px;" in css
    assert "var(--text-secondary)" in css


def test_ai_working_context_exists_and_documents_non_negotiable_boundaries():
    handoff = (REPO / "AI_WORKING_CONTEXT.md").read_text(encoding="utf-8")

    for phrase in (
        "Buy & Hold Portfolio Information System",
        "only explicit effective ledger events change holdings or cash",
        "diagnostic_reference_only",
        "ERC must not",
        "one canonical provider per refresh",
        "550 calendar days",
        "Fund Manager Review",
        "qport-appearance-v1",
        "Known limitations / future work",
        "Recommended reading order for a new AI session",
    ):
        assert phrase in handoff
