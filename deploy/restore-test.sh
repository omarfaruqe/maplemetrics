#!/bin/bash
# Proves a backup can be restored. Loads it into a scratch database inside the same PostgreSQL
# container, compares row counts with the live database, then deletes the scratch database.
# The live database is only read, never changed.
#
# Usage: bash deploy/restore-test.sh [path/to/backup.sql.gz]   (default: the newest backup)
set -euo pipefail

project_dir="${MAPLE_DIR:-$HOME/maplemetrics}"
backup_dir="${MAPLE_BACKUP_DIR:-$HOME/backups}"
db_user="${POSTGRES_USER:-maplemetrics}"
live_db="${POSTGRES_DB:-maplemetrics}"
scratch_db="restore_check"
tables=(warehouse_indicator warehouse_observation forecasting_forecast forecasting_forecastpoint)
compose=(docker compose -f docker-compose.yml -f docker-compose.server.yml)

cd "$project_dir"

newest="$(find "$backup_dir" -name 'maplemetrics-*.sql.gz' 2>/dev/null | sort | tail -n 1 || true)"
backup="${1:-$newest}"
if [ -z "$backup" ] || [ ! -f "$backup" ]; then
  echo "FAIL: no backup file found in $backup_dir" >&2
  exit 1
fi
echo "Backup under test: $backup ($(du -h "$backup" | cut -f1))"
gzip -t "$backup"

psql_in() { "${compose[@]}" exec -T db psql -U "$db_user" -v ON_ERROR_STOP=1 -q "$@"; }

counts() {
  local database="$1" table
  for table in "${tables[@]}"; do
    printf '%s %s\n' "$table" "$(psql_in -d "$database" -tAc "SELECT count(*) FROM $table")"
  done
}

cleanup() { psql_in -d postgres -c "DROP DATABASE IF EXISTS $scratch_db" >/dev/null 2>&1 || true; }
trap cleanup EXIT

cleanup
psql_in -d postgres -c "CREATE DATABASE $scratch_db" >/dev/null

started=$(date +%s)
gunzip -c "$backup" | psql_in -d "$scratch_db" >/dev/null
elapsed=$(( $(date +%s) - started ))
echo "Restored into scratch database in ${elapsed}s"

live_counts="$(counts "$live_db")"
restored_counts="$(counts "$scratch_db")"
printf '%-28s %12s %12s\n' "table" "live" "restored"
paste -d'|' <(echo "$live_counts") <(echo "$restored_counts") |
  awk -F'|' '{ split($1, live, " "); split($2, restored, " ");
               printf "%-28s %12s %12s\n", live[1], live[2], restored[2] }'

if [ "$live_counts" = "$restored_counts" ]; then
  echo "PASS: the backup restores and matches the live database."
elif [ "$(echo "$restored_counts" | awk '{s+=$2} END {print s}')" -gt 0 ]; then
  echo "PASS WITH DIFFERENCES: the backup restores and holds data, but counts differ from the live"
  echo "database. That is normal if data was loaded after the backup was taken."
else
  echo "FAIL: the restored database is empty." >&2
  exit 1
fi
