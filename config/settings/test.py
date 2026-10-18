"""Test settings: Postgres when POSTGRES_HOST is set (CI), otherwise in-memory SQLite."""

import os

from .base import *  # noqa: F401,F403

SECRET_KEY = "test-key"  # nosec B105
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

if not os.environ.get("POSTGRES_HOST"):
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
