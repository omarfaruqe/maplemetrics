from dataclasses import replace
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest
import requests

from apps.ingestion.catalog import BOC_SERIES, STATCAN_MEASURES, StatCanMeasure
from apps.ingestion.statcan import (
    StatCanError,
    describe_table,
    download_table,
    fetch_measure,
    parse_ref_date,
    read_table,
)

from .helpers import make_zip, make_zip_bytes, row

MEASURE = StatCanMeasure(
    code="TEST",
    name_en="Test",
    name_fr="Test",
    unit="percent",
    frequency="monthly",
    table_id="14100287",
    value_filters=(
        ("Labour force characteristics", "Unemployment rate"),
        ("Gender", "Total - Gender"),
    ),
)

ROWS = [
    row("2026-08", "Canada", "Unemployment rate", "Total - Gender", "6.9"),
    row("2026-08", "Quebec", "Unemployment rate", "Total - Gender", "5.5"),
    row("2026-08", "Quebec", "Employment rate", "Total - Gender", "61.0"),
    row("2026-08", "Quebec", "Unemployment rate", "Men+", "5.9"),
    row("2026-08", "Yukon", "Unemployment rate", "Total - Gender", "3.0"),
    row("2026-07", "Ontario", "Unemployment rate", "Total - Gender", ""),
    row("2026-07", "Alberta", "Unemployment rate", "Total - Gender", ".."),
]


def test_parse_ref_date_handles_months_years_days_and_junk():
    assert parse_ref_date("2026-08") == date(2026, 8, 1)
    assert parse_ref_date("2024") == date(2024, 1, 1)
    assert parse_ref_date("2026-08-15") == date(2026, 8, 15)
    assert parse_ref_date("2024-Q1") is None
    assert parse_ref_date("garbage") is None
    assert parse_ref_date(None) is None


def test_read_table_keeps_only_matching_rows(tmp_path):
    points = read_table(make_zip(tmp_path, ROWS), MEASURE)
    assert [(p.series, p.date, p.value) for p in points] == [
        ("Canada", date(2026, 8, 1), Decimal("6.9")),
        ("Quebec", date(2026, 8, 1), Decimal("5.5")),
    ]


def test_read_table_rejects_ambiguous_filters(tmp_path):
    loose = replace(MEASURE, value_filters=MEASURE.value_filters[:1])
    rows = [
        row("2026-08", "Canada", "Unemployment rate", "Total - Gender", "6.9"),
        row("2026-08", "Canada", "Unemployment rate", "Men+", "7.1"),
    ]
    with pytest.raises(StatCanError, match="Gender"):
        read_table(make_zip(tmp_path, rows), loose)


def test_read_table_suggests_close_values_when_nothing_matches(tmp_path):
    typo = replace(MEASURE, value_filters=(("Labour force characteristics", "Unemployment rat"),))
    with pytest.raises(StatCanError, match="Unemployment rate"):
        read_table(make_zip(tmp_path, ROWS), typo)


def test_read_table_reports_unknown_geographies(tmp_path):
    rows = [row("2026-08", "Atlantis", "Unemployment rate", "Total - Gender", "1.0")]
    with pytest.raises(StatCanError, match="expected geographies"):
        read_table(make_zip(tmp_path, rows), MEASURE)


def test_read_table_reports_missing_columns(tmp_path):
    bad = replace(MEASURE, value_filters=(("Nonexistent", "x"),))
    with pytest.raises(StatCanError, match="The columns are"):
        read_table(make_zip(tmp_path, ROWS), bad)


def test_read_table_rejects_files_that_are_not_zips(tmp_path):
    path = tmp_path / "14100287.zip"
    path.write_bytes(b"this is not a zip")
    with pytest.raises(StatCanError, match="not a valid zip"):
        read_table(path, MEASURE)


def test_describe_table_lists_dimension_values(tmp_path):
    description = describe_table(make_zip(tmp_path, ROWS), "14100287")
    assert description["Gender"] == (2, ["Men+", "Total - Gender"])
    assert "Quebec" in description["GEO"][1]
    assert "VALUE" not in description


def test_download_table_streams_to_disk(tmp_path):
    session = Mock()
    session.get.return_value.iter_content.return_value = [b"abc", b"def"]
    target = download_table("14100287", tmp_path, session=session)
    assert target.read_bytes() == b"abcdef"
    assert (
        session.get.call_args.args[0] == "https://www150.statcan.gc.ca/n1/tbl/csv/14100287-eng.zip"
    )


def test_download_table_wraps_network_errors(tmp_path):
    session = Mock()
    session.get.side_effect = requests.ConnectionError("boom")
    with pytest.raises(StatCanError, match="Download failed"):
        download_table("14100287", tmp_path, session=session)


def test_fetch_measure_downloads_and_reads(tmp_path):
    session = Mock()
    session.get.return_value.iter_content.return_value = [make_zip_bytes(ROWS)]
    points = fetch_measure(MEASURE, session=session)
    assert {p.series for p in points} == {"Canada", "Quebec"}


def test_catalog_codes_are_unique_and_well_formed():
    codes = [spec.code for spec in BOC_SERIES] + [m.code for m in STATCAN_MEASURES]
    assert len(codes) == len(set(codes))
    for measure in STATCAN_MEASURES:
        assert len(measure.table_id) == 8 and measure.table_id.isdigit()
        assert measure.value_filters
