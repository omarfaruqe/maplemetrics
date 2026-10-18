import logging
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger("maplemetrics.refresh")

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
        started = time.perf_counter()
        logger.info("refresh started", extra={"skip_forecasts": skip_forecasts})
        for label, command in STEPS:
            if skip_forecasts and command == "run_forecasts":
                continue
            self.stdout.write(f"== {label} ({command})")
            step_started = time.perf_counter()
            try:
                call_command(command, stdout=self.stdout, stderr=self.stderr)
            except Exception as error:  # noqa: BLE001
                # One source being down must not stop the others from refreshing.
                self.stderr.write(f"FAILED {label}: {error}")
                logger.exception(
                    "refresh step failed",
                    extra={
                        "step": command,
                        "seconds": round(time.perf_counter() - step_started, 1),
                    },
                )
                failed.append(label)
            else:
                logger.info(
                    "refresh step finished",
                    extra={
                        "step": command,
                        "seconds": round(time.perf_counter() - step_started, 1),
                    },
                )
        total = round(time.perf_counter() - started, 1)
        if failed:
            logger.error(
                "refresh finished with failures", extra={"failed": failed, "seconds": total}
            )
            raise CommandError("Refresh finished with failures: " + ", ".join(failed))
        logger.info("refresh finished", extra={"seconds": total})
        self.stdout.write(self.style.SUCCESS("Refresh finished."))
