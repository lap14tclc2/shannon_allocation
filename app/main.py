from __future__ import annotations

import hmac
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import Body, Cookie, FastAPI, Query, Request
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from portfolio.accounting import derive_state  # noqa: E402
from portfolio.auth import AuthError, SESSION_DAYS  # noqa: E402
from portfolio.automated_service import AutomatedPortfolioService  # noqa: E402
from portfolio.corrections import effective_events  # noqa: E402
from portfolio.dividend_store import SqliteDividendService  # noqa: E402
from portfolio.dividends import DividendLookupError  # noqa: E402
from portfolio.postgres import (  # noqa: E402
    PostgresAuthStore,
    PostgresPortfolioStore,
    drop_user_schema,
    reset_portfolio_schema,
)
from portfolio.validation import InputValidationError  # noqa: E402

SESSION_COOKIE = "qport_session"
PORTFOLIO_DELETE_CONFIRMATION = "XOA DANH MUC"

app = FastAPI(
    title="QPort API",
    version="vercel-migration-v1",
    docs_url="/api/docs" if os.environ.get("QPORT_API_DOCS") == "1" else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if os.environ.get("QPORT_API_DOCS") == "1" else None,
)

_auth_store: PostgresAuthStore | None = None
_services: dict[tuple[int, int], AutomatedPortfolioService] = {}
_dividend_services: dict[tuple[int, int], SqliteDividendService] = {}


class ApiError(Exception):
    def __init__(self, status: int, error: str, code: str, field: str | None = None) -> None:
        super().__init__(error)
        self.status = int(status)
        self.payload = {"error": error, "code": code, "field": field}


@app.exception_handler(ApiError)
def handle_api_error(_request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status, content=exc.payload)


@app.exception_handler(InputValidationError)
def handle_validation_error(_request: Request, exc: InputValidationError):
    return JSONResponse(status_code=400, content=exc.as_dict())


@app.exception_handler(AuthError)
def handle_auth_error(_request: Request, exc: AuthError):
    status = 404 if exc.code in {"USER_NOT_REGISTERED", "PORTFOLIO_NOT_FOUND"} else 400
    if exc.code == "INVALID_ADMIN_PASSWORD":
        status = 401
    elif exc.code == "PORTFOLIO_NAME_TAKEN":
        status = 409
    return JSONResponse(status_code=status, content=exc.as_dict())


def auth() -> PostgresAuthStore:
    global _auth_store
    if _auth_store is None:
        _auth_store = PostgresAuthStore()
    return _auth_store


def current_user(token: str | None) -> dict | None:
    return auth().authenticate(token)


def require_user(token: str | None) -> dict:
    user = current_user(token)
    if user is None:
        raise ApiError(401, "Authentication required.", "AUTH_REQUIRED")
    return user


def require_portfolio_user(token: str | None) -> dict:
    user = require_user(token)
    if user.get("role") == "ADMIN":
        raise ApiError(
            403,
            "Admin accounts do not access portfolio data through user routes.",
            "ADMIN_PORTFOLIO_FORBIDDEN",
        )
    return user


def require_admin(token: str | None) -> dict:
    user = require_user(token)
    if user.get("role") != "ADMIN":
        raise ApiError(403, "Admin access is required.", "ADMIN_REQUIRED")
    return user


def admin_target_user(user_id: int) -> dict:
    row = auth().user_by_id(int(user_id))
    if row is None:
        raise ApiError(404, "User does not exist.", "USER_NOT_FOUND", "user_id")
    if row.get("role") == "ADMIN":
        raise ApiError(400, "Admin account has no user portfolio.", "ADMIN_TARGET_FORBIDDEN", "user_id")
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def active_portfolio(user: dict) -> dict:
    return auth().active_portfolio(int(user["id"]))


def portfolio(user: dict) -> AutomatedPortfolioService:
    user_id = int(user["id"])
    selected = active_portfolio(user)
    key = (user_id, int(selected["id"]))
    svc = _services.get(key)
    if svc is None:
        svc = AutomatedPortfolioService(
            store=PostgresPortfolioStore(user_id, selected["schema_name"])
        )
        _services[key] = svc
    return svc


def dividends(user: dict) -> SqliteDividendService:
    user_id = int(user["id"])
    selected = active_portfolio(user)
    key = (user_id, int(selected["id"]))
    service = _dividend_services.get(key)
    if service is None:
        service = SqliteDividendService(portfolio(user).store, stop_on_first_data=False)
        _dividend_services[key] = service
    return service


def clear_portfolio_runtime(user_id: int, portfolio_id: int) -> None:
    key = (int(user_id), int(portfolio_id))
    _services.pop(key, None)
    _dividend_services.pop(key, None)


def clear_user_runtime(user_id: int) -> None:
    target = int(user_id)
    for key in [item for item in _services if item[0] == target]:
        _services.pop(key, None)
    for key in [item for item in _dividend_services if item[0] == target]:
        _dividend_services.pop(key, None)


def _secure_cookie() -> bool:
    if os.environ.get("QPORT_COOKIE_SECURE") in {"0", "false", "False"}:
        return False
    return bool(os.environ.get("VERCEL") or os.environ.get("QPORT_COOKIE_SECURE") == "1")


def _set_session_cookie(response: JSONResponse, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: JSONResponse) -> None:
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
    )


def _service_failure(svc: AutomatedPortfolioService, method: str, path: str, exc: Exception):
    code = getattr(exc, "code", "PORTFOLIO_ERROR")
    try:
        svc.log_failure(method=method, path=path, error=str(exc), code=code)
    except Exception:
        pass
    if isinstance(exc, InputValidationError):
        return JSONResponse(status_code=400, content=exc.as_dict())
    return JSONResponse(
        status_code=400,
        content={"error": str(exc), "code": code, "field": getattr(exc, "field", None)},
    )


@app.get("/api")
def api_root():
    return {
        "ok": True,
        "service": "qport",
        "runtime": "vercel-fastapi-postgresql",
        "persistence": "postgresql-schema-per-portfolio",
    }


@app.get("/api/health")
def health():
    store = auth()
    return {
        "ok": True,
        "runtime": "VERCEL" if os.environ.get("VERCEL") else "LOCAL",
        "database": "POSTGRESQL",
        "auth_schema": store.schema,
    }


# ---------------------------------------------------------------------------
# Authentication / admin
# ---------------------------------------------------------------------------
@app.get("/api/auth/me")
def auth_me(qport_session: str | None = Cookie(default=None)):
    user = current_user(qport_session)
    if user is None:
        raise ApiError(401, "Not signed in.", "AUTH_REQUIRED")
    return {"ok": True, "user": user}


@app.post("/api/auth/login")
def auth_login(body: dict = Body(default_factory=dict)):
    user, token = auth().login(body.get("username"), body.get("password"))
    response = JSONResponse(status_code=200, content={"ok": True, "user": user})
    _set_session_cookie(response, token)
    return response


@app.post("/api/auth/register")
def auth_register(body: dict = Body(default_factory=dict)):
    user = auth().register(body.get("username"))
    token = auth().create_session(user["id"])
    response = JSONResponse(status_code=201, content={"ok": True, "user": user})
    _set_session_cookie(response, token)
    return response


@app.post("/api/auth/logout")
def auth_logout(qport_session: str | None = Cookie(default=None)):
    auth().logout(qport_session)
    response = JSONResponse(status_code=200, content={"ok": True})
    _clear_session_cookie(response)
    return response


@app.get("/api/auth/users")
def auth_users(qport_session: str | None = Cookie(default=None)):
    require_admin(qport_session)
    return {"ok": True, "users": auth().list_users()}


@app.delete("/api/auth/users/{user_id}")
def auth_delete_user(user_id: int, qport_session: str | None = Cookie(default=None)):
    require_admin(qport_session)
    clear_user_runtime(user_id)
    return auth().delete_user(user_id)


@app.get("/api/admin/users/{user_id}/portfolio")
def admin_user_portfolio(user_id: int, qport_session: str | None = Cookie(default=None)):
    require_admin(qport_session)
    target = admin_target_user(user_id)
    return {
        "ok": True,
        "read_only": True,
        "user": target,
        "dashboard": portfolio(target).dashboard(),
    }


@app.post("/api/auth/admin/password")
def auth_change_admin_password(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    admin = require_admin(qport_session)
    result = auth().change_admin_password(
        admin["id"],
        body.get("current_password"),
        body.get("new_password"),
    )
    response = JSONResponse(status_code=200, content=result)
    _clear_session_cookie(response)
    return response


# ---------------------------------------------------------------------------
# Portfolio registry / selection
# ---------------------------------------------------------------------------
@app.get("/api/portfolios")
def portfolio_list(qport_session: str | None = Cookie(default=None)):
    user = require_portfolio_user(qport_session)
    selected = active_portfolio(user)
    rows = auth().list_portfolios(int(user["id"]))
    return {
        "ok": True,
        "active_portfolio_id": int(selected["id"]),
        "portfolios": rows,
        "scope": {
            "ledger_isolation": "POSTGRESQL_SCHEMA_PER_PORTFOLIO",
            "existing_data_policy": "LEGACY_SCHEMA_IS_DEFAULT_PORTFOLIO",
            "aggregate_ready": True,
        },
    }


@app.post("/api/portfolios")
def portfolio_create(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    created = auth().create_portfolio(int(user["id"]), body.get("name"))
    return JSONResponse(status_code=201, content={"ok": True, "portfolio": created})


@app.patch("/api/portfolios/{portfolio_id}")
def portfolio_rename(
    portfolio_id: int,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    renamed = auth().rename_portfolio(int(user["id"]), portfolio_id, body.get("name"))
    return {"ok": True, "portfolio": renamed}


@app.post("/api/portfolios/{portfolio_id}/select")
def portfolio_select(
    portfolio_id: int,
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    selected = auth().select_portfolio(int(user["id"]), portfolio_id)
    return {"ok": True, "active_portfolio_id": selected["id"], "portfolio": selected}


@app.delete("/api/portfolios/{portfolio_id}")
def portfolio_remove(
    portfolio_id: int,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    if str(body.get("confirmation") or "").strip() != PORTFOLIO_DELETE_CONFIRMATION:
        raise ApiError(
            400,
            f'Type "{PORTFOLIO_DELETE_CONFIRMATION}" to confirm portfolio deletion.',
            "PORTFOLIO_DELETE_CONFIRMATION_REQUIRED",
            "confirmation",
        )
    current = auth().portfolio_for_user(int(user["id"]), portfolio_id)
    if current is None:
        raise AuthError("PORTFOLIO_NOT_FOUND", "Portfolio does not exist.", "portfolio_id")
    clear_portfolio_runtime(int(user["id"]), portfolio_id)
    removed = auth().delete_portfolio(int(user["id"]), portfolio_id)
    return {
        "ok": True,
        "portfolio_deleted": True,
        "portfolio": removed,
        "account_preserved": True,
    }


# ---------------------------------------------------------------------------
# Portfolio reads
# ---------------------------------------------------------------------------
@app.get("/api/portfolio")
def portfolio_dashboard(qport_session: str | None = Cookie(default=None)):
    user = require_portfolio_user(qport_session)
    selected = active_portfolio(user)
    result = portfolio(user).dashboard()
    result["portfolio_context"] = selected
    return result


@app.get("/api/portfolio/holding-symbols")
def portfolio_holding_symbols(qport_session: str | None = Cookie(default=None)):
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    state = derive_state(effective_events(svc.store))
    symbols = sorted(
        str(symbol).upper()
        for symbol, position in state.positions.items()
        if float(position.shares or 0) > 0
    )
    return {"ok": True, "symbols": symbols}


@app.get("/api/portfolio/transactions")
def portfolio_transactions(qport_session: str | None = Cookie(default=None)):
    return {"transactions": portfolio(require_portfolio_user(qport_session)).transactions()}


@app.get("/api/portfolio/transaction-audit")
def portfolio_transaction_audit(qport_session: str | None = Cookie(default=None)):
    return {"corrections": portfolio(require_portfolio_user(qport_session)).transaction_audit()}


@app.get("/api/portfolio/performance")
def portfolio_performance(qport_session: str | None = Cookie(default=None)):
    return portfolio(require_portfolio_user(qport_session)).performance()


@app.get("/api/portfolio/risk")
def portfolio_risk(qport_session: str | None = Cookie(default=None)):
    return portfolio(require_portfolio_user(qport_session)).risk()


@app.get("/api/portfolio/snapshots")
def portfolio_snapshots(qport_session: str | None = Cookie(default=None)):
    return {"snapshots": portfolio(require_portfolio_user(qport_session)).snapshots()}


@app.get("/api/portfolio/market")
def portfolio_market(qport_session: str | None = Cookie(default=None)):
    return portfolio(require_portfolio_user(qport_session)).dashboard().get("market_data") or {}


@app.get("/api/portfolio/preferences")
def portfolio_preferences(qport_session: str | None = Cookie(default=None)):
    return portfolio(require_portfolio_user(qport_session)).preferences()


@app.get("/api/portfolio/operations")
def portfolio_operations(qport_session: str | None = Cookie(default=None)):
    return portfolio(require_portfolio_user(qport_session)).institutional_overview()


@app.get("/api/portfolio/logs")
def portfolio_logs(qport_session: str | None = Cookie(default=None)):
    return portfolio(require_portfolio_user(qport_session)).activity_log(limit=1000)


@app.get("/api/portfolio/dividends/health")
def portfolio_dividend_health(qport_session: str | None = Cookie(default=None)):
    return dividends(require_portfolio_user(qport_session)).health()


@app.get("/api/portfolio/dividends/latest/{symbol}")
def portfolio_latest_dividend(
    symbol: str,
    refresh: bool = Query(default=False),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    ticker = str(symbol or "").upper().strip()
    try:
        result = dividends(user).latest(ticker, force_refresh=refresh)
        svc._log(
            "USER",
            user["username"],
            "CORPORATE_ACTION",
            "DIVIDEND_HISTORY_LOOKUP",
            f"Loaded dividend history for {ticker}: {'FOUND' if result.get('found') else 'NOT_FOUND'} ({result.get('data_origin')}).",
            entity_type="SECURITY",
            entity_id=ticker,
            details={
                "found": result.get("found"),
                "event_count": result.get("event_count"),
                "latest": result.get("latest"),
                "data_origin": result.get("data_origin"),
                "source_counts": result.get("source_counts"),
                "errors": result.get("errors"),
            },
            status="SUCCESS" if result.get("found") else "PARTIAL",
        )
        return result
    except DividendLookupError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": str(exc), "code": "INVALID_TICKER", "field": "symbol"},
        )
    except Exception as exc:
        svc.log_failure(
            method="GET",
            path=f"/api/portfolio/dividends/latest/{ticker}",
            error=str(exc),
            code="DIVIDEND_LOOKUP_FAILED",
        )
        return JSONResponse(
            status_code=502,
            content={"error": str(exc), "code": "DIVIDEND_LOOKUP_FAILED", "field": None},
        )


# ---------------------------------------------------------------------------
# Portfolio writes
# ---------------------------------------------------------------------------
@app.delete("/api/portfolio")
def portfolio_delete_all(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    if str(body.get("confirmation") or "").strip() != PORTFOLIO_DELETE_CONFIRMATION:
        raise ApiError(
            400,
            f'Type "{PORTFOLIO_DELETE_CONFIRMATION}" to confirm portfolio deletion.',
            "PORTFOLIO_DELETE_CONFIRMATION_REQUIRED",
            "confirmation",
        )
    user_id = int(user["id"])
    selected = active_portfolio(user)
    clear_portfolio_runtime(user_id, int(selected["id"]))
    removed = reset_portfolio_schema(user_id, selected["schema_name"])
    PostgresPortfolioStore(user_id, selected["schema_name"])
    return {
        "ok": True,
        "portfolio_cleared": True,
        "portfolio_id": int(selected["id"]),
        "portfolio_name": selected["name"],
        "portfolio_data_removed": removed,
        "other_portfolios_preserved": True,
        "account_preserved": True,
    }


@app.post("/api/portfolio/transactions")
def portfolio_create_transaction(
    request: Request,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    try:
        return JSONResponse(status_code=201, content=svc.append_event(body, created_by=user["username"]))
    except Exception as exc:
        return _service_failure(svc, request.method, request.url.path, exc)


@app.patch("/api/portfolio/transactions/{event_id}")
def portfolio_update_transaction(
    event_id: int,
    request: Request,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    try:
        return svc.update_event(event_id, body, created_by=user["username"])
    except Exception as exc:
        return _service_failure(svc, request.method, request.url.path, exc)


@app.delete("/api/portfolio/transactions/{event_id}")
def portfolio_delete_transaction(
    event_id: int,
    request: Request,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    try:
        return svc.delete_event(event_id, body.get("reason"), created_by=user["username"])
    except Exception as exc:
        return _service_failure(svc, request.method, request.url.path, exc)


@app.post("/api/portfolio/sync")
def portfolio_sync(
    request: Request,
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    try:
        return svc.sync_daily(actor_type="USER", actor_id=user["username"])
    except Exception as exc:
        return _service_failure(svc, request.method, request.url.path, exc)


@app.post("/api/portfolio/reference-weights")
def portfolio_reference_weights(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    return portfolio(require_portfolio_user(qport_session)).set_reference_weights(body.get("weights") or {})


@app.post("/api/portfolio/cash-reserve")
def portfolio_cash_reserve(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    return portfolio(require_portfolio_user(qport_session)).set_cash_reserve(body.get("amount"))


@app.post("/api/portfolio/reconciliation")
def portfolio_reconciliation(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    return JSONResponse(
        status_code=201,
        content=portfolio(user).reconcile_broker(body, created_by=user["username"]),
    )


@app.post("/api/portfolio/corporate-actions/sync")
def portfolio_corporate_action_sync(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    return portfolio(require_portfolio_user(qport_session)).sync_corporate_actions(
        body.get("start"), body.get("end")
    )


@app.post("/api/portfolio/corporate-actions/{action_id}/verify")
def portfolio_corporate_action_verify(
    action_id: int,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    return portfolio(require_portfolio_user(qport_session)).verify_corporate_action(
        action_id, body.get("source_url")
    )


@app.post("/api/portfolio/corporate-actions/{action_id}/receipt")
def portfolio_corporate_action_receipt(
    action_id: int,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    return portfolio(require_portfolio_user(qport_session)).record_corporate_action_receipt(
        action_id, body
    )


@app.post("/api/portfolio/corporate-actions/post")
def portfolio_corporate_action_post(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    return portfolio(require_portfolio_user(qport_session)).post_corporate_action_receipt(
        int(body.get("action_id"))
    )


@app.post("/api/portfolio/settlements/{event_id}/confirm")
def portfolio_confirm_settlement(
    event_id: int,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    return portfolio(require_portfolio_user(qport_session)).confirm_settlement(
        event_id, body.get("note") or ""
    )


@app.post("/api/portfolio/nav/{snapshot_date}/lock")
def portfolio_lock_nav(
    snapshot_date: str,
    qport_session: str | None = Cookie(default=None),
):
    return portfolio(require_portfolio_user(qport_session)).lock_nav(snapshot_date)


@app.post("/api/portfolio/restatements/{restatement_id}/resolve")
def portfolio_resolve_restatement(
    restatement_id: int,
    qport_session: str | None = Cookie(default=None),
):
    return portfolio(require_portfolio_user(qport_session)).resolve_restatement(restatement_id)


@app.post("/api/portfolio/securities/{symbol}/resolve")
def portfolio_resolve_security(
    symbol: str,
    qport_session: str | None = Cookie(default=None),
):
    return portfolio(require_portfolio_user(qport_session)).resolve_security(symbol)


@app.post("/api/portfolio/securities/resolve")
def portfolio_resolve_all_securities(qport_session: str | None = Cookie(default=None)):
    return portfolio(require_portfolio_user(qport_session)).resolve_all_securities()


@app.post("/api/portfolio/securities/{symbol}")
def portfolio_update_security(
    symbol: str,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    return portfolio(require_portfolio_user(qport_session)).update_security(symbol, body)


@app.post("/api/portfolio/activity")
def portfolio_activity(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    return JSONResponse(
        status_code=201,
        content=portfolio(require_portfolio_user(qport_session)).log_client_activity(
            body.get("action"), body.get("details") or {}
        ),
    )


# ---------------------------------------------------------------------------
# Vercel Cron: once per day on Hobby. Schedule it after VN market close.
# ---------------------------------------------------------------------------
def _require_cron_authorization(request: Request) -> None:
    """Fail closed so a missing deployment secret can never expose a global sync."""
    secret = str(os.environ.get("CRON_SECRET") or "").strip()
    if not secret:
        raise ApiError(503, "CRON_SECRET is not configured.", "CRON_NOT_CONFIGURED")

    expected = f"Bearer {secret}"
    provided = str(request.headers.get("authorization") or "")
    if not hmac.compare_digest(provided, expected):
        raise ApiError(401, "Invalid cron authorization.", "CRON_UNAUTHORIZED")


@app.get("/api/cron/daily-sync")
def cron_daily_sync(request: Request):
    _require_cron_authorization(request)

    results: list[dict[str, Any]] = []
    for user in auth().list_users():
        if user.get("role") == "ADMIN":
            continue
        try:
            result = portfolio(user).sync_daily(actor_type="SYSTEM", actor_id="vercel-cron")
            results.append(
                {"user_id": user["id"], "username": user["username"], "ok": True, "result": result}
            )
        except Exception as exc:
            results.append(
                {"user_id": user["id"], "username": user["username"], "ok": False, "error": str(exc)}
            )
    return {"ok": all(row["ok"] for row in results), "users": results}
