from __future__ import annotations

import hmac
import json
import os
import sys
import time
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from fastapi import Body, Cookie, FastAPI, Query, Request
from fastapi.encoders import jsonable_encoder
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
from portfolio.financial_data import FinancialDataStore, StatementType
from portfolio.finance_catalog import get_canonical_dividend_events, latest_documents_for_user, list_securities, valuation_snapshot_from_catalog
from portfolio.value_engine import ValuationEngine
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
_requested_portfolio_id: ContextVar[int | None] = ContextVar(
    "qport_requested_portfolio_id",
    default=None,
)


class ApiError(Exception):
    def __init__(self, status: int, error: str, code: str, field: str | None = None) -> None:
        super().__init__(error)
        self.status = int(status)
        self.payload = {"error": error, "code": code, "field": field}


@app.middleware("http")
async def bind_portfolio_scope(request: Request, call_next):
    """Bind portfolio scope and emit portable structured request telemetry."""
    raw = str(request.headers.get("X-QPort-Portfolio-Id") or "").strip()
    requested = None
    if raw:
        try:
            requested = int(raw)
            if requested <= 0:
                raise ValueError
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "X-QPort-Portfolio-Id must be a positive integer.",
                    "code": "INVALID_PORTFOLIO_SCOPE",
                    "field": "portfolio_id",
                },
            )
    request_id = (
        str(request.headers.get("X-Request-ID") or "").strip()[:128]
        or str(request.headers.get("X-Vercel-ID") or "").strip()[:128]
        or uuid.uuid4().hex
    )
    started = time.perf_counter()
    print(json.dumps({
        "level": "info", "event": "request.started", "request_id": request_id,
        "method": request.method, "path": request.url.path,
        "environment": "vercel" if os.environ.get("VERCEL") else "local",
    }, ensure_ascii=False), flush=True)
    token = _requested_portfolio_id.set(requested)
    try:
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        print(json.dumps({
            "level": "info", "event": "request.completed", "request_id": request_id,
            "method": request.method, "path": request.url.path,
            "status_code": response.status_code, "duration_ms": duration_ms,
        }, ensure_ascii=False), flush=True)
        return response
    except Exception as exc:
        print(json.dumps({
            "level": "error", "event": "request.failed", "request_id": request_id,
            "method": request.method, "path": request.url.path,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "error_type": type(exc).__name__, "error": str(exc)[:500],
        }, ensure_ascii=False), flush=True)
        raise
    finally:
        _requested_portfolio_id.reset(token)


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
    user_id = int(user["id"])
    requested_id = _requested_portfolio_id.get()
    if requested_id is not None:
        selected = auth().portfolio_for_user(user_id, requested_id)
        if selected is None:
            raise ApiError(
                404,
                "Portfolio does not exist or does not belong to this account.",
                "PORTFOLIO_NOT_FOUND",
                "portfolio_id",
            )
        return selected
    return auth().active_portfolio(user_id)


def public_portfolio(row: dict) -> dict:
    return {
        key: value
        for key, value in row.items()
        if key not in {"schema_name", "user_id"}
    }


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


@app.get("/api/admin/finance-data")
def admin_finance_data(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    exchange: str | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    qport_session: str | None = Cookie(default=None),
):
    require_admin(qport_session)
    catalog = list_securities(offset, limit, exchange, status, q)
    # Crawling is an external-worker concern. Keep the capability explicit so
    # the admin UI can disable controls before a request reaches the backend.
    runtime_name = "vercel" if os.environ.get("VERCEL") else "local"
    worker_enabled = (
        runtime_name != "vercel"
        and str(os.environ.get("QPORT_FINANCE_RUNTIME") or "").strip().lower() in {"local", "worker"}
    )
    catalog["runtime"] = {
        "name": runtime_name,
        "can_crawl": worker_enabled,
        "read_only": not worker_enabled,
        "message": (
            "Crawl chạy bằng Local/Worker; production chỉ đọc database."
            if not worker_enabled else
            "Local/Worker có thể crawl và đồng bộ dữ liệu."
        ),
    }
    return {"ok": True, **catalog}


@app.post("/api/admin/finance-data/universe")
def admin_finance_data_universe(qport_session: str | None = Cookie(default=None)):
    require_admin(qport_session)
    from portfolio.finance_catalog import sync_universe
    result = sync_universe()
    if result.get("code") == "CRAWL_RUNTIME_INVALID":
        raise ApiError(503, result["message"], result["code"])
    return result

@app.post("/api/admin/finance-data/crawl-all")
def admin_finance_data_crawl_all(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    admin = require_admin(qport_session)
    from portfolio.finance_catalog import enqueue_crawl_all
    exchange = str(body.get("exchange") or "").upper().strip() or None
    result = enqueue_crawl_all(int(admin["id"]), exchange)
    if result.get("code") == "CRAWL_RUNTIME_INVALID":
        raise ApiError(503, result["message"], result["code"])
    if result.get("code") == "CRAWL_EXCHANGE_UNSUPPORTED":
        raise ApiError(400, result["message"], result["code"], "exchange")
    return result


@app.post("/api/admin/finance-data/crawl")
def admin_finance_data_crawl(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    admin = require_admin(qport_session)
    from portfolio.finance_catalog import crawl_symbol
    symbol = str(body.get("symbol") or "").upper().strip()
    if not symbol:
        raise ApiError(400, "Provide a symbol for an explicit crawl request.", "SYMBOL_REQUIRED", "symbol")
    result = crawl_symbol(symbol, int(admin["id"]))
    if result.get("code") == "CRAWL_RUNTIME_INVALID":
        raise ApiError(503, result["message"], result["code"])
    return result


@app.get("/api/admin/finance-data/{symbol}/audit")
def admin_finance_data_audit(
    symbol: str,
    qport_session: str | None = Cookie(default=None),
):
    require_admin(qport_session)
    from portfolio.finance_catalog import valuation_readiness_audit
    return {"ok": True, **valuation_readiness_audit(symbol)}


@app.post("/api/admin/finance-data/{symbol}/retry")
def admin_finance_data_retry(
    symbol: str,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    admin = require_admin(qport_session)
    from portfolio.finance_catalog import crawl_symbol
    if not body:
        raise ApiError(400, "Retry requires one document identity.", "DOCUMENT_TARGET_REQUIRED")
    result = crawl_symbol(
        symbol,
        int(admin["id"]),
        retry_failed_only=True,
        document_filter=body,
    )
    if result.get("code") == "CRAWL_RUNTIME_INVALID":
        raise ApiError(503, result["message"], result["code"])
    if result.get("code") in {"INVALID_DOCUMENT_TARGET", "DOCUMENT_NOT_IN_WORKER_SCOPE"}:
        raise ApiError(400, result.get("message", "Invalid document target."), result["code"])
    return result


@app.get("/api/portfolio/finance-data/{symbol}")
def portfolio_finance_data(
    symbol: str,
    qport_session: str | None = Cookie(default=None),
):
    require_portfolio_user(qport_session)
    result = latest_documents_for_user(symbol)
    if not result.get("ok"):
        raise ApiError(404, result["message"], result["code"], "symbol")
    return result


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
        "portfolios": [public_portfolio(row) for row in rows],
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
    return JSONResponse(status_code=201, content={"ok": True, "portfolio": public_portfolio(created)})


@app.patch("/api/portfolios/{portfolio_id}")
def portfolio_rename(
    portfolio_id: int,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    renamed = auth().rename_portfolio(int(user["id"]), portfolio_id, body.get("name"))
    return {"ok": True, "portfolio": public_portfolio(renamed)}


@app.post("/api/portfolios/{portfolio_id}/select")
def portfolio_select(
    portfolio_id: int,
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    selected = auth().select_portfolio(int(user["id"]), portfolio_id)
    return {"ok": True, "active_portfolio_id": selected["id"], "portfolio": public_portfolio(selected)}


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
        "portfolio": public_portfolio(removed),
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
    result["portfolio_context"] = public_portfolio(selected)
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


@app.get("/api/admin/logs")
def admin_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    category: str | None = Query(default=None),
    actor_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    qport_session: str | None = Cookie(default=None),
):
    """Admin-only log query with bounded per-portfolio cursor-style merging.

    Each schema is queried in occurred_at/id order in small pages. The
    application merges only the requested global prefix; it never loads a
    5,000-row history from every portfolio before sorting.
    """
    require_admin(qport_session)
    from portfolio.activity import list_activity_page

    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 200))
    target_end = page * page_size
    sources: list[dict[str, Any]] = []
    total = 0
    failed_reads = 0
    failed_portfolios: list[dict[str, Any]] = []

    for user in auth().list_users():
        if user.get("role") == "ADMIN":
            continue
        for selected in auth().list_portfolios(int(user["id"])):
            try:
                store = PostgresPortfolioStore(int(user["id"]), selected["schema_name"])
                rows, count = list_activity_page(
                    store,
                    page=1,
                    page_size=page_size,
                    category=category,
                    actor_type=actor_type,
                    status=status,
                    q=q,
                )
                decorated = [{
                    **row,
                    "user_id": int(user["id"]),
                    "username": user["username"],
                    "portfolio_id": int(selected["id"]),
                    "portfolio_name": selected["name"],
                } for row in rows]
                sources.append({
                    "store": store,
                    "rows": decorated,
                    "count": int(count),
                    "next_page": 2,
                    "user": user,
                    "portfolio": selected,
                })
                total += int(count)
            except Exception:
                failed_reads += 1
                failed_portfolios.append({
                    "user_id": int(user["id"]),
                    "username": user.get("username"),
                    "portfolio_id": int(selected["id"]),
                    "portfolio_name": selected.get("name"),
                })

    # K-way merge of already ordered per-schema pages. Memory is bounded by
    # one page per portfolio plus the requested page prefix.
    selected_rows: list[dict] = []
    target_end = min(target_end, total)
    while len(selected_rows) < target_end:
        best_index = None
        best_key = None
        for index, source in enumerate(sources):
            if not source["rows"]:
                continue
            row = source["rows"][0]
            key = (
                str(row.get("occurred_at") or ""),
                int(row.get("id") or 0),
                int(row.get("portfolio_id") or 0),
            )
            if best_key is None or key > best_key:
                best_key = key
                best_index = index
        if best_index is None:
            break
        source = sources[best_index]
        selected_rows.append(source["rows"].pop(0))
        if not source["rows"] and (source["next_page"] - 1) * page_size < source["count"]:
            try:
                rows, _ = list_activity_page(
                    source["store"],
                    page=source["next_page"],
                    page_size=page_size,
                    category=category,
                    actor_type=actor_type,
                    status=status,
                    q=q,
                )
            except Exception:
                failed_reads += 1
                failed_portfolios.append({
                    "user_id": int(source["user"]["id"]),
                    "username": source["user"].get("username"),
                    "portfolio_id": int(source["portfolio"]["id"]),
                    "portfolio_name": source["portfolio"].get("name"),
                })
                source["count"] = 0
                rows = []
            source["next_page"] += 1
            source["rows"] = [{
                **row,
                "user_id": int(source["user"]["id"]),
                "username": source["user"]["username"],
                "portfolio_id": int(source["portfolio"]["id"]),
                "portfolio_name": source["portfolio"]["name"],
            } for row in rows]

    start = (page - 1) * page_size
    visible = selected_rows[start:start + page_size]
    complete = failed_reads == 0
    pages = max(1, (total + page_size - 1) // page_size) if complete else None
    return {
        "logs": visible,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total if complete else None,
            "pages": pages,
            "partial": not complete,
            "failed_portfolios": failed_portfolios,
        },
        "filters": {"category": category or "ALL", "actor_type": actor_type or "ALL", "status": status or "ALL", "q": q or ""},
        "categories": ["SYSTEM", "AUTH", "PORTFOLIO", "TRANSACTION", "CORPORATE_ACTION", "SYNC"],
        "integrity": {"status": "DEFERRED" if complete else "BROKEN", "records": total if complete else None, "read_failures": failed_reads},
    }


@app.get("/api/portfolio/logs")
def portfolio_logs(qport_session: str | None = Cookie(default=None)):
    # The legacy path is intentionally admin-only; normal users cannot inspect logs.
    return admin_logs(qport_session=qport_session)


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
    canonical_events = get_canonical_dividend_events(ticker)
    if canonical_events:
        events = []
        for event in canonical_events:
            events.append({
                **event,
                "source": "qport_finance_canonical",
                "cross_source_match": event.get("quality_status") == "VERIFIED",
            })
        result = {
            "found": True,
            "symbol": ticker,
            "events": events,
            "event_count": len(events),
            "latest": events[0] if events else None,
            "data_origin": "DATABASE_CANONICAL",
            "source_counts": {"qport_finance": len(events)},
            "errors": [],
        }
        svc._log(
            "USER", user["username"], "CORPORATE_ACTION", "DIVIDEND_HISTORY_LOOKUP",
            f"Loaded canonical dividend history for {ticker}.",
            entity_type="SECURITY", entity_id=ticker,
            details={"event_count": len(events), "data_origin": "DATABASE_CANONICAL"},
            status="SUCCESS",
        )
        return result
    # Normal user routes are database-only in every runtime. When a stock has no
    # recorded dividend events in DB, return 200 with found=false and empty events.
    return {
        "found": False,
        "symbol": ticker,
        "events": [],
        "event_count": 0,
        "data_origin": "DATABASE_CANONICAL",
        "code": "FINANCE_DATA_MISSING",
        "error": None,
        "source_counts": {},
        "errors": [],
    }


@app.get("/api/portfolio/valuation/{symbol}")
def portfolio_symbol_valuation(
    symbol: str,
    qport_session: str | None = Cookie(default=None),
):
    """Build a valuation from validated Finance DB facts only."""
    import re
    from dataclasses import asdict
    from datetime import date, datetime, timedelta, timezone
    from decimal import Decimal, InvalidOperation

    from portfolio.financial_data.models import (
        CanonicalFact,
        ConsolidationScope,
        EntityType,
        FactIdentityKey,
        PeriodType,
        QualityStatus,
        StatementType,
    )
    from portfolio.finance_catalog import _schema_connection, FINANCE_SCHEMA, valuation_snapshot_from_catalog
    user = require_portfolio_user(qport_session)
    ticker = str(symbol or "").upper().strip()
    if not re.fullmatch(r"[A-Z0-9]{3,10}", ticker):
        raise ApiError(400, "Invalid stock symbol.", "INVALID_TICKER", "symbol")

    svc = portfolio(user)
    latest_row = svc.store.latest_price(ticker)
    market_price = latest_row.get("close") if latest_row else None
    if market_price is None or market_price <= 0:
        try:
            today_str = svc.today_vn()
            today_d = date.fromisoformat(today_str)
            start_str = (today_d - timedelta(days=30)).isoformat()
            from portfolio.market_data import AutoMarketData, frame_to_price_rows
            market_data = AutoMarketData()
            df = market_data.daily_history(ticker, start_str, today_str)
            if not df.empty:
                price_rows = frame_to_price_rows(ticker, df, source="vndirect")
                if price_rows:
                    svc.store.upsert_market_prices(price_rows)
                    market_price = price_rows[-1].get("close")
        except Exception:
            pass
    snapshot = valuation_snapshot_from_catalog(ticker, market_price)
    if not snapshot.get("ok"):
        return JSONResponse(status_code=404, content={
            "ok": False,
            "code": snapshot.get("code", "FINANCE_DATA_INCOMPLETE"),
            "error": snapshot.get("message", "contact admin"),
            "field": None,
            "symbol": ticker,
            "missing": snapshot.get("missing", []),
        })

    if str(snapshot.get("symbol") or "").upper() != ticker:
        raise ApiError(502, "Provider returned data for a different symbol.", "VALUATION_SYMBOL_MISMATCH")

    def normalized_key(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    def field(rows: list[dict], *aliases: str, reverse: bool = False):
        wanted = [normalized_key(alias) for alias in aliases]
        source = list(reversed(rows or [])) if reverse else list(rows or [])
        for row in source:
            if not isinstance(row, dict):
                continue
            normalized = {normalized_key(key): value for key, value in row.items()}
            for alias in wanted:
                for key, value in normalized.items():
                    if value is not None and value != "" and (key == alias or key.endswith(alias)):
                        return value
        return None

    def number(value) -> Decimal | None:
        if value is None or value == "":
            return None
        try:
            parsed = Decimal(str(value).replace(",", ""))
            return parsed if parsed.is_finite() else None
        except (InvalidOperation, ValueError, TypeError):
            return None

    income = list(snapshot.get("income_statement") or [])
    balance = list(snapshot.get("balance_sheet") or [])
    cash_flow = list(snapshot.get("cash_flow") or [])
    ratios = list(snapshot.get("ratios") or [])
    profile = list(snapshot.get("profile") or [])
    prices = list(snapshot.get("prices") or [])
    fetched_at = str(snapshot.get("fetched_at") or datetime.now(timezone.utc).isoformat())

    current_price = number(field(prices, "close", "close_price", reverse=True))
    net_income = number(field(income, "net_profit", "net_profit_after_tax", "profit_after_tax", "net_income"))
    operating_profit = number(field(income, "operating_profit", "profit_from_operation"))
    total_debt = number(field(balance, "total_debt", "debt", "borrowings"))
    short_debt = number(field(balance, "short_term_borrowings", "short_term_debt"))
    long_debt = number(field(balance, "long_term_borrowings", "long_term_debt"))
    cash = number(field(balance, "cash_and_cash_equivalents", "cash", "cash_equivalents"))
    short_investments = number(field(balance, "short_term_investments", "short_term_investment"))
    equity = number(field(balance, "equity", "owners_equity", "owner_equity"))
    depreciation = number(field(cash_flow, "depreciation", "depreciation_amortization"))
    capex = number(field(cash_flow, "capex", "purchase_of_fixed_assets", "fixed_asset_purchases"))
    operating_cash = number(field(cash_flow, "operating_cash_flow", "net_cash_from_operating_activities"))

    eps = number(field(ratios, "eps", "earning_per_share"))
    bvps = number(field(ratios, "bvps", "book_value_per_share"))
    pe = number(field(ratios, "pe", "price_to_earnings"))
    pb = number(field(ratios, "pb", "price_to_book"))
    roe = number(field(ratios, "roe", "return_on_equity"))
    dividend_yield = number(field(ratios, "dividend_yield", "cash_dividend_yield"))
    shares = number(field(ratios, "outstanding_share", "outstanding_shares", "shares_outstanding"))

    sector = field(profile, "industry", "industry_name", "sector", "icb_name3", "icb_name2")
    company_type = str(field(profile, "company_type", "type", "industry") or "")
    is_bank = any(token in f"{sector or ''} {company_type}".lower() for token in ("bank", "ngân hàng"))
    entity_type = EntityType.BANK if is_bank else EntityType.NORMAL_ENTERPRISE

    if current_price is None or current_price <= 0:
        raise ApiError(422, f"Provider không trả giá mới nhất hợp lệ cho {ticker}.", "VALUATION_PRICE_MISSING")
    if net_income is None or shares is None or shares <= 0:
        raise ApiError(422, f"BCTC mới nhất của {ticker} chưa đủ lợi nhuận và số cổ phiếu lưu hành để định giá.", "VALUATION_DATA_INCOMPLETE")

    fiscal_year_raw = number(snapshot.get("fiscal_year"))
    fiscal_quarter_raw = number(snapshot.get("fiscal_quarter"))
    if fiscal_year_raw is None or not 2000 <= fiscal_year_raw <= 2200:
        raise ApiError(422, "Finance DB thiếu kỳ báo cáo hợp lệ.", "VALUATION_DATA_INCOMPLETE")
    fiscal_year = int(fiscal_year_raw)
    fiscal_quarter = int(fiscal_quarter_raw) if fiscal_quarter_raw and 1 <= fiscal_quarter_raw <= 4 else None
    period_end = str(snapshot.get("period_end") or "")
    if not period_end:
        raise ApiError(422, "Finance DB thiếu ngày kết thúc kỳ báo cáo.", "VALUATION_DATA_INCOMPLETE")

    facts: list[CanonicalFact] = []

    def add_fact(code: str, statement_type: StatementType, value: Decimal | None, period_type: PeriodType) -> None:
        if value is None:
            return
        # Standardize unit scale: financial statements are expressed in billion VND (tỷ đồng) except for share counts
        fact_val = value if code == "IS.SHARES.OUTSTANDING" or abs(value) >= Decimal("1000000000") else value * Decimal("1000000000")
        fact_id = f"db-{ticker.lower()}-{code.lower().replace('.', '-')}-{fetched_at[:19]}"
        facts.append(CanonicalFact(
            canonical_fact_id=fact_id,
            identity=FactIdentityKey(
                security_id=f"sec-{ticker.lower()}",
                statement_type=statement_type,
                period_end=period_end,
                period_type=period_type,
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code=code,
                currency="VND",
            ),
            value=fact_val,
            quality_status=QualityStatus.SINGLE_SOURCE,
            decision_id=f"db-{ticker.lower()}-{fetched_at[:19]}",
            winning_candidate_id=f"finance-db-{ticker.lower()}-{code.lower()}",
            candidate_ids=[],
            observed_at=fetched_at,
            valid_from=fetched_at,
            reason=f"Validated Finance DB fact from {snapshot.get('provider')}",
        ))

    add_fact("IS.PROFIT.NET", StatementType.INCOME_STATEMENT, net_income, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)
    add_fact("IS.PROFIT.OPERATING", StatementType.INCOME_STATEMENT, operating_profit, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)
    add_fact("BS.DEBT.TOTAL", StatementType.BALANCE_SHEET, total_debt, PeriodType.INSTANT)
    add_fact("BS.LIABILITIES.SHORT_TERM_BORROWINGS", StatementType.BALANCE_SHEET, short_debt, PeriodType.INSTANT)
    add_fact("BS.LIABILITIES.LONG_TERM_BORROWINGS", StatementType.BALANCE_SHEET, long_debt, PeriodType.INSTANT)
    add_fact("BS.ASSETS.CASH_AND_EQUIVALENTS", StatementType.BALANCE_SHEET, cash, PeriodType.INSTANT)
    add_fact("BS.ASSETS.SHORT_TERM_INVESTMENTS", StatementType.BALANCE_SHEET, short_investments, PeriodType.INSTANT)
    add_fact("CF.OPERATING.DEPRECIATION", StatementType.CASH_FLOW, depreciation, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)
    add_fact("CF.CAPEX", StatementType.CASH_FLOW, capex, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)
    add_fact("CF.OPERATING.NET", StatementType.CASH_FLOW, operating_cash, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)
    add_fact("IS.SHARES.OUTSTANDING", StatementType.INCOME_STATEMENT, shares, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)

    scaled_net_income = net_income * Decimal("1000000000") if net_income is not None and abs(net_income) < Decimal("1000000000") else net_income
    scaled_equity = equity * Decimal("1000000000") if equity is not None and abs(equity) < Decimal("1000000000") else equity

    if bvps is None and scaled_equity is not None and shares > 0:
        bvps = scaled_equity / shares
    if eps is None and scaled_net_income is not None and shares > 0:
        eps = scaled_net_income / shares
    if pe is None and current_price is not None and eps is not None and eps > 0:
        pe = current_price / eps
    if pb is None and current_price is not None and bvps is not None and bvps > 0:
        pb = current_price / bvps
    if roe is None and scaled_net_income is not None and scaled_equity is not None and scaled_equity > 0:
        roe = (scaled_net_income / scaled_equity) * Decimal("100")

    def percent(value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return value * Decimal("100") if abs(value) <= Decimal("1") else value

    # Query multi-year historical series for long-term compounding analysis
    financial_history: list[dict[str, Any]] = []
    with _schema_connection(FINANCE_SCHEMA) as db:
        hist_rows = db.execute(
            """SELECT fiscal_year, line_item_code, value
               FROM canonical_facts
               WHERE symbol = ? AND period_type = 'FY' AND fiscal_quarter IS NULL
               ORDER BY fiscal_year ASC""",
            (ticker,),
        ).fetchall()
        by_year: dict[int, dict[str, Decimal]] = {}
        for r in hist_rows:
            by_year.setdefault(int(r["fiscal_year"]), {})[str(r["line_item_code"])] = Decimal(str(r["value"]))

        for y in sorted(by_year.keys()):
            items = by_year[y]
            np_val = items.get("IS.PROFIT.NET")
            eq_val = items.get("BS.EQUITY.TOTAL")
            cfo_val = items.get("CF.OPERATING.NET")
            capex_val = items.get("CF.CAPEX")
            shares_val = items.get("IS.SHARES.OUTSTANDING")
            debt_val = items.get("BS.DEBT.TOTAL")
            cash_val = items.get("BS.ASSETS.CASH_AND_EQUIVALENTS")
            rev_val = items.get("IS.REVENUE.NET")

            np_scaled = float(np_val * Decimal("1000000000")) if np_val is not None else None
            eq_scaled = float(eq_val * Decimal("1000000000")) if eq_val is not None else None
            cfo_scaled = float(cfo_val * Decimal("1000000000")) if cfo_val is not None else None
            capex_scaled = float(abs(capex_val) * Decimal("1000000000")) if capex_val is not None else None
            fcf_scaled = (cfo_scaled - capex_scaled) if (cfo_scaled is not None and capex_scaled is not None) else None
            debt_scaled = float(debt_val * Decimal("1000000000")) if debt_val is not None else None
            cash_scaled = float(cash_val * Decimal("1000000000")) if cash_val is not None else None
            shares_count = float(shares_val) if shares_val is not None else None

            roe_hist = round((float(np_val) / float(eq_val) * 100), 1) if (np_val is not None and eq_val and eq_val > Decimal("0")) else None
            conversion_hist = round((cfo_scaled / np_scaled * 100), 1) if (cfo_scaled is not None and np_scaled and np_scaled > 0) else None

            financial_history.append({
                "fiscal_year": y,
                "revenue": float(rev_val * Decimal("1000000000")) if rev_val is not None else None,
                "net_profit": np_scaled,
                "equity": eq_scaled,
                "roe": roe_hist,
                "operating_cash_flow": cfo_scaled,
                "free_cash_flow": fcf_scaled,
                "cash_conversion_ratio": conversion_hist,
                "shares_outstanding": shares_count,
                "total_debt": debt_scaled,
                "cash_and_equivalents": cash_scaled,
            })

    # Compute Value Investing Pillar Metrics
    np_series = [(h["fiscal_year"], h["net_profit"]) for h in financial_history if h.get("net_profit") is not None]
    cagr_5y = None
    if len(np_series) >= 5 and np_series[-5][1] and np_series[-1][1] and np_series[-5][1] > 0 and np_series[-1][1] > 0:
        y_start, v_start = np_series[-5]
        y_end, v_end = np_series[-1]
        span = y_end - y_start
        if span > 0:
            cagr_5y = round(((v_end / v_start) ** (1.0 / span) - 1.0) * 100, 1)

    # 1. Earnings Quality: Average 5Y Cash Conversion
    recent_conversions = [h["cash_conversion_ratio"] for h in financial_history[-5:] if h.get("cash_conversion_ratio") is not None]
    avg_cash_conversion_5y = round(sum(recent_conversions) / len(recent_conversions), 1) if recent_conversions else None
    latest_conversion = financial_history[-1].get("cash_conversion_ratio") if financial_history else None

    # 2. Financial Fortress: Debt Payback Period (Non-bank) or Capital Adequacy / Net Cash
    latest_hist = financial_history[-1] if financial_history else {}
    latest_debt = latest_hist.get("total_debt") or 0
    latest_cash = latest_hist.get("cash_and_equivalents") or 0
    net_debt_calc = 0.0 if is_bank else max(0.0, float(latest_debt - latest_cash))
    latest_cfo = latest_hist.get("operating_cash_flow") or 0
    debt_payback_years = round(net_debt_calc / latest_cfo, 1) if (latest_cfo and latest_cfo > 0 and net_debt_calc > 0) else 0.0

    fortress_status = "FORTRESS" if (is_bank or net_debt_calc == 0) else ("STRONG" if debt_payback_years < 3.0 else "MODERATE")
    fortress_diag = "Cơ cấu tài chính ngân hàng chuẩn mực (Huy động tiền gửi kinh doanh)." if is_bank else ("Pháo đài tiền mặt ròng dồi dào (Không có áp lực nợ)." if net_debt_calc == 0 else (f"Khả năng hoàn trả nợ ròng nhanh ({debt_payback_years} năm)." if debt_payback_years < 3.0 else f"Cần theo dõi đòn bẩy nợ ({debt_payback_years} năm hoàn nợ)."))

    # 3. Capital Allocation: 5Y Average ROE & Share Dilution
    recent_roes = [h["roe"] for h in financial_history[-5:] if h.get("roe") is not None]
    avg_roe_5y = round(sum(recent_roes) / len(recent_roes), 1) if recent_roes else None

    shares_series = [(h["fiscal_year"], h["shares_outstanding"]) for h in financial_history if h.get("shares_outstanding") is not None]
    share_dilution_5y = None
    true_dilution_diag = "Tỷ lệ sở hữu của cổ đông hiện hữu được duy trì tốt."
    if len(shares_series) >= 5 and shares_series[-5][1] and shares_series[-1][1] and shares_series[-5][1] > 0:
        s_old = shares_series[-5][1]
        s_new = shares_series[-1][1]
        with _schema_connection(FINANCE_SCHEMA) as db:
            stock_div_rows = db.execute(
                """SELECT stock_ratio FROM dividend_canonical 
                   WHERE symbol = ? AND dividend_type = 'STOCK_DIVIDEND' 
                   AND effective_event_date >= ?""",
                (ticker, f"{shares_series[-5][0]}-01-01")
            ).fetchall()
            cumulative_stock_div = 1.0
            for r in stock_div_rows:
                if r["stock_ratio"]:
                    cumulative_stock_div *= (1.0 + float(r["stock_ratio"]))
            
            expected_shares_from_bonus = s_old * cumulative_stock_div
            economic_dilution_pct = max(0.0, ((s_new - expected_shares_from_bonus) / s_old) * 100)
            share_dilution_5y = round(economic_dilution_pct, 1)

            if cumulative_stock_div > 1.05 and economic_dilution_pct < 5.0:
                true_dilution_diag = f"Số lượng CP tăng chủ yếu do chia thưởng/cổ tức cổ phiếu ({(cumulative_stock_div-1)*100:.0f}%), không gây pha loãng kinh tế thực cho cổ đông."
            elif economic_dilution_pct >= 10.0:
                true_dilution_diag = f"Có phát hành thêm/ESOP gây pha loãng kinh tế thực ({share_dilution_5y}% trong 5 năm)."
            else:
                true_dilution_diag = "Tỷ lệ sở hữu của cổ đông hiện hữu được bảo toàn tốt."

    value_investor_pillars = {
        "earnings_quality": {
            "latest_cash_conversion": latest_conversion,
            "avg_cash_conversion_5y": avg_cash_conversion_5y,
            "status": "EXCELLENT" if (avg_cash_conversion_5y and avg_cash_conversion_5y >= 90) else ("GOOD" if (avg_cash_conversion_5y and avg_cash_conversion_5y >= 70) else "WATCH"),
            "diagnosis": "Dòng tiền kinh doanh dồi dào, lợi nhuận chuyển hóa thành tiền mặt cao." if (avg_cash_conversion_5y and avg_cash_conversion_5y >= 90) else "Lợi nhuận có độ trễ hoặc thâm dụng vốn lưu động.",
        },
        "financial_fortress": {
            "net_debt_vnd": net_debt_calc,
            "debt_payback_years": debt_payback_years,
            "status": fortress_status,
            "diagnosis": fortress_diag,
        },
        "capital_allocation": {
            "avg_roe_5y": avg_roe_5y,
            "share_dilution_5y_pct": share_dilution_5y,
            "status": "EXCELLENT" if (avg_roe_5y and avg_roe_5y >= 18 and (share_dilution_5y is None or share_dilution_5y < 5)) else ("GOOD" if (avg_roe_5y and avg_roe_5y >= 13) else "WATCH"),
            "diagnosis": true_dilution_diag,
        },
    }

    report = ValuationEngine.evaluate(
        symbol=ticker,
        facts=facts,
        current_market_price=current_price,
        shares_outstanding=shares,
        diluted_shares_estimate=shares,
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
        entity_type=entity_type,
        fundamentals={
            "sector": sector,
            "eps": eps,
            "bvps": bvps,
            "pe": pe,
            "pb": pb,
            "roe": percent(roe),
            "dividend_yield": percent(dividend_yield),
            "source": snapshot.get("provider"),
            "as_of": fetched_at,
        },
        financial_history=financial_history,
        value_investor_pillars=value_investor_pillars,
    )
    response = JSONResponse(status_code=200, content=jsonable_encoder({
        "ok": True,
        "symbol": ticker,
        "valuation_snapshot": snapshot,
        "report": {
            **asdict(report),
            "financial_history_10y": financial_history,
            "cagr_5y_net_profit": cagr_5y,
            "value_investor_pillars": value_investor_pillars,
            "data_freshness": {
                "cache": "DATABASE",
                "fetched_at": fetched_at,
                "provider": snapshot.get("provider"),
                "api_variant": snapshot.get("api_variant"),
                "fallback_from": snapshot.get("fallback_from"),
                "fallback_reason": snapshot.get("fallback_reason"),
                "source_urls": snapshot.get("source_urls") or [],
            },
        },
        "data_freshness": {
            "cache": "DATABASE",
            "fetched_at": fetched_at,
            "provider": snapshot.get("provider"),
            "api_variant": snapshot.get("api_variant"),
            "symbol_verified": True,
        },
        "informational_only": True,
    }))
    response.headers["Cache-Control"] = "private, no-store, max-age=0, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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


@app.post("/api/portfolio/transactions/import/preview")
def portfolio_preview_transaction_import(
    request: Request,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    try:
        return svc.preview_import(body, created_by=user["username"])
    except Exception as exc:
        return _service_failure(svc, request.method, request.url.path, exc)


@app.post("/api/portfolio/transactions/import")
def portfolio_commit_transaction_import(
    request: Request,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    try:
        return JSONResponse(status_code=201, content=svc.import_events(body, created_by=user["username"]))
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
    selected = active_portfolio(user)
    svc = portfolio(user)
    try:
        sync_result = svc.sync_daily(actor_type="USER", actor_id=user["username"])
        dashboard = svc.dashboard()
        dashboard["portfolio_context"] = public_portfolio(selected)
        return {**sync_result, "dashboard": dashboard}
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