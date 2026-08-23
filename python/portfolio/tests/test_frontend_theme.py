from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def test_frontend_exposes_light_and_dark_theme_tokens():
    css = (FRONTEND_SRC / "buyhold.css").read_text(encoding="utf-8")
    assert ':root[data-theme="dark"]' in css
    assert ':root[data-theme="light"]' in css
    assert "--accent:" in css
    assert ".theme-toggle" in css


def test_theme_choice_is_persisted_and_respects_system_preference():
    nav = (FRONTEND_SRC / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    assert "qport-theme" in nav
    assert "localStorage" in nav
    assert "prefers-color-scheme: light" in nav
    assert "document.documentElement.dataset.theme" in nav


def test_primary_shell_uses_arena_style_horizontal_navigation():
    css = (FRONTEND_SRC / "buyhold.css").read_text(encoding="utf-8")
    assert ".nav-shell" in css
    assert "grid-template-columns: auto 1fr auto" in css
    assert "border-bottom: 1px solid var(--border)" in css
    assert "ui-monospace" in css
