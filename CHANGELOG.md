# Changelog

## Unreleased

### Data pipeline
- 12 new tests run the real ingestion commands and table reader with a Statistics Canada style
  file and prove that a refresh can be repeated safely: the same release twice changes nothing; a
  revised value replaces the old one without a duplicate; new months are added; months missing from
  a later file and suppressed values never erase stored data; and a failure while loading leaves
  none of that measure's rows behind. A full refresh run twice leaves identical data.
- A source that repeats a date in one batch is now stored once, with the last value. PostgreSQL
  refuses an upsert that names the same row twice, and the SQLite test database does not, so this
  is guarded in the loader rather than left to the database.

### CSV downloads
- Every table on the dashboard, the provinces page and the forecasts page now has a "Download data
  (CSV)" link (in French, "Télécharger les données (CSV)"). Downloads carry the full history, not
  just the rows shown, and the forecast file holds the history, the twelve forecast months, the
  range, the method and the unit.
- Files are the same in both languages: English column names, ISO dates and a dot for decimals.
  Each row names its source and licence. A byte order mark makes Excel read accents correctly, and
  text that could run as a spreadsheet formula is quoted. Unknown series, provinces or indicators
  answer 404.

### Reading guide
- New "How to read this" page at `/guide/`, in English and French: the real policy rate, unemployment
  and percentage points, real retail growth, how to read a forecast chart, what the 80% range is
  (and is not), what "compared with assuming no change" means, the limits of forecasts, a glossary
  and the data sources. The 80% and 10% figures come from the code, so text and behaviour cannot drift.
- Linked from the navigation and from the Forecasts page. Covered by the accessibility, axe,
  CSP and attribution tests like every other page.

### Project management
- Added `docs/project/`: charter, roadmap and prioritised backlog, sprint reviews with lessons
  learned, a risk register, a decision log (11 decisions) and a one-page case study. All are
  written from the repository's own history.

### Deployment
- Static files are now served by WhiteNoise. Before this, the production container collected and
  served nothing, so the Django admin would have appeared without any styling. The Docker build now
  runs `collectstatic`, and production uses hashed, pre-compressed files that browsers can cache
  indefinitely.
- Works behind the `/maplemetrics` URL prefix: links keep the prefix and the gateway strips it
  before the app looks the file up.
- Static file requests are logged at DEBUG, so the logs show real traffic.
- New tests collect the files and request them: hashed name, cache headers, gzip, the URL prefix,
  and a 404 for a missing file.

### Operations
- New `/status/` page (English and French) and `/status.json` endpoint. They check the database and
  cache, how many indicators are up to date, when data was last loaded (a stopped daily refresh
  shows up as a warning) and the forecasts. A failed database or cache answers 503 so a monitor
  can alert on it. The pages are never cached and expose no hostnames or secrets.
- Structured logging: one JSON line per event in production, readable text in development
  (`LOG_FORMAT`, `LOG_LEVEL`). Each request gets an id that appears in every log line it causes and
  in the `X-Request-ID` header; a trustworthy id from a proxy is reused.
- The daily refresh now logs its start, each step with its duration, any failure with the
  traceback, and its finish.
- Added `docs/operations.md`, and a Status link in the navigation.
- Backup and restore are now scripts in `deploy/`: `backup.sh` (verifies the archive before keeping
  it, prunes after 14 days) and `restore-test.sh` (restores into a scratch database, compares row
  counts with the live one, always cleans up). Tests run both against a pretend `docker`. The
  operations guide documents the cron schedule, which needs `-T` for `docker compose run`.

### Security
- Added a Content-Security-Policy and a Permissions-Policy. The site allows no scripts and no
  outside origins; inline styles are allowed only through a per-request nonce. The admin and the
  Swagger UI documentation get their own, looser policies.
- CI has a new `security` job running `bandit` and `pip-audit`, and a weekly scheduled run so new
  advisories are found without a code change.
- Dependabot opens weekly pull requests for Python packages, GitHub Actions and the Docker image.
- GitHub Actions moved to current major versions (`checkout`, `setup-python`, `setup-node`).
- Reviewed every bandit finding: three `mark_safe` calls in the chart code (now covered by escaping
  tests), one deliberate `except/continue` in the ARIMA search, and two non-password strings.
- Added `SECURITY.md` and `docs/security.md`, and a `make audit` command.
- New tests for the headers, the nonce, chart escaping, and (in the browser audit) that the policy
  does not block the pages' own styles.

### Data attribution
- Every page now ends with a footer crediting Statistics Canada (Open Licence, with the required
  "adapted from" and no-endorsement notices) and the Bank of Canada (source credit, adapted
  figures, no endorsement), in English and French, with links to each licence in the page language.
- A test checks all eight page and language combinations for the notices.

### Accessibility
- Fixed every issue an axe-core audit found: link and secondary text contrast in light mode, the
  green chart series, charts with no accessible name, and a table area that keyboard users could
  not scroll.
- Every chart now has an accessible name and a spoken summary (highest and lowest, or start and
  end values), in English and French.
- The navigation wraps on narrow screens, so the page no longer scrolls sideways at 320 px.
- Added a skip link, visible focus outlines, captions and header scopes on every table, and
  keyboard-reachable scroll areas.
- The province page now offers each chart as a table, like the dashboard and forecasts pages.
- Selecting a province, indicator or geography no longer reloads the page on change; use the Show
  button. Automatic submission disorients keyboard and screen reader users.
- New tests: colour contrast of every theme colour, page structure in both languages, and an
  opt-in browser audit with axe-core at desktop and 320 px widths in light and dark mode. CI runs
  the audit in a new `accessibility` job.

## 1.0.0

First release.

### Data engineering
- Bank of Canada Valet ingestion: exchange rate, policy rate, total CPI inflation, CPI-trim and
  CPI-median.
- Statistics Canada ingestion from full-table downloads: unemployment rate, retail trade sales and
  the consumer price index, for Canada and the ten provinces.
- PostgreSQL warehouse with idempotent upserts, so reruns and revised values are safe.
- Freshness report (command and page) that flags stale or empty indicators.
- `refresh_data` command that reloads every source and rebuilds the forecasts.

### Analysis
- Dashboard: real policy rate, unemployment by province, real retail sales growth.
- Province comparison against Canada.
- Server-rendered SVG charts with light and dark themes and a table view of every chart.

### Forecasting
- Six methods behind one interface, scored with a rolling-origin backtest (MAE, RMSE, MASE and
  the ratio to a no-change forecast).
- Stored 12-month forecasts with empirical 80% ranges taken from past backtest errors.
- Forecasts page that says plainly when a method is no better than assuming no change.

### Platform
- Read-only REST API under `/api/v1/` with OpenAPI schema and Swagger UI, paging, filtering,
  rate limiting and caching headers.
- English and French interface with a language switcher, French province names and decimal commas.
- Docker Compose stack (web, PostgreSQL, Redis) and a one-off `refresh` service.
- GitHub Actions: lint, tests against PostgreSQL, Docker build and smoke test.
- Production security settings checked by a test running `check --deploy`.
