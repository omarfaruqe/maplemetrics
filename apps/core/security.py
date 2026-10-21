"""Security headers that Django does not set on its own: a Content-Security-Policy and a
Permissions-Policy.

The site is server-rendered with no JavaScript, so its policy is strict: nothing may run, load
from another origin, or be framed. The only inline code is the ``<style>`` block in each page,
which is allowed by a per-request nonce, plus ``style`` attributes on chart elements.

Two areas need looser rules, and each gets its own policy:

* ``/admin/`` is Django's admin, which relies on its own inline styles.
* ``/api/v1/docs/`` is Swagger UI from drf-spectacular. Its code and styles are served from this
  project's own static files (the ``drf-spectacular-sidecar`` package), its start-up script is a
  separate request, and its one inline ``<style>`` carries the nonce. Nothing comes from a CDN and
  no inline script is allowed.
"""

from __future__ import annotations

import secrets

SITE_POLICY = (
    "default-src 'none'; "
    "style-src 'self' 'nonce-{nonce}'; "
    "style-src-attr 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'none'"
)

ADMIN_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'"
)

DOCS_POLICY = (
    "default-src 'none'; "
    "script-src 'self'; "
    "style-src 'self' 'nonce-{nonce}'; "
    "style-src-attr 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'none'"
)

PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"


def policy_for(path: str, nonce: str) -> str:
    """The Content-Security-Policy for a request path (without any URL prefix)."""
    if path.startswith("/admin/"):
        return ADMIN_POLICY
    if path.startswith("/api/v1/docs/"):
        return DOCS_POLICY.format(nonce=nonce)
    return SITE_POLICY.format(nonce=nonce)


class SecurityHeadersMiddleware:
    """Adds the policies above and exposes this request's nonce as ``request.csp_nonce``."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        if "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = policy_for(request.path_info, request.csp_nonce)
        if "Permissions-Policy" not in response:
            response["Permissions-Policy"] = PERMISSIONS_POLICY
        return response


def csp_nonce(request) -> dict[str, str]:
    """Template context processor: makes ``{{ csp_nonce }}`` available to ``<style nonce>``."""
    return {"csp_nonce": getattr(request, "csp_nonce", "")}
