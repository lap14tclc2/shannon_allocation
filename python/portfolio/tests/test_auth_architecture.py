from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
PORTFOLIO_DIR = Path(__file__).resolve().parents[1]
PYTHON_DIR = REPO_DIR / "python"
FRONTEND_DIR = REPO_DIR / "frontend"
FRONTEND_SRC = FRONTEND_DIR / "src"


def test_server_enforces_session_before_portfolio_api_and_scopes_service_by_user():
    source = (PYTHON_DIR / "buyhold_server.py").read_text(encoding="utf-8")
    assert 'SESSION_COOKIE = "qport_session"' in source
    assert 'if path.startswith("/api/portfolio")' in source
    assert "user = self._require_user()" in source
    assert "PortfolioStore(_auth().portfolio_db_path(user_id))" in source
    assert "svc.append_event(body, created_by=actor)" in source
    assert 'svc.update_event(eid, body, created_by=user["username"])' in source
    assert 'svc.delete_event(eid, body.get("reason"), created_by=user["username"])' in source


def test_auth_store_uses_fresh_namespace_per_user_db_and_no_embedded_admin_password():
    source = (PORTFOLIO_DIR / "auth.py").read_text(encoding="utf-8")
    assert '"auth-v1"' in source
    assert 'f"user-{int(user_id)}.sqlite3"' in source
    assert "UNIQUE" in source
    assert "PBKDF2_ITERATIONS" in source
    assert "PBKDF2_ITERATIONS = 600_000" in source
    assert "AUTH_SECURITY_VERSION" in source
    assert "bootstrap_admin_password" in source
    assert "DEFAULT_ADMIN_PASSWORD" not in source


def test_start_page_and_admin_management_ui_are_wired_without_credential_disclosure():
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
    assert "setup-admin" in auth_page
    assert "Remove user + data" in admin_page
    assert "Update admin password" in admin_page
    assert "logoutUser" in nav
    assert "currentUser?.role === 'ADMIN'" in nav


def test_cli_never_accepts_admin_password_as_command_line_argument():
    source = (PORTFOLIO_DIR / "cli.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--username"' in source
    assert "setup-admin" in source
    assert "getpass.getpass" in source
    assert 'parser.add_argument("--password"' not in source
    assert "AuthStore()" in source
    assert 'PortfolioStore(auth.portfolio_db_path(user["id"]))' in source
    assert "PortfolioService()" not in source


def test_http_surface_has_csrf_security_headers_body_cap_and_remote_bind_guard():
    server = (PYTHON_DIR / "buyhold_server.py").read_text(encoding="utf-8")
    api = (FRONTEND_SRC / "lib" / "api.js").read_text(encoding="utf-8")
    client = (FRONTEND_SRC / "entry-client.jsx").read_text(encoding="utf-8")

    assert '"X-QPort-Request": "1"' in server
    assert "CROSS_ORIGIN_REQUEST_BLOCKED" in server
    assert "Content-Security-Policy" in server
    assert "X-Frame-Options" in server
    assert "X-Content-Type-Options" in server
    assert "MAX_REQUEST_BODY" in server
    assert "REQUEST_TOO_LARGE" in server
    assert "--allow-trusted-network" in server
    assert "QPORT_SECURE_COOKIES" in server
    assert "ADMIN_RATE_LIMITED" in server
    assert "SAME_ORIGIN_HEADERS" in api
    assert "credentials: 'same-origin'" in api
    assert "qport-page-data" in client
    assert "window.__PAGE__" not in client
    assert "window.__PAGE__" not in server


def test_known_exposed_bootstrap_credential_cannot_reappear_in_current_tree():
    forbidden = "abc" + "123"
    targets = [
        REPO_DIR / "README.md",
        REPO_DIR / "user-guide.md",
        PYTHON_DIR / "buyhold_server.py",
        PORTFOLIO_DIR / "auth.py",
        PORTFOLIO_DIR / "cli.py",
        FRONTEND_SRC / "pages" / "AuthPage.jsx",
        FRONTEND_SRC / "pages" / "AdminPage.jsx",
        FRONTEND_SRC / "pages" / "GuidePage.jsx",
        FRONTEND_DIR / "test" / "auth-smoke.mjs",
    ]
    for path in targets:
        assert forbidden not in path.read_text(encoding="utf-8"), f"exposed credential found in {path}"


def test_legacy_single_user_database_is_removed_on_authenticated_server_start():
    source = (PYTHON_DIR / "buyhold_server.py").read_text(encoding="utf-8")
    assert "def _cleanup_legacy_database" in source
    assert '"portfolio.sqlite3"' in source
    assert "removed = _cleanup_legacy_database()" in source
