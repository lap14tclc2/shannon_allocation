from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse

from app.main import app

# Keep the FastAPI adapter limited to standard FastAPI primitives.  The
# experimental app.frontend() helper is not available in every Vercel Python
# runtime and can crash the function during module import.
_FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"
_INDEX_FILE = _FRONTEND_DIR / "index.html"


@app.get("/{path:path}", include_in_schema=False)
def serve_spa(path: str, request: Request):
    # API routes are registered before this catch-all.  Unknown API paths
    # should remain JSON 404s instead of returning the SPA shell.
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
