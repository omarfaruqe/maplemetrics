"""Statistics Canada full-table CSV downloads (public URL, no API key).

Every table is published as one zip holding ``<table_id>.csv``. Each row carries its own
labels (``GEO`` plus one column per dimension), so series are selected by name instead of
by hard-coded vector IDs. A wrong filter therefore fails loudly instead of loading the
wrong numbers.
"""

from __future__ import annotations

import csv
import difflib
import io
import tempfile
import zipfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests

from .bank_of_canada import Point, build_session
from .catalog import STATCAN_GEOGRAPHIES, StatCanMeasure

CSV_URL = "https://www150.statcan.gc.ca/n1/tbl/csv/{table_id}-eng.zip"

# Columns that describe a row rather than a dimension of the table.
META_COLUMNS = frozenset(
    {
        "REF_DATE",
        "GEO",
        "DGUID",
        "UOM",
        "UOM_ID",
        "SCALAR_FACTOR",
        "SCALAR_ID",
        "VECTOR",
        "COORDINATE",
        "VALUE",
        "STATUS",
        "SYMBOL",
        "TERMINATED",
        "DECIMALS",
    }
)
MAX_TRACKED_VALUES = 5000


class StatCanError(Exception):
    """Raised when a table cannot be downloaded, read, or matched to the catalog."""


def parse_ref_date(text: str | None) -> date | None:
    """Turn 'YYYY', 'YYYY-MM' or 'YYYY-MM-DD' into a date; anything else (quarters) is None."""
    parts = (text or "").strip().split("-")
    try:
        if len(parts) == 1:
            return date(int(parts[0]), 1, 1)
        if len(parts) == 2:
            return date(int(parts[0]), int(parts[1]), 1)
        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None
    return None


def _parse_value(text: str | None) -> Decimal | None:
    """Blank, suppressed ('..', 'x') and non-finite values become None."""
    if not text or not text.strip():
        return None
    try:
        value = Decimal(text.strip())
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def download_table(
    table_id: str,
    directory: Path,
    session: requests.Session | None = None,
    timeout: int = 120,
) -> Path:
    """Stream a table's zip to disk (these files can be tens of megabytes)."""
    session = session or build_session()
    url = CSV_URL.format(table_id=table_id)
    target = directory / f"{table_id}.zip"
    try:
        response = session.get(url, stream=True, timeout=timeout)
        try:
            response.raise_for_status()
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    handle.write(chunk)
        finally:
            response.close()
    except requests.RequestException as exc:
        raise StatCanError(f"Download failed for table {table_id}: {exc}") from exc
    return target


@contextmanager
def _open_csv(zip_path: Path, table_id: str) -> Iterator[csv.DictReader]:
    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise StatCanError(f"Table {table_id}: the download is not a valid zip file.") from exc
    with archive:
        names = archive.namelist()
        wanted = f"{table_id}.csv"
        name = wanted if wanted in names else None
        if name is None:
            name = next(
                (n for n in names if n.lower().endswith(".csv") and "metadata" not in n.lower()),
                None,
            )
        if name is None:
            raise StatCanError(f"Table {table_id}: no data CSV in the zip (found {names}).")
        with archive.open(name) as raw:
            yield csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))


def read_table(
    zip_path: Path,
    measure: StatCanMeasure,
    geographies: Sequence[str] = STATCAN_GEOGRAPHIES,
) -> list[Point]:
    """Rows matching the measure's filters, as Points whose ``series`` is the geography."""
    filters = dict(measure.value_filters)
    wanted_geographies = set(geographies)
    with _open_csv(zip_path, measure.table_id) as reader:
        header = list(reader.fieldnames or [])
        missing = [c for c in ("REF_DATE", "GEO", "VALUE", *filters) if c not in header]
        if missing:
            raise StatCanError(
                f"Table {measure.table_id}: column(s) {missing} not found. "
                f"The columns are: {header}"
            )
        dimensions = [c for c in header if c not in META_COLUMNS]
        seen: dict[str, set[str]] = {column: set() for column in ("GEO", *filters)}
        found: dict[tuple[str, date], tuple[Decimal, tuple[str | None, ...]]] = {}

        for row in reader:
            for column, values in seen.items():
                if len(values) < MAX_TRACKED_VALUES:
                    values.add(row[column] or "")
            geography = row["GEO"]
            if geography not in wanted_geographies:
                continue
            if any(row[column] != expected for column, expected in filters.items()):
                continue
            observed_on = parse_ref_date(row["REF_DATE"])
            value = _parse_value(row["VALUE"])
            if observed_on is None or value is None:
                continue
            signature = tuple(row[column] for column in dimensions)
            key = (geography, observed_on)
            previous = found.get(key)
            if previous is not None and previous[1] != signature:
                pairs = zip(dimensions, previous[1], signature, strict=True)
                differing = [column for column, old, new in pairs if old != new]
                raise StatCanError(
                    f"Table {measure.table_id} ({measure.code}): the filters match more than "
                    f"one row for {geography} {observed_on}. The rows differ in column(s) "
                    f"{differing}; add a filter for them in the catalog."
                )
            found[key] = (value, signature)

    if not found:
        raise StatCanError(_no_match_message(measure, seen, wanted_geographies))
    return [
        Point(series=geography, date=observed_on, value=value)
        for (geography, observed_on), (value, _) in sorted(found.items())
    ]


def _no_match_message(
    measure: StatCanMeasure, seen: dict[str, set[str]], wanted_geographies: set[str]
) -> str:
    problems: list[str] = []
    for column, expected in measure.value_filters:
        if expected not in seen[column]:
            close = difflib.get_close_matches(expected, sorted(seen[column]), n=5, cutoff=0.4)
            hint = f" Closest values: {close}." if close else ""
            problems.append(f"Column {column!r} has no value {expected!r}.{hint}")
    if not wanted_geographies & seen["GEO"]:
        problems.append(
            f"None of the expected geographies appear; examples: {sorted(seen['GEO'])[:8]}."
        )
    detail = " ".join(problems) or "Each filter matches on its own, but no row matches them all."
    return f"Table {measure.table_id} ({measure.code}): no rows matched. {detail}"


def describe_table(
    zip_path: Path, table_id: str, limit: int = 40
) -> dict[str, tuple[int, list[str]]]:
    """For each dimension column: how many distinct values it has and the first few."""
    with _open_csv(zip_path, table_id) as reader:
        columns = ["GEO", *[c for c in (reader.fieldnames or []) if c not in META_COLUMNS]]
        values: dict[str, set[str]] = {column: set() for column in columns}
        for row in reader:
            for column, found in values.items():
                if len(found) < MAX_TRACKED_VALUES:
                    found.add(row.get(column) or "")
    return {column: (len(found), sorted(found)[:limit]) for column, found in values.items()}


def fetch_measure(
    measure: StatCanMeasure,
    geographies: Sequence[str] = STATCAN_GEOGRAPHIES,
    session: requests.Session | None = None,
) -> list[Point]:
    """Download the measure's table and return its matching points."""
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = download_table(measure.table_id, Path(tmp), session=session)
        return read_table(zip_path, measure, geographies)
