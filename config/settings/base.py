"""Base settings shared by every environment."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    return env(name, str(default)).lower() in {"1", "true", "yes", "on"}


SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = [h for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.core",
    "apps.warehouse",
    "apps.ingestion",
    "apps.analytics",
    "apps.forecasting",
    "apps.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.security.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.security.csp_nonce",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "maplemetrics"),
        "USER": env("POSTGRES_USER", "maplemetrics"),
        "PASSWORD": env("POSTGRES_PASSWORD", "maplemetrics"),
        "HOST": env("POSTGRES_HOST", "db"),
        "PORT": env("POSTGRES_PORT", "5432"),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", "redis://redis:6379/1"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Bilingual (EN/FR) from day one.
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("fr", "Français")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "America/Toronto"
USE_I18N = True
USE_TZ = True

# Serving under a sub-path (for example https://host/maplemetrics/) when several projects share one
# server. The reverse proxy strips the prefix before the request reaches Django; Django adds it
# back to every URL it generates. Leave empty to serve from the root.
URL_PREFIX = env("DJANGO_URL_PREFIX").strip("/")

if URL_PREFIX:
    FORCE_SCRIPT_NAME = f"/{URL_PREFIX}"
    STATIC_URL = f"/{URL_PREFIX}/static/"
    # Cookies are scoped to the host, not the port, so projects on the same IP address would
    # otherwise overwrite each other's session, CSRF and language cookies.
    SESSION_COOKIE_NAME = f"{URL_PREFIX}_sessionid"
    SESSION_COOKIE_PATH = f"/{URL_PREFIX}/"
    CSRF_COOKIE_NAME = f"{URL_PREFIX}_csrftoken"
    CSRF_COOKIE_PATH = f"/{URL_PREFIX}/"
    LANGUAGE_COOKIE_NAME = f"{URL_PREFIX}_language"
    LANGUAGE_COOKIE_PATH = f"/{URL_PREFIX}/"
else:
    STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

API_THROTTLE_RATE = env("API_THROTTLE_RATE", "120/min")
API_CACHE_SECONDS = int(env("API_CACHE_SECONDS", "300"))

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS": "apps.api.pagination.StandardPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_THROTTLE_CLASSES": ["apps.api.throttling.AnonymousRateThrottle"],
    "COERCE_DECIMAL_TO_STRING": False,
    "UNAUTHENTICATED_USER": None,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "MapleMetrics API",
    "DESCRIPTION": (
        "Read-only access to Canadian economic data from the Bank of Canada and "
        "Statistics Canada, and the forecasts MapleMetrics builds from it."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
