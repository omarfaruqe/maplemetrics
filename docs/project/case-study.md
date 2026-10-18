# MapleMetrics: case study

**A bilingual Canadian economic data service with forecasts that show how far to trust them.**
Owned and directed by one person over nine days (2026-10-09 to 2026-10-17), built with an AI
development assistant (see below).
Source: https://github.com/omarfaruqe/maplemetrics

## The problem

The Bank of Canada and Statistics Canada publish open data, but through different interfaces and
formats, and forecasts built on such data are easy to over-trust. MapleMetrics collects the data,
presents it in English and French, and publishes forecasts alongside the evidence on how well the
same method performed in the past.

## What was built

- **A data pipeline** loading 5 Bank of Canada series and 3 Statistics Canada tables for Canada and
  the ten provinces. Loads are safe to repeat and pick up revisions; a freshness check flags stale
  data.
- **Analysis and charts**: a dashboard, a province-against-Canada comparison, and charts drawn on the
  server with a table view of every one.
- **Forecasts that are honest.** Six methods are compared by backtest. Each forecast shows an 80%
  range taken from past errors, and the page says in plain words when a method is no better than
  assuming nothing changes, which is the case for unemployment.
- **A read-only API** with OpenAPI documentation, paging, filtering and rate limits.
- **Both official languages** throughout, enforced by a test that fails on any untranslated string.
- **Deployment and operations**: Docker Compose, a status page, structured logs, health checks and
  a daily refresh.

## How AI assistance was used

The code was written with Claude (Anthropic) acting as a development assistant. The owner set the
requirements and priorities, made the design decisions recorded in the
[decision log](decision-log.md), applied every change to their own machine, ran the code against
real data and the real server, reported what did and did not work, and decided what to accept.
Several of the lessons below came from that loop: the assistant could not reach Statistics Canada
or the server, so problems appeared only when the owner ran the code. The test suite and CI
pipeline exist to check any change, whoever or whatever wrote it.

## How it was run

Work was split into six sprints for release 1.0 (Foundation, Data engineering, Analysis,
Forecasting, Platform, Documentation) and a set of increments for hosting and quality after the
release. Each sprint had a goal, a definition of done, a review and an update to the risk
register. The [charter](charter.md), [backlog](backlog.md), [sprint reviews](sprint-reviews.md),
[risk register](risk-register.md) and [decision log](decision-log.md) record this.

## Results

| | |
|---|---|
| Automated tests | 222 passing, 98.8% coverage, build fails below 80% |
| Pipeline | 5 checks on every push: lint, tests on PostgreSQL, accessibility, security, Docker smoke test |
| Accessibility | WCAG 2.2 AA, zero violations in an automated audit of every page, both languages, both themes, at desktop and 320 px |
| Security | Content-Security-Policy with no scripts, code and dependency scanning, no known vulnerable dependencies |
| Size | About 3,500 lines of application code and 2,800 of tests, 25 commits, one tagged release |

## What went wrong, and what it taught

- **Real data disagreed with assumptions.** The first run against real Statistics Canada tables
  showed a wrong filter, and the first real backtest showed wrong figures in its own report.
  Since then each data-facing feature is run on real data before it is called done.
- **Environment problems cost more than code problems.** Hosting on an existing server meant
  fixing an outdated Docker package, permissions and a port exposed twice. Each fix became a
  documented setting or test.
- **Copying files by hand hides mistakes.** A pasted test file with the wrong content removed 15
  tests without any error; it was caught only because the passing count was lower than expected.
  Files are now written directly and the expected count is checked.

## Limits, stated plainly

- The demo server is not yet reachable from the internet, and it uses plain HTTP until a domain
  exists. Both are tracked in the backlog.
- Backups exist but a restore has not been tested yet.
- Accessibility was checked with automated tools, not with people who use assistive technology.
- The French text has not been reviewed by a professional translator.

## What it demonstrates

Project planning and control (charter, prioritised backlog, risk register, decision log, sprint
reviews); data engineering (idempotent ingestion, a warehouse, freshness monitoring); applied
statistics with honest uncertainty; secure and accessible delivery in both official languages;
and the habit of making each claim checkable by a test or a document.
