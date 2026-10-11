from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.warehouse.freshness import EMPTY, FRESH, STALE, freshness_report
from apps.warehouse.models import Indicator, Observation

TODAY = date(2026, 10, 11)


def make_indicator(code, frequency, source="boc"):
    return Indicator.objects.create(
        code=code,
        source=source,
        name_en=f"{code} in English",
        name_fr=f"{code} en français",
        unit="",
        frequency=frequency,
    )


def add(indicator, geography, day):
    Observation.objects.create(
        indicator=indicator, geography=geography, date=day, value=Decimal("1.5")
    )


@pytest.fixture
def report(db):
    daily = make_indicator("DAILY_OK", "daily")
    add(daily, "Canada", TODAY - timedelta(days=3))
    add(daily, "Canada", TODAY - timedelta(days=10))

    cpi = make_indicator("CPI_LIKE", "monthly", source="statcan")
    add(cpi, "Canada", date(2026, 8, 1))
    add(cpi, "Quebec", date(2026, 8, 1))

    retail = make_indicator("RETAIL_LAG", "monthly", source="statcan")
    add(retail, "Canada", date(2026, 7, 1))

    lagging = make_indicator("LAGGING_PROVINCE", "monthly", source="statcan")
    add(lagging, "Canada", date(2026, 9, 1))
    add(lagging, "Quebec", date(2026, 5, 1))

    make_indicator("NO_DATA", "daily")
    return freshness_report(today=TODAY)


def by_code(report):
    return {row.code: row for row in report}


def test_normal_publication_lag_is_not_flagged(report):
    rows = by_code(report)
    assert rows["CPI_LIKE"].status == FRESH
    assert rows["CPI_LIKE"].days_behind == 71
    assert rows["RETAIL_LAG"].status == FRESH
    assert rows["RETAIL_LAG"].days_behind == 102


def test_one_lagging_geography_makes_the_indicator_stale(report):
    row = by_code(report)["LAGGING_PROVINCE"]
    assert row.status == STALE
    assert row.newest == date(2026, 9, 1)
    assert row.oldest_latest == date(2026, 5, 1)
    assert row.days_behind == 163
    assert row.geographies == 2


def test_counts_and_dates_for_a_healthy_series(report):
    row = by_code(report)["DAILY_OK"]
    assert (row.status, row.geographies, row.observations) == (FRESH, 1, 2)
    assert row.newest == TODAY - timedelta(days=3)
    assert row.source_label == "Bank of Canada"
    assert row.frequency_label == "Daily"


def test_indicator_without_observations_is_empty(report):
    row = by_code(report)["NO_DATA"]
    assert row.status == EMPTY
    assert row.newest is None and row.days_behind is None
    assert row.observations == 0


def test_problems_sort_first(report):
    assert [row.code for row in report] == [
        "LAGGING_PROVINCE",
        "NO_DATA",
        "DAILY_OK",
        "CPI_LIKE",
        "RETAIL_LAG",
    ]


@pytest.mark.parametrize("age, status", [(7, FRESH), (8, STALE)])
def test_daily_threshold_boundary(db, age, status):
    indicator = make_indicator("EDGE", "daily")
    add(indicator, "Canada", TODAY - timedelta(days=age))
    assert freshness_report(today=TODAY)[0].status == status


def test_command_prints_a_table(db):
    indicator = make_indicator("CMD_FRESH", "daily")
    add(indicator, "Canada", timezone.localdate() - timedelta(days=1))
    out = StringIO()
    call_command("freshness_report", stdout=out)
    assert "CODE" in out.getvalue()
    assert "CMD_FRESH" in out.getvalue()
    assert "fresh" in out.getvalue()


def test_command_fails_on_stale_data_but_still_prints(db):
    indicator = make_indicator("CMD_STALE", "daily")
    add(indicator, "Canada", timezone.localdate() - timedelta(days=30))
    out = StringIO()
    with pytest.raises(CommandError, match="CMD_STALE"):
        call_command("freshness_report", "--fail-if-stale", stdout=out)
    assert "CMD_STALE" in out.getvalue()


def test_command_passes_when_everything_is_fresh(db):
    indicator = make_indicator("CMD_OK", "daily")
    add(indicator, "Canada", timezone.localdate() - timedelta(days=1))
    call_command("freshness_report", "--fail-if-stale", stdout=StringIO())
