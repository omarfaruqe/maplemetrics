import numpy as np
from django.urls import reverse

from apps.analytics.kpis import add_months
from apps.analytics.tests.conftest import load
from apps.forecasting.models import Forecast, ForecastPoint
from apps.forecasting.tests.conftest import months
from apps.warehouse.models import Indicator


def store(code, geography, *, level, vs_naive, series_start=6.0, scale=1.0):
    values = series_start + np.cumsum(np.full(80, 0.01))
    load(code, [(geography, d, float(v)) for d, v in zip(months(80), values, strict=True)])
    forecast = Forecast.objects.create(
        indicator=Indicator.objects.get(code=code),
        geography=geography,
        method="ets",
        trained_through=months(80)[-1],
        interval_level=0.8,
        backtest_origins=22,
        mase=2.0,
        vs_naive=vs_naive,
    )
    last = months(80)[-1]
    ForecastPoint.objects.bulk_create(
        ForecastPoint(
            forecast=forecast,
            date=add_months(last, i),
            value=level * scale,
            lower=(level - i * 0.1) * scale,
            upper=(level + i * 0.1) * scale,
        )
        for i in range(1, 13)
    )


def page(client, **params):
    return client.get(reverse("forecasting:forecasts"), params).content.decode()


def test_empty_state_points_to_the_command(client, db):
    assert "No forecasts yet" in page(client)


def test_page_shows_chart_range_method_and_table(client, db):
    store("LFS_UNEMPLOYMENT_RATE", "Canada", level=6.9, vs_naive=0.5)
    html = page(client)
    assert "<svg" in html and "80% range" in html
    assert "Method: ets" in html and "22 past forecast dates" in html
    assert "50% lower error than assuming no change" in html
    assert "View as table" in html and "2016-10" in html


def test_page_is_honest_when_the_method_has_no_edge(client, db):
    store("LFS_UNEMPLOYMENT_RATE", "Canada", level=6.9, vs_naive=0.97)
    assert "no better than assuming no change" in page(client)
    Forecast.objects.update(vs_naive=None)
    assert "no better than assuming no change" in page(client)


def test_selectors_fall_back_to_a_valid_choice(client, db):
    store("LFS_UNEMPLOYMENT_RATE", "Canada", level=6.9, vs_naive=0.5)
    store("LFS_UNEMPLOYMENT_RATE", "Quebec", level=5.5, vs_naive=0.5)
    html = page(client, indicator="NOPE", geo="Atlantis")
    assert '<option value="LFS_UNEMPLOYMENT_RATE" selected>' in html
    assert '<option value="Canada" selected>' in html
    assert '<option value="Quebec" selected>' in page(client, geo="Quebec")


def test_geography_list_has_canada_first(client, db):
    store("LFS_UNEMPLOYMENT_RATE", "Quebec", level=5.5, vs_naive=0.5)
    store("LFS_UNEMPLOYMENT_RATE", "Canada", level=6.9, vs_naive=0.5)
    html = page(client)
    assert html.index('value="Canada"') < html.index('value="Quebec"')


def test_retail_sales_are_shown_in_billions(client, db):
    store(
        "RETAIL_SALES",
        "Canada",
        level=70_000_000,
        vs_naive=0.7,
        series_start=69_000_000,
        scale=1.0,
    )
    html = page(client, indicator="RETAIL_SALES")
    assert "Retail sales (billions of CAD)" in html
    assert "70.0" in html and "70,000,000" not in html


def test_page_renders_in_french(client, db):
    store("LFS_UNEMPLOYMENT_RATE", "Canada", level=6.9, vs_naive=0.5)
    html = client.get(reverse("forecasting:forecasts"), HTTP_ACCEPT_LANGUAGE="fr").content.decode()
    assert '<html lang="fr">' in html


def test_navigation_links_to_forecasts(client, db):
    html = client.get(reverse("analytics:dashboard")).content.decode()
    assert reverse("forecasting:forecasts") in html
