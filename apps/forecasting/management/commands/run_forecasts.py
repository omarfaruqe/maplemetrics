from django.core.management.base import BaseCommand, CommandError

from apps.analytics import kpis
from apps.forecasting.service import ForecastError, build_forecast, save_forecast
from apps.forecasting.targets import TARGETS
from apps.warehouse.models import Indicator


class Command(BaseCommand):
    help = "Build and store the current forecast for every indicator and geography."

    def add_arguments(self, parser):
        parser.add_argument("--indicator", choices=sorted(TARGETS), help="only this indicator")
        parser.add_argument("--geography", help="only this geography, for example Quebec")
        parser.add_argument("--horizon", type=int, default=12, help="months ahead")
        parser.add_argument("--origins", type=int, default=24, help="backtest origins for ranges")
        parser.add_argument("--step", type=int, default=2, help="months between backtest origins")

    def handle(self, *args, **options):
        codes = [options["indicator"]] if options["indicator"] else sorted(TARGETS)
        saved = skipped = 0
        for code in codes:
            if not Indicator.objects.filter(code=code).exists():
                self.stdout.write(f"skip {code}: not in the warehouse yet")
                skipped += 1
                continue
            geographies = [options["geography"]] if options["geography"] else kpis.geographies(code)
            for geography in geographies:
                try:
                    result = build_forecast(
                        code,
                        geography,
                        horizon=options["horizon"],
                        count=options["origins"],
                        step=options["step"],
                    )
                except ForecastError as error:
                    self.stdout.write(f"skip {code} / {geography}: {error}")
                    skipped += 1
                    continue
                save_forecast(result)
                saved += 1
                ratio = "n/a" if result.vs_naive is None else f"{result.vs_naive:.2f}"
                self.stdout.write(
                    f"{code} / {geography}: {result.method}, vs naive {ratio}, "
                    f"+{len(result.values)}m {result.values[-1]:,.2f} "
                    f"({result.lowers[-1]:,.2f} to {result.uppers[-1]:,.2f})"
                )
        if saved == 0 and skipped == 0:
            raise CommandError("nothing to forecast; run the ingest commands first")
        self.stdout.write(f"{saved} forecasts saved, {skipped} skipped.")
