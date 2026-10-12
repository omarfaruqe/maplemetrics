from django.core.management.base import BaseCommand, CommandError

from apps.forecasting.backtest import backtest
from apps.forecasting.targets import TARGETS, load_series

FEW_ORIGINS = 8
TIE_BELOW = 0.10


def format_number(value: float) -> str:
    """Thousands separators; whole numbers for big values such as retail sales in thousands."""
    if value != value:  # NaN
        return "-"
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:,.3f}"


def render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """Left-align the first column, right-align the rest, with widths that fit the content."""
    widths = [max(len(row[i]) for row in [headers, *rows]) for i in range(len(headers))]
    lines = []
    for row in [headers, *rows]:
        cells = [
            cell.ljust(width) if i == 0 else cell.rjust(width)
            for i, (cell, width) in enumerate(zip(row, widths, strict=True))
        ]
        lines.append("  ".join(cells))
    return lines


class Command(BaseCommand):
    help = "Backtest every forecasting method on one series and print a leaderboard."

    def add_arguments(self, parser):
        parser.add_argument("indicator", choices=sorted(TARGETS))
        parser.add_argument("--geography", default="Canada")
        parser.add_argument("--horizon", type=int, default=12, help="months ahead to forecast")
        parser.add_argument("--origins", type=int, default=12, help="number of forecast origins")
        parser.add_argument("--step", type=int, default=3, help="months between origins")
        parser.add_argument(
            "--min-train", type=int, default=60, help="fewest months a model may train on"
        )

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
                min_train=options["min_train"],
                log=TARGETS[code].log,
            )
        except ValueError as error:
            raise CommandError(str(error)) from error

        used = scores[0].forecasts + scores[0].failures
        self.stdout.write(
            f"{code} / {geography}: {len(values)} months, {dates[0]:%Y-%m} to {dates[-1]:%Y-%m}; "
            f"{used} origins {options['step']} months apart, horizon {horizon}, "
            f"training windows of at least {options['min_train']} months"
        )
        if used < FEW_ORIGINS:
            self.stdout.write(
                self.style.WARNING(
                    f"Only {used} forecast origins fit in this series; treat the ranking as "
                    "indicative, not conclusive."
                )
            )

        naive = next((s for s in scores if s.method == "naive"), None)
        marks = [m for m in (1, 3, 6, 12) if m <= horizon]
        headers = ["METHOD", "MASE", "VS NAIVE", *[f"MAE@{m}" for m in marks], "FAILED"]
        rows = []
        for score in scores:
            ratio = "-" if naive is None else f"{score.mase / naive.mase:.2f}"
            rows.append(
                [
                    score.method,
                    f"{score.mase:.3f}",
                    ratio,
                    *[format_number(score.mae[m - 1]) for m in marks],
                    str(score.failures),
                ]
            )
        for line in render_table(headers, rows):
            self.stdout.write(line)

        best = scores[0]
        if naive and best.method != "naive":
            gain = 1 - best.mase / naive.mase
            verdict = f"Best: {best.method}, {gain * 100:.0f}% lower error than naive."
            if gain < TIE_BELOW:
                verdict += " Under 10%: effectively a tie with naive."
            self.stdout.write(verdict)
        else:
            self.stdout.write("Best: naive. No model beat the naive baseline on this series.")
