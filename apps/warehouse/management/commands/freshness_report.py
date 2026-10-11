from django.core.management.base import BaseCommand, CommandError

from apps.warehouse.freshness import FRESH, freshness_report


class Command(BaseCommand):
    help = "Show how recent each indicator's data is."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-if-stale",
            action="store_true",
            help="Exit with an error when any indicator is stale or empty "
            "(for scheduled checks and CI).",
        )

    def handle(self, *args, **options):
        rows = freshness_report()
        header = (
            f"{'CODE':<26}{'SOURCE':<9}{'FREQ':<10}{'GEOS':>5}{'ROWS':>8}  "
            f"{'NEWEST':<12}{'OLDEST':<12}{'BEHIND':>7}  STATUS"
        )
        self.stdout.write(header)
        for row in rows:
            newest = str(row.newest) if row.newest else "-"
            oldest = str(row.oldest_latest) if row.oldest_latest else "-"
            behind = "-" if row.days_behind is None else f"{row.days_behind}d"
            self.stdout.write(
                f"{row.code:<26}{row.source:<9}{row.frequency:<10}{row.geographies:>5}"
                f"{row.observations:>8}  {newest:<12}{oldest:<12}{behind:>7}  {row.status}"
            )

        problems = [row for row in rows if row.status != FRESH]
        if options["fail_if_stale"] and problems:
            codes = ", ".join(row.code for row in problems)
            raise CommandError(f"{len(problems)} indicator(s) stale or empty: {codes}")
