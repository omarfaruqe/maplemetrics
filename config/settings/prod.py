"""Production settings."""

import re

from apps.core.logs import build_logging

from .base import *  # noqa: F401,F403
from .base import LOG_LEVEL, SECRET_KEY, URL_PREFIX, env, env_bool

if SECRET_KEY == "insecure-dev-key-change-me":  # pragma: no cover  # nosec B105
    raise RuntimeError("Set DJANGO_SECRET_KEY in production.")

# HTTPS is the default. Set DJANGO_HTTPS=false only for a plain-HTTP deployment
# (for example a server reached by IP address with no domain name and no certificate).
HTTPS = env_bool("DJANGO_HTTPS", True)

DEBUG = False
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", HTTPS)
# The container healthcheck calls /health/ over plain HTTP, so it must not be redirected.
# Django matches this against the full path, which includes the URL prefix when one is set.
_PREFIX_PATTERN = f"(?:{re.escape(URL_PREFIX)}/)?" if URL_PREFIX else ""
SECURE_REDIRECT_EXEMPT = [rf"^{_PREFIX_PATTERN}health/$"]
SESSION_COOKIE_SECURE = HTTPS
CSRF_COOKIE_SECURE = HTTPS
SECURE_HSTS_SECONDS = 31536000 if HTTPS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
# Joining the browser HSTS preload list is hard to undo, so it stays a deliberate, later decision.
SILENCED_SYSTEM_CHECKS = ["security.W021"]

# Static files are collected at image build time with a content hash in each name, so browsers
# can keep them indefinitely and a changed file always gets a new address. They are also
# pre-compressed. Development and tests keep the plain storage and need no collectstatic.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
WHITENOISE_USE_FINDERS = False

# Structured logs by default in production; set LOG_FORMAT=text to read them in a terminal.
LOGGING = build_logging(env("LOG_FORMAT", "json"), LOG_LEVEL)
