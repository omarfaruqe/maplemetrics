import numpy as np
import pytest

from apps.forecasting.backtest import backtest, origins
from apps.forecasting.methods import naive


def test_origins_are_oldest_first_and_leave_room_for_the_horizon():
    found = origins(length=100, horizon=12, count=4, step=3, min_train=50)
    assert found == [79, 82, 85, 88]
    assert max(found) + 12 <= 100


def test_origins_drop_windows_with_too_little_training_data():
    assert origins(length=100, horizon=12, count=10, step=10, min_train=60) == [68, 78, 88]


def test_origins_reject_a_series_that_is_too_short():
    with pytest.raises(ValueError, match="too short"):
        origins(length=40, horizon=12, count=4, step=3, min_train=96)


def perfect_line(train, horizon):
    slope = train[-1] - train[-2]
    return train[-1] + slope * np.arange(1, horizon + 1)


def test_perfect_method_scores_zero_and_ranks_first():
    values = np.arange(200.0)
    scores = backtest(
        values,
        {"naive": naive, "line": perfect_line},
        horizon=6,
        count=5,
        step=2,
        min_train=50,
    )
    assert [s.method for s in scores] == ["line", "naive"]
    assert scores[0].mase == pytest.approx(0)
    assert scores[1].mae[0] == pytest.approx(1.0)
    assert scores[1].mae[5] == pytest.approx(6.0)
    assert scores[1].mase == pytest.approx(3.5)


def test_failed_forecasts_are_counted_and_the_method_ranks_last():
    def broken(train, horizon):
        raise RuntimeError("no fit")

    def sometimes(train, horizon):
        if len(train) % 2 == 0:
            raise RuntimeError("unlucky")
        return naive(train, horizon)

    scores = backtest(
        np.arange(200.0),
        {"broken": broken, "naive": naive, "sometimes": sometimes},
        horizon=3,
        count=4,
        step=1,
        min_train=50,
    )
    by_name = {s.method: s for s in scores}
    assert by_name["broken"].failures == 4 and by_name["broken"].forecasts == 0
    assert np.isnan(by_name["broken"].mase)
    assert by_name["sometimes"].failures == 2 and by_name["sometimes"].forecasts == 2
    assert scores[-1].method == "broken"


def test_non_finite_forecasts_count_as_failures():
    def nan_forecast(train, horizon):
        return np.full(horizon, np.nan)

    (score,) = backtest(
        np.arange(120.0), {"nan": nan_forecast}, horizon=3, count=2, step=1, min_train=50
    )
    assert score.failures == 2


def test_models_see_only_the_past_and_a_capped_window():
    seen = []

    def spy(train, horizon):
        seen.append((len(train), float(train[-1])))
        return naive(train, horizon)

    values = np.arange(300.0)
    backtest(values, {"spy": spy}, horizon=6, count=3, step=5, min_train=50, max_train=100)
    assert [length for length, _ in seen] == [100, 100, 100]
    assert [last for _, last in seen] == [283.0, 288.0, 293.0]


def test_log_transform_is_applied_to_models_but_errors_use_original_units():
    seen = []

    def spy(train, horizon):
        seen.append(float(train[-1]))
        return naive(train, horizon)

    values = np.full(120, 100.0)
    (score,) = backtest(values, {"spy": spy}, horizon=3, count=2, step=1, min_train=50, log=True)
    assert seen[0] == pytest.approx(np.log(100.0))
    assert score.mae[0] == pytest.approx(0, abs=1e-9)


def test_error_scale_comes_from_the_recent_window_not_the_whole_history():
    values = np.concatenate([np.arange(100) * 0.1, 10 + np.arange(1, 101, dtype=float)])
    (score,) = backtest(
        values, {"naive": naive}, horizon=3, count=1, step=1, min_train=50, max_train=50
    )
    assert score.mae == pytest.approx([1.0, 2.0, 3.0])
    assert score.mase == pytest.approx(2.0)
