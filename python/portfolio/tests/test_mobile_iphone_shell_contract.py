from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend"
SRC = FRONTEND / "src"


def test_mobile_iphone_styles_are_loaded_after_all_desktop_and_feature_styles():
    entry = (SRC / "entry-client.jsx").read_text(encoding="utf-8")
    assert "import './mobile-iphone.css';" in entry
    assert entry.index("import './mobile-iphone.css';") > entry.index("import './responsive.css';")
    assert entry.index("import './mobile-iphone.css';") > entry.index("import './guide-friendly.css';")


def test_mobile_shell_is_scoped_below_tablet_breakpoint_so_desktop_is_unchanged():
    css = (SRC / "mobile-iphone.css").read_text(encoding="utf-8")
    assert "@media (max-width: 719px)" in css
    assert "every product-layout override is scoped below 720px" in css
    assert "@media (min-width: 720px)" not in css


def test_iphone_safe_areas_and_dynamic_viewport_are_supported():
    css = (SRC / "mobile-iphone.css").read_text(encoding="utf-8")
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert "viewport-fit=cover" in html
    assert "apple-mobile-web-app-capable" in html
    assert "safe-area-inset-top" in css
    assert "safe-area-inset-bottom" in css
    assert "100dvh" in css


def test_mobile_navigation_uses_top_app_bar_bottom_tabs_and_dismissible_sheet():
    nav = (SRC / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    css = (SRC / "mobile-iphone.css").read_text(encoding="utf-8")
    assert "MobileTabIcon" in nav
    assert "mobile-tab-icon" in nav
    assert "user-nav-links" in nav
    assert "mobile-nav-backdrop" in nav
    assert "Open account and appearance menu" in nav
    assert "position: fixed" in css
    assert "grid-template-columns: repeat(4" in css
    assert "bottom: 0" in css
    assert ".nav-open .app-nav-footer" in css


def test_mobile_controls_use_iphone_friendly_touch_sizes_and_ios_input_font():
    css = (SRC / "mobile-iphone.css").read_text(encoding="utf-8")
    assert "min-height: 44px" in css
    assert "min-height: 48px" in css
    assert "font-size: 16px" in css
    assert "touch-action: manipulation" in css


def test_mobile_content_uses_grouped_cards_without_crushing_auditable_tables():
    css = (SRC / "mobile-iphone.css").read_text(encoding="utf-8")
    assert "border-radius: 14px" in css
    assert ".table-scroll" in css
    assert ".holding-source-scroll" in css
    assert "scrollbar-width: none" in css
    assert ".portfolio-table th:first-child" in css
