# Sprint reviews

One review per sprint: the goal, what was delivered, the evidence, what went well, what went wrong
and what changed as a result. Test counts are the number passing at the end of the sprint where
they were recorded; earlier sprints did not record one.

## Sprint 0: Foundation (2026-10-09)

**Goal.** A project that builds, tests and runs the same way on any machine.

**Delivered.** Django project with settings split into base, dev, prod and test; Docker Compose
stack (web, PostgreSQL, Redis); pytest with a coverage gate; CI skeleton; CI badge.
Commits `742a389`, `3313232`, `439695a` (30 files in the first commit).

**Went well.** Splitting settings early made later security work simple: production refuses to
start with the development secret key, and tests run on SQLite locally and PostgreSQL in CI.

**Went wrong.** The first commit needed a follow-up commit to apply the formatter, so the lint check
was not being run before pushing.

**Changed.** Added a pre-commit configuration with `ruff`. (This lesson came back in release 1.1;
see below.)

## Sprint 1: Data engineering (2026-10-11)

**Goal.** Real data in a warehouse that can be reloaded safely.

**Delivered.** Warehouse models; Bank of Canada ingestion (5 series); Statistics Canada ingestion
(3 tables, Canada and 10 provinces); idempotent upserts; freshness report as a command and a page.
Commits `8c42341`, `dad6f53`, `abd32dc`, `78eb45d`.

**Evidence.** Data loaded in Docker on the owner's machine; the freshness page lists every
indicator with its status.

**Went well.** Treating re-runs as the normal case (upserts, full-table reloads so revisions are
picked up) removed a whole class of data bugs before any page existed.

**Went wrong.** The development environment cannot reach Statistics Canada, so the table layout
could not be checked while writing the parser. The first run against real tables showed the
retail-sales filter was wrong (`abd32dc`).

**Changed.** The sprint plan now includes an `--inspect` command that prints a table's real
structure on the owner's machine, and parsers are fitted to that output rather than to assumptions.

## Sprint 2: Analysis and dashboards (2026-10-11 to 2026-10-12)

**Goal.** Turn the data into something a person can read.

**Delivered.** KPI calculations; dashboard; province comparison; server-rendered SVG charts, each
with a table view. Commits `878167a`, `d4120ec`.

**Went well.** Drawing charts on the server as SVG meant no JavaScript build and one theme system
(CSS variables) for light and dark modes. See decision D-01.

**Went wrong.** Review of the first charts found negative bar labels colliding with category labels
and charts squashed on phones.

**Changed.** Labels now sit beside the baseline, and charts keep a minimum width inside a scrolling region.

## Sprint 3: Forecasting (2026-10-12 to 2026-10-13)

**Goal.** Forecasts that say how far they can be trusted.

**Delivered.** Six methods behind one interface; rolling-origin backtest with MAE, RMSE, MASE and
the ratio to a no-change forecast; stored 12-month forecasts with empirical 80% ranges; forecasts
page with a plain-language verdict. Commits `8a2bbe7`, `37787b8`, `b949491`.

**Evidence.** The backtest command was run on real data; the forecasts page states when a method is
no better than assuming no change (which is the case for unemployment).

**Went well.** Running the backtest on real data early exposed problems that unit tests had not.

**Went wrong.** The first real output showed the report header printed the requested number of
backtest origins instead of the actual number (one series had only three), and the backtest's
scaling was wrong. Fixed in `37787b8`, which also improved the leaderboard output.

**Changed.** The command's output now reports what was actually run, so a wrong figure is
visible to whoever runs it.

## Sprint 4: Platform (2026-10-13)

**Goal.** Usable by programs and in both official languages, and ready for production.

**Delivered.** Read-only REST API with OpenAPI docs (`a6dca47`); French and English interface with a
language switcher (`2ffc2a4`); rate limiting, response caching, production hardening and a
one-command scheduled refresh (`b8eb413`). Tests rose from 145 after the API to 160 after
translations, with coverage at 98.8%.

**Went well.** Making an untranslated string a failing test kept French complete without manual
checking.

**Went wrong.** The environment has no GNU gettext, so the usual translation workflow was
unavailable.

**Changed.** A small Python tool compiles the translation catalog and a test keeps the compiled
file in step with the source (decision D-04). The side effect is that contributors need no
extra software.

## Sprint 5: Documentation and release (2026-10-13)

**Goal.** Make the project understandable and release it.

**Delivered.** README with screenshots, architecture, data dictionary, forecasting methods note,
licence, changelog, home page opens the dashboard, tag `v1.0.0` (`5170cbe`). 169 tests passing.

**Went well.** The methods note states the limits of the forecasts in plain terms, which became
the project's main selling point rather than a caveat.

**Went wrong.** Nothing blocked the release. The main gap was that there was no hosted version
yet.

**Changed.** Hosting became the first item of the next release.

## Release 1.1, increment: Hosting (2026-10-16 to 2026-10-17)

**Goal.** Run the stack on an Ubuntu server that is reached by IP address and shared with other
projects.

**Delivered.** `DJANGO_HTTPS` switch for plain-HTTP servers (`fe7321e`); web port bound to
localhost (`bf4111a`); serving under `/maplemetrics/` with unique cookie names so projects on the
same address do not overwrite each other's cookies (`4501bac`).

**Went well.** Treating the URL prefix as configuration with its own tests (reverse URLs, cookie
paths, redirects, health check) meant the change was verified before touching the server.

**Went wrong.** A series of environment problems on the server: an old Docker Desktop package
shadowed the current Compose plugin; the Docker socket needed group membership; a credentials
helper blocked image pulls; the web port was published twice; `127.0.0.1` had to be added to the allowed hosts so the
container's health check could pass. Also, the CI lint check failed again after pasted
files differed in whitespace (`67f5b10`).

**Changed.** Each fix is documented, and the base Compose file now binds to localhost so a
server cannot accidentally expose the app. Pasting code between machines proved error-prone, so
files are now written directly into the working folder and compared by checksum.

## Release 1.1, increments: Quality and trust (2026-10-17)

**Goal.** Close the gaps a careful reviewer would find.

| Increment | Outcome | Evidence |
|---|---|---|
| Accessibility | An axe-core audit found 22 violations; all fixed. Zero on every page, both languages, light and dark, desktop and 320 px. 183 tests | CI `accessibility` job |
| Data attribution | Licence footer on every page, in both languages, checked by tests | `test_attribution.py` |
| Security | Content-Security-Policy with a per-request nonce; `bandit`; `pip-audit`; Dependabot. No known vulnerable dependencies. Three `mark_safe` findings reviewed and covered by escaping tests | CI `security` job |
| Observability | Status page and JSON endpoint; JSON logs with request ids. 215 tests | `test_status.py`, `test_logging.py` |
| Static files | WhiteNoise; the production container previously served no admin styling | `test_static_files.py` |

**Went well.** Each increment added a test that fails if the problem returns, so the quality
level is held by the pipeline, not by attention. A real-browser test confirmed the strict
security policy did not break the pages, and failed as intended when the nonce was removed.

**Went wrong.** A pasted test file contained the wrong content and silently removed 15 tests; it
was caught because the passing count (170) did not match the expected count (185).

**Changed.** The expected test count is now checked after every delivery, and files are copied
directly. Open items are tracked in the [backlog](backlog.md).
