#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${1:-}" == "--with-db" ]]; then
  docker compose -f docker-compose.vercel.yml up -d postgres
fi

export DATABASE_URL="${DATABASE_URL:-postgresql://qport:qport@127.0.0.1:5432/qport}"
export QPORT_COOKIE_SECURE="${QPORT_COOKIE_SECURE:-0}"

python -m uvicorn api.index:app --reload --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT INT TERM

cd "$ROOT/frontend"
npm run dev
