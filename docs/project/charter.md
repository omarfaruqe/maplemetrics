# Project charter

| | |
|---|---|
| **Project** | MapleMetrics |
| **Owner and developer** | Md Omar Faruqe |
| **Repository** | https://github.com/omarfaruqe/maplemetrics |
| **Started** | 2026-10-09 |
| **First release** | v1.0.0, 2026-10-13 |
| **Status (2026-10-17)** | Released and being hardened for hosting. See the [backlog](backlog.md) |

## Purpose

Canada's central bank and national statistics agency publish a great deal of open economic data,
but it arrives through different interfaces and formats, and forecasts built on it are rarely shown
with an honest account of how reliable they are. MapleMetrics brings the data together, presents
it in English and French, and publishes forecasts together with the evidence on how well the same
method has performed in the past.

It is also a portfolio project: it exercises the full chain from data ingestion to a hosted
service, and it was planned and documented the way a small team project would be.

## Objectives

| # | Objective | Measure of success |
|---|---|---|
| O1 | Load data from the Bank of Canada and Statistics Canada reliably | Eight sources loaded; re-running never duplicates or loses data; stale data is flagged |
| O2 | Turn the data into useful analysis | Dashboard, province comparison and a table view for every chart |
| O3 | Forecast without overstating confidence | Six methods compared by backtest; every forecast shows a range from past errors and says when it is no better than assuming no change |
| O4 | Serve both official languages | Every page, chart description and message available in English and French, enforced by a test |
| O5 | Offer the data programmatically | Read-only REST API with OpenAPI documentation, paging, filtering and rate limits |
| O6 | Keep quality high and visible | Automated checks on every push; coverage gate of 80% |
| O7 | Be accessible | WCAG 2.2 level AA, checked automatically on every push |
| O8 | Run on an ordinary Linux server | One-command Docker Compose deployment, health and status checks, structured logs |

## Scope

**In scope:** public data from two Canadian sources, for Canada and the ten provinces; a web
interface and read-only API; forecasts of three indicators; Docker-based deployment on one server.

**Out of scope:** user accounts or personal data; paid or real-time data; investment or policy
advice; territories (not in the chosen tables); other countries; a mobile app.

## Deliverables

Source code and tests; Docker Compose stack; CI pipeline; user and developer documentation
(README, architecture, data dictionary, forecasting methods, accessibility, security,
operations); these project-management documents.

## Success criteria and results

| Criterion | Target | Result on 2026-10-17 | Evidence |
|---|---|---|---|
| Automated test coverage | At least 80% (build fails below) | 98.8% | `pytest` output; CI `test` job |
| Tests passing | All | 222 passed, 2 browser audits run in CI | CI |
| Lint and format | Clean | Clean | CI `lint` job |
| Accessibility | WCAG 2.2 AA | 0 violations on every page, both languages, light and dark, desktop and 320 px (22 found and fixed on first audit) | CI `accessibility` job |
| Known vulnerable dependencies | None | None found | CI `security` job (`pip-audit`) |
| Translation completeness | No untranslated string | Enforced by a failing test | `test_i18n.py` |
| Runs from a clean checkout | `docker compose up` works | Yes | CI `docker` job smoke test |
| Publicly reachable demo | A URL anyone can open | **Not yet.** Runs on the server; access from outside is still being resolved | [Backlog](backlog.md) B-01 |

## Constraints

- One person, working part-time, so scope is cut to what can be finished and verified.
- Public data only, used under each provider's licence (see the site footer and README).
- No budget: open-source tools and a single existing server.
- The development environment cannot reach Statistics Canada, so data formats had to be verified
  by running inspection commands on the owner's machine before parsers were finished.

## Assumptions

- Statistics Canada and the Bank of Canada keep their open-data interfaces stable (tracked as
  risk R-01 and R-02).
- Users are analysts, students and members of the public who read English or French. These
  personas are assumed from the topic, not validated with interviews.
- A server with Docker is available for hosting.

## Stakeholders

| Who | Interest | How involved |
|---|---|---|
| Owner and developer | Delivers the project, owns scope and priorities | Plans, builds, reviews |
| Intended users (assumed) | Reliable, readable Canadian economic data in their language | Not consulted; accessibility and bilingual requirements stand in for their needs |
| Data providers | Correct attribution and licence compliance | Footer and README credits; no endorsement implied |
| Reviewers (employers, peers) | Evidence of planning, engineering quality and judgement | These documents, the repository and the CI record |

## Approach and definition of done

Work is organised in sprints, each with a goal. Sprints are time-boxed by the work, from a few
hours to a day or two, because there is one person and no fixed cadence. Each sprint is split into
parts that are committed separately so history shows progress and any part can be reverted.

A part is done when:

1. the new behaviour has tests and the full suite passes with coverage at or above the gate;
2. `ruff` lint and format are clean;
3. user-facing text exists in both languages and the translation test passes;
4. documentation and the changelog are updated;
5. it has been run against real data or a real environment where that is possible, not only in the
   test environment;
6. it is committed and the CI run on GitHub is green.

### How AI assistance is used

Code and documents are drafted with Claude (Anthropic) as a development assistant. The owner is
accountable for scope, priorities and design decisions, runs every change against real data and the
real server, and accepts or rejects the result. The assistant works in a separate environment with
no access to the owner's data sources or server, so verification on the owner's side is part of the
definition of done (item 5), and the automated checks apply equally to every change.

## Governance and change control

- **Scope changes** are made by editing the [backlog](backlog.md), with a note of what was
  traded off.
- **Risks** are tracked in the [risk register](risk-register.md) and reviewed at every sprint
  review.
- **Design decisions** that are hard to reverse are recorded in the [decision log](decision-log.md).
- **Releases** follow semantic versioning and are described in the [changelog](../../CHANGELOG.md).
- **Quality gates** are enforced by CI, not by memory: a failing check blocks the Docker job.
