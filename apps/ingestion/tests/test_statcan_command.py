from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command

from apps.ingestion.bank_of_canada import Point
from apps.ingestion.statcan import StatCanError
from apps.warehouse.models import Indicator, Observation

from .helpers import make_zip, row

FETCH = "apps.ingestion.management.commands.ingest_statcan.fetch_measure"
DOWNLOAD = "apps.ingestion.management.commands.ingest_statcan.download_table"


def points(canada_value="6.9"):
    month = date(2026, 8, 1)
    return [
        Point("Canada", month, Decimal(canada_value)),
        Point("Quebec", month, Decimal("5.5")),
    ]


def test_command_loads_geographies_and_is_idempotent(db):
    out = StringIO()
    with patch(FETCH, return_value=points()):
        call_command("ingest_statcan", "--measure", "LFS_UNEMPLOYMENT_RATE", stdout=out)
    assert "2 observations across 2 geographies" in out.getvalue()
    assert Observation.objects.filter(geography="Quebec").count() == 1
    indicator = Indicator.objects.get(code="LFS_UNEMPLOYMENT_RATE")
    assert indicator.source == Indicator.Source.STATISTICS_CANADA

    with patch(FETCH, return_value=points(canada_value="7.0")):
        call_command("ingest_statcan", "--measure", "LFS_UNEMPLOYMENT_RATE", stdout=StringIO())
    assert Observation.objects.count() == 2
    assert Observation.objects.get(geography="Canada").value == Decimal("7.0")


def test_command_rejects_unknown_measure(db):
    with pytest.raises(CommandError):
        call_command("ingest_statcan", "--measure", "NOPE", stdout=StringIO())


def test_command_reports_statcan_failures(db):
    with patch(FETCH, side_effect=StatCanError("down")), pytest.raises(CommandError, match="down"):
        call_command("ingest_statcan", "--measure", "CPI_ALL_ITEMS", stdout=StringIO())


def test_inspect_prints_columns_and_values(tmp_path):
    zip_path = make_zip(tmp_path, [row("2026-08", "Quebec", "Unemployment rate", "Men+", "5.9")])
    out = StringIO()
    with patch(DOWNLOAD, return_value=zip_path):
        call_command("ingest_statcan", "--inspect", "14100287", stdout=out)
    assert "Gender (1 distinct): ['Men+']" in out.getvalue()


def test_inspect_rejects_bad_table_ids():
    with pytest.raises(CommandError):
        call_command("ingest_statcan", "--inspect", "abc", stdout=StringIO())
