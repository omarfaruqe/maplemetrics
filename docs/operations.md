# Operations

How to see what the running system is doing, and how to tell when something is wrong.

## Status page

| Address | For | Answers |
|---|---|---|
| `/health/` | Docker's healthcheck | `200` if the database responds, `503` if not |
| `/status/` | People | A page with each check in plain language, in English and French |
| `/status.json` | Monitors and scripts | The same checks as JSON |

`/status/` and `/status.json` run five checks:

| Check | Fails or warns when |
|---|---|
| Database | The database does not answer (**fail**, the page returns 503) |
| Cache | A value cannot be written to and read back from Redis (**fail**, 503) |
| Indicator freshness | Any indicator is stale or empty, or nothing is loaded (**warn**) |
| Last data load | Nothing was loaded in the last three days, which means the daily refresh stopped (**warn**) |
| Forecasts | No forecasts have been built (**warn**) |

A warning still answers `200`, because the site works; only a failed database or cache answers
`503`. The overall status is `ok`, `attention` (at least one warning) or `down`. The pages are
never cached, and nothing in them names a host, a password or a connection string.

Point an external uptime monitor at `/status.json` and alert when the status code is not `200`.
To also catch a stopped refresh, alert when `"status"` is not `"ok"`:

```bash
curl -s http://SERVER/maplemetrics/status.json
```

## Logs

The app writes one line per event to standard output, where Docker collects it. In production each
line is a JSON object:

```json
{"time": "2026-10-17T22:41:07.512+00:00", "level": "INFO", "logger": "maplemetrics.request",
 "message": "GET /dashboard/ 200", "request_id": "5f0c...", "method": "GET",
 "path": "/dashboard/", "status": 200, "duration_ms": 41.3}
```

In development the same events are printed as readable text. Two settings control this:

| Variable | Default | Meaning |
|---|---|---|
| `LOG_FORMAT` | `json` in production, `text` otherwise | `json` or `text` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR` |

### Request ids

Every request gets an id, which appears in each log line written while handling it and in the
`X-Request-ID` response header. If a reverse proxy already sends a short, plain `X-Request-ID`, it is
reused, so a request can be followed from the proxy into the app. Anything else is replaced.

To follow one request:

```bash
docker compose -f docker-compose.yml -f docker-compose.server.yml logs web | grep 5f0c
```

### What gets logged

| Logger | Events |
|---|---|
| `maplemetrics.request` | Every request: method, path, status, duration. Server errors are `ERROR`. Healthchecks are `DEBUG`, so they do not drown real traffic |
| `maplemetrics.refresh` | The daily refresh: start, each step with its duration, any step that failed (with the traceback), and the finish |
| `django` | Django's own warnings and errors, in the same format |

### Useful searches

With `jq` installed on the server:

```bash
docker compose -f docker-compose.yml -f docker-compose.server.yml logs --no-log-prefix web \
  | jq -c 'select(.status >= 500)'

docker compose -f docker-compose.yml -f docker-compose.server.yml logs --no-log-prefix web \
  | jq -c 'select(.duration_ms > 500) | {path, duration_ms}'
```

The refresh runs from cron, so its output goes to the file named in the cron line. Its log lines
are JSON too, and `grep refresh` shows how long each step took and whether one failed.

## Scheduled jobs, backups and restore

Two jobs run every day from the server's crontab (times are the server's time zone):

| Time | Job | What it does |
|---|---|---|
| 06:00 | Refresh | Reloads every source and rebuilds the forecasts; output goes to `~/maplemetrics-refresh.log` |
| 06:30 | Backup | `deploy/backup.sh` writes `~/backups/maplemetrics-DATE.sql.gz`, keeps 14 days, and output goes to `~/maplemetrics-backup.log` |

`docker compose run` needs `-T` in cron because cron has no terminal. The backup script only keeps an
archive that `gzip -t` can read, so a failed dump never replaces a good backup.

To install the schedule (once; running it twice creates duplicates):

```bash
(crontab -l 2>/dev/null; echo '0 6 * * * cd $HOME/maplemetrics && docker compose -f docker-compose.yml -f docker-compose.server.yml run --rm -T refresh >> $HOME/maplemetrics-refresh.log 2>&1'; echo '30 6 * * * bash $HOME/maplemetrics/deploy/backup.sh >> $HOME/maplemetrics-backup.log 2>&1') | crontab -
crontab -l
```

### Testing that a backup restores

A backup that has never been restored is an assumption. `deploy/restore-test.sh` loads the newest
backup (or the file you name) into a scratch database inside the same PostgreSQL container,
compares row counts of the main tables with the live database, prints how long the restore took,
and drops the scratch database. The live database is only read.

```bash
bash deploy/restore-test.sh
bash deploy/restore-test.sh ~/backups/maplemetrics-2026-10-18.sql.gz
```

| Result | Meaning |
|---|---|
| `PASS` | The backup restores and every count matches |
| `PASS WITH DIFFERENCES` | It restores and holds data, but data was loaded after the backup was taken (normal) |
| `FAIL` | The archive is unreadable, the restore errored, or the restored database is empty. Exit code 1 |

Run it after the first backup, after any change to the database structure, and from time to time.
The latest result belongs in the [risk register](project/risk-register.md) (R-09).

### Restoring for real

To recover from data loss: stop the web service, drop and recreate the database, load the backup,
and start the web service again. Because every source is public, the other way to recover is to
start with an empty database and run the refresh, which rebuilds everything in several minutes;
the backup mainly saves time.

```bash
docker compose -f docker-compose.yml -f docker-compose.server.yml stop web
docker compose -f docker-compose.yml -f docker-compose.server.yml exec -T db psql -U maplemetrics -d postgres -c "DROP DATABASE maplemetrics" -c "CREATE DATABASE maplemetrics"
gunzip -c ~/backups/maplemetrics-DATE.sql.gz | docker compose -f docker-compose.yml -f docker-compose.server.yml exec -T db psql -U maplemetrics -d maplemetrics
docker compose -f docker-compose.yml -f docker-compose.server.yml start web
```

Backups sit on the same disk as the database, so copy `~/backups` to another machine now and then;
a disk failure would take both.

## Not covered yet

- **Log shipping and retention.** Logs stay in Docker on the server and are lost if the container
  is removed. A log collector would be the next step if there were more than one server.
- **Metrics and alerting.** There are no counters or graphs, and nothing pages anyone. The status
  endpoint is the hook for an external monitor.
