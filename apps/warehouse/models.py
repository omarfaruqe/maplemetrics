from django.db import models


class Indicator(models.Model):
    """A named economic series (for example the Bank of Canada policy rate)."""

    class Source(models.TextChoices):
        BANK_OF_CANADA = "boc", "Bank of Canada"
        STATISTICS_CANADA = "statcan", "Statistics Canada"

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUAL = "annual", "Annual"

    code = models.CharField(max_length=64, unique=True)
    source = models.CharField(max_length=16, choices=Source.choices)
    name_en = models.CharField(max_length=200)
    name_fr = models.CharField(max_length=200)
    unit = models.CharField(max_length=32, blank=True)
    frequency = models.CharField(max_length=16, choices=Frequency.choices)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} ({self.name_en})"


class Observation(models.Model):
    """One value of an indicator for a geography on a date."""

    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name="observations")
    geography = models.CharField(max_length=64, default="Canada")
    date = models.DateField()
    value = models.DecimalField(max_digits=20, decimal_places=6)
    ingested_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["indicator", "geography", "date"]
        constraints = [
            models.UniqueConstraint(
                fields=["indicator", "geography", "date"], name="uniq_indicator_geo_date"
            )
        ]
        indexes = [models.Index(fields=["indicator", "date"])]

    def __str__(self) -> str:
        return f"{self.indicator.code} {self.geography} {self.date}: {self.value}"
