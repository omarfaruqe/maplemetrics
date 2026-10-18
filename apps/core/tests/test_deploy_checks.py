import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.prod",
    "DJANGO_SECRET_KEY": "k9#Xv2!pQz7$Lw4&Rm8^Tn1*Ys6(Hd3)Bf5+Gj0-Cc9_Ea2=Uo7~Ik4",
    "DJANGO_ALLOWED_HOSTS": "example.com",
    "DJANGO_SECURE_SSL_REDIRECT": "true",
}


def run_in_production(*args, **extra_env):
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env={**os.environ, **PRODUCTION_ENV, **extra_env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_production_settings_pass_djangos_deployment_checks():
    result = run_in_production("manage.py", "check", "--deploy", "--fail-level", "WARNING")
    assert result.returncode == 0, result.stdout + result.stderr


def test_health_check_is_exempt_from_the_https_redirect():
    code = (
        "import django; django.setup(); from django.conf import settings; "
        "print(settings.SECURE_SSL_REDIRECT, settings.SECURE_REDIRECT_EXEMPT)"
    )
    result = run_in_production("-c", code)
    assert result.stdout.strip() == "True ['^health/$']", result.stdout + result.stderr


def test_plain_http_mode_disables_https_only_settings():
    code = (
        "import django; django.setup(); from django.conf import settings as s; "
        "print(s.SECURE_SSL_REDIRECT, s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE, "
        "s.SECURE_HSTS_SECONDS)"
    )
    env = {**PRODUCTION_ENV, "DJANGO_HTTPS": "false"}
    env.pop("DJANGO_SECURE_SSL_REDIRECT")
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env={**{k: v for k, v in os.environ.items() if k != "DJANGO_SECURE_SSL_REDIRECT"}, **env},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.stdout.strip() == "False False False 0", result.stdout + result.stderr


def test_url_prefix_is_added_to_generated_urls_and_cookies():
    code = (
        "import django; django.setup(); "
        "from django.conf import settings as s; from django.urls import reverse; "
        "from django.test import Client; "
        "r = Client().get('/', secure=True, HTTP_HOST='example.com'); "
        "print(reverse('analytics:dashboard'), r['Location'], s.SESSION_COOKIE_PATH, "
        "s.CSRF_COOKIE_NAME, s.STATIC_URL)"
    )
    result = run_in_production("-c", code, DJANGO_URL_PREFIX="/maplemetrics/")
    expected = (
        "/maplemetrics/dashboard/ /maplemetrics/dashboard/ /maplemetrics/ "
        "maplemetrics_csrftoken /maplemetrics/static/"
    )
    assert result.stdout.strip() == expected, result.stdout + result.stderr


def test_no_url_prefix_by_default():
    code = (
        "import django; django.setup(); from django.urls import reverse; "
        "from django.conf import settings as s; "
        "print(reverse('analytics:dashboard'), s.STATIC_URL)"
    )
    result = run_in_production("-c", code)
    assert result.stdout.strip() == "/dashboard/ /static/", result.stdout + result.stderr


def test_health_check_stays_exempt_under_a_url_prefix():
    code = (
        "import django; django.setup(); from django.conf import settings; "
        "import re; p = settings.SECURE_REDIRECT_EXEMPT[0]; "
        "print(bool(re.match(p, 'maplemetrics/health/')), bool(re.match(p, 'health/')), "
        "bool(re.match(p, 'maplemetrics/dashboard/')))"
    )
    result = run_in_production("-c", code, DJANGO_URL_PREFIX="/maplemetrics")
    assert result.stdout.strip() == "True True False", result.stdout + result.stderr
