# Risk register

Scores are likelihood (1 to 5) times impact (1 to 5), so 1 to 25. Reviewed at every sprint review.
Last review: 2026-10-17.

**Rating:** 15 and above is high, 8 to 14 is medium, below 8 is low.

| ID | Risk | L | I | Score | Response and mitigation | Residual | Status |
|---|---|---|---|---|---|---|---|
| R-01 | Statistics Canada changes a table's layout, member names or download format, and ingestion silently loads wrong or no data | 3 | 4 | 12 | Parsers fitted to real inspected output; `--inspect` command to re-check a table; freshness report and status page flag stale or empty indicators; tests on recorded samples | Medium | Mitigated. Recorded real responses (B-07) would improve this |
| R-02 | Bank of Canada Valet API changes, rate-limits or goes down | 2 | 3 | 6 | Incremental loads, one source failing does not stop the others, failures are logged with duration; terms of use credited in the footer and respected | Low | Mitigated |
| R-03 | Statistics Canada revises past values, making stored data and backtests wrong | 4 | 3 | 12 | Tables are reloaded in full on every refresh and upserted; methods note explains that backtests use revised history | Low | Mitigated, documented |
| R-04 | Forecasts are read as advice or as more certain than they are | 3 | 4 | 12 | Ranges come from real past errors; page states when a method is no better than assuming no change; README and footer say forecasts are projections, not advice | Low | Mitigated. A "How to read this" page (B-10) would help |
| R-05 | A dependency has a known vulnerability | 3 | 4 | 12 | `pip-audit` on every push and weekly; Dependabot pull requests; bounded version ranges | Low | Mitigated |
| R-06 | Insecure code or missing hardening reaches production | 2 | 5 | 10 | `bandit` in CI; Content-Security-Policy; `check --deploy` test; production refuses the development secret key; port bound to localhost by default | Low | Mitigated |
| R-07 | Traffic to the demo is unencrypted because the server is reached by IP address over HTTP | 5 | 2 | 10 | Only public data is served and there are no accounts; documented in the security notes; HTTPS settings are ready (B-05) | Medium | Accepted until a domain exists |
| R-08 | Data goes stale unnoticed (cron stops, server restarts, source outage) | 3 | 3 | 9 | Status page warns after three days without a load; `/status.json` for an external monitor; refresh logs each step | Medium | Partly mitigated. Cron and monitor are not yet verified on the server (B-03) |
| R-09 | The database is lost and the backup cannot be restored | 2 | 5 | 10 | A daily backup script is provided but not yet confirmed running; data can be rebuilt from public sources in minutes | Medium | **Open.** The restore has never been tested (B-04). Until then the backup is an assumption |
| R-10 | The demo is not reachable from outside, so the project cannot be shown live | 4 | 3 | 12 | Server and containers are healthy locally; diagnosis of the network path is in progress | High until fixed | **Open** (B-01) |
| R-11 | Accessibility regressions as pages change | 3 | 3 | 9 | Contrast and structure tests on every run; axe-core audit in CI in both languages, both themes, desktop and 320 px | Low | Mitigated. Real-user testing (B-15) has not happened |
| R-12 | Untranslated or inconsistent French | 3 | 3 | 9 | A failing test on any untranslated string or stale compiled catalog | Low | Mitigated. The translations have not been reviewed by a professional translator |
| R-13 | Licence terms are breached or misattributed | 2 | 4 | 8 | Notices required by the Statistics Canada Open Licence and the Bank of Canada terms are in the footer on every page, checked by tests; no logos used; "not endorsed" wording | Low | Mitigated |
| R-14 | Single person: illness, time pressure or loss of the machine stops the project | 3 | 3 | 9 | Everything is in version control with CI; architecture, operations and decisions are written down; scope is limited | Medium | Accepted |
| R-15 | Copy-and-paste errors when moving files between machines cause hidden regressions | 3 | 3 | 9 | Files are now written directly; the passing-test count is checked after each change; CI blocks a broken push | Low | Mitigated. This happened once (pasted test file held the wrong content) |
| R-16 | Secrets leak through the repository or logs | 2 | 5 | 10 | `.env` is git-ignored; no secrets in the status page or logs; the container build uses a throwaway key | Low | Mitigated |
| R-17 | Scope creep delays hosting and quality work | 4 | 2 | 8 | Backlog is prioritised with trade-offs recorded; new features wait behind items that prove the system works in operation | Low | Managed |

## Reading the register

- **High right now:** R-10 only. Fixing it is the top backlog item.
- **Open and not yet proven:** R-09 (restore) and R-08 (cron on the server). These are cheap to
  close, and they are what turns "designed" into "operated".
- **Accepted on purpose:** R-07 and R-14, with the reason written next to them.
