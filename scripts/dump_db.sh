#!/usr/bin/env bash
# F1 INSIGHT — dump the local MySQL warehouse for cloud deployment.
# Usage:
#   scripts/dump_db.sh [output.sql.gz]     (default: backend/logs/f1_insight_dump.sql.gz)
#
# The dump includes schema + data of the six fact tables and dimension
# tables. Load it into your hosted MySQL with:
#   zcat backend/logs/f1_insight_dump.sql.gz | mysql -h <host> -u <user> -p f1_insight
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/backend/logs/f1_insight_dump.sql.gz}"
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-f1user}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-f1pass}"
MYSQL_DB="${MYSQL_DB:-f1_insight}"

mkdir -p "$(dirname "$OUT")"
echo "-> dumping ${MYSQL_DB} @ ${MYSQL_HOST}:${MYSQL_PORT} -> $OUT"
mysqldump --single-transaction --quick --no-tablespaces \
  -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" \
  "$MYSQL_DB" | gzip > "$OUT"
echo "-> done: $(du -h "$OUT" | cut -f1)"