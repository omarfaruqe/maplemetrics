"""Server-rendered SVG charts, so the dashboard needs no JavaScript or chart library.

Colors come from CSS custom properties (``--series-1`` and so on) defined by the page, which is
how light and dark mode switch without touching the markup. Hover text uses ``<title>`` elements.

Every chart carries an accessible name (``aria-label``) and a plain-language description of what it
shows (``<desc>``), because screen readers cannot read the drawing itself. The pages also offer the
same numbers as a table.
"""

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass
from datetime import date
from html import escape

from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from apps.core.localize import number


@dataclass(frozen=True)
class Line:
    name: str
    color: str  # CSS variable name, for example "--series-1"
    points: list[tuple[date, float]]


@dataclass(frozen=True)
class Bar:
    label: str
    value: float
    tooltip: str
    emphasis: bool = False


def nice_ticks(low: float, high: float, target: int = 5) -> list[float]:
    """Round tick values covering [low, high]."""
    if high == low:
        high = low + 1
    raw = (high - low) / target
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    start = math.floor(low / step) * step
    ticks = []
    value = start
    while value < high + step * 0.999:
        ticks.append(round(value, 10))
        value += step
    return ticks


def _fmt(value: float, decimals: int = 1) -> str:
    return number(value, decimals).replace("-", "−")


def svg_open(width: int, height: int, label: str = "", summary: str = "") -> str:
    """Opening ``<svg>`` tag with an accessible name and an optional description."""
    attributes = f'viewBox="0 0 {width} {height}" role="img" class="chart"'
    attributes += f' aria-label="{escape(label or _("Chart"), quote=True)}"'
    description = ""
    if summary:
        description_id = "chart-" + format(zlib.crc32(f"{label}|{summary}".encode()), "08x")
        attributes += f' aria-describedby="{description_id}"'
        description = f'<desc id="{description_id}">{escape(summary)}</desc>'
    return f'<svg {attributes} xmlns="http://www.w3.org/2000/svg">{description}'


def describe_lines(lines: list[Line], unit: str = "%") -> str:
    """One sentence per series: where it started, where it ended and its range."""
    sentences = []
    for line in lines:
        if not line.points:
            continue
        values = [value for _day, value in line.points]
        (first_day, first), (last_day, last) = line.points[0], line.points[-1]
        sentences.append(
            _(
                "%(name)s: %(first)s%(unit)s in %(first_month)s, "
                "%(last)s%(unit)s in %(last_month)s; lowest %(low)s%(unit)s, "
                "highest %(high)s%(unit)s."
            )
            % {
                "name": line.name,
                "first": _fmt(first, 2),
                "first_month": f"{first_day:%Y-%m}",
                "last": _fmt(last, 2),
                "last_month": f"{last_day:%Y-%m}",
                "low": _fmt(min(values), 2),
                "high": _fmt(max(values), 2),
                "unit": unit,
            }
        )
    return " ".join(sentences)


def describe_bars(bars: list[Bar], unit: str = "%", decimals: int = 1) -> str:
    """The highest and lowest bars, plus the highlighted one (Canada) for comparison."""
    if not bars:
        return ""
    highest = max(bars, key=lambda bar: bar.value)
    lowest = min(bars, key=lambda bar: bar.value)
    sentences = [
        _("Highest: %(label)s, %(value)s%(unit)s. Lowest: %(low_label)s, %(low_value)s%(unit)s.")
        % {
            "label": highest.label,
            "value": _fmt(highest.value, decimals),
            "low_label": lowest.label,
            "low_value": _fmt(lowest.value, decimals),
            "unit": unit,
        }
    ]
    for bar in bars:
        if bar.emphasis and bar not in (highest, lowest):
            sentences.append(
                _("%(label)s: %(value)s%(unit)s.")
                % {"label": bar.label, "value": _fmt(bar.value, decimals), "unit": unit}
            )
    return " ".join(sentences)


def spread_labels(positions: list[float], gap: float = 15.0) -> list[float]:
    """Nudge label y positions apart so none are closer than ``gap``; order is preserved."""
    order = sorted(range(len(positions)), key=lambda i: positions[i])
    placed = list(positions)
    for previous, current in zip(order, order[1:], strict=False):
        placed[current] = max(placed[current], placed[previous] + gap)
    return placed


def line_chart(
    lines: list[Line], unit: str = "%", width: int = 760, height: int = 340, label: str = ""
) -> str:
    """A multi-series line chart on a single y axis with a zero line, year ticks and end labels."""
    left, right, top, bottom = 44, 120, 12, 28
    all_points = [point for line in lines for point in line.points]
    if not all_points:
        return ""
    days = [day.toordinal() for day, _ in all_points]
    values = [value for _, value in all_points]
    x_min, x_max = min(days), max(days)
    ticks = nice_ticks(min(values + [0]), max(values + [0]))
    y_min, y_max = ticks[0], ticks[-1]

    def x(day: date) -> float:
        span = (x_max - x_min) or 1
        return left + (day.toordinal() - x_min) / span * (width - left - right)

    def y(value: float) -> float:
        return top + (y_max - value) / (y_max - y_min) * (height - top - bottom)

    parts = [svg_open(width, height, label, describe_lines(lines, unit))]
    for tick in ticks:
        zero = tick == 0
        parts.append(
            f'<line x1="{left}" x2="{width - right}" y1="{y(tick):.1f}" y2="{y(tick):.1f}" '
            f'class="{"axis" if zero else "grid"}"/>'
            f'<text x="{left - 8}" y="{y(tick) + 4:.1f}" text-anchor="end" class="tick">'
            f"{_fmt(tick, 0 if float(tick).is_integer() else 1)}</text>"
        )
    first_year = min(day for day, _ in all_points).year
    last_year = max(day for day, _ in all_points).year
    year_step = max(1, math.ceil((last_year - first_year) / 6))
    for year in range(first_year + 1, last_year + 1, year_step):
        px = x(date(year, 1, 1))
        parts.append(
            f'<text x="{px:.1f}" y="{height - 8}" text-anchor="middle" class="tick">{year}</text>'
        )
    drawn = [line for line in lines if line.points]
    label_ys = dict(
        zip(
            (line.name for line in drawn),
            spread_labels([y(line.points[-1][1]) for line in drawn]),
            strict=True,
        )
    )
    for line in drawn:
        path = " ".join(
            f"{'M' if i == 0 else 'L'}{x(day):.1f},{y(value):.1f}"
            for i, (day, value) in enumerate(line.points)
        )
        parts.append(f'<path d="{path}" class="line" style="stroke:var({line.color})"/>')
        last_day, last_value = line.points[-1]
        parts.append(
            f'<circle cx="{x(last_day):.1f}" cy="{y(last_value):.1f}" r="4" class="dot" '
            f'style="fill:var({line.color})"/>'
            f'<text x="{x(last_day) + 10:.1f}" y="{label_ys[line.name] + 4:.1f}" class="label">'
            f"{escape(line.name)} {_fmt(last_value)}{unit}</text>"
        )
        for day, value in line.points:
            parts.append(
                f'<circle cx="{x(day):.1f}" cy="{y(value):.1f}" r="6" class="hit">'
                f"<title>{escape(line.name)}, {day:%Y-%m}: {_fmt(value, 2)}{unit}</title></circle>"
            )
    parts.append("</svg>")
    # Every text value above goes through escape(); see test_chart_escaping.py.
    return mark_safe("".join(parts))  # noqa: S308  # nosec


def bar_chart(
    bars: list[Bar], unit: str = "%", width: int = 760, decimals: int = 1, label: str = ""
) -> str:
    """Horizontal bars from a zero baseline. Negative values go left in the 'negative' color."""
    if not bars:
        return ""
    row_height, gap = 26, 8
    left, right, top = 190, 70, 6
    height = top + len(bars) * (row_height + gap)
    values = [bar.value for bar in bars]
    low, high = min(values + [0]), max(values + [0])
    span = (high - low) or 1
    plot = width - left - right

    def x(value: float) -> float:
        return left + (value - low) / span * plot

    zero = x(0)
    parts = [
        svg_open(width, height, label, describe_bars(bars, unit, decimals)),
        f'<line x1="{zero:.1f}" x2="{zero:.1f}" y1="0" y2="{height}" class="axis"/>',
    ]
    for i, bar in enumerate(bars):
        y = top + i * (row_height + gap)
        end = x(bar.value)
        bar_x, bar_w = min(zero, end), max(abs(end - zero), 1)
        color = "--negative" if bar.value < 0 else ("--emphasis" if bar.emphasis else "--series-1")
        weight = ' class="label strong"' if bar.emphasis else ' class="label"'
        # Value labels sit just right of the bar end, or right of the baseline for negative bars,
        # so they never run into the category labels on the left.
        label_x = (end if bar.value >= 0 else zero) + 8
        anchor = "start"
        parts.append(
            f'<text x="{left - 12}" y="{y + row_height / 2 + 4:.1f}" text-anchor="end"{weight}>'
            f"{escape(bar.label)}</text>"
            f'<rect x="{bar_x:.1f}" y="{y}" width="{bar_w:.1f}" height="{row_height}" rx="4" '
            f'style="fill:var({color})"><title>{escape(bar.tooltip)}</title></rect>'
            f'<text x="{label_x:.1f}" y="{y + row_height / 2 + 4:.1f}" text-anchor="{anchor}" '
            f'class="value">{_fmt(bar.value, decimals)}{unit}</text>'
        )
    parts.append("</svg>")
    # Every text value above goes through escape(); see test_chart_escaping.py.
    return mark_safe("".join(parts))  # noqa: S308  # nosec
