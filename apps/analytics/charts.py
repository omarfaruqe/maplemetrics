"""Server-rendered SVG charts, so the dashboard needs no JavaScript or chart library.

Colors come from CSS custom properties (``--series-1`` and so on) defined by the page, which is
how light and dark mode switch without touching the markup. Hover text uses ``<title>`` elements.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from html import escape

from django.utils.safestring import mark_safe


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
    return f"{value:.{decimals}f}".replace("-", "\u2212")


def line_chart(lines: list[Line], unit: str = "%", width: int = 760, height: int = 340) -> str:
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

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" class="chart" '
        'xmlns="http://www.w3.org/2000/svg">'
    ]
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
    for line in lines:
        if not line.points:
            continue
        path = " ".join(
            f"{'M' if i == 0 else 'L'}{x(day):.1f},{y(value):.1f}"
            for i, (day, value) in enumerate(line.points)
        )
        parts.append(f'<path d="{path}" class="line" style="stroke:var({line.color})"/>')
        last_day, last_value = line.points[-1]
        parts.append(
            f'<circle cx="{x(last_day):.1f}" cy="{y(last_value):.1f}" r="4" class="dot" '
            f'style="fill:var({line.color})"/>'
            f'<text x="{x(last_day) + 10:.1f}" y="{y(last_value) + 4:.1f}" class="label">'
            f"{escape(line.name)} {_fmt(last_value)}{unit}</text>"
        )
        for day, value in line.points:
            parts.append(
                f'<circle cx="{x(day):.1f}" cy="{y(value):.1f}" r="6" class="hit">'
                f"<title>{escape(line.name)}, {day:%Y-%m}: {_fmt(value, 2)}{unit}</title></circle>"
            )
    parts.append("</svg>")
    return mark_safe("".join(parts))  # noqa: S308


def bar_chart(bars: list[Bar], unit: str = "%", width: int = 760, decimals: int = 1) -> str:
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
        f'<svg viewBox="0 0 {width} {height}" role="img" class="chart" '
        'xmlns="http://www.w3.org/2000/svg">',
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
    return mark_safe("".join(parts))  # noqa: S308
