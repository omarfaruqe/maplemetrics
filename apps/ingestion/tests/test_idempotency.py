"""Re-running a refresh must never duplicate, lose or corrupt data, even when the source revises.

These tests run the real commands and the real table reader. Only the download is replaced, by
a zip with Statistics Canada's column layout (byte order mark, metadata file and all).
"""

from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command

from apps.ingestion.bank_of_canada import Point
from apps.ingestion.catalog import StatCanMeasure
from apps.ingestion.loaders import load_points, sync_indicators
from apps.warehouse.models import Indicator, Observation

from .helpers import make_zip, row

MEASURE = StatCanMeasure(
    code="LFS_UNEMPLOYMENT_RATE",
    name_en="Unemployment rate",
    name_fr="Taux de chômage",
    unit="percent",
    frequency="monthly",
    table_id="14100287",
    value_filters=(
        ("Labour force characteristics", "Unemployment rate"),
        ("Gender", "Total - Gender"),
    ),
)
COMMAND_MEASURES = "apps.ingestion.management.commands.ingest_statcan.STATCAN_MEASURES"
DOWNLOAD = "apps.ingestion.statcan.download_table"


def unemployment(month, canada, quebec):
    return [
        row(month, "Canada", "Unemployment rate", "Total - Gender", canada),
        row(month, "Quebec", "Unemployment rate", "Total - Gender", quebec),
        row(month, "Quebec", "Employment rate", "Total - Gender", "61.0"),
    ]


RELEASE_1 = unemployment("2026-06", "6.8", "5.4") + unemployment("2026-07", "6.9", "5.5")


def ingest(tmp_path, rows):
    """One refresh of the unemployment table from a file holding ``rows``."""
    zip_path = make_zip(tmp_path, rows)
    out = StringIO()
    with patch(COMMAND_MEASURES, (MEASURE,)), patch(DOWNLOAD, return_value=zip_path):
        call_command("ingest_statcan", "--measure", MEASURE.code, stdout=out)
    return out.getvalue()


def stored():
    return {
        (o.geography, o.date): o.value
        for o in Observation.objects.filter(indicator__code=MEASURE.code)
    }


def test_running_the_same_release_twice_changes_nothing(db, tmp_path):
    ingest(tmp_path, RELEASE_1)
    first = stored()
    ingest(tmp_path, RELEASE_1)
    assert stored() == first
    assert len(first) == 4
    assert Indicator.objects.filter(code=MEASURE.code).count() == 1


def test_a_revised_value_replaces_the_old_one_without_a_duplicate(db, tmp_path):
    ingest(tmp_path, RELEASE_1)
    revised = unemployment("2026-06", "7.0", "5.4") + unemployment("2026-07", "6.9", "5.5")
    ingest(tmp_path, revised)
    values = stored()
    assert len(values) == 4
    assert values[("Canada", date(2026, 6, 1))] == Decimal("7.0")
    assert values[("Quebec", date(2026, 6, 1))] == Decimal("5.4")
    assert values[("Canada", date(2026, 7, 1))] == Decimal("6.9")


def test_a_new_month_is_added_and_older_months_are_untouched(db, tmp_path):
    ingest(tmp_path, RELEASE_1)
    before = stored()
    ingest(tmp_path, RELEASE_1 + unemployment("2026-08", "7.1", "5.6"))
    after = stored()
    assert len(after) == 6
    assert {key: after[key] for key in before} == before


def test_a_month_missing_from_a_later_release_is_kept(db, tmp_path):
    """The loader never deletes: an incomplete download cannot erase history."""
    ingest(tmp_path, RELEASE_1)
    ingest(tmp_path, unemployment("2026-07", "6.9", "5.5"))
    assert len(stored()) == 4
    assert stored()[("Canada", date(2026, 6, 1))] == Decimal("6.8")


def test_a_suppressed_value_does_not_overwrite_a_real_one(db, tmp_path):
    ingest(tmp_path, RELEASE_1)
    ingest(tmp_path, unemployment("2026-07", "..", "5.5") + unemployment("2026-06", "6.8", "5.4"))
    assert stored()[("Canada", date(2026, 7, 1))] == Decimal("6.9")


def test_trailing_zeros_do_not_make_a_new_value(db, tmp_path):
    ingest(tmp_path, RELEASE_1)
    ingest(
        tmp_path, unemployment("2026-06", "6.80", "5.40") + unemployment("2026-07", "6.9", "5.5")
    )
    assert stored() == {
        ("Canada", date(2026, 6, 1)): Decimal("6.8"),
        ("Quebec", date(2026, 6, 1)): Decimal("5.4"),
        ("Canada", date(2026, 7, 1)): Decimal("6.9"),
        ("Quebec", date(2026, 7, 1)): Decimal("5.5"),
    }


def test_a_table_with_the_wrong_columns_fails_and_leaves_stored_data_alone(db, tmp_path):
    ingest(tmp_path, RELEASE_1)
    before = stored()
    broken = [row("2026-08", "Canada", "Some other measure", "Total - Gender", "9.9")]
    with pytest.raises(CommandError, match="no rows matched"):
        ingest(tmp_path, broken)
    assert stored() == before


def test_a_failure_while_loading_a_measure_writes_none_of_its_rows(db, tmp_path):
    """All geographies of one measure are saved together or not at all."""
    real = load_points
    calls = []

    def fail_on_second(indicator, points, geography="Canada"):
        calls.append(geography)
        if len(calls) == 2:
            raise RuntimeError("database went away")
        return real(indicator, points, geography=geography)

    zip_path = make_zip(tmp_path, RELEASE_1)
    with (
        patch(COMMAND_MEASURES, (MEASURE,)),
        patch(DOWNLOAD, return_value=zip_path),
        patch("apps.ingestion.management.commands.ingest_statcan.load_points", fail_on_second),
        pytest.raises(RuntimeError),
    ):
        call_command("ingest_statcan", "--measure", MEASURE.code, stdout=StringIO())
    assert Observation.objects.count() == 0


def test_the_report_counts_what_was_read_not_what_was_new(db, tmp_path):
    first = ingest(tmp_path, RELEASE_1)
    second = ingest(tmp_path, RELEASE_1)
    assert first == second
    assert "4 observations across 2 geographies" in second


def test_a_repeated_date_in_one_batch_is_stored_once_with_the_last_value(db):
    indicator = sync_indicators([MEASURE], source="statcan")[MEASURE.code]
    day = date(2026, 7, 1)
    loaded = load_points(
        indicator,
        [Point("Canada", day, Decimal("6.9")), Point("Canada", day, Decimal("7.0"))],
    )
    assert loaded == 1
    assert Observation.objects.get().value == Decimal("7.0")


def test_a_bank_of_canada_revision_of_the_latest_day_is_applied(db):
    command = "apps.ingestion.management.commands.ingest_boc.fetch_observations"
    day = date(2026, 10, 7)
    with patch(command, return_value=[Point("FXUSDCAD", day, Decimal("1.4257"))]):
        call_command("ingest_boc", "--series", "FXUSDCAD", stdout=StringIO())
    # The next run starts at the latest stored day, so a revision of that day arrives again.
    with patch(command, return_value=[Point("FXUSDCAD", day, Decimal("1.4300"))]) as fetch:
        call_command("ingest_boc", "--series", "FXUSDCAD", stdout=StringIO())
    assert fetch.call_args.kwargs["start_date"] == day
    assert Observation.objects.count() == 1
    assert Observation.objects.get().value == Decimal("1.4300")


def test_a_full_refresh_run_twice_leaves_the_same_data(db, tmp_path):
    zip_path = make_zip(tmp_path, RELEASE_1)
    boc = "apps.ingestion.management.commands.ingest_boc.fetch_observations"
    points = [Point("FXUSDCAD", date(2026, 10, 7), Decimal("1.4257"))]

    def refresh():
        with (
            patch(COMMAND_MEASURES, (MEASURE,)),
            patch(DOWNLOAD, return_value=zip_path),
            patch(boc, return_value=points),
        ):
            call_command("refresh_data", "--skip-forecasts", stdout=StringIO())
        return sorted(
            (o.indicator.code, o.geography, o.date, o.value) for o in Observation.objects.all()
        )

    first = refresh()
    assert refresh() == first
    assert sum(1 for code, *_ in first if code == MEASURE.code) == 4
    assert len(first) == len(set(first))
