"""What we forecast and how to load it from the warehouse."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

from apps.analytics import kpis


@dataclass(frozen=True)
class Target:
    code: str
    log: bool  # model the logarithm: for positive levels that grow proportionally


TARGETS: dict[str, Target] = {
    kpis.UNEMPLOYMENT: Target(kpis.UNEMPLOYMENT, log=False),
    kpis.RETAIL_SALES: Target(kpis.RETAIL_SALES, log=True),
    kpis.CPI_INDEX: Target(kpis.CPI_INDEX, log=True),
}


def trailing_contiguous(points: list[tuple[date, float]]) -> list[tuple[date, float]]:
    """The most recent run of consecutive months; seasonal methods need an unbroken calendar."""
    start = 0
    for i in range(1, len(points)):
        if kpis.add_months(points[i - 1][0], 1) != points[i][0].replace(day=1):
            start = i
    return points[start:]


def load_series(code: str, geography: str) -> tuple[list[date], np.ndarray]:
    """Dates and values of one monthly series, restricted to its latest unbroken stretch."""
    points = trailing_contiguous(kpis.series(code, geography))
    return [day for day, _ in points], np.array([value for _, value in points], dtype=float)
