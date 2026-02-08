#!/usr/bin/env bash
# scripts/setup.sh — One-time setup for ChiefOps backend
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/.venv"

echo "── Creating Python venv at $VENV_DIR ──"
python3 -m venv "$VENV_DIR"

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "── Installing requirements-dev.txt ──"
pip install --upgrade pip
pip install -r "$BACKEND_DIR/requirements-dev.txt"

echo ""
echo "Setup complete. Start developing:"
echo "  make infra      # Docker services (frontend + mongo + redis)"
echo "  make backend    # Backend on host (separate terminal)"
