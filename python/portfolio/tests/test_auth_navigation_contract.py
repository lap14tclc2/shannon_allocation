from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_api_redirects_only_expired_authenticated_sessions_to_login():
    source = (FRONTEND / "lib" / "api.js").read_text(encoding="utf-8")
    assert "redirectExpiredSession" in source
    assert "res.status !== 401" in source
    assert "data?.code !== 'AUTH_REQUIRED'" in source
    assert "window.location.pathname === '/login'" in source
    assert "authRedirectInProgress" in source
    assert "window.location.replace(`/login?${params.toString()}`)" in source
    # Invalid admin credentials are also HTTP 401 but must remain visible on the login form.
    assert "INVALID_ADMIN_PASSWORD" not in source


def test_logout_always_navigates_to_explicit_login_route():
    source = (FRONTEND / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    assert "await logoutUser()" in source
    assert "window.location.replace('/login?logged_out=1')" in source
    assert "window.location.assign('/')" not in source


def test_relogin_restores_safe_internal_page_after_session_expiry():
    source = (FRONTEND / "pages" / "AuthPage.jsx").read_text(encoding="utf-8")
    assert "function safeNextPath()" in source
    assert "raw.startsWith('/')" in source
    assert "raw.startsWith('//')" in source
    assert "raw.startsWith('/login')" in source
    assert "reason') === 'session_expired'" in source
    assert "window.location.replace(result.user?.role === 'ADMIN' ? '/admin' : nextPath)" in source
    assert "Your session expired" in source
