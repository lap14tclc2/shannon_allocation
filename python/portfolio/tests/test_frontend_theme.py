from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def test_frontend_exposes_dark_default_and_semantic_color_tokens():
    css = (FRONTEND_SRC / "buyhold.css").read_text(encoding="utf-8")
    assert ':root[data-theme="dark"]' in css
    assert ':root[data-theme="light"]' in css
    assert "--accent:" in css
    assert "ui-monospace" in css


def test_theme_choice_is_persisted_and_clears_legacy_palette_keys():
    appearance = (FRONTEND_SRC / "lib" / "appearance.js").read_text(encoding="utf-8")
    assert "STORAGE_KEY = 'qport-theme-v1'" in appearance
    assert "DEFAULT_THEME = 'retro'" in appearance
    assert "VISUAL_THEMES" in appearance and "'cyber'" in appearance
    assert "localStorage.setItem(STORAGE_KEY, theme)" in appearance
    assert "LEGACY_APPEARANCE_KEYS" in appearance
    assert "qport-appearance-v1" in appearance


def test_theme_is_applied_before_spa_boot_and_sets_both_attributes():
    entry = (FRONTEND_SRC / "entry-vercel.jsx").read_text(encoding="utf-8")
    appearance = (FRONTEND_SRC / "lib" / "appearance.js").read_text(encoding="utf-8")
    assert "applyStoredTheme();" in entry
    assert entry.index("applyStoredTheme();") < entry.index("const root = createRoot")
    assert "root.dataset.theme = colorScheme" in appearance
    assert "root.dataset.visualTheme = theme" in appearance


def test_theme_selector_exposes_retro_and_cyber_systems():
    component = (FRONTEND_SRC / "components" / "AppearanceControls.jsx").read_text(encoding="utf-8")
    for phrase in ("Retro Ledger", "Cyber Fantasy", "role=\"radiogroup\"", "aria-checked", "Escape"):
        assert phrase in component
    assert "aria-label" in component


def test_primary_shell_uses_arena_style_horizontal_navigation_on_desktop():
    css = (FRONTEND_SRC / "buyhold.css").read_text(encoding="utf-8")
    assert ".nav-shell" in css
    assert "grid-template-columns: auto 1fr auto" in css
    assert "border-bottom: 1px solid var(--border)" in css
    assert "ui-monospace" in css
