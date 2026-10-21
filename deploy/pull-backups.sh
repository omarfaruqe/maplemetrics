#!/bin/bash
# Copy the server's database backups to this computer. Run it on your Mac, not on the server.
#
# The Mac connects to the server, so the server holds no key to your copy. Files that already
# arrived are never downloaded again. Every archive is tested with gzip -t, and the script exits
# with an error if one is damaged or if the newest copy is more than two days old, which means the
# server stopped making backups.
#
# Settings (environment variables, all optional):
#   MAPLE_REMOTE       user@host of the server        (default faruqe@103.99.176.180)
#   MAPLE_REMOTE_DIR   backup folder on the server    (default backups)
#   MAPLE_LOCAL_DIR    where copies are kept here     (default ~/Backups/maplemetrics)
#   MAPLE_KEEP_DAYS    delete local copies older than (default 365)
set -euo pipefail

remote="${MAPLE_REMOTE:-faruqe@103.99.176.180}"
remote_dir="${MAPLE_REMOTE_DIR:-backups}"
local_dir="${MAPLE_LOCAL_DIR:-$HOME/Backups/maplemetrics}"
keep_days="${MAPLE_KEEP_DAYS:-365}"

log() { echo "$(date '+%Y-%m-%dT%H:%M:%S%z') $*"; }

mkdir -p "$local_dir"

# BatchMode makes a missing key fail at once instead of waiting for a password nobody can type.
# -r is needed to look inside the server's folder; --exclude='*' keeps it from going deeper.
if ! rsync -rt --partial \
  -e "ssh -o BatchMode=yes -o ConnectTimeout=20" \
  --include='maplemetrics-*.sql.gz' --exclude='*' \
  "$remote:$remote_dir/" "$local_dir/"; then
  log "FAIL: could not copy from $remote:$remote_dir (is the server reachable, and does ssh work without a password?)"
  exit 1
fi

copies=0
damaged=0
for file in "$local_dir"/maplemetrics-*.sql.gz; do
  [ -e "$file" ] || continue
  copies=$((copies + 1))
  if ! gzip -t "$file" 2>/dev/null; then
    log "FAIL: $file is damaged"
    damaged=$((damaged + 1))
  fi
done

if [ "$copies" -eq 0 ]; then
  log "FAIL: no backups found in $local_dir"
  exit 1
fi
if [ "$damaged" -gt 0 ]; then
  exit 1
fi

if ! find "$local_dir" -name 'maplemetrics-*.sql.gz' -mtime -2 | grep -q .; then
  log "FAIL: the newest backup is more than two days old; the server may have stopped making them"
  exit 1
fi

find "$local_dir" -name 'maplemetrics-*.sql.gz' -mtime +"$keep_days" -delete
newest="$(find "$local_dir" -name 'maplemetrics-*.sql.gz' | sort | tail -n 1)"
log "OK: $copies backups here, newest $(basename "$newest") ($(du -h "$newest" | cut -f1))"
