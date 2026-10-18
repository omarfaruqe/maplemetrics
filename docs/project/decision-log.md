# Decision log

Each entry records a choice that would be costly to reverse: the situation, the options, what was
chosen and what it costs. Newer entries do not delete older ones; a changed decision gets a new
entry that supersedes the old one.

| ID | Decision | Date | Status |
|---|---|---|---|
| D-01 | Draw charts on the server as SVG | 2026-10-11 | Accepted |
| D-02 | Full reload and upsert for Statistics Canada data | 2026-10-11 | Accepted |
| D-03 | Compute forecasts ahead of time and store them | 2026-10-13 | Accepted |
| D-04 | Compile the translation catalog with a small Python tool | 2026-10-13 | Accepted |
| D-05 | Prediction ranges from past forecast errors | 2026-10-13 | Accepted |
| D-06 | Public read-only API without keys | 2026-10-13 | Accepted |
| D-07 | Serve plain HTTP behind an explicit switch | 2026-10-16 | Accepted, to be superseded by HTTPS (B-05) |
| D-08 | Share one server by URL path, with a prefix setting | 2026-10-17 | Accepted, not yet verified in operation (B-01) |
| D-09 | Strict Content-Security-Policy with a per-request nonce | 2026-10-17 | Accepted |
| D-10 | Serve static files with WhiteNoise | 2026-10-17 | Accepted |
| D-11 | WCAG 2.2 AA as a tested requirement | 2026-10-17 | Accepted |

---

## D-01. Draw charts on the server as SVG

**Context.** The charts must work in light and dark mode, be readable by assistive technology,
and not need a front-end build.
**Options.** A JavaScript chart library; images rendered with a plotting library; SVG built by
the server.
**Decision.** Build SVG strings in Python and style them with CSS variables.
**Consequences.** No JavaScript at all, which later allowed a policy that forbids scripts
(D-09). Charts get names and descriptions easily. The cost is more chart code to maintain
(tick selection, label placement) and less interactivity; hover text needs a pointer, so each
chart also has a description and a table.

## D-02. Full reload and upsert for Statistics Canada data

**Context.** Statistics Canada revises seasonally adjusted values after the fact.
**Options.** Load only new dates; reload everything and update changed rows.
**Decision.** Reload each table in full and upsert on (indicator, geography, date).
**Consequences.** Revisions are picked up and re-running is always safe. The download is larger
and slower than an incremental load, which is acceptable for a daily job. Bank of Canada series,
which are not revised, load incrementally.

## D-03. Compute forecasts ahead of time and store them

**Context.** Fitting and backtesting six methods across about 33 series takes minutes.
**Options.** Compute on request; compute on a schedule and store.
**Decision.** A command builds and stores forecasts after each data refresh.
**Consequences.** Pages are fast and predictable and a request never runs a model. Forecasts are
as old as the last refresh, which the status page makes visible.

## D-04. Compile the translation catalog with a small Python tool

**Context.** The standard workflow needs GNU gettext, which is missing from the development
environment, laptops and CI by default.
**Options.** Require gettext everywhere; commit only compiled files; write a compiler.
**Decision.** A short Python parser and `.mo` builder, with tests that fail on any untranslated
string or stale compiled file.
**Consequences.** No extra software for contributors and French cannot silently fall behind.
The tool must handle the catalog features in use; unusual gettext features would need work.

## D-05. Prediction ranges from past forecast errors

**Context.** A forecast without a range overstates certainty, and a normal-distribution range
assumes something the data may not support.
**Options.** Model-based intervals; a fixed percentage; ranges taken from the method's own
rolling-origin errors.
**Decision.** Use the empirical error quantiles from the backtest for the 80% range, and say so on
the page, including when a method is no better than assuming no change.
**Consequences.** Ranges reflect how the method actually erred on that series. They need enough
history to have backtest origins and they describe the past, not a guarantee.

## D-06. Public read-only API without keys

**Context.** The data is already public and the API only reads it.
**Options.** Keys and accounts; open access with limits.
**Decision.** Open access with a per-client rate limit and cache headers.
**Consequences.** No account system to build or secure and no friction for users. Abuse control
relies on the rate limit; a key system could be added if usage required it.

## D-07. Serve plain HTTP behind an explicit switch

**Context.** The demo server is reached by IP address; there is no domain, so no certificate.
**Options.** Self-signed certificate; wait for a domain; HTTP with the secure defaults switched off.
**Decision.** `DJANGO_HTTPS` defaults to true. Setting it to false turns off the HTTPS redirect,
secure cookies and HSTS together, for this one deployment.
**Consequences.** The safe behaviour stays the default and the exception is explicit and tested.
Traffic is unencrypted until HTTPS is added (risk R-07, backlog B-05).

## D-08. Share one server by URL path, with a prefix setting

**Context.** Several projects will run on one IP address, and the owner wants
`http://IP/maplemetrics/`, not a port per project.
**Options.** A port per project; subdomains (need a domain); a path prefix with a gateway.
**Decision.** `DJANGO_URL_PREFIX` makes Django generate prefixed URLs. A reverse proxy
(Caddy) on port 80 strips the prefix and forwards to the app. Session, CSRF and language cookies
get prefix-specific names and paths so projects on the same host do not overwrite each other's.
**Consequences.** Adding a project is adding a route. The app must never hard-code a path, which
tests enforce. The proxy is shared infrastructure, so a mistake there affects every project; it is
not yet verified in operation.

## D-09. Strict Content-Security-Policy with a per-request nonce

**Context.** With no JavaScript on the site (D-01), almost everything a policy would normally
allow can be forbidden.
**Options.** No policy; a loose policy with `unsafe-inline`; a strict policy with a nonce.
**Decision.** The site allows no scripts and no outside origins. The one inline style block per
page is allowed by a fresh nonce; `style` attributes on chart elements are allowed. The admin and the
Swagger UI page, which need more, get their own looser policies.
**Consequences.** Injected scripts would not run. A real-browser test checks the policy does not
break the pages. Swagger UI still loads from a CDN with an inline script, so its page is the
weakest point (backlog B-06).

## D-10. Serve static files with WhiteNoise

**Context.** The only static files are the admin's, and the production container served none.
**Options.** A separate web server or the gateway serving files; object storage and a CDN;
WhiteNoise inside the app.
**Decision.** WhiteNoise, with files collected during the image build, hashed and compressed.
**Consequences.** No extra service or configuration and it works behind any proxy or prefix. The
app process serves the files, which is fine at this scale.

## D-11. WCAG 2.2 AA as a tested requirement

**Context.** The site is meant to serve the public in two languages, and Canadian public-sector
services are expected to be accessible.
**Options.** Follow guidelines informally; audit once by hand; automate the checks.
**Decision.** Target WCAG 2.2 AA and enforce it with contrast and structure tests on every run, and
an axe-core audit in CI across all pages, both languages, both themes and a 320 px width.
**Consequences.** The first audit found 22 violations that were all fixed and cannot return
unnoticed. Automated tools find only part of the problems, so testing with real users remains
open (B-15).
