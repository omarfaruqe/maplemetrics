import re
import tempfile
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.ingestion.catalog import STATCAN_MEASURES
from apps.ingestion.loaders import load_points, sync_indicators
from apps.ingestion.statcan import StatCanError, describe_table, download_table, fetch_measure
from apps.warehouse.models import Indicator


class Command(BaseCommand):
    help = "Load Statistics Canada tables (national and provincial) into the warehouse."

    def add_arguments(self, parser):
        parser.add_argument(
            "--measure",
            nargs="*",
            help="Measure codes to load (default: every measure in the catalog).",
        )
        parser.add_argument(
            "--inspect",
            metavar="TABLE_ID",
            help="Print the columns and example values of a table (for example 14100287), "
            "then exit without loading anything.",
        )

    def handle(self, *args, **options):
        if options["inspect"]:
            self._inspect(options["inspect"])
            return

        wanted = options["measure"]
        specs = [m for m in STATCAN_MEASURES if not wanted or m.code in wanted]
        if not specs:
            raise CommandError(f"No known measure matched: {wanted}")

        indicators = sync_indicators(specs, source=Indicator.Source.STATISTICS_CANADA)

        # Each run reloads a table's full history: Statistics Canada revises past values
        # (seasonal adjustment), and the upsert makes re-running safe.
        for measure in specs:
            try:
                points = fetch_measure(measure)
            except StatCanError as exc:
                raise CommandError(str(exc)) from exc

            by_geography = defaultdict(list)
            for point in points:
                by_geography[point.series].append(point)

            with transaction.atomic():
                total = sum(
                    load_points(indicators[measure.code], geo_points, geography=geography)
                    for geography, geo_points in by_geography.items()
                )
            self.stdout.write(
                f"{measure.code}: {total} observations across {len(by_geography)} geographies"
            )

    def _inspect(self, table_id: str) -> None:
        if not re.fullmatch(r"\d{8}", table_id):
            raise CommandError("The table id must be eight digits, for example 14100287.")
        with tempfile.TemporaryDirectory() as tmp:
            try:
                zip_path = download_table(table_id, Path(tmp))
                description = describe_table(zip_path, table_id)
            except StatCanError as exc:
                raise CommandError(str(exc)) from exc
        for column, (count, examples) in description.items():
            self.stdout.write(f"{column} ({count} distinct): {examples}")
