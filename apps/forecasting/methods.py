"""Forecasting methods. Each takes a training array and a horizon and returns that many values.

The first three are deliberately simple baselines: a forecasting model only earns its place by
beating them out of sample (see backtest.py).
"""

from __future__ import annotations

import warnings
from collections.abc import Callable

import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing

SEASON = 12  # monthly data

Forecaster = Callable[[np.ndarray, int], np.ndarray]


def naive(train: np.ndarray, horizon: int) -> np.ndarray:
    """Tomorrow looks like today: repeat the last observation."""
    return np.repeat(train[-1], horizon)


def seasonal_naive(train: np.ndarray, horizon: int) -> np.ndarray:
    """Repeat the same month of the last year."""
    last_year = train[-SEASON:]
    repeats = -(-horizon // SEASON)
    return np.tile(last_year, repeats)[:horizon]


def drift(train: np.ndarray, horizon: int) -> np.ndarray:
    """Continue the average change per month seen over the whole training window."""
    slope = (train[-1] - train[0]) / (len(train) - 1)
    return train[-1] + slope * np.arange(1, horizon + 1)


def ets(train: np.ndarray, horizon: int) -> np.ndarray:
    """Exponential smoothing with a damped additive trend (so trends fade out)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(
            train, trend="add", damped_trend=True, initialization_method="estimated"
        ).fit()
    return np.asarray(fit.forecast(horizon))


def ets_seasonal(train: np.ndarray, horizon: int) -> np.ndarray:
    """Damped-trend exponential smoothing with additive monthly seasonality."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(
            train,
            trend="add",
            damped_trend=True,
            seasonal="add",
            seasonal_periods=SEASON,
            initialization_method="estimated",
        ).fit()
    return np.asarray(fit.forecast(horizon))


def arima(train: np.ndarray, horizon: int) -> np.ndarray:
    """ARIMA(p, 1, q) with drift. The orders p, q in 0..2 are picked by AIC on the training data."""
    best_aic = np.inf
    best_fit = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p in range(3):
            for q in range(3):
                # A failed order is simply not a candidate, so skipping it is intended.
                try:
                    fit = ARIMA(train, order=(p, 1, q), trend="t").fit()
                except Exception:  # noqa: BLE001  # nosec B112
                    continue
                if np.isfinite(fit.aic) and fit.aic < best_aic:
                    best_aic, best_fit = fit.aic, fit
    if best_fit is None:
        raise ValueError("no ARIMA order could be fitted")
    return np.asarray(best_fit.forecast(horizon))


METHODS: dict[str, Forecaster] = {
    "naive": naive,
    "seasonal_naive": seasonal_naive,
    "drift": drift,
    "ets": ets,
    "ets_seasonal": ets_seasonal,
    "arima": arima,
}
