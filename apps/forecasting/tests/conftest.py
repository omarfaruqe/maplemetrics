from datetime import date

import numpy as np
import pytest

from apps.analytics.kpis import add_months
from apps.analytics.tests.conftest import load


def months(count, start=date(2010, 1, 1)):
    return [add_months(start, i) for i in range(count)]


def random_walk(seed, start=6.0, scale=0.15, count=160):
    rng = np.random.default_rng(seed)
    return start + np.cumsum(rng.normal(0, scale, count))


@pytest.fixture
def unemployment_two_geographies(db):
    rows = []
    for seed, geography in ((1, "Canada"), (2, "Quebec")):
        for day, value in zip(months(160), random_walk(seed), strict=True):
            rows.append((geography, day, round(float(value), 3)))
    load("LFS_UNEMPLOYMENT_RATE", rows)


@pytest.fixture
def cpi(db):
    index = 100 * np.exp(np.cumsum(np.full(160, 0.002)) + random_walk(5, 0, 0.001))
    rows = [("Canada", d, round(float(v), 3)) for d, v in zip(months(160), index, strict=True)]
    load("CPI_ALL_ITEMS", rows)
