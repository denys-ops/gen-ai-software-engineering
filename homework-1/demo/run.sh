#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "Installing dependencies..."
uv sync

echo "Starting server on http://localhost:3000 ..."
PYTHONPATH=src uv run uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
