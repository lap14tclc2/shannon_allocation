#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${1:-}" == "--with-db" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker was requested with --with-db but docker is not installed or not on PATH." >&2
    echo "Omit --with-db and export DATABASE_URL for an external PostgreSQL database." >&2
    exit 1
  fi
  docker compose -f docker-compose.vercel.yml up -d --wait postgres
  export DATABASE_URL="${DATABASE_URL:-postgresql://qport:qport@127.0.0.1:5432/qport}"
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  cat >&2 <<'EOF'
DATABASE_URL is required.

Without Docker:
  export DATABASE_URL='postgresql://USER:PASSWORD@HOST/DB?sslmode=require'
  ./scripts/dev-vercel.sh

Docker remains optional:
  ./scripts/dev-vercel.sh --with-db
EOF
  exit 1
fi

export QPORT_COOKIE_SECURE="${QPORT_COOKIE_SECURE:-0}"
export CRON_SECRET="${CRON_SECRET:-qport-local-dev-only}"

python -m uvicorn api.index:app --reload --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT INT TERM

cd "$ROOT/frontend"
npm run dev
