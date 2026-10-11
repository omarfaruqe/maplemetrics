"""How recent each indicator's data is, so stale pipelines get noticed."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from django.db.models import Count, Max
from django.utils import timezone

from .models import Indicator, Observation

FRESH = "fresh"
STALE = "stale"
EMPTY = "empty"

# Days a series may trail today before it is flagged. A period is dated by its first day and
# Statistics Canada publishes a month about 7 to 11 weeks after it starts, so the newest monthly
# point can be nearly four months old right before the next release. Tune as the catalog grows.
STALE_AFTER_DAYS = {
    Indicator.Frequency.DAILY.value: 7,
    Indicator.Frequency.MONTHLY.value: 120,
    Indicator.Frequency.QUARTERLY.value: 200,
    Indicator.Frequency.ANNUAL.value: 500,
}
DEFAULT_STALE_AFTER_DAYS = 120

_SORT_RANK = {STALE: 0, EMPTY: 1, FRESH: 2}


@dataclass(frozen=True)
class FreshnessRow:
    code: str
    name_en: str
    name_fr: str
    source: str
    source_label: str
    frequency: str
    frequency_label: str
    geographies: int
    observations: int
    newest: date | None
    oldest_latest: date | None
    days_behind: int | None
    status: str


def freshness_report(today: date | None = None) -> list[FreshnessRow]:
    """One row per indicator. Problems sort first.

    ``oldest_latest`` is the earliest of each geography's latest date, so a single lagging
    province makes the whole indicator stale instead of hiding behind the national figure.
    """
    today = today or timezone.localdate()

    latest_dates: dict[int, list[date]] = defaultdict(list)
    row_counts: dict[int, int] = defaultdict(int)
    per_geography = (
        Observation.objects.order_by()
        .values("indicator_id", "geography")
        .annotate(latest=Max("date"), n=Count("id"))
    )
    for item in per_geography:
        latest_dates[item["indicator_id"]].append(item["latest"])
        row_counts[item["indicator_id"]] += item["n"]

    report: list[FreshnessRow] = []
    for indicator in Indicator.objects.all():
        dates = latest_dates.get(indicator.id, [])
        if dates:
            oldest_latest = min(dates)
            days_behind = (today - oldest_latest).days
            limit = STALE_AFTER_DAYS.get(indicator.frequency, DEFAULT_STALE_AFTER_DAYS)
            status = STALE if days_behind > limit else FRESH
            newest = max(dates)
        else:
            oldest_latest = newest = days_behind = None
            status = EMPTY
        report.append(
            FreshnessRow(
                code=indicator.code,
                name_en=indicator.name_en,
                name_fr=indicator.name_fr,
                source=indicator.source,
                source_label=indicator.get_source_display(),
                frequency=indicator.frequency,
                frequency_label=indicator.get_frequency_display(),
                geographies=len(dates),
                observations=row_counts.get(indicator.id, 0),
                newest=newest,
                oldest_latest=oldest_latest,
                days_behind=days_behind,
                status=status,
            )
        )
    report.sort(key=lambda row: (_SORT_RANK[row.status], row.source, row.code))
    return report
