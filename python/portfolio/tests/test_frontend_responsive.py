from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def _responsive_css() -> str:
    return (FRONTEND_SRC / "responsive.css").read_text(encoding="utf-8")


def test_mobile_first_styles_are_loaded_last():
    entry = (FRONTEND_SRC / "entry-client.jsx").read_text(encoding="utf-8")
    assert "import './buyhold.css';" in entry
    assert "import './responsive.css';" in entry
    assert entry.index("import './responsive.css';") > entry.index("import './buyhold.css';")


def test_responsive_contract_is_mobile_first():
    css = _responsive_css()
    assert "@media (max-width:" not in css
    assert "@media (min-width: 480px)" in css
    assert "@media (min-width: 720px)" in css
    assert "@media (min-width: 1024px)" in css
    assert "grid-template-columns: minmax(0, 1fr);" in css


def test_mobile_navigation_and_touch_targets_are_safe():
    css = _responsive_css()
    assert ".nav-toggle" in css
    assert "min-height: 44px" in css
    assert ".nav-open .app-nav-links" in css
    assert "justify-content: space-between" in css


def test_mobile_forms_avoid_ios_zoom_and_stack_controls():
    css = _responsive_css()
    assert "font-size: 16px" in css
    assert ".form-grid" in css
    assert ".row-actions" in css
    assert ".inline-delete" in css


def test_wide_tables_scroll_inside_viewport():
    css = _responsive_css()
    assert ".table-scroll" in css
    assert "overflow-x: auto" in css
    assert "-webkit-overflow-scrolling: touch" in css
    assert "width: max-content" in css
    assert "min-width: 100%" in css


def test_mobile_chart_can_scroll_without_forcing_page_overflow():
    css = _responsive_css()
    assert ".chart" in css
    assert "min-width: 560px" in css
    assert "overflow-x: hidden" in css
