import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.core import status
from apps.core.tests.site_pages import seed_site
from apps.warehouse.models import Indicator, Observation


def checks_by_key(client, **kwargs):
    body = client.get(reverse("core:status_json"), **kwargs).json()
    return body, body["checks"]


def test_empty_site_works_but_asks_for_data(client, db):
    response = client.get(reverse("core:status_json"))
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "attention"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["cache"]["status"] == "ok"
    assert body["checks"]["data"]["status"] == "warn"
    assert body["checks"]["last_refresh"]["status"] == "warn"
    assert body["checks"]["forecasts"]["status"] == "warn"


def test_loaded_site_reports_ok(client, db):
    seed_site()
    body, checks = checks_by_key(client)
    assert checks["database"]["latency_ms"] >= 0
    assert checks["last_refresh"]["status"] == "ok"
    assert checks["forecasts"]["count"] == 3
    assert body["version"]
    assert body["time"]


def test_stale_data_is_a_warning_not_an_outage(client, db):
    indicator = Indicator.objects.create(
        code="OLD", source="boc", name_en="Old", name_fr="Vieux", frequency="daily"
    )
    Observation.objects.create(
        indicator=indicator,
        geography="Canada",
        date=timezone.localdate() - timedelta(days=2000),
        value=1,
    )
    response = client.get(reverse("core:status_json"))
    assert response.status_code == 200
    assert response.json()["checks"]["data"]["status"] == "warn"


def test_old_refresh_is_flagged(client, db):
    seed_site()
    Observation.objects.update(ingested_at=timezone.now() - timedelta(days=10))
    assert (
        client.get(reverse("core:status_json")).json()["checks"]["last_refresh"]["status"] == "warn"
    )


def test_database_down_returns_503_on_both_endpoints(client, db):
    with patch("apps.core.status.connection") as mocked:
        mocked.cursor.side_effect = RuntimeError("down")
        json_response = client.get(reverse("core:status_json"))
        page_response = client.get(reverse("core:status"))
    assert json_response.status_code == 503
    assert json_response.json()["status"] == "down"
    assert json_response.json()["checks"]["database"]["status"] == "fail"
    assert page_response.status_code == 503


def test_cache_down_is_detected(client, db):
    with patch("apps.core.status.cache") as mocked:
        mocked.get.return_value = None
        response = client.get(reverse("core:status_json"))
    assert response.status_code == 503
    assert response.json()["checks"]["cache"]["status"] == "fail"
    with patch("apps.core.status.cache") as mocked:
        mocked.set.side_effect = ConnectionError("no redis")
        assert client.get(reverse("core:status_json")).status_code == 503


def test_page_is_bilingual_and_never_cached(client, db):
    seed_site()
    english = client.get(reverse("core:status"))
    assert "System status" in english.content.decode()
    assert "no-cache" in english["Cache-Control"] or "no-store" in english["Cache-Control"]
    french = client.get(reverse("core:status"), HTTP_ACCEPT_LANGUAGE="fr").content.decode()
    assert "État du système" in french
    assert '<html lang="fr">' in french


def test_json_exposes_no_hostnames_or_secrets(client, db):
    seed_site()
    text = json.dumps(client.get(reverse("core:status_json")).json())
    for forbidden in ("postgres", "redis://", "password", "SECRET"):
        assert forbidden.lower() not in text.lower()


def test_overall_picks_the_worst_status():
    ok = status.Check("a", "A", status.OK, "")
    warn = status.Check("b", "B", status.WARN, "")
    fail = status.Check("c", "C", status.FAIL, "")
    assert status.overall([ok]) == "ok"
    assert status.overall([ok, warn]) == "attention"
    assert status.overall([ok, warn, fail]) == "down"


@pytest.mark.parametrize("name", ["core:status", "core:status_json"])
def test_status_is_linked_from_the_navigation(client, db, name):
    html = client.get(reverse("analytics:dashboard")).content.decode()
    assert reverse("core:status") in html
