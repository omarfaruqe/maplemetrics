#!/bin/bash
# Nightly database backup. Run by cron on the server; safe to run by hand at any time.
# Writes ~/backups/maplemetrics-YYYY-MM-DD.sql.gz and keeps 14 days of them.
set -euo pipefail

project_dir="${MAPLE_DIR:-$HOME/maplemetrics}"
backup_dir="${MAPLE_BACKUP_DIR:-$HOME/backups}"
compose=(docker compose -f docker-compose.yml -f docker-compose.server.yml)

cd "$project_dir"
mkdir -p "$backup_dir"
target="$backup_dir/maplemetrics-$(date +%F).sql.gz"

"${compose[@]}" exec -T db pg_dump -U "${POSTGRES_USER:-maplemetrics}" \
  "${POSTGRES_DB:-maplemetrics}" | gzip > "$target.tmp"

# Only a complete, readable archive replaces the day's backup.
gzip -t "$target.tmp"
mv "$target.tmp" "$target"

find "$backup_dir" -name 'maplemetrics-*.sql.gz' -mtime +14 -delete
find "$backup_dir" -name 'maplemetrics-*.tmp' -mtime +1 -delete
echo "$(date -Is) backup written: $target ($(du -h "$target" | cut -f1))"
