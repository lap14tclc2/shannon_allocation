#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
export NODEJS_VERSION="${NODEJS_VERSION:-22}"

mkdir -p "$HOME/qport-data/auth-v1"

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r python/requirements-alwaysdata.txt

cd "$ROOT/frontend"
npm ci
npm run build
npm run build:ssr

echo
echo "QPort AlwaysData setup complete."
echo "User Program command:"
echo "$ROOT/.venv/bin/python $ROOT/python/serve_alwaysdata.py"
