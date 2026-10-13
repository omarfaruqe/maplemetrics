from datetime import date

from apps.forecasting.charts import forecast_chart

HISTORY = [(date(2026, 1, 1), 6.0), (date(2026, 2, 1), 6.2), (date(2026, 3, 1), 6.1)]
FORECAST = [
    (date(2026, 4, 1), 6.1, 5.8, 6.4),
    (date(2026, 5, 1), 6.1, 5.6, 6.6),
]


def test_chart_draws_history_dashed_forecast_band_and_tooltips():
    svg = forecast_chart(HISTORY, FORECAST)
    assert svg.startswith("<svg")
    assert "<polygon" in svg
    assert "stroke-dasharray:6 4" in svg
    assert "2026-05 forecast: 6.10%" in svg
    assert "80% range 5.60 to 6.60%" in svg
    assert "2026-02: 6.20%" in svg


def test_chart_labels_the_final_forecast_value_with_its_unit():
    assert "6.1%" in forecast_chart(HISTORY, FORECAST)
    assert "6.1</text>" in forecast_chart(HISTORY, FORECAST, unit="")


def test_chart_needs_both_history_and_forecast():
    assert forecast_chart([], FORECAST) == ""
    assert forecast_chart(HISTORY, []) == ""
