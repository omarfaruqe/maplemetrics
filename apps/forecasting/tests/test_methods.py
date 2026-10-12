import numpy as np
import pytest

from apps.forecasting import methods


def test_naive_repeats_the_last_value():
    assert methods.naive(np.array([1.0, 2.0, 5.0]), 3).tolist() == [5.0, 5.0, 5.0]


def test_seasonal_naive_repeats_the_last_year_and_wraps():
    train = np.arange(1.0, 25.0)
    forecast = methods.seasonal_naive(train, 14)
    assert forecast[:12].tolist() == list(range(13, 25))
    assert forecast[12:].tolist() == [13.0, 14.0]


def test_drift_continues_the_average_change():
    train = np.array([10.0, 12.0, 14.0, 16.0])
    assert methods.drift(train, 3).tolist() == [18.0, 20.0, 22.0]


@pytest.fixture
def seasonal_trend():
    months = np.arange(120)
    return 100 + 0.5 * months + 5 * np.sin(2 * np.pi * months / 12)


@pytest.mark.parametrize("name", ["ets", "ets_seasonal", "arima"])
def test_statistical_methods_return_finite_forecasts_of_the_right_length(name, seasonal_trend):
    forecast = methods.METHODS[name](seasonal_trend, 12)
    assert len(forecast) == 12
    assert np.all(np.isfinite(forecast))


def test_seasonal_ets_tracks_a_clean_seasonal_pattern(seasonal_trend):
    train, actual = seasonal_trend[:-12], seasonal_trend[-12:]
    seasonal_error = np.abs(methods.ets_seasonal(train, 12) - actual).mean()
    naive_error = np.abs(methods.naive(train, 12) - actual).mean()
    assert seasonal_error < naive_error / 3


def test_arima_follows_a_steady_trend():
    train = 50 + 0.4 * np.arange(100) + np.random.default_rng(3).normal(0, 0.05, 100)
    forecast = methods.arima(train, 6)
    assert forecast[-1] > train[-1]
    assert forecast[-1] == pytest.approx(50 + 0.4 * 105, abs=1.0)


def test_arima_raises_when_nothing_can_be_fitted(monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(methods, "ARIMA", broken)
    with pytest.raises(ValueError, match="no ARIMA order"):
        methods.arima(np.arange(50.0), 3)


def test_registry_lists_every_method():
    assert list(methods.METHODS) == [
        "naive",
        "seasonal_naive",
        "drift",
        "ets",
        "ets_seasonal",
        "arima",
    ]
