"""Fan chart: history, the forecast line and the range past forecasts stayed within."""

from __future__ import annotations

import math
from datetime import date
from html import escape

from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from apps.analytics.charts import _fmt, nice_ticks, svg_open


def forecast_chart(
    history: list[tuple[date, float]],
    forecast: list[tuple[date, float, float, float]],
    unit: str = "%",
    decimals: int = 1,
    level: int = 80,
    width: int = 760,
    height: int = 340,
    label: str = "",
) -> str:
    """History as a solid line, the forecast dashed, and a shaded band for the range.

    ``forecast`` rows are (date, value, lower, upper). The y axis follows the data rather than
    starting at zero, since these are levels and the story is the recent movement.
    """
    if not history or not forecast:
        return ""
    left, right, top, bottom = 52, 90, 12, 28
    days = [d.toordinal() for d, _ in history] + [row[0].toordinal() for row in forecast]
    values = [v for _, v in history] + [row[2] for row in forecast] + [row[3] for row in forecast]
    ticks = nice_ticks(min(values), max(values))
    y_min, y_max = ticks[0], ticks[-1]
    x_min, x_max = min(days), max(days)

    def x(day: date) -> float:
        return left + (day.toordinal() - x_min) / ((x_max - x_min) or 1) * (width - left - right)

    def y(value: float) -> float:
        return top + (y_max - value) / ((y_max - y_min) or 1) * (height - top - bottom)

    end_row = forecast[-1]
    summary = _(
        "Latest actual: %(actual)s%(unit)s in %(month)s. Forecast for %(end_month)s: "
        "%(value)s%(unit)s, with a %(level)d%% range from %(low)s%(unit)s to %(high)s%(unit)s."
    ) % {
        "actual": _fmt(history[-1][1], decimals + 1),
        "month": f"{history[-1][0]:%Y-%m}",
        "end_month": f"{end_row[0]:%Y-%m}",
        "value": _fmt(end_row[1], decimals + 1),
        "low": _fmt(end_row[2], decimals + 1),
        "high": _fmt(end_row[3], decimals + 1),
        "level": level,
        "unit": unit,
    }
    parts = [svg_open(width, height, label, summary)]
    for tick in ticks:
        tick_label = _fmt(tick, 0 if float(tick).is_integer() else decimals)
        parts.append(
            f'<line x1="{left}" x2="{width - right}" y1="{y(tick):.1f}" y2="{y(tick):.1f}" '
            'class="grid"/>'
            f'<text x="{left - 8}" y="{y(tick) + 4:.1f}" text-anchor="end" class="tick">'
            f"{tick_label}</text>"
        )
    first_year, last_year = min(d.year for d, _ in history), max(r[0].year for r in forecast)
    year_step = max(1, math.ceil((last_year - first_year) / 6))
    for year in range(first_year + 1, last_year + 1, year_step):
        parts.append(
            f'<text x="{x(date(year, 1, 1)):.1f}" y="{height - 8}" text-anchor="middle" '
            f'class="tick">{year}</text>'
        )

    last_day, last_value = history[-1]
    upper_edge = [(r[0], r[3]) for r in forecast]
    lower_edge = [(r[0], r[2]) for r in reversed(forecast)]
    band = [(last_day, last_value), *upper_edge, *lower_edge]
    outline = " ".join(f"{x(d):.1f},{y(v):.1f}" for d, v in band)
    parts.append(f'<polygon points="{outline}" style="fill:var(--series-1);fill-opacity:0.16"/>')
    parts.append(
        f'<line x1="{x(last_day):.1f}" x2="{x(last_day):.1f}" y1="{top}" y2="{height - bottom}" '
        'class="axis" style="stroke-dasharray:2 4"/>'
    )

    solid = " ".join(
        f"{'M' if i == 0 else 'L'}{x(d):.1f},{y(v):.1f}" for i, (d, v) in enumerate(history)
    )
    parts.append(f'<path d="{solid}" class="line" style="stroke:var(--series-1)"/>')
    dashed_points = [(last_day, last_value), *[(r[0], r[1]) for r in forecast]]
    dashed = " ".join(
        f"{'M' if i == 0 else 'L'}{x(d):.1f},{y(v):.1f}" for i, (d, v) in enumerate(dashed_points)
    )
    parts.append(
        f'<path d="{dashed}" class="line" style="stroke:var(--series-1);stroke-dasharray:6 4"/>'
    )

    end_day, end_value = forecast[-1][0], forecast[-1][1]
    parts.append(
        f'<circle cx="{x(end_day):.1f}" cy="{y(end_value):.1f}" r="4" class="dot" '
        'style="fill:var(--series-1)"/>'
        f'<text x="{x(end_day) + 10:.1f}" y="{y(end_value) + 4:.1f}" class="label">'
        f"{_fmt(end_value, decimals)}{escape(unit)}</text>"
    )
    for d, v in history:
        parts.append(
            f'<circle cx="{x(d):.1f}" cy="{y(v):.1f}" r="6" class="hit">'
            f"<title>{d:%Y-%m}: {_fmt(v, decimals + 1)}{escape(unit)}</title></circle>"
        )
    for d, v, lo, hi in forecast:
        tip = _(
            "%(month)s forecast: %(value)s%(unit)s (%(level)d%% range %(low)s to %(high)s%(unit)s)"
        ) % {
            "month": f"{d:%Y-%m}",
            "value": _fmt(v, decimals + 1),
            "unit": unit,
            "level": level,
            "low": _fmt(lo, decimals + 1),
            "high": _fmt(hi, decimals + 1),
        }
        parts.append(
            f'<circle cx="{x(d):.1f}" cy="{y(v):.1f}" r="6" class="hit">'
            f"<title>{escape(tip)}</title></circle>"
        )
    parts.append("</svg>")
    # Every text value above goes through escape(); see test_chart_escaping.py.
    return mark_safe("".join(parts))  # noqa: S308  # nosec B703 B308
