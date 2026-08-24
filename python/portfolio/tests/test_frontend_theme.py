from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def test_frontend_exposes_dark_default_and_semantic_color_tokens():
    css = (FRONTEND_SRC / "buyhold.css").read_text(encoding="utf-8")
    assert ':root[data-theme="dark"]' in css
    assert ':root[data-theme="light"]' in css
    assert "--accent:" in css
    assert "ui-monospace" in css


def test_appearance_choice_is_persisted_as_custom_palette():
    nav = (FRONTEND_SRC / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    appearance = (FRONTEND_SRC / "lib" / "appearance.js").read_text(encoding="utf-8")
    assert "AppearanceControls" in nav
    assert "qport-appearance-v1" in appearance
    assert "localStorage" in appearance
    assert "root.dataset.theme = 'dark'" in appearance
    assert "qport-theme" not in nav


def test_primary_shell_uses_arena_style_horizontal_navigation_on_desktop():
    css = (FRONTEND_SRC / "buyhold.css").read_text(encoding="utf-8")
    assert ".nav-shell" in css
    assert "grid-template-columns: auto 1fr auto" in css
    assert "border-bottom: 1px solid var(--border)" in css
    assert "ui-monospace" in css
