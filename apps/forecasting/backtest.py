"""Rolling-origin evaluation: fit on the past only, forecast ahead, compare with what happened."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .methods import METHODS, Forecaster


@dataclass(frozen=True)
class MethodScore:
    method: str
    forecasts: int  # origins that produced a forecast
    failures: int  # origins where the method raised
    mae: list[float]  # mean absolute error at horizon 1..H
    rmse: list[float]
    mase: float  # mean absolute error over all horizons / naive one-step error (below 1 beats it)
    errors: list[list[float]] = field(default_factory=list)  # forecast - actual, origin x horizon


def origins(length: int, horizon: int, count: int, step: int, min_train: int) -> list[int]:
    """Indexes where each training window ends, oldest first, leaving ``horizon`` points ahead."""
    last = length - horizon
    found = [last - step * k for k in range(count)]
    found = [o for o in found if o >= min_train]
    if not found:
        raise ValueError(
            f"series of {length} points is too short for horizon {horizon} "
            f"with at least {min_train} training points"
        )
    return sorted(found)


def backtest(
    values: np.ndarray,
    methods: dict[str, Forecaster] | None = None,
    *,
    horizon: int = 12,
    count: int = 12,
    step: int = 3,
    min_train: int = 60,
    max_train: int = 240,
    log: bool = False,
) -> list[MethodScore]:
    """Score every method on the same forecast origins, best (lowest MASE) first.

    Training windows hold at most ``max_train`` points, so old regimes fade out. With ``log`` set,
    models see the logarithm but errors are measured in the original units.
    """
    methods = METHODS if methods is None else methods
    values = np.asarray(values, dtype=float)
    points = origins(len(values), horizon, count, step, min_train)
    # The error scale comes from the same recent window the models train on, so a long, very
    # different history (CPI in 1914 versus today) cannot distort the comparison.
    first = points[0]
    scale = float(np.mean(np.abs(np.diff(values[max(0, first - max_train) : first]))))
    if scale == 0:
        scale = np.finfo(float).eps

    scores = []
    for name, forecaster in methods.items():
        errors = np.full((len(points), horizon), np.nan)
        failures = 0
        for row, origin in enumerate(points):
            train = values[max(0, origin - max_train) : origin]
            actual = values[origin : origin + horizon]
            try:
                predicted = forecaster(np.log(train) if log else train, horizon)
                predicted = np.exp(predicted) if log else predicted
                if len(predicted) != horizon or not np.all(np.isfinite(predicted)):
                    raise ValueError("forecast has the wrong length or non-finite values")
            except Exception:  # noqa: BLE001 - any failure counts against the method, not the run
                failures += 1
                continue
            errors[row] = predicted - actual
        ok = ~np.isnan(errors).all(axis=1)
        if ok.any():
            absolute = np.abs(errors[ok])
            mae = absolute.mean(axis=0)
            rmse = np.sqrt((errors[ok] ** 2).mean(axis=0))
            mase = float(absolute.mean() / scale)
        else:
            mae = rmse = np.full(horizon, np.nan)
            mase = float("nan")
        scores.append(
            MethodScore(
                name,
                int(ok.sum()),
                failures,
                mae.tolist(),
                rmse.tolist(),
                mase,
                errors[ok].tolist(),
            )
        )
    scores.sort(key=lambda s: (np.isnan(s.mase), s.mase))
    return scores
