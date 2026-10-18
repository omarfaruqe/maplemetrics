"""Charts are returned as safe HTML, so every piece of text in them must be escaped first."""

from datetime import date
from html.parser import HTMLParser

from apps.analytics.charts import Bar, Line, bar_chart, line_chart
from apps.forecasting.charts import forecast_chart

HOSTILE = '"><img src=x onerror=alert(1)><script>alert(2)</script>'


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: set[str] = set()
        self.attributes: set[str] = set()

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        self.attributes.update(name for name, _value in attrs)


def assert_inert(svg: str):
    """Hostile text may appear as text, but never as an element or an event handler."""
    parsed = Elements()
    parsed.feed(svg)
    assert not parsed.tags & {"script", "img", "iframe", "object"}
    assert not [name for name in parsed.attributes if name.startswith("on")]
    assert "&lt;script&gt;" in svg


def test_line_chart_escapes_names_and_labels():
    points = [(date(2025, 1, 1), 1.0), (date(2025, 2, 1), 2.0)]
    svg = line_chart([Line(HOSTILE, "--series-1", points)], label=HOSTILE)
    assert_inert(svg)


def test_bar_chart_escapes_labels_tooltips_and_title():
    svg = bar_chart(
        [Bar(HOSTILE, 1.0, HOSTILE), Bar("Canada", 2.0, "ok", emphasis=True)], label=HOSTILE
    )
    assert_inert(svg)


def test_forecast_chart_escapes_label_and_unit():
    history = [(date(2025, 1, 1), 1.0), (date(2025, 2, 1), 2.0)]
    forecast = [(date(2025, 3, 1), 2.0, 1.5, 2.5)]
    svg = forecast_chart(history, forecast, unit=HOSTILE, label=HOSTILE)
    assert_inert(svg)
