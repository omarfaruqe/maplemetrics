import csv
import io

import pytest
from django.urls import reverse

from apps.core.csvout import cell, csv_response
from apps.core.tests.site_pages import seed_site

pytestmark = pytest.mark.django_db


def parse(response):
    text = response.content.decode("utf-8")
    assert text.startswith("﻿")
    return list(csv.reader(io.StringIO(text.lstrip("﻿"))))


def test_cells_are_plain_numbers_and_formulas_are_defused():
    assert cell(2.5) == "2.5"
    assert cell(3.0) == "3"
    assert cell(-0.15) == "-0.15"
    assert cell(0.00001) == "0"
    assert cell(None) == ""
    assert cell("Québec") == "Québec"
    for text in ("=1+1", "+1", "-1", "@SUM(A1)"):
        assert cell(text).startswith("'")


def test_response_is_an_attachment_with_a_byte_order_mark():
    response = csv_response("x.csv", ["a", "b"], [(1, "é")])
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    assert response["Content-Disposition"] == 'attachment; filename="x.csv"'
    assert parse(response) == [["a", "b"], ["1", "é"]]


def test_policy_rate_download_has_every_month_and_the_source(client):
    seed_site()
    rows = parse(client.get(reverse("analytics:rates_csv")))
    assert rows[0] == [
        "date",
        "policy_rate_pct",
        "core_inflation_pct",
        "real_policy_rate_pct",
        "source",
    ]
    assert len(rows) > 1
    for row in rows[1:]:
        assert row[1:4] == [str(round(float(v), 4)).rstrip("0").rstrip(".") for v in row[1:4]]
        assert "Open Government Licence" in row[4]
        assert float(row[3]) == pytest.approx(float(row[1]) - float(row[2]), abs=0.01)


def test_province_tables_download_matches_the_page(client):
    seed_site()
    unemployment = parse(client.get(reverse("analytics:unemployment_csv")))
    assert {row[0] for row in unemployment[1:]} == {"Canada", "Quebec", "Ontario"}
    retail = parse(client.get(reverse("analytics:retail_csv")))
    by_geo = {row[0]: row for row in retail[1:]}
    assert by_geo["Canada"][2:5] == ["4", "3", "0.97"]


def test_province_series_download_compares_with_canada(client):
    seed_site()
    url = reverse("analytics:province_csv")
    rows = parse(client.get(url, {"series": "unemployment", "geo": "Quebec"}))
    assert rows[0][:4] == [
        "geography",
        "date",
        "unemployment_rate_pct",
        "canada_unemployment_rate_pct",
    ]
    assert all(row[0] == "Quebec" for row in rows[1:])


def test_province_download_rejects_unknown_input(client):
    seed_site()
    url = reverse("analytics:province_csv")
    assert client.get(url, {"series": "nope", "geo": "Quebec"}).status_code == 404
    assert client.get(url, {"series": "unemployment", "geo": "Atlantis"}).status_code == 404
    assert client.get(url).status_code == 404


def test_forecast_download_has_history_then_forecast(client):
    seed_site()
    url = reverse("forecasting:forecast_csv")
    response = client.get(url, {"indicator": "LFS_UNEMPLOYMENT_RATE", "geo": "Canada"})
    rows = parse(response)
    header, body = rows[0], rows[1:]
    assert header[:5] == ["indicator", "geography", "kind", "date", "value"]
    kinds = [row[2] for row in body]
    assert kinds.count("forecast") == 12
    assert kinds.index("forecast") == kinds.count("actual")
    forecast = [row for row in body if row[2] == "forecast"]
    assert all(float(r[5]) <= float(r[4]) <= float(r[6]) for r in forecast)
    assert forecast[0][8] == "ets" and forecast[0][9] == "80"
    assert "lfs_unemployment_rate-canada" in response["Content-Disposition"]


def test_forecast_download_rejects_unknown_input(client):
    seed_site()
    url = reverse("forecasting:forecast_csv")
    assert client.get(url, {"indicator": "X", "geo": "Canada"}).status_code == 404
    assert (
        client.get(url, {"indicator": "LFS_UNEMPLOYMENT_RATE", "geo": "Atlantis"}).status_code
        == 404
    )


def test_pages_link_to_their_downloads_in_both_languages(client):
    from apps.core.tests.site_pages import render_pages

    seed_site()
    pages = render_pages(client)
    for language, label in (("en", "Download data (CSV)"), ("fr", "Télécharger les données (CSV)")):
        assert pages[f"dashboard-{language}"].count(label) == 3
        assert pages[f"provinces-{language}"].count(label) == 3
        assert pages[f"forecasts-{language}"].count(label) == 1
    assert "downloads/forecast.csv?indicator=LFS_UNEMPLOYMENT_RATE" in pages["forecasts-en"]
