from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_guide_is_written_for_normal_users_not_developers():
    source = (FRONTEND / "pages" / "GuidePage.jsx").read_text(encoding="utf-8")
    assert "Use QPort with confidence" in source
    assert "Start here" in source
    assert "What each page answers" in source
    assert "Common things you will do" in source
    assert "Understand the status words" in source
    assert "If something looks wrong" in source

    # Build/install instructions belong in README/docs, not the in-app normal-user guide.
    for developer_token in (
        "npm ci",
        "npm run build",
        "pip install",
        "python serve.py",
        "Institutional-lite daily workflow",
        "What Operations means",
        "NAV restatement",
    ):
        assert developer_token not in source


def test_guide_explains_actual_user_workflow_and_key_semantics():
    source = (FRONTEND / "pages" / "GuidePage.jsx").read_text(encoding="utf-8")
    for token in (
        "Position import",
        "Transactions",
        "Portfolio",
        "Performance",
        "Risk",
        "BUY",
        "SELL",
        "Received dividends",
        "READY",
        "BUILDING",
        "STALE / PARTIAL",
        "ERROR",
        "ERC is only an advanced diagnostic reference",
        "missing values are not zero",
    ):
        assert token in source


def test_guide_keeps_technical_integrity_rules_collapsed_and_optional():
    source = (FRONTEND / "pages" / "GuidePage.jsx").read_text(encoding="utf-8")
    assert '<details className="card guide-advanced">' in source
    assert "Advanced: Data integrity rules" in source
    assert "You normally do not need these details" in source
    assert "Risk information never changes shares" in source


def test_guide_has_friendly_readable_layout_loaded_globally():
    css = (FRONTEND / "guide-friendly.css").read_text(encoding="utf-8")
    entry = (FRONTEND / "entry-client.jsx").read_text(encoding="utf-8")
    assert "import './guide-friendly.css';" in entry
    assert "font-size: 13.5px" in css
    assert "font-size: 15px" in css
    assert ".guide-start-grid" in css
    assert ".guide-page-grid" in css
    assert ".guide-status-grid" in css
    assert ".guide-faq-grid" in css
