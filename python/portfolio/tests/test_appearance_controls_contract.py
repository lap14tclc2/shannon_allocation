from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_navigation_uses_theme_selector_not_light_dark_switch():
    nav = (FRONTEND / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    assert "AppearanceControls" in nav
    assert "toggleTheme" not in nav
    assert "preferredTheme" not in nav
    assert "prefers-color-scheme" not in nav


def test_theme_choice_is_persisted_and_legacy_keys_are_removed():
    source = (FRONTEND / "lib" / "appearance.js").read_text(encoding="utf-8")
    assert "STORAGE_KEY = 'qport-theme-v1'" in source
    assert "DEFAULT_THEME = 'retro'" in source
    assert "'retro'" in source and "'cyber'" in source
    assert "localStorage.setItem(STORAGE_KEY" in source
    assert "qport-appearance-v1" in source
    assert "root.dataset.visualTheme = theme" in source


def test_theme_is_applied_before_spa_boot_and_css_order_is_preserved():
    entry = (FRONTEND / "entry-vercel.jsx").read_text(encoding="utf-8")
    assert "applyStoredTheme();" in entry
    assert "import './appearance-controls.css';" in entry
    assert entry.index("import './accessibility-polish.css';") < entry.index("import './appearance-controls.css';")
    assert entry.index("applyStoredTheme();") < entry.index("const root = createRoot")


def test_theme_selector_is_keyboard_and_click_outside_safe():
    component = (FRONTEND / "components" / "AppearanceControls.jsx").read_text(encoding="utf-8")
    assert "Escape" in component
    assert "pointerdown" in component
    assert "aria-haspopup" in component
    assert "aria-expanded" in component
    assert "aria-label" in component


def test_theme_picker_is_portaled_to_body_and_viewport_owned():
    component = (FRONTEND / "components" / "AppearanceControls.jsx").read_text(encoding="utf-8")
    assert "createPortal" in component
    assert "document.body" in component
    assert "appearance-overlay" in component
    assert "appearance-backdrop" in component
    assert "theme-sheet-open" in component
    css = (FRONTEND / "appearance-controls.css").read_text(encoding="utf-8")
    assert ".appearance-overlay" in css
    assert "z-index: 700" in css
    assert ".appearance-backdrop" in css
    mobile = (FRONTEND / "mobile-iphone.css").read_text(encoding="utf-8")
    assert "body.theme-sheet-open" in mobile


def test_appearance_popover_is_compact_and_mobile_safe():
    css = (FRONTEND / "appearance-controls.css").read_text(encoding="utf-8")
    assert ".appearance-popover" in css
    assert "width: min(390px, calc(100vw - 32px));" in css
    assert "max-height: calc(100vh - 82px);" in css
    assert "overflow: auto" in css
    assert "@media (max-width: 719px)" in css
    assert "width: calc(100vw - 24px);" in css


def test_mobile_touch_targets_are_at_least_44px():
    css = (FRONTEND / "appearance-controls.css").read_text(encoding="utf-8")
    assert ".appearance-close" in css
    assert "min-height: 44px" in css
    assert ".theme-option" in css
    assert "min-height: 82px" in css
