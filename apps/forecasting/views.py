from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _

from apps.analytics import kpis
from apps.core.localize import geography_name

from .charts import forecast_chart
from .models import Forecast
from .targets import TARGETS, load_series

HISTORY_MONTHS = 60
NO_EDGE = 0.9  # a method within 10% of naive is not meaningfully better


def display_for(code: str) -> dict:
    """Title, unit and scaling per indicator. Retail sales are stored in thousands of CAD."""
    return {
        kpis.UNEMPLOYMENT: {"title": _("Unemployment rate"), "unit": "%", "scale": 1.0, "dp": 1},
        kpis.RETAIL_SALES: {
            "title": _("Retail sales (billions of CAD)"),
            "unit": "",
            "scale": 1e-6,
            "dp": 1,
        },
        kpis.CPI_INDEX: {
            "title": _("Consumer price index (2002=100)"),
            "unit": "",
            "scale": 1.0,
            "dp": 1,
        },
    }[code]


def verdict(vs_naive: float | None) -> str:
    """Plain-language statement of whether the method beat assuming nothing changes."""
    if vs_naive is None or vs_naive >= NO_EDGE:
        return _(
            "In backtests this method was no better than assuming no change, so read the line "
            "as 'about where it is now' and the shaded band as the useful part."
        )
    return _("In backtests this method had %(pct)d%% lower error than assuming no change.") % {
        "pct": round((1 - vs_naive) * 100)
    }


def forecasts(request: HttpRequest) -> HttpResponse:
    """History and forecast for one indicator and geography, with the evidence behind it."""
    available = {code: [] for code in TARGETS}
    for code, geography in Forecast.objects.values_list("indicator__code", "geography"):
        if code in available:
            available[code].append(geography)
    available = {
        code: sorted(geos, key=lambda name: (name != kpis.NATIONAL, name))
        for code, geos in available.items()
        if geos
    }
    context = {"active": "forecasts", "has_data": bool(available)}
    if not available:
        return render(request, "forecasting/forecasts.html", context)

    code = request.GET.get("indicator", "")
    if code not in available:
        code = kpis.UNEMPLOYMENT if kpis.UNEMPLOYMENT in available else next(iter(available))
    geographies = available[code]
    geo = request.GET.get("geo", "")
    if geo not in geographies:
        geo = kpis.NATIONAL if kpis.NATIONAL in geographies else geographies[0]

    forecast = Forecast.objects.select_related("indicator").get(indicator__code=code, geography=geo)
    points = list(forecast.points.all())
    shown = display_for(code)
    scale, dp, unit = shown["scale"], shown["dp"], shown["unit"]
    dates, values = load_series(code, geo)
    history = [(d, v * scale) for d, v in zip(dates, values, strict=True)][-HISTORY_MONTHS:]
    rows = [(p.date, p.value * scale, p.lower * scale, p.upper * scale) for p in points]
    level = round(forecast.interval_level * 100)

    context.update(
        {
            "indicators": [(c, display_for(c)["title"]) for c in available],
            "geographies": geographies,
            "code": code,
            "geo": geo,
            "title": shown["title"],
            "unit": unit,
            "dp": dp,
            "forecast": forecast,
            "rows": rows,
            "last_actual": history[-1] if history else None,
            "final": rows[-1] if rows else None,
            "level": level,
            "verdict": verdict(forecast.vs_naive),
            "chart": forecast_chart(
                history,
                rows,
                unit=unit,
                decimals=dp,
                level=level,
                label=f"{shown['title']}: {geography_name(geo)}",
            ),
        }
    )
    return render(request, "forecasting/forecasts.html", context)
