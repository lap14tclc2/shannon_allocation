from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
PORTFOLIO_DIR = Path(__file__).resolve().parents[1]
PYTHON_DIR = REPO_DIR / "python"
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def test_server_enforces_session_before_portfolio_api_and_scopes_service_by_user():
    source = (PYTHON_DIR / "buyhold_server.py").read_text(encoding="utf-8")
    assert "SESSION_COOKIE = \"qport_session\"" in source
    assert "if path.startswith(\"/api/portfolio\")" in source
    assert "user = self._require_portfolio_user()" in source
    assert "PortfolioStore(_auth().portfolio_db_path(user_id))" in source
    assert "svc.append_event(body, created_by=actor)" in source
    assert "svc.update_event(eid, self._body(), created_by=user[\"username\"])" in source
    assert "svc.delete_event(eid, self._body().get(\"reason\"), created_by=user[\"username\"])" in source


def test_admin_is_administration_only_and_never_opens_portfolio_book():
    server = (PYTHON_DIR / "buyhold_server.py").read_text(encoding="utf-8")
    client = (FRONTEND_SRC / "entry-client.jsx").read_text(encoding="utf-8")
    nav = (FRONTEND_SRC / "components" / "AppNav.jsx").read_text(encoding="utf-8")

    assert "ADMIN_PORTFOLIO_FORBIDDEN" in server
    assert 'if user.get("role") == "ADMIN":' in server
    assert 'return self._page("admin", user) if path == "/admin" else self._redirect("/admin")' in server
    assert 'if page != "admin":' in server
    assert 'return self._redirect("/admin")' in server
    assert 'if user.get("role") == "ADMIN":\n                continue' in server
    assert "page.props?.currentUser?.role === 'ADMIN'" in client
    assert "window.location.replace('/admin')" in client
    assert "const adminMode = active === 'admin' || currentUser?.role === 'ADMIN'" in nav
    assert "adminMode ? '/admin' : '/'" in nav


def test_auth_store_uses_fresh_namespace_and_per_user_database_files():
    source = (PORTFOLIO_DIR / "auth.py").read_text(encoding="utf-8")
    assert '"auth-v1"' in source
    assert 'f"user-{int(user_id)}.sqlite3"' in source
    assert "UNIQUE" in source
    assert "PBKDF2_ITERATIONS" in source
    assert "DEFAULT_ADMIN_PASSWORD" in source


def test_start_page_and_admin_management_ui_are_wired_to_ssr_and_client_without_credential_disclosure():
    client = (FRONTEND_SRC / "entry-client.jsx").read_text(encoding="utf-8")
    ssr = (FRONTEND_SRC / "ssr-entry.jsx").read_text(encoding="utf-8")
    auth_page = (FRONTEND_SRC / "pages" / "AuthPage.jsx").read_text(encoding="utf-8")
    admin_page = (FRONTEND_SRC / "pages" / "AdminPage.jsx").read_text(encoding="utf-8")
    guide = (FRONTEND_SRC / "pages" / "GuidePage.jsx").read_text(encoding="utf-8")
    readme = (REPO_DIR / "README.md").read_text(encoding="utf-8")
    server = (PYTHON_DIR / "buyhold_server.py").read_text(encoding="utf-8")

    for source in (client, ssr):
        assert "AuthPage" in source
        assert "AdminPage" in source
        assert "auth:" in source
        assert "admin:" in source
    assert "Sign in with your username" in auth_page
    assert "Register username" in auth_page
    assert "isAdmin" in auth_page
    assert "Remove user + data" in admin_page
    assert "Update admin password" in admin_page

    for visible_source in (auth_page, admin_page, guide, readme, server):
        assert "admin / abc123" not in visible_source
    assert 'print("Default admin:' not in server


def test_cli_cannot_bypass_authenticated_user_database_routing():
    source = (PORTFOLIO_DIR / "cli.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--username", required=True' in source
    assert "AuthStore()" in source
    assert 'if user.get("role") == "ADMIN":' in source
    assert "Admin is administration-only" in source
    assert 'PortfolioStore(auth.portfolio_db_path(user["id"]))' in source
    assert "PortfolioService()" not in source


def test_legacy_single_user_database_is_removed_on_authenticated_server_start():
    source = (PYTHON_DIR / "buyhold_server.py").read_text(encoding="utf-8")
    assert "def _cleanup_legacy_database" in source
    assert '"portfolio.sqlite3"' in source
    assert "removed = _cleanup_legacy_database()" in source
