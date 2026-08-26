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
    qport_session: str | None = Cookie(default=None),
):
    require_admin(qport_session)
    catalog = list_securities(offset, limit, exchange)
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


@app.post("/api/admin/finance-data/{symbol}/retry")
def admin_finance_data_retry(
    symbol: str,
    qport_session: str | None = Cookie(default=None),
):
    admin = require_admin(qport_session)
    from portfolio.finance_catalog import crawl_symbol
    result = crawl_symbol(symbol, int(admin["id"]), retry_failed_only=True)
    if result.get("code") == "CRAWL_RUNTIME_INVALID":
        raise ApiError(503, result["message"], result["code"])
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
            rows, _ = list_activity_page(
                source["store"],
                page=source["next_page"],
                page_size=page_size,
                category=category,
                actor_type=actor_type,
                status=status,
                q=q,
            )
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
    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "logs": visible,
        "pagination": {"page": page, "page_size": page_size, "total": total, "pages": pages},
        "filters": {"category": category or "ALL", "actor_type": actor_type or "ALL", "status": status or "ALL", "q": q or ""},
        "categories": ["SYSTEM", "AUTH", "PORTFOLIO", "TRANSACTION", "CORPORATE_ACTION", "SYNC"],
        "integrity": {"status": "DEFERRED" if failed_reads == 0 else "BROKEN", "records": total, "read_failures": failed_reads},
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
    # Normal user routes are database-only in every runtime. Provider crawling
    # belongs to the admin/local-worker ingestion path and never runs as a
    # cache-aside request from a user endpoint.
    return JSONResponse(status_code=404, content={
        "found": False,
        "symbol": ticker,
        "events": [],
        "event_count": 0,
        "data_origin": "DATABASE_CANONICAL",
        "code": "FINANCE_DATA_MISSING",
        "error": "contact admin",
        "source_counts": {},
        "errors": [],
    })


@app.get("/api/portfolio/valuation/{symbol}")
def portfolio_symbol_valuation(
    symbol: str,
    qport_session: str | None = Cookie(default=None),
):
    """Build a valuation from validated Finance DB facts only."""
    import re
    from dataclasses import asdict
    from datetime import datetime, timezone
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
    require_portfolio_user(qport_session)
    ticker = str(symbol or "").upper().strip()
    if not re.fullmatch(r"[A-Z0-9]{3,10}", ticker):
        raise ApiError(400, "Invalid stock symbol.", "INVALID_TICKER", "symbol")

    svc = portfolio(current_user(qport_session))
    latest_row = svc.store.latest_price(ticker)
    market_price = latest_row.get("close") if latest_row else None
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
    entity_type = EntityType.BANK if any(token in f"{sector or ''} {company_type}".lower() for token in ("bank", "ngân hàng")) else EntityType.NORMAL_ENTERPRISE

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
            value=value,
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

    if bvps is None and equity is not None and shares > 0:
        bvps = equity / shares
    if eps is None and shares > 0:
        eps = net_income / shares

    def percent(value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return value * Decimal("100") if abs(value) <= Decimal("1") else value

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
    )
    response = JSONResponse(status_code=200, content=jsonable_encoder({
        "ok": True,
        "report": {
            **asdict(report),
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