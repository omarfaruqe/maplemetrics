"""Pages must stay cheap as the data grows: few queries, and the same number however many provinces.

Query counts are exact and so are safe to assert. Timings are not, so the time limits are generous:
they exist to catch a page that has become slow by an order of magnitude, not to rank machines.
"""

import statistics
import time

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.core.tests.perf_data import PROVINCES, seed_realistic

pytestmark = pytest.mark.django_db

# Measured on 2026-10-21 with eleven geographies and twenty years of data, plus one of headroom.
PAGES = {
    "dashboard": (lambda: reverse("analytics:dashboard"), 6),
    "provinces": (lambda: reverse("analytics:provinces") + "?geo=Quebec", 10),
    "forecasts": (
        lambda: reverse("forecasting:forecasts") + "?indicator=LFS_UNEMPLOYMENT_RATE&geo=Quebec",
        5,
    ),
    "freshness": (lambda: reverse("core:freshness"), 3),
    "status": (lambda: reverse("core:status"), 7),
    "guide": (lambda: reverse("core:guide"), 1),
    "policy-rate-csv": (lambda: reverse("analytics:rates_csv"), 3),
    "unemployment-csv": (lambda: reverse("analytics:unemployment_csv"), 2),
    "retail-csv": (lambda: reverse("analytics:retail_csv"), 3),
    "province-csv": (
        lambda: reverse("analytics:province_csv") + "?series=real-retail&geo=Quebec",
        6,
    ),
    "forecast-csv": (
        lambda: reverse("forecasting:forecast_csv") + "?indicator=LFS_UNEMPLOYMENT_RATE&geo=Quebec",
        4,
    ),
}
SECONDS_PER_PAGE = 1.5


@pytest.fixture
def realistic(db):
    seed_realistic()


def count_queries(client, url):
    client.get(url)  # the first request pays for loading templates and translations
    with CaptureQueriesContext(connection) as queries:
        response = client.get(url)
    assert response.status_code == 200
    return len(queries)


@pytest.mark.parametrize("name", PAGES)
def test_page_stays_within_its_query_budget(client, realistic, name):
    make_url, budget = PAGES[name]
    used = count_queries(client, make_url())
    assert used <= budget, f"{name} used {used} queries; the budget is {budget}"


@pytest.mark.parametrize("name", PAGES)
def test_page_answers_quickly_with_realistic_data(client, realistic, name):
    url = PAGES[name][0]()
    client.get(url)
    times = []
    for _ in range(3):
        started = time.perf_counter()
        assert client.get(url).status_code == 200
        times.append(time.perf_counter() - started)
    assert statistics.median(times) < SECONDS_PER_PAGE, f"{name}: {times}"


@pytest.mark.parametrize("name", PAGES)
def test_query_count_does_not_grow_with_the_number_of_provinces(client, db, name):
    """A query per province would pass a budget today and fail as soon as one is added."""
    first = ("Canada", "Quebec", "Ontario")
    seed_realistic(first)
    url = PAGES[name][0]()
    few = count_queries(client, url)
    seed_realistic(tuple(p for p in PROVINCES if p not in first))
    assert count_queries(client, url) == few, name
