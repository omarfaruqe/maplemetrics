from datetime import date

import pytest

from apps.analytics import kpis


def test_add_months_crosses_year_boundaries():
    assert kpis.add_months(date(2026, 1, 15), -12) == date(2025, 1, 1)
    assert kpis.add_months(date(2026, 1, 1), -1) == date(2025, 12, 1)
    assert kpis.add_months(date(2026, 11, 20), 3) == date(2027, 2, 1)


def test_empty_warehouse_gives_empty_results(db):
    assert kpis.real_policy_rate() == []
    assert kpis.unemployment_by_province() == []
    assert kpis.real_retail_growth() == []


def test_policy_rate_uses_the_last_value_of_each_month(economy):
    monthly = kpis.month_end_policy_rate()
    assert monthly[date(2026, 6, 1)] == 2.50
    assert monthly[date(2026, 8, 1)] == 2.25


def test_real_rate_is_policy_minus_core_for_months_with_both(economy):
    points = {p.date: p for p in kpis.real_policy_rate()}
    assert set(points) == {date(2026, 6, 1), date(2026, 7, 1), date(2026, 8, 1)}
    assert points[date(2026, 8, 1)].real == pytest.approx(-0.25)
    assert points[date(2026, 6, 1)].real == pytest.approx(-0.5)


def test_unemployment_sorted_highest_first_with_year_change(economy):
    rows = kpis.unemployment_by_province()
    assert [r.geography for r in rows] == ["Ontario", "Canada", "Quebec"]
    canada = next(r for r in rows if r.geography == "Canada")
    assert canada.change == pytest.approx(-0.4)
    ontario = rows[0]
    assert ontario.year_ago is None and ontario.change is None


def test_real_retail_growth_deflates_by_cpi(economy):
    rows = {r.geography: r for r in kpis.real_retail_growth()}
    assert "Ontario" not in rows
    canada = rows["Canada"]
    assert canada.nominal == pytest.approx(4.0)
    assert canada.inflation == pytest.approx(3.0)
    assert canada.real == pytest.approx(0.97, abs=0.01)
    quebec = rows["Quebec"]
    assert quebec.nominal == pytest.approx(2.0)
    assert quebec.inflation == pytest.approx(5.0)
    assert quebec.real < -2.8
    assert [r.geography for r in kpis.real_retail_growth()] == ["Canada", "Quebec"]
