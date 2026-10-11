from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command

from apps.ingestion.bank_of_canada import Point, ValetError
from apps.ingestion.catalog import BOC_SERIES
from apps.ingestion.loaders import latest_date, load_points, sync_indicators
from apps.warehouse.models import Indicator, Observation

COMMAND = "apps.ingestion.management.commands.ingest_boc.fetch_observations"


@pytest.fixture
def indicator(db):
    return sync_indicators(BOC_SERIES[:1], source=Indicator.Source.BANK_OF_CANADA)["FXUSDCAD"]


def test_sync_indicators_is_idempotent(db):
    sync_indicators(BOC_SERIES, source="boc")
    sync_indicators(BOC_SERIES, source="boc")
    assert Indicator.objects.count() == len(BOC_SERIES)


def test_load_points_upserts_without_duplicates(indicator):
    day = date(2026, 10, 7)
    load_points(indicator, [Point("FXUSDCAD", day, Decimal("1.40"))])
    load_points(indicator, [Point("FXUSDCAD", day, Decimal("1.45"))])
    assert Observation.objects.count() == 1
    assert Observation.objects.get().value == Decimal("1.45")
    assert latest_date(indicator) == day


def test_load_points_with_no_rows_returns_zero(indicator):
    assert load_points(indicator, []) == 0


def test_command_loads_and_then_resumes_from_latest_date(db):
    first = [Point("FXUSDCAD", date(2026, 10, 6), Decimal("1.42"))]
    second = [Point("FXUSDCAD", date(2026, 10, 7), Decimal("1.43"))]
    with patch(COMMAND, return_value=first) as fetch:
        call_command("ingest_boc", "--series", "FXUSDCAD", stdout=StringIO())
    assert fetch.call_args.kwargs["start_date"] == date(2015, 1, 1)

    with patch(COMMAND, return_value=second) as fetch:
        call_command("ingest_boc", "--series", "FXUSDCAD", stdout=StringIO())
    assert fetch.call_args.kwargs["start_date"] == date(2026, 10, 6)
    assert Observation.objects.count() == 2


def test_command_rejects_unknown_series(db):
    with pytest.raises(CommandError):
        call_command("ingest_boc", "--series", "NOPE", stdout=StringIO())


def test_command_reports_api_failure(db):
    with patch(COMMAND, side_effect=ValetError("down")), pytest.raises(CommandError):
        call_command("ingest_boc", "--series", "FXUSDCAD", stdout=StringIO())
