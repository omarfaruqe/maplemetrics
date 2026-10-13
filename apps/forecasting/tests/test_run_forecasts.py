from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from apps.analytics.tests.conftest import load
from apps.forecasting.models import Forecast
from apps.forecasting.tests.conftest import months

FAST = ["--origins=3", "--step=3"]


def run(*args):
    out = StringIO()
    call_command("run_forecasts", *args, *FAST, stdout=out)
    return out.getvalue()


def test_forecasts_every_geography_of_an_indicator(unemployment_two_geographies):
    text = run("--indicator=LFS_UNEMPLOYMENT_RATE")
    assert "LFS_UNEMPLOYMENT_RATE / Canada: ets" in text
    assert "LFS_UNEMPLOYMENT_RATE / Quebec: ets" in text
    assert "2 forecasts saved, 0 skipped." in text
    assert Forecast.objects.count() == 2


def test_runs_all_indicators_and_skips_those_not_loaded(unemployment_two_geographies):
    text = run()
    assert "skip CPI_ALL_ITEMS: not in the warehouse yet" in text
    assert "skip RETAIL_SALES: not in the warehouse yet" in text
    assert "2 forecasts saved, 2 skipped." in text


def test_can_target_one_geography(unemployment_two_geographies):
    text = run("--indicator=LFS_UNEMPLOYMENT_RATE", "--geography=Quebec")
    assert "1 forecasts saved" in text
    assert Forecast.objects.get().geography == "Quebec"


def test_rerunning_does_not_duplicate(unemployment_two_geographies):
    run("--indicator=LFS_UNEMPLOYMENT_RATE")
    run("--indicator=LFS_UNEMPLOYMENT_RATE")
    assert Forecast.objects.count() == 2


def test_short_series_are_skipped_with_a_reason(unemployment_two_geographies):
    load("LFS_UNEMPLOYMENT_RATE", [("Ontario", d, 6.0) for d in months(30)])
    text = run("--indicator=LFS_UNEMPLOYMENT_RATE")
    assert "skip LFS_UNEMPLOYMENT_RATE / Ontario: series of 30 points is too short" in text
    assert "2 forecasts saved, 1 skipped." in text


def test_an_empty_warehouse_skips_every_indicator(db):
    assert "0 forecasts saved, 3 skipped." in run()


def test_an_indicator_without_any_observations_is_an_error(db):
    load("LFS_UNEMPLOYMENT_RATE", [])
    with pytest.raises(CommandError, match="nothing to forecast"):
        run("--indicator=LFS_UNEMPLOYMENT_RATE")


def test_unknown_indicator_is_rejected(db):
    with pytest.raises(CommandError):
        call_command("run_forecasts", "--indicator=NOPE")
