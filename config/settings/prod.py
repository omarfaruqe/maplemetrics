"""Production settings."""

from .base import *  # noqa: F401,F403
from .base import SECRET_KEY, env_bool

if SECRET_KEY == "insecure-dev-key-change-me":  # pragma: no cover
    raise RuntimeError("Set DJANGO_SECRET_KEY in production.")

DEBUG = False
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
