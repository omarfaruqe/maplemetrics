from datetime import date

from apps.analytics.charts import Bar, Line, bar_chart, line_chart, nice_ticks, spread_labels


def test_nice_ticks_cover_the_range_with_round_steps():
    ticks = nice_ticks(-0.8, 5.3)
    assert ticks[0] <= -0.8 and ticks[-1] >= 5.3
    assert 0 in ticks


def test_nice_ticks_handles_flat_data():
    assert len(nice_ticks(2.0, 2.0)) >= 2


def test_line_chart_draws_series_labels_and_tooltips():
    svg = line_chart(
        [
            Line("Policy rate", "--series-1", [(date(2025, 1, 1), 3.0), (date(2026, 1, 1), 2.5)]),
            Line("Real rate", "--series-3", [(date(2025, 1, 1), -0.5), (date(2026, 1, 1), 0.2)]),
        ]
    )
    assert svg.startswith("<svg")
    assert svg.count('class="line"') == 2
    assert "Policy rate 2.5%" in svg
    assert "<title>Real rate, 2026-01: 0.20%</title>" in svg
    assert "\u22120.5" in svg or "-0.5" in svg


def test_line_chart_without_points_is_empty():
    assert line_chart([Line("x", "--series-1", [])]) == ""
    assert line_chart([]) == ""


def test_line_chart_escapes_names():
    svg = line_chart([Line("<b>", "--series-1", [(date(2026, 1, 1), 1.0)])])
    assert "<b>" not in svg and "&lt;b&gt;" in svg


def test_bar_chart_colors_negative_and_emphasis_bars():
    svg = bar_chart(
        [Bar("Canada", 1.0, "tip A", emphasis=True), Bar("Quebec", -2.5, "tip B")],
        decimals=2,
    )
    assert "var(--emphasis)" in svg
    assert "var(--negative)" in svg
    assert "<title>tip B</title>" in svg
    assert "\u22122.50%" in svg


def test_bar_chart_without_bars_is_empty():
    assert bar_chart([]) == ""


def test_spread_labels_separates_close_labels_and_keeps_order():
    placed = spread_labels([100.0, 101.0, 300.0])
    assert placed[1] - placed[0] >= 15
    assert placed[2] == 300.0
    assert spread_labels([50.0, 10.0]) == [50.0, 10.0]


def test_line_chart_end_labels_do_not_overlap():
    same = [(date(2025, 1, 1), 2.0), (date(2026, 1, 1), 2.0)]
    svg = line_chart([Line("Quebec", "--series-1", same), Line("Canada", "--context", same)])
    ys = sorted(
        float(part.split('y="')[1].split('"')[0])
        for part in svg.split("<text ")
        if 'class="label"' in part
    )
    assert len(ys) == 2 and ys[1] - ys[0] >= 15
