from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from apps.warehouse.models import Indicator, Observation


def test_page_explains_when_nothing_is_loaded(client, db):
    response = client.get(reverse("core:freshness"))
    assert response.status_code == 200
    assert "No data loaded yet" in response.content.decode()


def test_page_shows_status_and_localized_names(client, db):
    indicator = Indicator.objects.create(
        code="PAGE_TEST",
        source="boc",
        name_en="English name",
        name_fr="Nom français",
        unit="",
        frequency="daily",
    )
    Observation.objects.create(
        indicator=indicator,
        geography="Canada",
        date=timezone.localdate() - timedelta(days=30),
        value=Decimal("1"),
    )

    english = client.get(reverse("core:freshness")).content.decode()
    assert "PAGE_TEST" in english
    assert "English name" in english
    assert "Stale" in english
    assert "Bank of Canada" in english

    french = client.get(reverse("core:freshness"), HTTP_ACCEPT_LANGUAGE="fr").content.decode()
    assert "Nom français" in french
    assert '<html lang="fr">' in french
