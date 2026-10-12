from datetime import date
from io import StringIO

import numpy as np
import pytest
from django.core.management import CommandError, call_command

from apps.analytics.kpis import add_months
from apps.analytics.tests.conftest import load
from apps.forecasting.targets import load_series, trailing_contiguous


def months(count, start=date(2010, 1, 1)):
    return [add_months(start, i) for i in range(count)]


def test_trailing_contiguous_keeps_only_the_latest_unbroken_run():
    days = months(5) + months(4, start=date(2011, 1, 1))
    points = [(day, float(i)) for i, day in enumerate(days)]
    run = trailing_contiguous(points)
    assert [value for _, value in run] == [5.0, 6.0, 7.0, 8.0]


def test_trailing_contiguous_handles_empty_and_clean_series():
    assert trailing_contiguous([]) == []
    clean = [(day, 1.0) for day in months(6)]
    assert trailing_contiguous(clean) == clean


@pytest.fixture
def unemployment(db):
    rng = np.random.default_rng(7)
    values = 6 + np.cumsum(rng.normal(0, 0.15, 160))
    load(
        "LFS_UNEMPLOYMENT_RATE",
        [("Canada", d, round(v, 3)) for d, v in zip(months(160), values, strict=True)],
    )


def test_load_series_returns_dates_and_values(unemployment):
    dates, values = load_series("LFS_UNEMPLOYMENT_RATE", "Canada")
    assert len(dates) == len(values) == 160
    assert load_series("LFS_UNEMPLOYMENT_RATE", "Quebec")[1].size == 0


def test_command_prints_a_leaderboard(unemployment):
    out = StringIO()
    call_command(
        "evaluate_forecasts",
        "LFS_UNEMPLOYMENT_RATE",
        "--horizon=6",
        "--origins=2",
        "--step=2",
        stdout=out,
    )
    text = out.getvalue()
    assert "LFS_UNEMPLOYMENT_RATE / Canada: 160 months" in text
    for method in ("naive", "seasonal_naive", "drift", "ets", "ets_seasonal", "arima"):
        assert method in text
    assert "MAE@6" in text and "MAE@12" not in text
    assert "Best:" in text


def test_command_rejects_an_unknown_indicator(db):
    with pytest.raises(CommandError):
        call_command("evaluate_forecasts", "NOPE")


def test_command_explains_when_there_is_no_data(db):
    with pytest.raises(CommandError, match="run the ingest commands"):
        call_command("evaluate_forecasts", "LFS_UNEMPLOYMENT_RATE", "--geography=Quebec")


def test_command_explains_when_the_series_is_too_short(db):
    load("LFS_UNEMPLOYMENT_RATE", [("Canada", d, 6.0) for d in months(30)])
    with pytest.raises(CommandError, match="too short"):
        call_command("evaluate_forecasts", "LFS_UNEMPLOYMENT_RATE")
