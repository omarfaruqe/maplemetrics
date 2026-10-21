from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _

from apps.core.localize import geography_name, number

from . import kpis
from .charts import Bar, Line, bar_chart, line_chart


def dashboard(request: HttpRequest) -> HttpResponse:
    """Headline indicators with the charts behind them."""
    rates = kpis.real_policy_rate()
    unemployment = kpis.unemployment_by_province()
    retail = kpis.real_retail_growth()

    national_unemployment = next((r for r in unemployment if r.geography == kpis.NATIONAL), None)
    national_retail = next((r for r in retail if r.geography == kpis.NATIONAL), None)
    latest_rate = rates[-1] if rates else None

    tiles = []
    if latest_rate:
        tiles += [
            (_("Policy rate"), f"{number(latest_rate.policy, 2)}%", f"{latest_rate.date:%Y-%m}"),
            (
                _("Core inflation (CPI-trim)"),
                f"{number(latest_rate.core)}%",
                f"{latest_rate.date:%Y-%m}",
            ),
            (_("Real policy rate"), f"{number(latest_rate.real, 2)}%", f"{latest_rate.date:%Y-%m}"),
        ]
    if national_unemployment:
        tiles.append(
            (
                _("Unemployment, Canada"),
                f"{number(national_unemployment.rate)}%",
                f"{national_unemployment.date:%Y-%m}",
            )
        )
    if national_retail:
        tiles.append(
            (
                _("Real retail growth, Canada"),
                f"{number(national_retail.real, signed=True)}%",
                _("year over year, %(month)s") % {"month": f"{national_retail.date:%Y-%m}"},
            )
        )

    rate_chart = line_chart(
        [
            Line(_("Policy rate"), "--series-1", [(p.date, p.policy) for p in rates]),
            Line(_("Core inflation"), "--series-2", [(p.date, p.core) for p in rates]),
            Line(_("Real rate"), "--series-3", [(p.date, p.real) for p in rates]),
        ],
        label=_("Policy rate, core inflation and the real rate"),
    )
    unemployment_chart = bar_chart(
        [
            Bar(
                geography_name(r.geography),
                r.rate,
                _("%(geo)s, %(month)s: %(rate)s%% (change over 12 months: %(chg)s)")
                % {
                    "geo": geography_name(r.geography),
                    "month": f"{r.date:%Y-%m}",
                    "rate": number(r.rate),
                    "chg": _("n/a")
                    if r.change is None
                    else _("%(value)s pts") % {"value": number(r.change, signed=True)},
                },
                emphasis=r.geography == kpis.NATIONAL,
            )
            for r in unemployment
        ],
        label=_("Unemployment rate by province"),
    )
    retail_chart = bar_chart(
        [
            Bar(
                geography_name(r.geography),
                r.real,
                _("%(geo)s: sales %(nom)s%%, prices %(inf)s%%, real %(real)s%%")
                % {
                    "geo": geography_name(r.geography),
                    "nom": number(r.nominal),
                    "inf": number(r.inflation),
                    "real": number(r.real),
                },
                emphasis=r.geography == kpis.NATIONAL,
            )
            for r in retail
        ],
        label=_("Real retail sales growth by province"),
    )
    context = {
        "tiles": tiles,
        "rates": rates[-24:][::-1],
        "rate_chart": rate_chart,
        "unemployment": unemployment,
        "unemployment_chart": unemployment_chart,
        "retail": retail,
        "retail_chart": retail_chart,
        "has_data": bool(rates or unemployment or retail),
        "active": "dashboard",
    }
    return render(request, "analytics/dashboard.html", context)


HISTORY_MONTHS = 120


def _tile(name: str, geo: str, geo_points, canada_points) -> tuple[str, str, str] | None:
    """A tile with the province's latest value and its gap to Canada in the same month."""
    if not geo_points:
        return None
    day, value = geo_points[-1]
    note = f"{day:%Y-%m}"
    canada = dict(canada_points).get(day)
    if geo != kpis.NATIONAL and canada is not None:
        note += " \u00b7 " + _("%(diff)s pts vs Canada") % {
            "diff": number(value - canada, signed=True)
        }
    return name, f"{number(value)}%", note


def provinces(request: HttpRequest) -> HttpResponse:
    """One province against Canada: unemployment, inflation and real retail growth."""
    options = kpis.geographies()
    fallback = "Quebec" if "Quebec" in options else (options[-1] if options else "")
    asked = request.GET.get("geo", "")
    geo = asked if asked in options else fallback

    panels = []
    tiles = []
    if geo:
        sources = [
            (
                "unemployment",
                _("Unemployment rate"),
                lambda g: kpis.series(kpis.UNEMPLOYMENT, g),
                _("Seasonally adjusted, 15 years and over."),
            ),
            (
                "inflation",
                _("Inflation (CPI, year over year)"),
                lambda g: kpis.yoy_series(kpis.CPI_INDEX, g),
                _("Change in the all-items consumer price index over twelve months."),
            ),
            (
                "real-retail",
                _("Real retail sales growth (year over year)"),
                kpis.real_retail_yoy,
                _("Retail sales growth over twelve months, deflated by CPI."),
            ),
        ]
        for key, title, getter, note in sources:
            geo_points = getter(geo)
            canada_points = getter(kpis.NATIONAL)
            lines = [Line(geography_name(geo), "--series-1", geo_points[-HISTORY_MONTHS:])]
            if geo != kpis.NATIONAL:
                lines.append(
                    Line(
                        geography_name(kpis.NATIONAL), "--context", canada_points[-HISTORY_MONTHS:]
                    )
                )
            tile = _tile(title, geo, geo_points, canada_points)
            canada_by_day = dict(canada_points)
            if tile:
                tiles.append(tile)
            panels.append(
                {
                    "key": key,
                    "title": title,
                    "note": note,
                    "chart": line_chart(lines, label=f"{title}: {geography_name(geo)}"),
                    "rows": [
                        (day, value, canada_by_day.get(day))
                        for day, value in reversed(geo_points[-HISTORY_MONTHS:])
                    ],
                    "has_data": bool(geo_points),
                    "compare": geo != kpis.NATIONAL,
                }
            )
    context = {
        "options": options,
        "geo": geo,
        "tiles": tiles,
        "panels": panels,
        "active": "provinces",
    }
    return render(request, "analytics/provinces.html", context)
