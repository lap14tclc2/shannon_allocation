from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend"
SRC = FRONTEND / "src"


def test_mobile_iphone_styles_are_loaded_last_in_vercel_entry():
    entry = (SRC / "entry-vercel.jsx").read_text(encoding="utf-8")
    assert "import './mobile-iphone.css';" in entry
    assert "import './mobile-scroll-fix.css';" in entry
    assert entry.index("import './mobile-iphone.css';") > entry.index("import './responsive.css';")
    assert entry.index("import './mobile-scroll-fix.css';") > entry.index("import './mobile-iphone.css';")


def test_mobile_shell_is_scoped_below_tablet_breakpoint_so_desktop_is_unchanged():
    css = (SRC / "mobile-iphone.css").read_text(encoding="utf-8")
    assert "@media (max-width: 719px)" in css
    assert "All product-layout overrides stay below 720px" in css


def test_iphone_safe_areas_and_dynamic_viewport_are_supported():
    css = (SRC / "mobile-iphone.css").read_text(encoding="utf-8")
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert "viewport-fit=cover" in html
    assert "apple-mobile-web-app-capable" in html
    assert "safe-area-inset-top" in css
    assert "safe-area-inset-bottom" in css
    assert "100dvh" in css


def test_mobile_navigation_is_portaled_to_real_viewport():
    nav = (SRC / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    css = (SRC / "mobile-iphone.css").read_text(encoding="utf-8")
    assert "createPortal" in nav
    assert "document.body" in nav
    assert 'className="mobile-tab-bar"' in nav
    assert "mobile-account-sheet" in nav
    assert 'className="mobile-nav-backdrop"' in nav
    assert "position: fixed" in css
    assert "grid-template-columns: repeat(4" in css
    assert "bottom: 0" in css


def test_mobile_controls_use_iphone_friendly_touch_sizes_and_ios_input_font():
    css = (SRC / "mobile-iphone.css").read_text(encoding="utf-8")
    assert "min-height: 44px" in css
    assert "font-size: 16px" in css
    assert "touch-action: manipulation" in css


def test_mobile_content_keeps_wide_audit_data_scrollable():
    css = (SRC / "mobile-iphone.css").read_text(encoding="utf-8")
    assert ".table-scroll" in css
    assert "overflow-x: auto" in css
    assert ".portfolio-table th:first-child" in css
