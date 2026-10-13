from datetime import date
from itertools import pairwise

import numpy as np
import pytest

from apps.analytics.tests.conftest import load
from apps.forecasting import service
from apps.forecasting.methods import METHODS
from apps.forecasting.models import Forecast, ForecastPoint
from apps.forecasting.service import (
    ForecastError,
    build_forecast,
    interval_halfwidths,
    save_forecast,
)
from apps.forecasting.tests.conftest import months

FAST = {"count": 3, "step": 3}


def test_halfwidths_are_the_quantile_of_absolute_errors_per_horizon():
    errors = np.array([[1.0, -2.0], [3.0, 4.0], [-5.0, 6.0]])
    assert interval_halfwidths(errors, 1.0).tolist() == [5.0, 6.0]
    assert interval_halfwidths(errors, 0.5).tolist() == [3.0, 4.0]


def test_halfwidths_never_narrow_with_the_horizon():
    errors = np.array([[5.0, 1.0, 2.0]])
    assert interval_halfwidths(errors, 0.8).tolist() == [5.0, 5.0, 5.0]


def test_forecast_has_consecutive_months_and_a_range_around_each_value(
    unemployment_two_geographies,
):
    result = build_forecast("LFS_UNEMPLOYMENT_RATE", "Canada", **FAST)
    assert result.method == "ets"
    assert len(result.dates) == len(result.values) == 12
    assert result.dates[0] == date(2023, 5, 1) and result.dates[-1] == date(2024, 4, 1)
    assert result.trained_through == date(2023, 4, 1)
    for low, value, high in zip(result.lowers, result.values, result.uppers, strict=True):
        assert 0 <= low <= value <= high
    widths = [high - low for low, high in zip(result.lowers, result.uppers, strict=True)]
    assert all(later >= earlier - 1e-9 for earlier, later in pairwise(widths))
    assert result.backtest_origins == 3 and result.level == 0.8
    assert result.vs_naive is not None and result.vs_naive > 0


def test_log_targets_use_their_chosen_method_and_stay_positive(cpi):
    result = build_forecast("CPI_ALL_ITEMS", "Canada", **FAST)
    assert result.method == "drift"
    assert min(result.lowers) > 0 and result.values[-1] > result.values[0]


def test_constant_series_has_no_naive_ratio(db):
    load("LFS_UNEMPLOYMENT_RATE", [("Canada", d, 6.0) for d in months(120)])
    assert build_forecast("LFS_UNEMPLOYMENT_RATE", "Canada", **FAST).vs_naive is None


def test_missing_and_short_series_raise_forecast_errors(db):
    with pytest.raises(ForecastError, match="no data"):
        build_forecast("LFS_UNEMPLOYMENT_RATE", "Canada")
    load("LFS_UNEMPLOYMENT_RATE", [("Canada", d, 6.0) for d in months(30)])
    with pytest.raises(ForecastError, match="too short"):
        build_forecast("LFS_UNEMPLOYMENT_RATE", "Canada")


def test_a_method_that_fails_everywhere_raises(unemployment_two_geographies, monkeypatch):
    def broken(train, horizon):
        raise RuntimeError("no fit")

    monkeypatch.setitem(METHODS, "ets", broken)
    with pytest.raises(ForecastError, match="failed at every backtest origin"):
        build_forecast("LFS_UNEMPLOYMENT_RATE", "Canada", **FAST)


@pytest.mark.parametrize("final_call", ["raise", "nan"])
def test_a_method_that_fails_only_on_the_final_fit_raises(
    unemployment_two_geographies, monkeypatch, final_call
):
    calls = {"n": 0}

    def flaky(train, horizon):
        calls["n"] += 1
        if calls["n"] <= 3:
            return np.repeat(train[-1], horizon)
        if final_call == "raise":
            raise RuntimeError("boom")
        return np.full(horizon, np.nan)

    monkeypatch.setitem(METHODS, "ets", flaky)
    expected = "could not fit" if final_call == "raise" else "unusable forecast"
    with pytest.raises(ForecastError, match=expected):
        build_forecast("LFS_UNEMPLOYMENT_RATE", "Canada", **FAST)


def test_saving_twice_keeps_one_forecast_with_twelve_points(unemployment_two_geographies):
    result = build_forecast("LFS_UNEMPLOYMENT_RATE", "Canada", **FAST)
    first = save_forecast(result)
    second = save_forecast(result)
    assert first.pk == second.pk
    assert Forecast.objects.count() == 1 and ForecastPoint.objects.count() == 12
    stored = Forecast.objects.get()
    assert stored.method == "ets" and stored.backtest_origins == 3
    assert stored.points.first().date == date(2023, 5, 1)


def test_saving_a_new_result_replaces_the_old_points(unemployment_two_geographies):
    result = build_forecast("LFS_UNEMPLOYMENT_RATE", "Canada", **FAST)
    save_forecast(result)
    shorter = service.ForecastResult(
        **{
            **result.__dict__,
            "dates": result.dates[:3],
            "values": result.values[:3],
            "lowers": result.lowers[:3],
            "uppers": result.uppers[:3],
        }
    )
    save_forecast(shorter)
    assert ForecastPoint.objects.count() == 3
