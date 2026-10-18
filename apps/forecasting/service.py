"""Turn a backtested method into a stored forecast with an empirical prediction range."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
from django.db import transaction

from apps.analytics.kpis import add_months
from apps.warehouse.models import Indicator

from .backtest import backtest
from .methods import METHODS, naive
from .models import Forecast, ForecastPoint
from .targets import TARGETS, load_series


class ForecastError(ValueError):
    """A series cannot be forecast (no data, too short, or the method failed)."""


DEFAULT_LEVEL = 0.8


@dataclass(frozen=True)
class ForecastResult:
    code: str
    geography: str
    method: str
    trained_through: date
    dates: list[date]
    values: list[float]
    lowers: list[float]
    uppers: list[float]
    backtest_origins: int
    mase: float
    vs_naive: float | None
    level: float


def interval_halfwidths(errors: np.ndarray, level: float) -> np.ndarray:
    """Per-horizon half-widths: the ``level`` quantile of past absolute errors, never narrowing.

    "80%" therefore means: in past backtests, 80% of this method's forecasts at that horizon
    landed within this distance of the actual value.
    """
    widths = np.quantile(np.abs(np.asarray(errors, dtype=float)), level, axis=0)
    return np.maximum.accumulate(widths)


def build_forecast(
    code: str,
    geography: str,
    *,
    horizon: int = 12,
    count: int = 24,
    step: int = 2,
    min_train: int = 60,
    max_train: int = 240,
    level: float = DEFAULT_LEVEL,
) -> ForecastResult:
    """Backtest the chosen method, then forecast ``horizon`` months past the latest data."""
    target = TARGETS[code]
    dates, values = load_series(code, geography)
    if len(values) == 0:
        raise ForecastError("no data")
    forecaster = METHODS[target.method]
    try:
        scores = backtest(
            values,
            {"naive": naive, target.method: forecaster},
            horizon=horizon,
            count=count,
            step=step,
            min_train=min_train,
            max_train=max_train,
            log=target.log,
        )
    except ValueError as error:
        raise ForecastError(str(error)) from error
    by_name = {score.method: score for score in scores}
    chosen = by_name[target.method]
    if chosen.forecasts == 0:
        raise ForecastError(f"{target.method} failed at every backtest origin")

    train = values[-max_train:]
    try:
        raw = forecaster(np.log(train) if target.log else train, horizon)
        point = np.exp(raw) if target.log else np.asarray(raw, dtype=float)
    except Exception as error:  # noqa: BLE001 - reported as a forecasting failure
        raise ForecastError(f"{target.method} could not fit: {error}") from error
    if len(point) != horizon or not np.all(np.isfinite(point)):
        raise ForecastError(f"{target.method} returned an unusable forecast")

    half = interval_halfwidths(np.array(chosen.errors), level)
    baseline = by_name["naive"].mase
    vs_naive = chosen.mase / baseline if baseline and baseline > 0 else None
    return ForecastResult(
        code=code,
        geography=geography,
        method=target.method,
        trained_through=dates[-1],
        dates=[add_months(dates[-1], i) for i in range(1, horizon + 1)],
        values=point.tolist(),
        lowers=np.maximum(point - half, 0.0).tolist(),
        uppers=(point + half).tolist(),
        backtest_origins=chosen.forecasts,
        mase=chosen.mase,
        vs_naive=vs_naive,
        level=level,
    )


@transaction.atomic
def save_forecast(result: ForecastResult) -> Forecast:
    """Store a result as the current forecast of its series, replacing the previous one."""
    indicator = Indicator.objects.get(code=result.code)
    forecast, _ = Forecast.objects.update_or_create(
        indicator=indicator,
        geography=result.geography,
        defaults={
            "method": result.method,
            "trained_through": result.trained_through,
            "interval_level": result.level,
            "backtest_origins": result.backtest_origins,
            "mase": result.mase,
            "vs_naive": result.vs_naive,
        },
    )
    forecast.points.all().delete()
    ForecastPoint.objects.bulk_create(
        ForecastPoint(forecast=forecast, date=day, value=value, lower=lower, upper=upper)
        for day, value, lower, upper in zip(
            result.dates, result.values, result.lowers, result.uppers, strict=True
        )
    )
    return forecast
