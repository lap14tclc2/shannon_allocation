from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

_FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"
_INDEX_FILE = _FRONTEND_DIR / "index.html"

_startup_error: BaseException | None = None
try:
    from app.main import app  # type: ignore
except BaseException as exc:  # keep the function alive to expose a safe diagnostic
    _startup_error = exc
    app = FastAPI(title="QPort bootstrap")

    @app.get("/{path:path}", include_in_schema=False)
    def startup_failure(path: str, request: Request):
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=503,
                content={
                    "ok": False,
                    "code": "APP_STARTUP_FAILED",
                    "error": "QPort API could not start.",
                    "exception_type": type(_startup_error).__name__,
                    "exception": str(_startup_error)[:500],
                },
            )
        if _INDEX_FILE.is_file():
            return FileResponse(_INDEX_FILE)
        return JSONResponse(
            status_code=503,
            content={"ok": False, "code": "APP_STARTUP_FAILED"},
        )

if _startup_error is None:

    @app.get("/{path:path}", include_in_schema=False)
    def serve_spa(path: str, request: Request):
        # API routes are registered before this catch-all.
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=404,
                content={"ok": False, "error": "Not found", "code": "NOT_FOUND"},
            )

        requested = (_FRONTEND_DIR / path).resolve()
        try:
            requested.relative_to(_FRONTEND_DIR.resolve())
        except ValueError:
            requested = _INDEX_FILE

        if requested.is_file():
            return FileResponse(requested)
        if _INDEX_FILE.is_file():
            return FileResponse(_INDEX_FILE)
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "error": "Frontend build is unavailable.",
                "code": "FRONTEND_BUILD_UNAVAILABLE",
            },
        )
