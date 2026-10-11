from datetime import date
from decimal import Decimal

import pytest

from apps.warehouse.models import Indicator, Observation


def load(code, rows, frequency="monthly"):
    indicator, _ = Indicator.objects.get_or_create(
        code=code,
        defaults={
            "source": "statcan",
            "name_en": code,
            "name_fr": code,
            "unit": "",
            "frequency": frequency,
        },
    )
    Observation.objects.bulk_create(
        Observation(indicator=indicator, geography=geo, date=day, value=Decimal(str(value)))
        for geo, day, value in rows
    )


@pytest.fixture
def economy(db):
    """Two geographies, enough history for year-over-year comparisons."""
    load(
        "V39079",
        [
            ("Canada", date(2026, 6, 5), 2.75),
            ("Canada", date(2026, 6, 25), 2.50),
            ("Canada", date(2026, 7, 10), 2.50),
            ("Canada", date(2026, 8, 12), 2.25),
        ],
        frequency="daily",
    )
    load(
        "CPI_TRIM",
        [
            ("Canada", date(2026, 6, 1), 3.0),
            ("Canada", date(2026, 7, 1), 2.8),
            ("Canada", date(2026, 8, 1), 2.5),
            ("Canada", date(2026, 9, 1), 2.4),
        ],
    )
    load(
        "LFS_UNEMPLOYMENT_RATE",
        [
            ("Canada", date(2025, 9, 1), 6.9),
            ("Canada", date(2026, 9, 1), 6.5),
            ("Quebec", date(2025, 9, 1), 5.0),
            ("Quebec", date(2026, 9, 1), 5.4),
            ("Ontario", date(2026, 9, 1), 7.1),
        ],
    )
    load(
        "RETAIL_SALES",
        [
            ("Canada", date(2025, 7, 1), 100000),
            ("Canada", date(2026, 7, 1), 104000),
            ("Quebec", date(2025, 7, 1), 20000),
            ("Quebec", date(2026, 7, 1), 20400),
            ("Ontario", date(2026, 7, 1), 40000),
        ],
    )
    load(
        "CPI_ALL_ITEMS",
        [
            ("Canada", date(2025, 7, 1), 160.0),
            ("Canada", date(2026, 7, 1), 164.8),
            ("Quebec", date(2025, 7, 1), 150.0),
            ("Quebec", date(2026, 7, 1), 157.5),
            ("Ontario", date(2026, 7, 1), 170.0),
        ],
    )
