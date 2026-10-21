"""A warehouse about the size of the real one, for query-count and timing tests."""

from datetime import date, timedelta

from apps.analytics import kpis
from apps.analytics.kpis import add_months
from apps.analytics.tests.conftest import load
from apps.forecasting.models import Forecast, ForecastPoint
from apps.warehouse.models import Indicator

PROVINCES = (
    "Canada",
    "Newfoundland and Labrador",
    "Prince Edward Island",
    "Nova Scotia",
    "New Brunswick",
    "Quebec",
    "Ontario",
    "Manitoba",
    "Saskatchewan",
    "Alberta",
    "British Columbia",
)
MONTHS = 240  # twenty years of monthly data
LAST_MONTH = date(2026, 8, 1)


def month_list(count: int = MONTHS) -> list[date]:
    return [add_months(LAST_MONTH, -i) for i in range(count - 1, -1, -1)]


def seed_realistic(geographies: tuple[str, ...] = PROVINCES) -> None:
    """Monthly series for every geography, a daily policy rate, and stored forecasts."""
    months = month_list()
    national = kpis.NATIONAL in geographies
    series = [
        (kpis.UNEMPLOYMENT, 6.0, 0.01),
        (kpis.RETAIL_SALES, 1_000_000.0, 2_500.0),
        (kpis.CPI_INDEX, 100.0, 0.25),
    ]
    if national:
        series.append((kpis.CORE_INFLATION, 2.0, 0.001))
    for code, base, step in series:
        names = (kpis.NATIONAL,) if code == kpis.CORE_INFLATION else geographies
        rows = []
        for geography in names:
            rows += [(geography, day, base + step * i) for i, day in enumerate(months)]
        load(code, rows)

    if national:
        first_day = LAST_MONTH - timedelta(days=365 * 10)
        daily = [
            (kpis.NATIONAL, first_day + timedelta(days=i), 2.0 + (i % 400) / 400)
            for i in range((LAST_MONTH - first_day).days + 1)
        ]
        load(kpis.POLICY_RATE, daily, frequency="daily")

    for code in (kpis.UNEMPLOYMENT, kpis.RETAIL_SALES, kpis.CPI_INDEX):
        indicator = Indicator.objects.get(code=code)
        for geography in geographies:
            forecast = Forecast.objects.create(
                indicator=indicator,
                geography=geography,
                method="ets",
                trained_through=LAST_MONTH,
                backtest_origins=22,
                mase=1.5,
                vs_naive=0.8,
            )
            ForecastPoint.objects.bulk_create(
                ForecastPoint(
                    forecast=forecast,
                    date=add_months(LAST_MONTH, i),
                    value=10.0 + i,
                    lower=9.0 + i,
                    upper=11.0 + i,
                )
                for i in range(1, 13)
            )
