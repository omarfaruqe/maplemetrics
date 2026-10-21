"""CSV versions of the dashboard and province tables, with everything the charts are drawn from."""

from django.http import Http404, HttpRequest

from apps.core.csvout import BOTH, STATCAN, csv_response

from . import kpis

PROVINCE_SERIES = {
    "unemployment": (lambda g: kpis.series(kpis.UNEMPLOYMENT, g), "unemployment_rate_pct", STATCAN),
    "inflation": (lambda g: kpis.yoy_series(kpis.CPI_INDEX, g), "cpi_change_12m_pct", STATCAN),
    "real-retail": (kpis.real_retail_yoy, "real_retail_growth_12m_pct", STATCAN),
}


def rates(request: HttpRequest):
    """The full history of the policy rate, core inflation and the real rate."""
    rows = [(p.date, p.policy, p.core, p.real, BOTH) for p in kpis.real_policy_rate()]
    header = ["date", "policy_rate_pct", "core_inflation_pct", "real_policy_rate_pct", "source"]
    return csv_response("maplemetrics-policy-rate.csv", header, rows)


def unemployment(request: HttpRequest):
    rows = [
        (r.geography, r.date, r.rate, r.year_ago, r.change, STATCAN)
        for r in kpis.unemployment_by_province()
    ]
    header = [
        "geography",
        "date",
        "unemployment_rate_pct",
        "rate_12_months_earlier_pct",
        "change_pts",
        "source",
    ]
    return csv_response("maplemetrics-unemployment-by-province.csv", header, rows)


def retail(request: HttpRequest):
    rows = [
        (r.geography, r.date, r.nominal, r.inflation, r.real, STATCAN)
        for r in kpis.real_retail_growth()
    ]
    header = [
        "geography",
        "date",
        "retail_sales_growth_12m_pct",
        "price_growth_12m_pct",
        "real_retail_growth_12m_pct",
        "source",
    ]
    return csv_response("maplemetrics-real-retail-by-province.csv", header, rows)


def province(request: HttpRequest):
    """One province's full history for one series, beside Canada."""
    key = request.GET.get("series", "")
    geo = request.GET.get("geo", "")
    if key not in PROVINCE_SERIES or geo not in kpis.geographies():
        raise Http404("Unknown series or geography")
    getter, column, source = PROVINCE_SERIES[key]
    canada = dict(getter(kpis.NATIONAL))
    rows = [(geo, day, value, canada.get(day), source) for day, value in getter(geo)]
    header = ["geography", "date", column, f"canada_{column}", "source"]
    slug = geo.lower().replace(" ", "-")
    return csv_response(f"maplemetrics-{key}-{slug}.csv", header, rows)
