# Security

MapleMetrics serves only public data and accepts no user content, so the aim is a small attack
surface and automatic detection of problems in what it depends on. This page lists what is in
place and what is not.

## In the application

| Control | How | Where |
|---|---|---|
| Content-Security-Policy | The site allows no scripts, no outside origins and no framing. The one inline `<style>` block per page is allowed by a fresh nonce on every request | `apps/core/security.py` |
| Looser policies, kept separate | `/admin/` and the Swagger UI at `/api/v1/docs/` each get their own policy, because they need more than the site does | same file |
| Permissions-Policy | Camera, microphone, location, payment and USB are switched off | same file |
| HTTPS settings | Redirect to HTTPS, secure cookies, HSTS and a proxy header, switchable with `DJANGO_HTTPS=false` for a plain-HTTP server | `config/settings/prod.py` |
| Other headers | `nosniff`, `same-origin` referrer policy, `X-Frame-Options: DENY`, cross-origin opener policy | same file |
| Escaping | Charts are built as SVG text and marked safe, so every piece of text in them is escaped first | `apps/*/charts.py` |
| Read-only API | Only GET, no authentication to bypass, rate limited | `apps/api/` |
| Static files | Served by WhiteNoise from files collected at build time, so nothing at request time reads the file system outside that folder | `config/settings/`, `Dockerfile` |
| Container | Runs as a non-root user; the base compose file publishes the app on `127.0.0.1` only | `Dockerfile`, `docker-compose.yml` |
| Secrets | Read from the environment; production refuses to start with the development key; `.env` is not in git | `config/settings/` |

## In the pipeline

| Check | What it catches | When |
|---|---|---|
| `check --deploy` test | Missing production hardening in Django settings | every test run |
| Header tests | A page without a policy, a style block without a nonce, any `<script>` or inline event handler | every test run |
| Escaping tests | Text in a chart turning into an element or an event handler | every test run |
| Browser test | The policy blocking the page's own styles or charts in a real browser | CI, `accessibility` job |
| `bandit` | Common insecure code patterns | every push, weekly |
| `pip-audit` | Dependencies with a published vulnerability | every push, weekly |
| Dependabot | Outdated Python packages, GitHub Actions and the Docker base image, as pull requests | weekly |

Run the two scanners locally with `make audit` (after `pip install -r requirements-dev.txt`).

## Choices worth knowing

- **Swagger UI needs a looser policy.** The interactive API documentation loads its code from the
  jsDelivr CDN and starts itself with an inline script, so `/api/v1/docs/` allows both. It is a
  documentation page with no sensitive data, and the rest of the site is not affected.
  Serving Swagger from the project itself (the `drf-spectacular-sidecar` package) would remove the
  CDN dependency; that is a possible later change.
- **Two bandit findings are marked on purpose.** `mark_safe` in the chart code is safe because
  every text value is escaped before it is added, and the tests above check that. The development
  secret-key string is a guard that stops production starting, not a password. Each marker has the
  reason beside it.
- **`style` attributes are allowed.** Chart colours are set with `style` attributes that point at
  CSS variables, so the policy permits inline style attributes but not inline scripts. Style
  injection is a far smaller risk than script injection.

## Not covered yet

- **HTTPS on the demo server.** It is reached by IP address over plain HTTP, so traffic is not
  encrypted. That is acceptable for public data and not for anything else. A domain name and a
  certificate are the fix, and the settings already support them.
- **Container image scanning.** Dependabot keeps the base image current, but the built image is
  not scanned.
- **Security headers on the gateway.** They come from Django. A shared reverse proxy for several
  projects could add its own.

To report a problem, see [SECURITY.md](../SECURITY.md).
