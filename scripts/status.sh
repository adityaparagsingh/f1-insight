#!/usr/bin/env bash
# F1 INSIGHT — report the health of MySQL, the API and the frontend,
# plus current warehouse row counts.
# Usage:  scripts/status.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ---------------------------------------------------------------- MySQL
DB_URL="mysql+pymysql://f1user:f1pass@127.0.0.1:3306/f1_insight"
if mysqladmin ping --host=127.0.0.1 --port=3306 --user=f1user --password=f1pass \
    --silent >/dev/null 2>&1; then
  echo "[ok]   MySQL is up (127.0.0.1:3306)"
  mysql -uf1user -pf1pass f1_insight -N -e "
    SELECT '  fact_race_result', COUNT(*) FROM fact_race_result
    UNION ALL SELECT '  fact_qualifying', COUNT(*) FROM fact_qualifying
    UNION ALL SELECT '  fact_pit_stop', COUNT(*) FROM fact_pit_stop
    UNION ALL SELECT '  fact_lap', COUNT(*) FROM fact_lap
    UNION ALL SELECT '  fact_driver_standing', COUNT(*) FROM fact_driver_standing
    UNION ALL SELECT '  fact_constructor_standing', COUNT(*) FROM fact_constructor_standing
    UNION ALL SELECT '  TOTAL', (SELECT (SELECT COUNT(*) FROM fact_race_result)
       +(SELECT COUNT(*) FROM fact_qualifying)+(SELECT COUNT(*) FROM fact_pit_stop)
       +(SELECT COUNT(*) FROM fact_lap)+(SELECT COUNT(*) FROM fact_driver_standing)
       +(SELECT COUNT(*) FROM fact_constructor_standing));" 2>/dev/null
else
  echo "[FAIL] MySQL is NOT reachable (127.0.0.1:3306)"
fi

# ------------------------------------------------------------------ API
if curl -s --max-time 5 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  echo "[ok]   API is up (http://127.0.0.1:8000/api)"
  curl -s --max-time 10 http://127.0.0.1:8000/api/health \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('  status:', d['status'], '| db:', d['database'], '| version:', d['version'])" 2>/dev/null || true
else
  echo "[FAIL] API is NOT reachable — run scripts/run_backend.sh"
fi

# ------------------------------------------------------------- frontend
if curl -s --max-time 5 -o /dev/null http://127.0.0.1:5173/ 2>&1; then
  echo "[ok]   Frontend is up (http://127.0.0.1:5173)"
else
  echo "[FAIL] Frontend NOT reachable — run scripts/run_frontend.sh"
fi