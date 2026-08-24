from __future__ import annotations

from app.main import app

# Vercel's FastAPI framework extension serves the built SPA while preserving
# all /api/* routes defined on the FastAPI application. Local development does
# not import this adapter; it runs app.main directly behind Vite's dev proxy.
app.frontend("/", directory="frontend/dist")  # type: ignore[attr-defined]
