"""CSV download of one forecast: the history it learned from and the months it predicts."""

from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404

from apps.analytics import kpis
from apps.core.csvout import STATCAN, csv_response

from .models import Forecast
from .targets import TARGETS, load_series

# Values are written as stored, so the unit column says what they are.
UNITS = {
    kpis.UNEMPLOYMENT: "percent",
    kpis.RETAIL_SALES: "thousands of CAD",
    kpis.CPI_INDEX: "index, 2002=100",
}


def forecast(request: HttpRequest):
    code = request.GET.get("indicator", "")
    geo = request.GET.get("geo", "")
    if code not in TARGETS:
        raise Http404("Unknown indicator")
    chosen = get_object_or_404(
        Forecast.objects.select_related("indicator"), indicator__code=code, geography=geo
    )
    unit = UNITS.get(code, "")
    level = round(chosen.interval_level * 100)
    dates, values = load_series(code, geo)
    rows = [
        (code, geo, "actual", d, v, None, None, unit, "", None, STATCAN)
        for d, v in zip(dates, values, strict=True)
    ]
    rows += [
        (
            code,
            geo,
            "forecast",
            p.date,
            p.value,
            p.lower,
            p.upper,
            unit,
            chosen.method,
            level,
            STATCAN,
        )
        for p in chosen.points.all()
    ]
    header = [
        "indicator",
        "geography",
        "kind",
        "date",
        "value",
        "lower",
        "upper",
        "unit",
        "method",
        "range_level_pct",
        "source",
    ]
    slug = geo.lower().replace(" ", "-")
    return csv_response(f"maplemetrics-forecast-{code.lower()}-{slug}.csv", header, rows)
