#!/usr/bin/env bash
# F1 INSIGHT — start the whole stack in one shot.
# Starts (or skips, if already running): MySQL → backend API → frontend, then
# prints the status. Idempotent, safe to re-run at any time.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# ------------------------------------------------------------------ MySQL
if mysqladmin ping -h 127.0.0.1 -P 3306 -uf1user -pf1pass --silent >/dev/null 2>&1; then
  echo "[ok]   MySQL already running"
else
  echo "[..]   starting MySQL (dedicated datadir, requires manual start after reboot)"
  mysqld --datadir=/opt/homebrew/var/mysql-f1 --port=3306 \
    --bind-address=127.0.0.1 --socket=/tmp/mysql.sock >/tmp/f1_mysql.log 2>&1 &
  for _ in $(seq 1 30); do
    mysqladmin ping -h 127.0.0.1 -uf1user -pf1pass --silent >/dev/null 2>&1 && break
    sleep 1
  done
fi

# -------------------------------------------------------------------- API
if curl -s --max-time 3 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  echo "[ok]   API already running"
else
  echo "[..]   starting API"
  "$ROOT/scripts/run_backend.sh"
fi

# ------------------------------------------------------------- frontend
if curl -s --max-time 3 -o /dev/null http://127.0.0.1:5173/; then
  echo "[ok]   Frontend already running"
else
  echo "[..]   starting frontend"
  "$ROOT/scripts/run_frontend.sh"
fi

echo
"$ROOT/scripts/status.sh"