"""Shared helpers for tests that look at every public page in both languages."""

from datetime import date

from django.conf import settings
from django.urls import reverse
from django.utils import translation

from apps.analytics.tests.conftest import load
from apps.forecasting.tests.test_forecast_page import store

LANGUAGES = ("en", "fr")


def seed_site():
    """Enough data for every page to draw its charts and tables."""
    for geography, value in (("Canada", 6.5), ("Quebec", 5.4), ("Ontario", 7.1)):
        store("LFS_UNEMPLOYMENT_RATE", geography, level=value, vs_naive=0.8)
    load(
        "V39079",
        [
            ("Canada", date(2026, 6, 5), 2.75),
            ("Canada", date(2026, 7, 10), 2.50),
            ("Canada", date(2026, 8, 12), 2.25),
        ],
        frequency="daily",
    )
    load(
        "CPI_TRIM",
        [
            ("Canada", date(2026, 6, 1), 3.0),
            ("Canada", date(2026, 7, 1), 2.8),
            ("Canada", date(2026, 8, 1), 2.5),
            ("Canada", date(2026, 9, 1), 2.4),
        ],
    )
    load(
        "RETAIL_SALES",
        [
            ("Canada", date(2025, 7, 1), 100000),
            ("Canada", date(2026, 7, 1), 104000),
            ("Quebec", date(2025, 7, 1), 20000),
            ("Quebec", date(2026, 7, 1), 20400),
        ],
    )
    load(
        "CPI_ALL_ITEMS",
        [
            ("Canada", date(2025, 7, 1), 160.0),
            ("Canada", date(2026, 7, 1), 164.8),
            ("Quebec", date(2025, 7, 1), 150.0),
            ("Quebec", date(2026, 7, 1), 157.5),
        ],
    )


def page_urls() -> dict[str, str]:
    return {
        "dashboard": reverse("analytics:dashboard"),
        "provinces": reverse("analytics:provinces") + "?geo=Quebec",
        "forecasts": reverse("forecasting:forecasts")
        + "?indicator=LFS_UNEMPLOYMENT_RATE&geo=Canada",
        "freshness": reverse("core:freshness"),
    }


def render_pages(client) -> dict[str, str]:
    """HTML of every page in both languages, keyed like ``dashboard-fr``."""
    html = {}
    try:
        for language in LANGUAGES:
            client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
            for name, url in page_urls().items():
                response = client.get(url)
                assert response.status_code == 200, (name, language)
                html[f"{name}-{language}"] = response.content.decode()
    finally:
        translation.deactivate()
    return html
