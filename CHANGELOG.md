# Changelog

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