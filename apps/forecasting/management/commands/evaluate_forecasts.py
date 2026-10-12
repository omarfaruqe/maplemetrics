from django.core.management.base import BaseCommand, CommandError

from apps.forecasting.backtest import backtest
from apps.forecasting.targets import TARGETS, load_series


class Command(BaseCommand):
    help = "Backtest every forecasting method on one series and print a leaderboard."

    def add_arguments(self, parser):
        parser.add_argument("indicator", choices=sorted(TARGETS))
        parser.add_argument("--geography", default="Canada")
        parser.add_argument("--horizon", type=int, default=12, help="months ahead to forecast")
        parser.add_argument("--origins", type=int, default=12, help="number of forecast origins")
        parser.add_argument("--step", type=int, default=3, help="months between origins")

    def handle(self, *args, **options):
        code, geography = options["indicator"], options["geography"]
        dates, values = load_series(code, geography)
        if len(values) == 0:
            raise CommandError(f"no {code} data for {geography}; run the ingest commands first")
        horizon = options["horizon"]
        try:
            scores = backtest(
                values,
                horizon=horizon,
                count=options["origins"],
                step=options["step"],
                log=TARGETS[code].log,
            )
        except ValueError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            f"{code} / {geography}: {len(values)} months, {dates[0]:%Y-%m} to {dates[-1]:%Y-%m}; "
            f"{options['origins']} origins {options['step']} months apart, horizon {horizon}"
        )
        marks = [m for m in (1, 3, 6, 12) if m <= horizon]
        header = f"{'METHOD':<16}{'MASE':>7}" + "".join(f"{'MAE@' + str(m):>9}" for m in marks)
        self.stdout.write(header + f"{'FAILED':>8}")
        for score in scores:
            cells = "".join(f"{score.mae[m - 1]:>9.3f}" for m in marks)
            self.stdout.write(f"{score.method:<16}{score.mase:>7.3f}{cells}{score.failures:>8}")

        naive = next((s for s in scores if s.method == "naive"), None)
        best = scores[0]
        if naive and best.method != "naive":
            self.stdout.write(
                f"Best: {best.method} (MASE {best.mase:.3f}), "
                f"{(1 - best.mase / naive.mase) * 100:.0f}% lower error than naive."
            )
        else:
            self.stdout.write("Best: naive. No model beat the naive baseline on this series.")
