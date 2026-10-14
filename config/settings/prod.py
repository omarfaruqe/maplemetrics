"""Production settings."""

from .base import *  # noqa: F401,F403
from .base import SECRET_KEY, env_bool

if SECRET_KEY == "insecure-dev-key-change-me":  # pragma: no cover
    raise RuntimeError("Set DJANGO_SECRET_KEY in production.")

DEBUG = False
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
# The container healthcheck calls /health/ over plain HTTP, so it must not be redirected.
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
# Joining the browser HSTS preload list is hard to undo, so it stays a deliberate, later decision.
SILENCED_SYSTEM_CHECKS = ["security.W021"]
