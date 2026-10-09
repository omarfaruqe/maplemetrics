# MapleMetrics

![CI](https://github.com/omarfaruqe/maplemetrics/actions/workflows/ci.yml/badge.svg)


Canadian economic and market intelligence: a containerized platform that ingests Canadian public
data (Statistics Canada, Bank of Canada, CMHC), models it in a warehouse, forecasts key
indicators, and serves dashboards and an API through Django.

**Status:** Sprint 0 (foundation).

## Quick start

```bash
cp .env.example .env      # then edit secrets
docker compose up --build # web on http://localhost:8000, health at /health/
```

## Local development without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                    # uses in-memory SQLite unless POSTGRES_HOST is set
ruff check . && ruff format --check .
```

## Layout

```
config/        Django project (split settings: base, dev, prod, test)
apps/core/     Health endpoint and landing page (more apps arrive in later sprints)
.github/       CI: lint, tests against PostgreSQL, Docker build and smoke test
```

## Roadmap

| Sprint | Focus |
|---|---|
| 0 | Foundation: Django, Docker Compose, tests, CI |
| 1 | Data engineering: Statistics Canada and Bank of Canada ingestion, warehouse |
| 2 | Analysis: KPIs and dashboards |
| 3 | Forecasting models |
| 4 | REST API, EN/FR interface, hardening |
| 5 | Documentation and release |