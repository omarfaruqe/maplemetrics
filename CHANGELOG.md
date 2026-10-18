# Changelog

## Unreleased

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
