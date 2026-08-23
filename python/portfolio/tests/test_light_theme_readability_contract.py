from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_warm_cream_light_theme_is_loaded_last():
    entry = (FRONTEND / "entry-client.jsx").read_text(encoding="utf-8")
    assert "import './cream-light-theme.css';" in entry
    assert entry.index("import './accessibility-polish.css';") < entry.index("import './cream-light-theme.css';")


def test_light_theme_uses_warm_paper_not_cold_white():
    css = (FRONTEND / "cream-light-theme.css").read_text(encoding="utf-8")
    assert ':root[data-theme="light"]' in css
    assert "--bg: #eee3c5;" in css
    assert "--panel: #f8efd8;" in css
    assert "--input: #fbf2dd;" in css
    assert "--text: #211d15;" in css
    assert "--text-secondary: #4c4435;" in css
    assert "--muted: #655b47;" in css
    assert "background: var(--bg);" in css
    assert "font-weight: 500;" in css


def test_light_theme_keeps_semantic_colors_and_focus_visible():
    css = (FRONTEND / "cream-light-theme.css").read_text(encoding="utf-8")
    for token in ("--success:", "--danger:", "--warning:", "--info:", "--accent:"):
        assert token in css
    assert "outline: 2px solid var(--accent);" in css
    assert ".status-partial" in css
    assert ".market-history-ready" in css
