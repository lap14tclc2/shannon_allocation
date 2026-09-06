from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
PORTFOLIO_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = REPO_DIR / "frontend" / "src"
API = REPO_DIR / "app" / "main.py"
POSTGRES = PORTFOLIO_DIR / "postgres.py"


def test_fastapi_enforces_session_before_portfolio_api_and_scopes_service_by_user():
    source = API.read_text(encoding="utf-8")
    assert 'SESSION_COOKIE = "qport_session"' in source
    assert "def require_portfolio_user" in source
    assert "PostgresPortfolioStore(user_id, selected[\"schema_name\"])" in source
    assert "svc.append_event(body, created_by=user[\"username\"])" in source
    assert "svc.update_event(event_id, body, created_by=user[\"username\"])" in source
    assert "svc.delete_event(event_id, body.get(\"reason\"), created_by=user[\"username\"])" in source


def test_admin_is_administration_only_and_never_opens_portfolio_book():
    api = API.read_text(encoding="utf-8")
    client = (FRONTEND_SRC / "entry-vercel.jsx").read_text(encoding="utf-8")
    nav = (FRONTEND_SRC / "components" / "AppNav.jsx").read_text(encoding="utf-8")

    assert "ADMIN_PORTFOLIO_FORBIDDEN" in api
    assert "def require_admin" in api
    assert "user.role === 'ADMIN' && !adminPath" in client
    assert "user.role !== 'ADMIN' && adminPath" in client
    assert "const adminMode = active === 'admin' || currentUser?.role === 'ADMIN'" in nav
    assert "adminMode ? '/admin' : '/'" in nav


def test_postgres_auth_uses_one_schema_per_user_and_case_insensitive_usernames():
    source = POSTGRES.read_text(encoding="utf-8")
    assert 'AUTH_SCHEMA = "qport_auth"' in source
    assert 'USER_SCHEMA_PREFIX = "qport_user_"' in source
    assert "PostgresPortfolioStore(int(row[\"id\"]))" in source
    assert "ON users (LOWER(username))" in source
    assert "PBKDF2" in (PORTFOLIO_DIR / "auth.py").read_text(encoding="utf-8")
    assert "QPORT_ADMIN_PASSWORD" in source


def test_start_page_and_admin_management_ui_are_wired_to_spa_without_credential_disclosure():
    client = (FRONTEND_SRC / "entry-vercel.jsx").read_text(encoding="utf-8")
    auth_page = (FRONTEND_SRC / "pages" / "AuthPage.jsx").read_text(encoding="utf-8")
    admin_page = (FRONTEND_SRC / "pages" / "AdminPage.jsx").read_text(encoding="utf-8")
    guide = (FRONTEND_SRC / "pages" / "GuidePage.jsx").read_text(encoding="utf-8")
    readme = (REPO_DIR / "README.md").read_text(encoding="utf-8")
    api = API.read_text(encoding="utf-8")

    assert "AuthPage" in client
    assert "AdminPage" in client
    assert "'/admin': AdminPage" in client
    assert "pathname === '/login'" in client
    assert "Đăng nhập vào QPort" in auth_page
    assert "Tạo danh mục mới" in auth_page
    assert "isAdmin" in auth_page
    assert "Xóa user + data" in admin_page
    assert "Xem danh mục" in admin_page
    assert "PostgreSQL schema" in admin_page

    for visible_source in (auth_page, admin_page, guide, readme, api):
        assert "admin / abc123" not in visible_source


def test_cli_uses_same_postgres_user_routing_as_web_runtime():
    source = (PORTFOLIO_DIR / "cli.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--username", required=True' in source
    assert "PostgresAuthStore()" in source
    assert 'if user.get("role") == "ADMIN":' in source
    assert "Admin is administration-only" in source
    assert 'PostgresPortfolioStore(user["id"])' in source
    assert 'service = AutomatedPortfolioService(store=' in source


def test_vercel_runtime_never_depends_on_local_sqlite_database_paths():
    api = API.read_text(encoding="utf-8")
    client = (FRONTEND_SRC / "entry-vercel.jsx").read_text(encoding="utf-8")
    assert "sqlite3" not in api
    assert "portfolio.sqlite3" not in api
    assert "buyhold_server" not in api
    assert "entry-client" not in client
    assert "window.__PAGE__" not in client
