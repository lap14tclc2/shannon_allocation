from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
PORTFOLIO_DIR = Path(__file__).resolve().parents[1]
PYTHON_DIR = REPO_DIR / "python"
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def test_server_enforces_session_before_portfolio_api_and_scopes_service_by_user():
    source = (PYTHON_DIR / "buyhold_server.py").read_text(encoding="utf-8")
    assert "SESSION_COOKIE = \"qport_session\"" in source
    assert "if path.startswith(\"/api/portfolio\")" in source
    assert "user = self._require_user()" in source
    assert "PortfolioStore(_auth().portfolio_db_path(user_id))" in source
    assert "svc.append_event(body, created_by=actor)" in source
    assert "svc.update_event(eid, self._body(), created_by=user[\"username\"])" in source
    assert "svc.delete_event(eid, self._body().get(\"reason\"), created_by=user[\"username\"])" in source


def test_auth_store_uses_fresh_namespace_and_per_user_database_files():
    source = (PORTFOLIO_DIR / "auth.py").read_text(encoding="utf-8")
    assert '"auth-v1"' in source
    assert 'f"user-{int(user_id)}.sqlite3"' in source
    assert "UNIQUE" in source
    assert "PBKDF2_ITERATIONS" in source
    assert "DEFAULT_ADMIN_PASSWORD = \"abc123\"" in source


def test_start_page_and_admin_management_ui_are_wired_to_ssr_and_client():
    client = (FRONTEND_SRC / "entry-client.jsx").read_text(encoding="utf-8")
    ssr = (FRONTEND_SRC / "ssr-entry.jsx").read_text(encoding="utf-8")
    auth_page = (FRONTEND_SRC / "pages" / "AuthPage.jsx").read_text(encoding="utf-8")
    admin_page = (FRONTEND_SRC / "pages" / "AdminPage.jsx").read_text(encoding="utf-8")
    nav = (FRONTEND_SRC / "components" / "AppNav.jsx").read_text(encoding="utf-8")

    for source in (client, ssr):
        assert "AuthPage" in source
        assert "AdminPage" in source
        assert "auth:" in source
        assert "admin:" in source
    assert "Sign in with your username" in auth_page
    assert "Register username" in auth_page
    assert "isAdmin" in auth_page
    assert "admin / abc123" in auth_page
    assert "Remove user + data" in admin_page
    assert "Update admin password" in admin_page
    assert "logoutUser" in nav
    assert "currentUser?.role === 'ADMIN'" in nav


def test_cli_cannot_bypass_authenticated_user_database_routing():
    source = (PORTFOLIO_DIR / "cli.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--username", required=True' in source
    assert "AuthStore()" in source
    assert 'PortfolioStore(auth.portfolio_db_path(user["id"]))' in source
    assert "PortfolioService()" not in source


def test_legacy_single_user_database_is_removed_on_authenticated_server_start():
    source = (PYTHON_DIR / "buyhold_server.py").read_text(encoding="utf-8")
    assert "def _cleanup_legacy_database" in source
    assert '"portfolio.sqlite3"' in source
    assert "removed = _cleanup_legacy_database()" in source
