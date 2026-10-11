"""Write fetched points into the warehouse tables (idempotent upserts)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from django.db.models import Max
from django.utils import timezone

from apps.warehouse.models import Indicator, Observation

from .bank_of_canada import Point
from .catalog import SeriesSpec


def sync_indicators(specs: Iterable[SeriesSpec], source: str) -> dict[str, Indicator]:
    """Create or update an Indicator row for each series spec."""
    indicators: dict[str, Indicator] = {}
    for spec in specs:
        indicator, _ = Indicator.objects.update_or_create(
            code=spec.code,
            defaults={
                "source": source,
                "name_en": spec.name_en,
                "name_fr": spec.name_fr,
                "unit": spec.unit,
                "frequency": spec.frequency,
            },
        )
        indicators[spec.code] = indicator
    return indicators


def latest_date(indicator: Indicator, geography: str = "Canada") -> date | None:
    """Most recent stored date for an indicator, used for incremental refreshes."""
    return Observation.objects.filter(indicator=indicator, geography=geography).aggregate(
        latest=Max("date")
    )["latest"]


def load_points(indicator: Indicator, points: Iterable[Point], geography: str = "Canada") -> int:
    """Upsert points for one indicator. Re-running never creates duplicates."""
    now = timezone.now()
    rows = [
        Observation(
            indicator=indicator,
            geography=geography,
            date=point.date,
            value=point.value,
            ingested_at=now,
        )
        for point in points
    ]
    if not rows:
        return 0
    Observation.objects.bulk_create(
        rows,
        batch_size=1000,
        update_conflicts=True,
        unique_fields=["indicator", "geography", "date"],
        update_fields=["value", "ingested_at"],
    )
    return len(rows)
