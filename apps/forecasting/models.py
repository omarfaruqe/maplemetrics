from django.db import models

from apps.warehouse.models import Indicator


class Forecast(models.Model):
    """The current forecast of one indicator for one geography, with how well its method did."""

    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name="forecasts")
    geography = models.CharField(max_length=64)
    method = models.CharField(max_length=32)
    trained_through = models.DateField()
    interval_level = models.FloatField(default=0.8)
    backtest_origins = models.PositiveSmallIntegerField()
    mase = models.FloatField()
    vs_naive = models.FloatField(null=True, blank=True)  # method error / naive error; below 1 wins
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["indicator", "geography"]
        constraints = [
            models.UniqueConstraint(fields=["indicator", "geography"], name="uniq_forecast_series")
        ]

    def __str__(self) -> str:
        return f"{self.indicator.code} {self.geography} ({self.method})"


class ForecastPoint(models.Model):
    """One forecast month with the range that past forecasts of this method stayed within."""

    forecast = models.ForeignKey(Forecast, on_delete=models.CASCADE, related_name="points")
    date = models.DateField()
    value = models.FloatField()
    lower = models.FloatField()
    upper = models.FloatField()

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["forecast", "date"], name="uniq_forecast_point_date")
        ]

    def __str__(self) -> str:
        return f"{self.forecast} {self.date}: {self.value:.3f}"
