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


def run_in_production(*args):
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env={**os.environ, **PRODUCTION_ENV},
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
