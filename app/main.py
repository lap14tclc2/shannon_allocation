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

import psycopg
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
from portfolio.corrections import (
    begin_request_memo,
    clear_request_memo,
    end_request_memo,
)  # noqa: E402
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
# Bound the long-lived per-portfolio service caches so a long-running local
# process cannot grow without limit. Vercel instances are short-lived anyway,
# but the cap protects local dev and any persistent worker.
MAX_CACHED_SERVICES = 128
_requested_portfolio_id: ContextVar[int | None] = ContextVar(
    "qport_requested_portfolio_id",
    default=None,
)


@app.on_event("startup")
def app_startup_warmup():
    """Warm up expensive candidate evaluation caches asynchronously on application startup."""
    try:
        from portfolio.value_engine.munger_candidates import warm_munger_candidates_cache_async
        warm_munger_candidates_cache_async()
    except Exception:
        pass


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
    _, memo_token = begin_request_memo()
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
        end_request_memo(memo_token)
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


@app.exception_handler(psycopg.Error)
def handle_psycopg_error(_request: Request, exc: psycopg.Error):
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "message": "Không thể kết nối cơ sở dữ liệu PostgreSQL. Vui lòng kiểm tra dịch vụ PostgreSQL.",
                "code": "DATABASE_UNAVAILABLE",
                "details": str(exc),
            }
        },
    )


@app.exception_handler(RuntimeError)
def handle_runtime_error(_request: Request, exc: RuntimeError):
    msg = str(exc)
    if "DATABASE_URL" in msg:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "message": "DATABASE_URL chưa được cấu hình.",
                    "code": "DATABASE_NOT_CONFIGURED",
                    "details": msg,
                }
            },
        )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Lỗi hệ thống.",
                "code": "INTERNAL_SERVER_ERROR",
                "details": msg,
            }
        },
    )


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


def _cache_service(key: tuple[int, int], svc: AutomatedPortfolioService) -> AutomatedPortfolioService:
    if len(_services) >= MAX_CACHED_SERVICES:
        # Evict one arbitrary (oldest-inserted) entry to bound memory. The next
        # request recreates it cheaply; services are stateless across requests.
        try:
            _services.pop(next(iter(_services)))
        except StopIteration:
            pass
    _services[key] = svc
    return svc


def portfolio(user: dict) -> AutomatedPortfolioService:
    user_id = int(user["id"])
    selected = active_portfolio(user)
    key = (user_id, int(selected["id"]))
    svc = _services.get(key)
    if svc is None:
        svc = AutomatedPortfolioService(
            store=PostgresPortfolioStore(user_id, selected["schema_name"])
        )
        _cache_service(key, svc)
    return svc


def dividends(user: dict) -> SqliteDividendService:
    user_id = int(user["id"])
    selected = active_portfolio(user)
    key = (user_id, int(selected["id"]))
    service = _dividend_services.get(key)
    if service is None:
        service = SqliteDividendService(portfolio(user).store, stop_on_first_data=False)
        if len(_dividend_services) >= MAX_CACHED_SERVICES:
            try:
                _dividend_services.pop(next(iter(_dividend_services)))
            except StopIteration:
                pass
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


def _crawl_enabled() -> bool:
    """Provider crawling (TCBS fetch) UI gating: show only off-Vercel (local/dev).

    The stricter ``QPORT_FINANCE_RUNTIME`` gate is still enforced by
    ``crawl_symbol``/``_validate_crawl_runtime`` at crawl time — this flag only
    decides whether the crawl button is visible.
    """
    return not bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))


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

@app.post("/api/admin/prices/backfill")
def admin_prices_backfill(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    """Backfill market_prices cho toàn universe (mã có BCTC nhưng chưa có giá).

    user-test.md §19: screener chỉ bao phủ mã có giá → cần giá để tính MOS.
    Threaded fetch VNDirect/Vnstock; persist vào market_prices.
    """
    require_admin(qport_session)
    from portfolio.finance_catalog import backfill_market_prices
    limit = body.get("limit") or None
    result = backfill_market_prices(limit=int(limit) if limit else None)
    return {"ok": True, **result}

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
    svc = portfolio(require_portfolio_user(qport_session))
    # Market metadata only needs current positions + prices, not the full
    # dashboard pipeline (risk, performance, snapshots, suggestions).
    state = derive_state(effective_events(svc.store))
    symbols = sorted(state.positions)
    prices = svc.store.latest_prices(symbols)
    return svc._market_metadata(symbols, prices)


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


@app.post("/api/admin/activity/reanchor")
def admin_activity_reanchor(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    """Re-anchor a broken activity chain (PREV_HASH_MISMATCH / historical break).

    P0 audit (feedback 31/08): a BROKEN chain with PREV_HASH_MISMATCH is the
    exact case ``reanchor_activity_chain`` is designed to migrate: it starts a
    NEW verified segment anchored to the last known-good hash WITHOUT rewriting
    history (legacy segment stays BROKEN_HISTORICAL, new appends VERIFIED_FROM_ANCHOR).

    Body (all optional):
      - user_id / portfolio_id: re-anchor a single portfolio. When omitted the
        endpoint re-anchors every non-admin portfolio whose chain is BROKEN.
      - reason / operator: migration metadata (defaults: "feedback-20260831").
    """
    require_admin(qport_session)
    from portfolio.activity import reanchor_activity_chain, verify_activity_chain

    user_id = body.get("user_id")
    portfolio_id = body.get("portfolio_id")
    operator = str(body.get("operator") or "admin-feedback-20260831")[:100]
    reason = str(body.get("reason") or "re-anchor after PREV_HASH_MISMATCH")[:200]

    targets: list[dict[str, Any]] = []
    if user_id is not None:
        user = admin_target_user(int(user_id))
        if portfolio_id is not None:
            selected = next((p for p in auth().list_portfolios(int(user["id"])) if int(p["id"]) == int(portfolio_id)), None)
            if selected is None:
                raise ApiError(404, "Portfolio not found.", "PORTFOLIO_NOT_FOUND", "portfolio_id")
            targets.append({"store": PostgresPortfolioStore(int(user["id"]), selected["schema_name"]), "label": f"user {user['id']} / portfolio {selected['id']}"})
        else:
            for selected in auth().list_portfolios(int(user["id"])):
                targets.append({"store": PostgresPortfolioStore(int(user["id"]), selected["schema_name"]), "label": f"user {user['id']} / portfolio {selected['id']}"})
    else:
        for user in auth().list_users():
            if user.get("role") == "ADMIN":
                continue
            for selected in auth().list_portfolios(int(user["id"])):
                targets.append({"store": PostgresPortfolioStore(int(user["id"]), selected["schema_name"]), "label": f"user {user['id']} / portfolio {selected['id']}"})

    results: list[dict[str, Any]] = []
    for target in targets:
        store = target["store"]
        integrity = verify_activity_chain(store)
        if integrity["status"] not in ("BROKEN",):
            results.append({"portfolio": target["label"], "reanchored": False, "status": integrity["status"], "records": integrity["records"]})
            continue
        result = reanchor_activity_chain(store, operator=operator, reason=reason)
        results.append({
            "portfolio": target["label"],
            "reanchored": result.get("reanchored"),
            "status": result.get("status"),
            "records": result.get("records"),
            "anchor_id": result.get("anchor_id"),
            "genesis_anchor": result.get("genesis_anchor"),
            "anchor": result.get("anchor"),
        })
    return {"ok": True, "operator": operator, "reason": reason, "results": results}


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


@app.get("/api/portfolio/screener")
def portfolio_screener_endpoint(
    mos_filter: str | None = "buffett_qualified",
    min_liquidity: float | None = 10.0,
    min_score: int | None = None,
    exchange: str | None = None,
    search: str | None = None,
    sort_by: str = "mos",
    limit: int = 200,
    qport_session: str | None = Cookie(default=None),
):
    """Screen universe by Buffett Margin of Safety, Liquidity, and Quality."""
    require_portfolio_user(qport_session)
    from portfolio.screener import get_screener_results
    result = get_screener_results(
        mos_filter=mos_filter,
        min_liquidity=min_liquidity,
        min_score=min_score,
        exchange=exchange,
        search=search,
        sort_by=sort_by,
        limit=limit,
    )
    result["crawl_enabled"] = _crawl_enabled()
    return result


# ---------------------------------------------------------------------------
# Allocation (Buffett Core + Thorp Overlay) — advisory, read-only
# ---------------------------------------------------------------------------
def _allocation_inputs(svc, extra_symbols: list[str] | None = None) -> tuple[list[dict], dict, float, str]:
    """Read current portfolio state for allocation without writing anything."""
    from portfolio.accounting import derive_state
    from portfolio.corrections import effective_events

    state = derive_state(effective_events(svc.store))
    symbols = sorted(state.positions)
    history_symbols = sorted(set(symbols) | {str(s).upper() for s in (extra_symbols or []) if s})
    prices = svc.store.latest_prices(symbols)
    base_rows, _ = svc._mark_to_market(state, prices)
    histories = svc._histories(history_symbols)
    cash = float(state.cash)
    return base_rows, histories, cash, svc.today_vn()


def _allocation_valuation_map(symbols: list[str]) -> dict:
    """Build symbol -> valuation signal from the canonical scored universe.

    DB-first: reads the cached screener universe; prices are persisted in the
    finance DB by the existing screener pipeline. No allocation-specific crawl.
    """
    from portfolio.allocation.eligibility import signal_from_screener_item
    from portfolio.screener import compute_all_screener_scores

    items = compute_all_screener_scores(force_refresh=False)
    signals = {item["symbol"]: signal_from_screener_item(item) for item in items}
    return {str(s).upper(): signals.get(str(s).upper()) for s in symbols}


def _allocation_candidates() -> list[dict]:
    """Candidate discovery reuses the existing Screener (never executes trades)."""
    from portfolio.screener import get_screener_results

    result = get_screener_results(
        mos_filter="all",
        min_liquidity=10.0,
        sort_by="mos",
        limit=80,
    )
    return result.get("items", [])


def _validate_allocation_changes(changes) -> list[dict]:
    import re

    if not isinstance(changes, list) or len(changes) > 50:
        raise ApiError(400, "Simulation changes must be a list of up to 50 items.", "INVALID_CHANGES", "changes")
    clean: list[dict] = []
    for index, change in enumerate(changes):
        if not isinstance(change, dict):
            raise ApiError(400, "Each change must be an object.", "INVALID_CHANGES", "changes")
        symbol = str(change.get("symbol") or "").upper().strip()
        if not re.fullmatch(r"[A-Z0-9]{3,10}", symbol):
            raise ApiError(400, "Invalid stock symbol.", "INVALID_SYMBOL", "changes")
        try:
            target = float(change.get("target_weight"))
        except (TypeError, ValueError):
            raise ApiError(400, "target_weight must be a number between 0 and 1.", "INVALID_TARGET_WEIGHT", "changes")
        if not (0.0 <= target <= 1.0):
            raise ApiError(400, "target_weight must be a number between 0 and 1.", "INVALID_TARGET_WEIGHT", "changes")
        clean.append({"symbol": symbol, "target_weight": round(target, 6)})
    return clean


@app.get("/api/portfolio/allocation")
def portfolio_allocation(qport_session: str | None = Cookie(default=None)):
    """Read-only advisory allocation for the active portfolio.

    Returns portfolio verdict, holding decisions, candidate opportunities,
    suggested cash range, risk summary and reason codes. Never executes a trade.
    """
    from portfolio.allocation.service import AllocationService

    user = require_portfolio_user(qport_session)
    selected = active_portfolio(user)
    svc = portfolio(user)
    try:
        candidate_items = _allocation_candidates()
        candidate_symbols = [str(item["symbol"]).upper() for item in candidate_items if item.get("symbol")]
        base_rows, histories, cash, as_of = _allocation_inputs(svc, extra_symbols=candidate_symbols)
        valuation_map = _allocation_valuation_map([r["symbol"] for r in base_rows])
        report = AllocationService().evaluate(
            position_rows=base_rows,
            histories=histories,
            cash=cash,
            portfolio_id=int(selected["id"]),
            as_of=as_of,
            valuation_map=valuation_map,
            candidate_items=candidate_items,
        )
        payload = report.to_dict()
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(500, f"Lỗi tính toán phân bổ vốn: {exc}", "ALLOCATION_CALCULATION_ERROR")

    return {
        "ok": True,
        "allocation": payload,
        "portfolio_context": public_portfolio(selected),
        "no_action_required": bool(payload["no_action_required"]),
        "informational_only": True,
        "policy": "INFORMATION_ONLY",
    }


@app.post("/api/portfolio/allocation/simulate")
def portfolio_allocation_simulate(
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    """Simulate hypothetical position changes (before/after risk).

    The simulation is advisory and in-memory only: it never persists a
    transaction and never changes holdings or cash.
    """
    from portfolio.allocation.service import AllocationService

    user = require_portfolio_user(qport_session)
    selected = active_portfolio(user)
    svc = portfolio(user)
    changes = _validate_allocation_changes(body.get("changes") or [])
    try:
        candidate_items = _allocation_candidates()
        candidate_symbols = [str(item["symbol"]).upper() for item in candidate_items if item.get("symbol")]
        base_rows, histories, cash, as_of = _allocation_inputs(svc, extra_symbols=candidate_symbols)
        valuation_map = _allocation_valuation_map([r["symbol"] for r in base_rows])
        report = AllocationService().simulate(
            changes=changes,
            position_rows=base_rows,
            histories=histories,
            cash=cash,
            portfolio_id=int(selected["id"]),
            as_of=as_of,
            valuation_map=valuation_map,
            candidate_items=candidate_items,
        )
        payload = report.to_dict()
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(500, f"Lỗi mô phỏng phân bổ vốn: {exc}", "ALLOCATION_SIMULATION_ERROR")

    return {
        "ok": True,
        "allocation": payload,
        "informational_only": True,
        "persisted": False,
        "policy": "SIMULATION_ONLY_NO_PERSISTENCE",
    }


@app.get("/api/portfolio/valuation/{symbol}")
def portfolio_symbol_valuation(
    symbol: str,
    qport_session: str | None = Cookie(default=None),
):
    """Build a valuation from validated Finance DB facts only using canonical builder."""
    from portfolio.canonical_valuation import build_canonical_valuation
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    result = build_canonical_valuation(symbol, store=svc.store)
    if not result.get("ok"):
        return JSONResponse(status_code=404 if result.get("code") in {"FINANCE_DATA_INCOMPLETE", "VALUATION_DATA_INCOMPLETE"} else 400, content=result)

    payload = {
        **result,
        "informational_only": True,
        "crawl_enabled": _crawl_enabled(),
    }
    response = JSONResponse(status_code=200, content=jsonable_encoder(payload))
    response.headers["Cache-Control"] = "private, no-store, max-age=0, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/api/portfolio/business/{symbol}/munger")
def portfolio_symbol_munger_analysis(
    symbol: str,
    qport_session: str | None = Cookie(default=None),
):
    """Munger-style long-term financial statement analysis engine for symbol."""
    from portfolio.canonical_valuation import build_canonical_valuation
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    ticker = str(symbol or "").upper().strip()
    val_data = build_canonical_valuation(ticker, store=svc.store)
    return {
        "ok": True,
        "symbol": ticker,
        "munger_analysis": val_data.get("munger_analysis", {}),
        "valuation": val_data,
    }


@app.get("/api/portfolio/crawl-status")
def portfolio_crawl_status(qport_session: str | None = Cookie(default=None)):
    """Whether TCBS crawling is available (local/worker) vs read-only (Vercel)."""
    require_portfolio_user(qport_session)
    return {"ok": True, "crawl_enabled": _crawl_enabled()}


@app.post("/api/portfolio/valuation/{symbol}/crawl")
def portfolio_symbol_valuation_crawl(
    symbol: str,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    """Fetch/backfill the TCBS financial history for one symbol (7–10Y full-cycle).

    Optional body ``{ "token": "Bearer ..." }`` persists the user's TCBS bearer
    token (stored in the portfolio's app_meta) before crawling. On 401/403 the
    endpoint returns ``TCBS_AUTH_REQUIRED`` so the UI can prompt for a token.
    """
    import re as _re
    from portfolio.finance_catalog import crawl_symbol, TcbsAuthRequiredError

    user = require_portfolio_user(qport_session)
    ticker = str(symbol or "").upper().strip()
    if not _re.fullmatch(r"[A-Z0-9]{3,10}", ticker):
        raise ApiError(400, "Invalid stock symbol.", "INVALID_TICKER", "symbol")

    if not _crawl_enabled():
        raise ApiError(
            403,
            "Crawl dữ liệu TCBS chỉ khả dụng trên môi trường local/worker "
            "(Vercel là database-read-only). Chạy bộ lọc/crawl ở local để cập nhật lịch sử BCTC.",
            "CRAWL_DISABLED_ON_VERCEL",
        )

    svc = portfolio(user)
    token = str(body.get("token") or "").strip()
    if token:
        # Persist the user's token for later crawls (stored in the portfolio DB).
        svc.store.set_meta("tcbs_bearer_token", token)
    else:
        stored = svc.store.get_meta("tcbs_bearer_token")
        if stored:
            token = stored

    if not token:
        raise ApiError(
            401,
            "Cần TCBS Bearer token để crawl. Mở tcinvest.tcbs.com.vn → F12 → Network → "
            "chọn request apiextaws → copy header Authorization (Bearer eyJ…).",
            "TCBS_AUTH_REQUIRED",
        )

    try:
        result = crawl_symbol(ticker, int(user["id"]), token=token, force_refresh=bool(body.get("force_refresh")))
    except TcbsAuthRequiredError as exc:
        raise ApiError(401, str(exc), "TCBS_AUTH_REQUIRED")
    except Exception as exc:
        raise ApiError(502, f"Crawl TCBS thất bại: {exc}", "CRAWL_FAILED")

    if result.get("code") == "CRAWL_RUNTIME_INVALID":
        raise ApiError(503, result["message"], result["code"])
    return result


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


@app.get("/api/portfolio/securities/lookup")
@app.get("/api/portfolio/search/symbols")
def portfolio_securities_lookup(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    qport_session: str | None = Cookie(default=None),
):
    require_portfolio_user(qport_session)
    from portfolio.finance_catalog import search_securities_lookup
    return {"ok": True, "results": search_securities_lookup(q, limit)}


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


# ------------------------------------------------------------------
# Terminal Portfolio Position Management (TASK-150)
# ------------------------------------------------------------------

@app.get("/api/portfolio/positions")
def portfolio_positions_view(
    refresh: bool = Query(default=False),
    qport_session: str | None = Cookie(default=None),
):
    return portfolio(require_portfolio_user(qport_session)).positions_view(force_refresh=refresh)


@app.post("/api/portfolio/positions")
def portfolio_add_position(
    request: Request,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    result = svc.add_position(
        body.get("symbol", ""),
        body.get("quantity"),
        body.get("average_cost"),
        created_by=user["username"],
    )
    return JSONResponse(status_code=201, content=jsonable_encoder(result))


@app.put("/api/portfolio/positions/{symbol}")
def portfolio_update_position(
    symbol: str,
    body: dict = Body(default_factory=dict),
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    return portfolio(user).update_position(
        symbol,
        body.get("quantity"),
        body.get("average_cost"),
        created_by=user["username"],
    )


@app.delete("/api/portfolio/positions/{symbol}")
def portfolio_delete_position(
    symbol: str,
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    return portfolio(user).delete_position(symbol, created_by=user["username"])


@app.get("/api/portfolio/positions/{symbol}/split-adjustment")
def portfolio_get_split_adjustment(
    symbol: str,
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    return portfolio(user).get_split_adjustment(symbol)


@app.post("/api/portfolio/positions/{symbol}/auto-split-adjust")
def portfolio_apply_split_adjustment(
    symbol: str,
    qport_session: str | None = Cookie(default=None),
):
    user = require_portfolio_user(qport_session)
    return portfolio(user).apply_split_adjustment(symbol, created_by=user["username"])


@app.get("/api/portfolio/cash")
def portfolio_get_cash(qport_session: str | None = Cookie(default=None)):
    return portfolio(require_portfolio_user(qport_session)).get_cash()


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
    return portfolio(require_portfolio_user(qport_session)).record_activity(body)

# ---------------------------------------------------------------------------
# Buffett-Munger Workspaces API Routes (Terminal, Business, Capital, History)
# ---------------------------------------------------------------------------

@app.get("/api/portfolio/personal-finance")
def api_portfolio_personal_finance_get(qport_session: str | None = Cookie(default=None)):
    """Retrieve persisted personal balance sheet for current user/portfolio."""
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    pb_data = svc.get_personal_balance_sheet()
    return {
        "ok": True,
        "configured": pb_data is not None,
        "personal_balance_sheet": pb_data,
    }


@app.post("/api/portfolio/personal-finance")
def api_portfolio_personal_finance_post(body: dict, qport_session: str | None = Cookie(default=None)):
    """Persist personal balance sheet for current user/portfolio."""
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    return svc.set_personal_balance_sheet(body)


@app.get("/api/portfolio/terminal")
def api_portfolio_terminal(qport_session: str | None = Cookie(default=None)):
    """Buffett-Munger Terminal Homepage aggregate data endpoint."""
    from portfolio.personal_finance.models import CapitalDurabilityMetrics, PersonalBalanceSheetInput
    from portfolio.personal_finance.service import calculate_capital_durability
    from portfolio.personal_finance.stress import run_crash_job_loss_stress_engine
    from portfolio.policy.context_builder import build_decision_context
    from portfolio.policy.engine import evaluate_decision
    from portfolio.value_engine.business_review import evaluate_business_review
    from portfolio.value_engine.value_trap import evaluate_value_trap

    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    dash = svc.dashboard()
    pf = dash.get("portfolio") if isinstance(dash.get("portfolio"), dict) else dash
    positions = pf.get("positions") or []
    cash = float(pf.get("cash") or 0.0)
    equity = float(pf.get("equity_value") or 0.0)

    # Personal Fortress
    pb_data = svc.get_personal_balance_sheet()
    if pb_data:
        pb_input = PersonalBalanceSheetInput.from_dict(pb_data)
        durability = calculate_capital_durability(pb_input, portfolio_equity_value=equity, deployable_portfolio_cash=cash)
        stress_input = pb_input
    else:
        pb_input = None
        durability = CapitalDurabilityMetrics(
            survival_reserve_status="UNKNOWN",
            status="UNKNOWN",
            available_long_term_capital=0.0,
        )
        stress_input = PersonalBalanceSheetInput()

    largest_pos = max([float(p.get("market_value") or 0.0) for p in positions], default=0.0)
    stress_results = run_crash_job_loss_stress_engine(stress_input, equity, cash, largest_pos)

    # Decision Matrix & Exceptions
    decision_items = []
    exceptions = []

    for pos in positions:
        sym = pos.get("symbol")
        item = svc.runtime_decision(sym)
        decision_items.append(item)

        if item.get("decision") in ("BUILD_RESERVE_FIRST", "REVIEW_BUSINESS", "WAIT_FOR_MOS", "SELL_REVIEW", "SELL"):
            exceptions.append(item)

    # Coach Summary
    if durability.survival_reserve_status == "UNSAFE":
        coach_summary = "CẢNH BÁO PHÁO ĐÀI: Quỹ dự phòng cá nhân dưới mức an toàn. Hãy ưu tiên tích lũy dự phòng trước khi mua thêm cổ phiếu."
    elif durability.survival_reserve_status == "UNKNOWN":
        coach_summary = "CẢNH BÁO THIẾU DỮ LIỆU: Chưa cấu hình Bảng Cân Đối Cá Nhân. Mọi hành động MUA bị cấm."
    elif exceptions:
        coach_summary = f"Hệ thống phát hiện {len(exceptions)} mục cần chú ý (Xem danh sách Cần Chú Ý bên dưới)."
    else:
        coach_summary = "KHÔNG CẦN HÀNH ĐỘNG (NO ACTION REQUIRED). Danh mục đang hoạt động lành mạnh. Không có cơ hội đạt Biên an toàn để giải ngân mới."

    return {
        "ok": True,
        "fortress": durability.to_dict(),
        "stress_scenarios": [s.to_dict() for s in stress_results],
        "holdings_matrix": decision_items,
        "exceptions": exceptions,
        "coach_summary": coach_summary,
    }


@app.get("/api/portfolio/business/candidates")
@app.get("/api/portfolio/business-candidates")
def api_portfolio_business_candidates(
    tier: str | None = "all",
    liquidity: str | None = "all",
    search: str | None = None,
    min_val_billion: float | None = None,
    limit: int = 50,
    qport_session: str | None = Cookie(default=None),
):
    """Get Munger long-term investment candidates across canonical universe."""
    require_portfolio_user(qport_session)
    from portfolio.value_engine.munger_candidates import get_munger_candidates

    return get_munger_candidates(
        tier=tier,
        liquidity=liquidity,
        search=search,
        min_val_billion=min_val_billion,
        limit=limit,
    )


@app.get("/api/portfolio/business/{symbol}")
def api_portfolio_business(symbol: str, qport_session: str | None = Cookie(default=None)):
    """Buffett-Munger Business Workspace detail endpoint."""
    from portfolio.canonical_valuation import build_canonical_valuation

    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    ticker = str(symbol or "").strip().upper()

    runtime_data = svc.runtime_decision(ticker)
    canonical_val = build_canonical_valuation(ticker, store=svc.store)
    munger_analysis = canonical_val.get("munger_analysis", {})

    munger_checklist = [
        {"question": "Tại sao luận điểm đầu tư này có thể sai?", "key": "thesis_failure"},
        {"question": "Điều gì có thể làm suy yếu vĩnh viễn Moat của doanh nghiệp?", "key": "moat_erosion"},
        {"question": "Chuyện gì xảy ra nếu lợi nhuận bình thường giảm 30–50%?", "key": "earnings_drop"},
        {"question": "Nếu giá trị nội tại bị ước tính cao hơn 30% thì sao?", "key": "iv_overestimate"},
        {"question": "Tôi có thể tiếp tục nắm giữ nếu giá cổ phiếu giảm tiếp 50%?", "key": "price_drop_holding"},
        {"question": "Tôi có tiếp tục sở hữu nếu thị trường đóng cửa 5 năm?", "key": "market_closure"},
        {"question": "Tôi đang mua giá trị hay chỉ phản ứng với giá sập?", "key": "value_vs_reaction"},
        {"question": "Bằng chứng thực tế nào sẽ chứng minh tôi đã sai?", "key": "falsification_evidence"},
    ]

    return {
        "ok": True,
        "symbol": ticker,
        "munger_analysis": munger_analysis,
        "canonical_valuation": canonical_val,
        "holding": runtime_data.get("holding"),
        "valuation": runtime_data.get("valuation"),
        "business_review": runtime_data.get("business_review"),
        "value_trap": runtime_data.get("value_trap"),
        "decision": runtime_data.get("evidence"),
        "munger_checklist": munger_checklist,
    }


@app.get("/api/portfolio/capital")
def api_portfolio_capital(qport_session: str | None = Cookie(default=None)):
    """Buffett-Munger Capital Workspace endpoint."""
    from portfolio.personal_finance.models import CapitalDurabilityMetrics, PersonalBalanceSheetInput
    from portfolio.personal_finance.service import calculate_capital_durability

    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    dash = svc.dashboard()
    pf = dash.get("portfolio") if isinstance(dash.get("portfolio"), dict) else dash
    cash = float(pf.get("cash") or 0.0)
    equity = float(pf.get("equity_value") or 0.0)

    pb_data = svc.get_personal_balance_sheet()
    if pb_data:
        pb_input = PersonalBalanceSheetInput.from_dict(pb_data)
        durability = calculate_capital_durability(pb_input, portfolio_equity_value=equity, deployable_portfolio_cash=cash)
    else:
        pb_input = PersonalBalanceSheetInput()
        durability = CapitalDurabilityMetrics(
            survival_reserve_status="UNKNOWN",
            status="UNKNOWN",
            available_long_term_capital=0.0,
        )

    return {
        "ok": True,
        "configured": pb_data is not None,
        "personal_finance_input": pb_input.to_dict(),
        "durability": durability.to_dict(),
        "buckets": {
            "survival_reserve": pb_input.safe_liquid_assets,
            "compounding_asset": equity,
            "near_term_liability_fund": pb_input.near_term_liabilities,
            "opportunity_cash": durability.opportunity_cash,
            "available_long_term_capital": durability.available_long_term_capital,
        },
    }


@app.get("/api/portfolio/history")
def api_portfolio_history(qport_session: str | None = Cookie(default=None)):
    """Buffett-Munger Compounding History Workspace endpoint."""
    user = require_portfolio_user(qport_session)
    svc = portfolio(user)
    dash = svc.dashboard()
    pf = dash.get("portfolio") if isinstance(dash.get("portfolio"), dict) else dash

    return {
        "ok": True,
        "nav_history": dash.get("history") or pf.get("history") or [],
        "transactions": svc.transactions()[:100],
        "summary": {
            "total_nav": pf.get("nav"),
            "total_cost": pf.get("cost_basis"),
            "unrealized_pnl": pf.get("unrealized_pnl"),
            "return_pct": pf.get("unrealized_return_pct"),
        },
    }


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