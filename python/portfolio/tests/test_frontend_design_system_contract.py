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


def test_spa_copy_is_utf8_and_refreshes_without_document_reload():
    checked = [
        FRONTEND_SRC / "entry-vercel.jsx",
        FRONTEND_SRC / "lib" / "store.js",
    ]
    mojibake_markers = ("Ã", "Ä", "Æ", "áº", "á»")
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
