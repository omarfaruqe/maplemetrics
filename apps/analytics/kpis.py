"""Economic indicators computed from the warehouse.

Every function reads stored observations and returns plain dataclasses, so views, the future
REST API and the forecasting code can share them. Missing data yields empty results, never
exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from apps.warehouse.models import Observation

POLICY_RATE = "V39079"
CORE_INFLATION = "CPI_TRIM"
UNEMPLOYMENT = "LFS_UNEMPLOYMENT_RATE"
RETAIL_SALES = "RETAIL_SALES"
CPI_INDEX = "CPI_ALL_ITEMS"
NATIONAL = "Canada"


@dataclass(frozen=True)
class RatePoint:
    date: date
    policy: float
    core: float
    real: float


@dataclass(frozen=True)
class UnemploymentRow:
    geography: str
    date: date
    rate: float
    year_ago: float | None
    change: float | None


@dataclass(frozen=True)
class RetailRow:
    geography: str
    date: date
    nominal: float
    inflation: float
    real: float


def add_months(day: date, months: int) -> date:
    """First day of the month ``months`` away from ``day``'s month."""
    index = day.year * 12 + (day.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


def series(code: str, geography: str = NATIONAL) -> list[tuple[date, float]]:
    """Observations of one indicator and geography, oldest first."""
    rows = (
        Observation.objects.filter(indicator__code=code, geography=geography)
        .order_by("date")
        .values_list("date", "value")
    )
    return [(day, float(value)) for day, value in rows]


def _by_geography(code: str) -> dict[str, dict[date, float]]:
    result: dict[str, dict[date, float]] = {}
    rows = Observation.objects.filter(indicator__code=code).values_list(
        "geography", "date", "value"
    )
    for geography, day, value in rows:
        result.setdefault(geography, {})[day] = float(value)
    return result


def month_end_policy_rate() -> dict[date, float]:
    """The policy rate in force at the end of each month, keyed by the month's first day."""
    monthly: dict[date, float] = {}
    for day, value in series(POLICY_RATE):
        monthly[day.replace(day=1)] = value
    return monthly


def real_policy_rate() -> list[RatePoint]:
    """Policy rate minus core inflation (CPI-trim), per month with both available."""
    policy = month_end_policy_rate()
    points = []
    for day, core in series(CORE_INFLATION):
        month = day.replace(day=1)
        if month in policy:
            points.append(RatePoint(month, policy[month], core, round(policy[month] - core, 4)))
    return points


def unemployment_by_province() -> list[UnemploymentRow]:
    """Latest unemployment rate per geography with the change from a year earlier, highest first."""
    rows = []
    for geography, values in _by_geography(UNEMPLOYMENT).items():
        latest = max(values)
        year_ago = values.get(add_months(latest, -12))
        change = None if year_ago is None else round(values[latest] - year_ago, 4)
        rows.append(UnemploymentRow(geography, latest, values[latest], year_ago, change))
    rows.sort(key=lambda row: (-row.rate, row.geography))
    return rows


def real_retail_growth() -> list[RetailRow]:
    """Year-over-year retail sales growth deflated by CPI, per geography, in percent.

    Real growth is (1 + nominal) / (1 + inflation) - 1, using the CPI index of the same months.
    Geographies missing any of the four observations are skipped.
    """
    cpi = _by_geography(CPI_INDEX)
    rows = []
    for geography, sales in _by_geography(RETAIL_SALES).items():
        latest = max(sales)
        earlier = add_months(latest, -12)
        prices = cpi.get(geography, {})
        needed = (sales.get(earlier), prices.get(latest), prices.get(earlier))
        if None in needed or 0 in needed:
            continue
        sales_then, cpi_now, cpi_then = needed
        nominal = sales[latest] / sales_then - 1
        inflation = cpi_now / cpi_then - 1
        real = (1 + nominal) / (1 + inflation) - 1
        rows.append(
            RetailRow(
                geography,
                latest,
                round(nominal * 100, 2),
                round(inflation * 100, 2),
                round(real * 100, 2),
            )
        )
    rows.sort(key=lambda row: (-row.real, row.geography))
    return rows


def geographies(code: str = UNEMPLOYMENT) -> list[str]:
    """Geographies that have data for ``code``, Canada first and the rest alphabetical."""
    names = (
        Observation.objects.filter(indicator__code=code)
        .values_list("geography", flat=True)
        .distinct()
    )
    return sorted(set(names), key=lambda name: (name != NATIONAL, name))


def _year_over_year(code: str, geography: str) -> list[tuple[date, float]]:
    values = dict(series(code, geography))
    points = []
    for day in sorted(values):
        before = values.get(add_months(day, -12))
        if before:
            points.append((day, (values[day] / before - 1) * 100))
    return points


def yoy_series(code: str, geography: str = NATIONAL) -> list[tuple[date, float]]:
    """Year-over-year percent change of an index or level, for months with a year-earlier value."""
    return [(day, round(value, 2)) for day, value in _year_over_year(code, geography)]


def real_retail_yoy(geography: str = NATIONAL) -> list[tuple[date, float]]:
    """Retail sales growth over twelve months minus price growth, as a real percent change."""
    inflation = dict(_year_over_year(CPI_INDEX, geography))
    points = []
    for day, nominal in _year_over_year(RETAIL_SALES, geography):
        if day in inflation:
            real = ((1 + nominal / 100) / (1 + inflation[day] / 100) - 1) * 100
            points.append((day, round(real, 2)))
    return points
