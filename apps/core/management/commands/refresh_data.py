from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

STEPS = (
    ("Bank of Canada", "ingest_boc"),
    ("Statistics Canada", "ingest_statcan"),
    ("Forecasts", "run_forecasts"),
)


class Command(BaseCommand):
    help = "Reload every data source, then rebuild the forecasts. Meant to run on a schedule."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-forecasts",
            action="store_true",
            help="Reload data only; leave the stored forecasts as they are.",
        )

    def handle(self, *args, skip_forecasts=False, **options):
        failed = []
        for label, command in STEPS:
            if skip_forecasts and command == "run_forecasts":
                continue
            self.stdout.write(f"== {label} ({command})")
            try:
                call_command(command, stdout=self.stdout, stderr=self.stderr)
            except Exception as error:  # noqa: BLE001
                # One source being down must not stop the others from refreshing.
                self.stderr.write(f"FAILED {label}: {error}")
                failed.append(label)
        if failed:
            raise CommandError("Refresh finished with failures: " + ", ".join(failed))
        self.stdout.write(self.style.SUCCESS("Refresh finished."))
