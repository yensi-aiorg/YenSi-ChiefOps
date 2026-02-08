#!/usr/bin/env bash
# scripts/dev.sh — Start the ChiefOps backend on the host
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/.venv"

# ── Activate venv ─────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
  echo "ERROR: Python venv not found at $VENV_DIR"
  echo "Run 'make setup' first."
  exit 1
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ── Load .env from project root ──────────────────────
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env"
  set +a
fi

# ── Launch uvicorn ────────────────────────────────────
export PYTHONPATH="$BACKEND_DIR"
export PYTHONUNBUFFERED=1

cd "$BACKEND_DIR"
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 23101 \
  --reload \
  --reload-dir app \
  --log-level debug
