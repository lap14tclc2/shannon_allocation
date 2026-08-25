from __future__ import annotations

import json
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[3]
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def test_canonical_design_system_loads_after_legacy_styles():
    entry = (FRONTEND_SRC / "entry-vercel.jsx").read_text(encoding="utf-8")
    assert "import './design-system-v1.css';" in entry
    assert entry.index("mobile-scroll-fix.css") < entry.index("design-system-v1.css")

    css = (FRONTEND_SRC / "design-system-v1.css").read_text(encoding="utf-8")
    assert '--font-ui:' in css
    assert '--font-numeric:' in css
    assert 'font-family: var(--font-ui)' in css
    assert 'font-family: var(--font-numeric)' in css
    assert '@media (prefers-reduced-motion: reduce)' in css
    assert '--accent: #4aa3ff' in css


def test_header_v2_uses_custom_portfolio_navigation():
    entry = (FRONTEND_SRC / "entry-vercel.jsx").read_text(encoding="utf-8")
    nav = (FRONTEND_SRC / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    css = (FRONTEND_SRC / "header-v2.css").read_text(encoding="utf-8")

    assert entry.index("design-system-v1.css") < entry.index("header-v2.css")
    assert "<select" not in nav
    assert 'aria-haspopup="menu"' in nav
    assert 'aria-label="Mở tài khoản và tùy chọn"' in nav
    assert "portfolio-menu-option" in nav
    assert "header-user-avatar" in nav
    assert "@media (max-width: 719px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_retro_ledger_theme_and_privacy_contract():
    entry = (FRONTEND_SRC / "entry-vercel.jsx").read_text(encoding="utf-8")
    appearance = (FRONTEND_SRC / "lib" / "appearance.js").read_text(encoding="utf-8")
    controls = (FRONTEND_SRC / "components" / "AppearanceControls.jsx").read_text(encoding="utf-8")
    nav = (FRONTEND_SRC / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    dashboard = (FRONTEND_SRC / "pages" / "VietnamesePortfolioDashboard.jsx").read_text(encoding="utf-8")
    css = (FRONTEND_SRC / "japanese-retro-theme.css").read_text(encoding="utf-8")

    assert entry.index("header-v2.css") < entry.index("japanese-retro-theme.css")
    assert "qport-theme-v1" in appearance
    assert "DEFAULT_THEME = 'retro'" in appearance
    assert "theme === 'retro' ? 'light' : 'dark'" in appearance
    assert "Retro Ledger" in controls
    assert "Cyber Fantasy" in controls
    assert "qport.privacy-mode.v1" in nav
    assert "Sổ tài sản" in nav
    assert 'data-sensitive="money"' in dashboard
    assert ".privacy-mode [data-sensitive=\"money\"]" in css
    assert "--retro-bg: #efe4cf" in css
    assert "--retro-panel: #fffaf0" in css
    assert "--retro-ink: #201d18" in css
    assert "Showa print palette" in css
    assert "Yu Gothic UI" not in css
    assert "ĐÃ XÁC NHẬN" in css

    checked_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in FRONTEND_SRC.rglob("*")
        if path.suffix in {".js", ".jsx", ".css"}
    )
    assert not any(
        "\u3040" <= char <= "\u30ff"
        or "\u3400" <= char <= "\u4dbf"
        or "\u4e00" <= char <= "\u9fff"
        for char in checked_text
    )


def test_quick_import_starts_empty_and_performance_metrics_are_responsive():
    quick_import = (FRONTEND_SRC / "components" / "QuickImportPanel.jsx").read_text(encoding="utf-8")
    quick_import_css = (FRONTEND_SRC / "quick-import.css").read_text(encoding="utf-8")
    performance = (FRONTEND_SRC / "pages" / "PerformancePage.jsx").read_text(encoding="utf-8")
    performance_css = (FRONTEND_SRC / "performance-interactive.css").read_text(encoding="utf-8")

    assert "useState('')" in quick_import
    assert "placeholder={importTemplate(mode)}" in quick_import
    assert "function clearInput()" in quick_import
    assert "Xóa dữ liệu" in quick_import
    assert ".quick-import-textarea::placeholder" in quick_import_css

    assert '<dl className="performance-health-grid">' in performance
    assert "cashflowQualityLabel" in performance
    assert "Chỉ có số dư đầu kỳ" in performance
    assert "grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))" in performance_css
    assert "overflow-wrap: anywhere" in performance_css


def test_spa_copy_is_utf8_and_refreshes_without_document_reload():
    checked = [
        path
        for path in FRONTEND_SRC.rglob("*")
        if path.suffix in {".js", ".jsx", ".css"}
    ]
    mojibake_markers = ("Ã¡", "Ã¢", "Ã£", "Ã©", "Ä‘", "Æ°", "áº", "á»")
    for path in checked:
        source = path.read_text(encoding="utf-8")
        assert not any(marker in source for marker in mojibake_markers), path

    performance = (FRONTEND_SRC / "pages" / "PerformancePage.jsx").read_text(encoding="utf-8")
    transactions = (FRONTEND_SRC / "pages" / "TransactionsPage.jsx").read_text(encoding="utf-8")
    assert "window.location.reload" not in performance
    assert "window.location.replace('/transactions')" not in transactions
    assert "dispatch(loadRoute({ pathname: '/performance' }))" in performance
    assert "dispatch(loadRoute({ pathname: '/transactions' }))" in transactions


def test_vercel_cache_contract_keeps_shell_fresh_and_assets_immutable():
    config = json.loads((REPO_DIR / "vercel.json").read_text(encoding="utf-8"))
    headers = {row["source"]: row["headers"] for row in config["headers"]}

    assert {
        "key": "Cache-Control",
        "value": "public, max-age=31536000, immutable",
    } in headers["/assets/:path*"]
    assert {
        "key": "Cache-Control",
        "value": "private, no-store, max-age=0",
    } in headers["/api/:path*"]

    shell_policy = {
        "key": "Cache-Control",
        "value": "public, max-age=0, must-revalidate",
    }
    for path in (
        "/",
        "/login",
        "/portfolios",
        "/transactions",
        "/performance",
        "/risk",
        "/settings",
        "/guide",
    ):
        assert shell_policy in headers[path]
