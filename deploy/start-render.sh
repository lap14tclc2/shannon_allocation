#!/usr/bin/env bash
set -euo pipefail

export QPORT_AUTH_NAMESPACE="${QPORT_AUTH_NAMESPACE:-/data/qport}"
export R2_PREFIX="${R2_PREFIX:-qport}"
export PORT="${PORT:-10000}"

mkdir -p "$QPORT_AUTH_NAMESPACE" /tmp/litestream-meta

python /app/deploy/restore_from_r2.py

exec litestream replicate \
  -config /app/deploy/litestream.yml \
  -exec "python /app/python/serve.py --host 0.0.0.0 --port ${PORT}"
