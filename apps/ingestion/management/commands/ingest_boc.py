from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.bank_of_canada import ValetError, fetch_observations
from apps.ingestion.catalog import BOC_SERIES
from apps.ingestion.loaders import latest_date, load_points, sync_indicators
from apps.warehouse.models import Indicator

DEFAULT_START = date(2015, 1, 1)


class Command(BaseCommand):
    help = "Load Bank of Canada series into the warehouse (incremental by default)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--series",
            nargs="*",
            help="Series codes to load (default: every series in the catalog).",
        )
        parser.add_argument(
            "--start",
            type=date.fromisoformat,
            help="Start date YYYY-MM-DD. Default: the latest stored date, or 2015-01-01.",
        )

    def handle(self, *args, **options):
        wanted = options["series"]
        specs = [s for s in BOC_SERIES if not wanted or s.code in wanted]
        if not specs:
            raise CommandError(f"No known series matched: {wanted}")

        indicators = sync_indicators(specs, source=Indicator.Source.BANK_OF_CANADA)

        for spec in specs:
            indicator = indicators[spec.code]
            start = options["start"] or latest_date(indicator) or DEFAULT_START
            try:
                points = fetch_observations([spec.code], start_date=start)
            except ValetError as exc:
                raise CommandError(str(exc)) from exc
            count = load_points(indicator, points)
            self.stdout.write(f"{spec.code}: {count} observations since {start}")
