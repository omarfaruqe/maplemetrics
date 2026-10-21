# Roadmap and backlog

Dates and commit ids come from the git history. "Evidence" is where to look to confirm a claim.

## Roadmap

```mermaid
gantt
    dateFormat  YYYY-MM-DD
    axisFormat  %m-%d
    section Release 1.0
    Sprint 0 Foundation            :done, s0, 2026-10-09, 1d
    Sprint 1 Data engineering      :done, s1, 2026-10-11, 1d
    Sprint 2 Analysis              :done, s2, 2026-10-11, 2d
    Sprint 3 Forecasting           :done, s3, 2026-10-12, 2d
    Sprint 4 API, French, hardening:done, s4, 2026-10-13, 1d
    Sprint 5 Docs and release      :done, s5, 2026-10-13, 1d
    section Release 1.1
    Hosting (HTTP mode, URL prefix):done, h1, 2026-10-16, 3d
    Quality and trust increments   :done, q1, 2026-10-17, 1d
    Project documents              :active, p1, 2026-10-17, 1d
```

## Delivered

### Release 1.0 (tag `v1.0.0`, 2026-10-13)

| Sprint | Goal | Delivered | Commits |
|---|---|---|---|
| 0 Foundation | A project that builds, tests and runs anywhere | Django project with split settings, Docker Compose (web, PostgreSQL, Redis), test setup, CI skeleton, CI badge | `742a389`, `3313232`, `439695a` |
| 1 Data engineering | Real data in a warehouse, safely re-loadable | Indicator and Observation models; Bank of Canada ingestion (5 series); Statistics Canada ingestion (3 tables, Canada and 10 provinces); idempotent upserts; freshness report command and page | `8c42341`, `dad6f53`, `abd32dc`, `78eb45d` |
| 2 Analysis | Turn data into insight | KPIs (real policy rate, unemployment by province, real retail growth); dashboard; province comparison; server-rendered SVG charts with table views | `878167a`, `d4120ec` |
| 3 Forecasting | Forecasts with honest reliability | Six methods behind one interface; rolling-origin backtest; stored 12-month forecasts with empirical 80% ranges; forecasts page with plain-language verdict | `8a2bbe7`, `37787b8`, `b949491` |
| 4 Platform | Usable by programs and by both official languages; production-ready | Read-only REST API with OpenAPI docs; French and English interface and translation tooling; rate limiting, caching, production settings, scheduled refresh command | `a6dca47`, `2ffc2a4`, `b8eb413` |
| 5 Documentation and release | Understandable and releasable | README with screenshots, architecture, data dictionary, forecasting methods, licence, changelog, `v1.0.0` tag | `5170cbe` |

### Release 1.1 (in progress, unreleased)

| Increment | Delivered | Commits |
|---|---|---|
| Hosting on a plain server | `DJANGO_HTTPS` switch for HTTP-only deployments; web port bound to localhost; serving under a URL prefix (`/maplemetrics/`) with unique cookie names | `fe7321e`, `67f5b10`, `bf4111a`, `4501bac` |
| Accessibility | WCAG 2.2 AA fixes, chart descriptions, captions, skip link, axe-core audit in CI | `3e9e3ec` |
| Data attribution | Licence and source footer in both languages, checked by tests | `3e23adb` |
| Security | Content-Security-Policy, `bandit`, `pip-audit`, Dependabot, updated Actions | `cf6b0a2` |
| Observability | `/status/` page and `/status.json`, structured JSON logs with request ids | `3e6b0e3` |
| Static files | WhiteNoise, build-time `collectstatic` | `9b6fbb5` |
| Backup and restore | Scripted, tested backup (`deploy/backup.sh`) and restore check (`deploy/restore-test.sh`); first real restore verified on the server 2026-10-18 | `deploy/`, `test_deploy_scripts.py` |
| Project documents | This folder | `docs/project/` |
| Live hosting | Site reachable from outside at `/maplemetrics/` through the shared gateway; first full data refresh loaded 8 of 8 indicators and 33 forecasts; status page all `ok` (verified 2026-10-18) | (server; no commit) |

## Open backlog

Priority uses MoSCoW (Must, Should, Could). Effort is S (under an hour), M (a few hours), L (a day or more).

| ID | Item | Priority | Effort | Why it matters | Status |
|---|---|---|---|---|---|
| B-01 | Make the server reachable from the internet on port 80 and confirm the demo URL loads | Must | S | The charter's last success criterion; a live demo is the best proof of the project | **Done 2026-10-18.** Verified from outside with `curl` (redirect to the dashboard, through the gateway) and `/status.json` |
| B-02 | Confirm the first full data refresh loaded and the status page reads "ok" | Must | S | Proves the pipeline works in production | **Done 2026-10-18.** Status `ok`: 8 of 8 indicators fresh, 33 forecasts, last load minutes old |
| B-03 | Set up and verify the daily cron refresh and backup job on the server | Must | S | Without it the data goes stale and the status page warns | Done (verified 2026-10-20: backups written on three consecutive mornings, refresh finished in 186 s, status `ok`) |
| B-04 | Restore runbook: restore a backup into a clean database and record the steps and time taken | Must | M | A backup that has never been restored is an assumption | **Done 2026-10-18.** `deploy/restore-test.sh` restored a real backup into a scratch database on the server and the counts matched (`PASS`). Procedure in the operations guide |
| B-05 | HTTPS with a domain name and certificate | Should | M | Needed before anything beyond public data is hosted; settings already support it | Waiting on a domain |
| B-06 | Serve Swagger UI from the project (no CDN) and tighten the docs-page policy | Should | S | Removes the last outside dependency at runtime | Open |
| B-07 | Ingestion idempotency and revision tests against recorded real responses | Should | M | Protects the most important data-engineering promise | Done for idempotency and revisions (12 tests, 2026-10-21); real recorded samples moved to B-18 |
| B-08 | Query-count and response-time tests for the main pages | Should | M | Catches slow pages before users do | Open |
| B-09 | CSV download for any chart or table | Should | S | Most requested feature for an open-data tool | Done |
| B-10 | "How to read this" page: real rate, MASE, empirical ranges in plain language, in both languages | Should | M | The forecasting honesty is the project's differentiator; it should be explained | Done |
| B-11 | Forecast accuracy over time (compare past forecasts with what happened) | Could | L | Turns backtests into a live track record | Open |
| B-12 | Additional indicators (for example GDP, wages, housing) | Could | L | Broader value; each needs a catalog entry, tests and French names | Open |
| B-13 | Side-by-side comparison of two provinces | Could | M | Natural extension of the province page | Open |
| B-14 | Container image vulnerability scan in CI | Could | S | Dependabot updates the base image but the built image is not scanned | Open |
| B-15 | Usability test with screen-reader users | Could | M | Automated tools find only part of the problems | Open |
| B-16 | Demo GIF and a short video walkthrough for the README | Could | S | Faster to review than screenshots | Open |
| B-17 | Copy backups off the server automatically | Should | M | Backups sit on the same disk as the database, so a disk failure would lose both | Open |
| B-18 | Record real Statistics Canada and Bank of Canada responses as trimmed test fixtures | Could | S | The idempotency tests use files built to the real column layout; real samples would also catch format changes | Open |

## Prioritisation notes

- Items that prove the system works in operation (B-01 to B-04) come before new features,
  because an unverified deployment is a bigger risk than a missing feature.
- Trust items (B-04, B-05, B-07) come before reach items (B-09, B-12), in line with the project's
  theme of being honest about reliability.
- Items that were considered and left out are listed in the charter's out-of-scope section.
