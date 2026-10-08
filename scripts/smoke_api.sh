#!/usr/bin/env bash
# F1 INSIGHT — smoke-test the live API: curl a representative set of endpoints
# and report HTTP status codes. Exits nonzero if any endpoint fails.
# Usage:  scripts/smoke_api.sh [base_url]   (default http://127.0.0.1:8000/api)
set -uo pipefail

BASE="${1:-http://127.0.0.1:8000/api}"

check() {
  local label="$1" url="$2"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$url")
  if [[ "$code" == "200" ]]; then
    printf '  ok   %-42s %s\n' "$label" "$code"
  else
    printf '  FAIL %-42s %s\n' "$label" "$code"
    return 1
  fi
}

echo "smoke-testing $BASE"
fail=0

check "health"                  "$BASE/health"
check "seasons"                 "$BASE/seasons"
check "races (limit 5)"         "$BASE/races?limit=5"
check "drivers (limit 5)"       "$BASE/drivers?limit=5"
check "constructors (limit 5)"  "$BASE/constructors?limit=5"
check "circuits (limit 5)"      "$BASE/circuits?limit=5"
check "analytics overview"      "$BASE/analytics/overview"
check "analytics top drivers"   "$BASE/analytics/drivers?sort=points&limit=10"
check "analytics drivers compare" "$BASE/analytics/drivers/compare?ids=1,44"
check "analytics qualifying"    "$BASE/analytics/qualifying"
check "analytics pit-stops"     "$BASE/analytics/pit-stops"
check "analytics position changes" "$BASE/analytics/races/position-changes?limit=5"
check "OLAP rollup"             "$BASE/olap/rollup?dimensions=constructor,season&limit=5"
check "OLAP drilldown season"   "$BASE/olap/drilldown?level=season"
check "OLAP slice"              "$BASE/olap/slice?dimension=season&value=2023"
check "OLAP dice"               "$BASE/olap/dice?season_from=2022&season_to=2024&limit=5"
check "OLAP pivot"              "$BASE/olap/pivot?rows=constructor&cols=season&limit_rows=5"
check "mining clusters"         "$BASE/mining/clusters"
check "mining prediction"       "$BASE/mining/prediction"
check "mining association"      "$BASE/mining/association-rules"
check "mining classification"   "$BASE/mining/classification"
check "insights"                "$BASE/insights"
check "openapi.json"            "http://127.0.0.1:8000/openapi.json"

echo
if [[ "$fail" -eq 0 ]]; then
  echo "ALL ENDPOINTS OK"
else
  echo "some endpoints failed"
fi
exit "$fail"