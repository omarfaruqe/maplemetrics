from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _

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
            (_("Policy rate"), f"{latest_rate.policy:.2f}%", f"{latest_rate.date:%Y-%m}"),
            (
                _("Core inflation (CPI-trim)"),
                f"{latest_rate.core:.1f}%",
                f"{latest_rate.date:%Y-%m}",
            ),
            (_("Real policy rate"), f"{latest_rate.real:.2f}%", f"{latest_rate.date:%Y-%m}"),
        ]
    if national_unemployment:
        tiles.append(
            (
                _("Unemployment, Canada"),
                f"{national_unemployment.rate:.1f}%",
                f"{national_unemployment.date:%Y-%m}",
            )
        )
    if national_retail:
        tiles.append(
            (
                _("Real retail growth, Canada"),
                f"{national_retail.real:+.1f}%",
                _("year over year, %(month)s") % {"month": f"{national_retail.date:%Y-%m}"},
            )
        )

    rate_chart = line_chart(
        [
            Line(_("Policy rate"), "--series-1", [(p.date, p.policy) for p in rates]),
            Line(_("Core inflation"), "--series-2", [(p.date, p.core) for p in rates]),
            Line(_("Real rate"), "--series-3", [(p.date, p.real) for p in rates]),
        ]
    )
    unemployment_chart = bar_chart(
        [
            Bar(
                r.geography,
                r.rate,
                _("%(geo)s, %(month)s: %(rate).1f%% (change over 12 months: %(chg)s)")
                % {
                    "geo": r.geography,
                    "month": f"{r.date:%Y-%m}",
                    "rate": r.rate,
                    "chg": "n/a" if r.change is None else f"{r.change:+.1f} pts",
                },
                emphasis=r.geography == kpis.NATIONAL,
            )
            for r in unemployment
        ]
    )
    retail_chart = bar_chart(
        [
            Bar(
                r.geography,
                r.real,
                _("%(geo)s: sales %(nom).1f%%, prices %(inf).1f%%, real %(real).1f%%")
                % {"geo": r.geography, "nom": r.nominal, "inf": r.inflation, "real": r.real},
                emphasis=r.geography == kpis.NATIONAL,
            )
            for r in retail
        ]
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
    }
    return render(request, "analytics/dashboard.html", context)
