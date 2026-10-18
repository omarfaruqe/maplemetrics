"""System status: is the app working, and is its data up to date?

Each check returns a status of ``ok``, ``warn`` or ``fail``. A failure of something the site cannot
work without (the database or the cache) makes the whole status page answer 503, so an external
monitor can alert on it. Stale or missing data is a warning: the site still works.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.forecasting.models import Forecast
from apps.warehouse.freshness import EMPTY, FRESH, STALE, freshness_report
from apps.warehouse.models import Observation

OK, WARN, FAIL = "ok", "warn", "fail"

# Refreshes are scheduled daily, so data older than this means the schedule has stopped working.
REFRESH_WARN_AFTER = timedelta(days=3)


@dataclass(frozen=True)
class Check:
    key: str
    title: str
    status: str
    message: str
    data: dict = field(default_factory=dict)


def _database() -> Check:
    title = _("Database")
    started = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # noqa: BLE001
        return Check("database", title, FAIL, _("Not reachable."))
    latency = round((time.perf_counter() - started) * 1000, 1)
    return Check(
        "database",
        title,
        OK,
        _("Responding in %(ms)s ms.") % {"ms": latency},
        {"latency_ms": latency},
    )


def _cache() -> Check:
    title = _("Cache")
    key = f"status-probe-{uuid.uuid4().hex}"
    started = time.perf_counter()
    try:
        cache.set(key, "ok", 10)
        working = cache.get(key) == "ok"
        cache.delete(key)
    except Exception:  # noqa: BLE001
        working = False
    if not working:
        return Check("cache", title, FAIL, _("Not reachable."))
    latency = round((time.perf_counter() - started) * 1000, 1)
    return Check(
        "cache", title, OK, _("Responding in %(ms)s ms.") % {"ms": latency}, {"latency_ms": latency}
    )


def _data() -> Check:
    title = _("Indicator freshness")
    rows = freshness_report()
    counts = {
        FRESH: sum(row.status == FRESH for row in rows),
        STALE: sum(row.status == STALE for row in rows),
        EMPTY: sum(row.status == EMPTY for row in rows),
    }
    data = {"indicators": len(rows), **counts}
    if not rows or counts[FRESH] == 0 and counts[STALE] == 0:
        return Check("data", title, WARN, _("No data loaded yet."), data)
    if counts[STALE] or counts[EMPTY]:
        message = _(
            "%(fresh)d of %(total)d indicators are up to date; %(stale)d stale, %(empty)d empty."
        ) % {
            "fresh": counts[FRESH],
            "total": len(rows),
            "stale": counts[STALE],
            "empty": counts[EMPTY],
        }
        return Check("data", title, WARN, message, data)
    message = _("All %(total)d indicators are up to date.") % {"total": len(rows)}
    return Check("data", title, OK, message, data)


def _last_refresh() -> Check:
    title = _("Last data load")
    newest = Observation.objects.aggregate(newest=Max("ingested_at"))["newest"]
    if newest is None:
        return Check("last_refresh", title, WARN, _("Nothing has been loaded yet."), {})
    age = timezone.now() - newest
    data = {"at": newest.isoformat(), "age_hours": round(age.total_seconds() / 3600, 1)}
    local = timezone.localtime(newest)
    message = _("%(when)s (%(hours)d hours ago).") % {
        "when": f"{local:%Y-%m-%d %H:%M}",
        "hours": int(age.total_seconds() // 3600),
    }
    return Check("last_refresh", title, WARN if age > REFRESH_WARN_AFTER else OK, message, data)


def _forecasts() -> Check:
    title = _("Forecasts")
    count = Forecast.objects.count()
    if count == 0:
        return Check("forecasts", title, WARN, _("No forecasts built yet."), {"count": 0})
    newest = Forecast.objects.aggregate(newest=Max("updated_at"))["newest"]
    local = timezone.localtime(newest)
    message = _("%(count)d forecasts, newest built %(when)s.") % {
        "count": count,
        "when": f"{local:%Y-%m-%d %H:%M}",
    }
    return Check("forecasts", title, OK, message, {"count": count, "newest": newest.isoformat()})


def run_checks() -> list[Check]:
    return [_database(), _cache(), _data(), _last_refresh(), _forecasts()]


def overall(checks: list[Check]) -> str:
    """``down`` if anything failed, ``attention`` if anything warns, otherwise ``ok``."""
    if any(check.status == FAIL for check in checks):
        return "down"
    if any(check.status == WARN for check in checks):
        return "attention"
    return "ok"


def snapshot() -> dict:
    """Everything the status page and the JSON endpoint show."""
    checks = run_checks()
    return {
        "overall": overall(checks),
        "version": settings.APP_VERSION,
        "time": timezone.now(),
        "checks": checks,
    }
