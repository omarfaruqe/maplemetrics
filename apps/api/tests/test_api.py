from datetime import date

import pytest
from django.urls import reverse

from apps.analytics.tests.conftest import economy, load  # noqa: F401
from apps.forecasting.models import Forecast, ForecastPoint
from apps.warehouse.models import Indicator


@pytest.fixture
def stored_forecast(economy):  # noqa: F811
    forecast = Forecast.objects.create(
        indicator=Indicator.objects.get(code="LFS_UNEMPLOYMENT_RATE"),
        geography="Canada",
        method="ets",
        trained_through=date(2026, 9, 1),
        backtest_origins=20,
        mase=2.0,
        vs_naive=0.95,
    )
    ForecastPoint.objects.create(
        forecast=forecast, date=date(2026, 10, 1), value=6.5, lower=6.0, upper=7.0
    )
    return forecast


def get(client, name, **kwargs):
    return client.get(reverse(f"api:{name}", kwargs=kwargs.pop("kwargs", None)), kwargs)


def test_indicator_list_has_counts_and_dates(client, economy):  # noqa: F811
    body = get(client, "indicator-list").json()
    by_code = {row["code"]: row for row in body["results"]}
    assert body["count"] == 5
    assert by_code["LFS_UNEMPLOYMENT_RATE"]["observation_count"] == 5
    assert by_code["LFS_UNEMPLOYMENT_RATE"]["latest_date"] == "2026-09-01"
    assert by_code["LFS_UNEMPLOYMENT_RATE"]["first_date"] == "2025-09-01"


def test_indicator_detail_by_code(client, economy):  # noqa: F811
    response = get(client, "indicator-detail", kwargs={"code": "V39079"})
    assert response.status_code == 200
    assert response.json()["frequency"] == "daily"


def test_unknown_indicator_is_404(client, economy):  # noqa: F811
    assert get(client, "indicator-detail", kwargs={"code": "NOPE"}).status_code == 404


def test_indicator_name_follows_language(client, db):
    load("CPI_TRIM", [("Canada", date(2026, 1, 1), 2.0)])
    Indicator.objects.filter(code="CPI_TRIM").update(name_en="English", name_fr="Français")
    url = reverse("api:indicator-detail", kwargs={"code": "CPI_TRIM"})
    assert client.get(url).json()["name"] == "English"
    assert client.get(url, headers={"Accept-Language": "fr"}).json()["name"] == "Français"


def test_observations_filtered_and_ordered(client, economy):  # noqa: F811
    body = get(
        client, "observation-list", indicator="LFS_UNEMPLOYMENT_RATE", geography="Quebec"
    ).json()
    assert body["count"] == 2
    assert [row["date"] for row in body["results"]] == ["2025-09-01", "2026-09-01"]
    assert body["results"][0]["value"] == 5.0
    assert body["results"][0]["indicator"] == "LFS_UNEMPLOYMENT_RATE"


def test_observations_date_range(client, economy):  # noqa: F811
    body = get(
        client,
        "observation-list",
        indicator="LFS_UNEMPLOYMENT_RATE",
        geography="Canada",
        start="2026-01-01",
        end="2026-12-31",
    ).json()
    assert [row["date"] for row in body["results"]] == ["2026-09-01"]


def test_bad_date_is_a_400_naming_the_field(client, economy):  # noqa: F811
    response = get(client, "observation-list", start="yesterday")
    assert response.status_code == 400
    assert "start" in response.json()


def test_pagination_page_size(client, economy):  # noqa: F811
    body = get(client, "observation-list", page_size=3).json()
    assert len(body["results"]) == 3
    assert body["next"] is not None
    assert body["count"] > 3


def test_observations_are_read_only(client, economy):  # noqa: F811
    response = client.post(reverse("api:observation-list"), {})
    assert response.status_code == 405


def test_forecast_list_and_detail_include_points(client, stored_forecast):
    listing = get(client, "forecast-list", indicator="LFS_UNEMPLOYMENT_RATE").json()
    assert listing["count"] == 1
    detail = get(client, "forecast-detail", kwargs={"pk": stored_forecast.pk}).json()
    assert detail["method"] == "ets"
    assert detail["indicator"] == "LFS_UNEMPLOYMENT_RATE"
    assert detail["points"] == [{"date": "2026-10-01", "value": 6.5, "lower": 6.0, "upper": 7.0}]


def test_forecast_filter_by_geography(client, stored_forecast):
    assert get(client, "forecast-list", geography="Quebec").json()["count"] == 0


def test_schema_is_generated(client, economy):  # noqa: F811
    response = client.get(reverse("api:schema"), {"format": "json"})
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/observations/" in paths
    assert "/api/v1/forecasts/{id}/" in paths


def test_docs_page_loads(client):
    assert client.get(reverse("api:docs")).status_code == 200
