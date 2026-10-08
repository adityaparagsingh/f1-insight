#!/usr/bin/env bash
# F1 INSIGHT — start the FastAPI backend (uvicorn).
# Usage:  scripts/run_backend.sh [--reload] [--port 8000]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

PY="$ROOT/backend/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "error: virtualenv not found at $PY — run: python -m venv backend/.venv"
  echo "  then: backend/.venv/bin/pip install -r backend/requirements.txt"
  exit 1
fi

PORT=8000
EXTRA=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --reload) EXTRA+=(--reload) ;;
    --port) shift; PORT="$1" ;;
    *) EXTRA+=("$1") ;;
  esac
  shift
done

mkdir -p "$ROOT/backend/logs"
LOG="$ROOT/backend/logs/api.log"
echo "-> starting uvicorn on 127.0.0.1:$PORT (log: $LOG)"
nohup "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" "${EXTRA[@]}" \
  > "$LOG" 2>&1 &
echo "   pid $! — health: http://127.0.0.1:$PORT/api/health — docs: http://127.0.0.1:$PORT/docs"