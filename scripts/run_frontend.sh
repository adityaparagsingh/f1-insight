#!/usr/bin/env bash
# F1 INSIGHT — start the React + Vite frontend dev server.
# Usage:  scripts/run_frontend.sh [--port 5173] [--host 127.0.0.1]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/frontend"

if [[ ! -d node_modules ]]; then
  echo "-> installing frontend dependencies (first run)"
  npm install
fi

HOST=127.0.0.1
PORT=5173
EXTRA=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) shift; PORT="$1" ;;
    --host) shift; HOST="$1" ;;
    *) EXTRA+=("$1") ;;
  esac
  shift
done

mkdir -p "$ROOT/backend/logs"
LOG="$ROOT/backend/logs/vite.log"
echo "-> starting Vite dev server on http://${HOST}:${PORT} (log: $LOG)"
nohup npm run dev -- --host "$HOST" --port "$PORT" "${EXTRA[@]}" > "$LOG" 2>&1 &
echo "   pid $!"