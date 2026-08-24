from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_navigation_uses_color_overlay_not_light_dark_switch():
    nav = (FRONTEND / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    assert "AppearanceControls" in nav
    assert "toggleTheme" not in nav
    assert "preferredTheme" not in nav
    assert "prefers-color-scheme" not in nav
    assert "qport-theme" not in nav
    assert "Use light theme" not in nav
    assert "Use dark theme" not in nav


def test_default_is_dark_and_custom_palette_is_persisted():
    source = (FRONTEND / "lib" / "appearance.js").read_text(encoding="utf-8")
    assert "qport-appearance-v1" in source
    assert "background: '#090a09'" in source
    assert "text: '#f1f4ef'" in source
    assert "secondary: '#b3bcb3'" in source
    assert "muted: '#8e988e'" in source
    assert "root.dataset.theme = 'dark'" in source
    assert "localStorage.setItem(STORAGE_KEY" in source
    assert "localStorage.removeItem(STORAGE_KEY" in source
    assert "color-mix" in source


def test_custom_palette_is_applied_before_spa_boot_and_css_order_is_preserved():
    entry = (FRONTEND / "entry-vercel.jsx").read_text(encoding="utf-8")
    assert "applyStoredAppearance" in entry
    assert "applyStoredAppearance();" in entry
    assert "cream-light-theme.css" not in entry
    assert "import './appearance-controls.css';" in entry
    assert entry.index("import './accessibility-polish.css';") < entry.index("import './appearance-controls.css';")
    assert entry.index("applyStoredAppearance();") < entry.index("const root = createRoot")


def test_overlay_exposes_background_and_semantic_text_colors():
    component = (FRONTEND / "components" / "AppearanceControls.jsx").read_text(encoding="utf-8")
    for field in (
        "Background",
        "Primary text",
        "Secondary text",
        "Muted text",
        "Accent / links",
        "Positive / ready",
        "Warning / building",
        "Negative / error",
        "Information",
    ):
        assert field in component
    assert 'type="color"' in component
    assert "Saved automatically" in component
    assert "Reset default dark" in component
    assert "role=\"dialog\"" in component


def test_appearance_overlay_is_compact_and_mobile_safe():
    css = (FRONTEND / "appearance-controls.css").read_text(encoding="utf-8")
    assert ".appearance-popover" in css
    assert "width: min(360px, calc(100vw - 32px));" in css
    assert "max-height: calc(100vh - 82px);" in css
    assert "@media (max-width: 719px)" in css
    assert "width: calc(100vw - 24px);" in css
