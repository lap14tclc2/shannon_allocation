from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_mobile_navigation_is_portaled_outside_top_nav_containing_block():
    nav = (FRONTEND / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    assert "import { createPortal } from 'react-dom'" in nav
    assert "createPortal(" in nav
    assert "document.body" in nav
    assert 'className="mobile-tab-bar"' in nav
    assert 'className="mobile-account-sheet"' in nav
    assert 'className="mobile-nav-backdrop"' in nav
    assert 'className="app-nav-links desktop-nav-links"' in nav
    assert 'className="app-nav-footer desktop-nav-footer"' in nav


def test_mobile_shell_is_viewport_fixed_and_desktop_is_untouched():
    css = (FRONTEND / "mobile-iphone.css").read_text(encoding="utf-8")
    assert "@media (max-width: 719px)" in css
    assert ".mobile-tab-bar" in css
    assert "position: fixed" in css
    assert "bottom: 0" in css
    assert ".desktop-nav-links" in css
    assert ".desktop-nav-footer" in css
    assert "display: none !important" in css
    assert "env(safe-area-inset-top" in css
    assert "env(safe-area-inset-bottom" in css


def test_mobile_portfolio_uses_readable_native_like_hierarchy():
    css = (FRONTEND / "mobile-iphone.css").read_text(encoding="utf-8")
    assert ".overview-metrics" in css
    assert 'grid-template-areas:' in css
    assert '"label value"' in css
    assert ".portfolio-hero .hero-actions > .btn-ghost" in css
    assert "grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)" in css
    assert ".holdings-head .table-tools" in css
    assert "overflow-x: auto" in css
    assert "font-size: 16px" in css


def test_mobile_sheet_locks_background_and_stays_above_tabs():
    css = (FRONTEND / "mobile-iphone.css").read_text(encoding="utf-8")
    nav = (FRONTEND / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    assert "mobile-sheet-open" in nav
    assert "body.mobile-sheet-open" in css
    assert ".mobile-account-sheet" in css
    assert "z-index: 520" in css
    assert ".appearance-popover" in css
    assert "z-index: 560" in css
