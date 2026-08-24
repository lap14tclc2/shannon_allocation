#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -z "${DATABASE_URL:-}" ]]; then
  cat >&2 <<'EOF'
DATABASE_URL is required.

Example:
  export DATABASE_URL='postgresql://USER:PASSWORD@HOST/DB'
  ./scripts/dev-vercel.sh
EOF
  exit 1
fi

export QPORT_COOKIE_SECURE="${QPORT_COOKIE_SECURE:-0}"
export CRON_SECRET="${CRON_SECRET:-qport-local-dev-only}"

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT INT TERM

cd "$ROOT/frontend"
npm run dev
