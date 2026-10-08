#!/usr/bin/env bash
# F1 INSIGHT — run the ETL pipeline (all CLI options are passed through).
# Examples:
#   scripts/run_etl.sh --all
#   scripts/run_etl.sh --season 2024
#   scripts/run_etl.sh --all --rps 2 --retries 8
#   scripts/run_etl.sh --all --stage reference,results
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

PY="$ROOT/backend/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "error: virtualenv not found at $PY"
  exit 1
fi

echo "-> ETL: python -m etl.run $*"
exec "$PY" -m etl.run "$@"