import numpy as np

from apps.forecasting.backtest import backtest
from apps.forecasting.methods import naive


def test_scores_expose_signed_errors_per_origin_and_horizon():
    (score,) = backtest(
        np.arange(120.0), {"naive": naive}, horizon=4, count=5, step=2, min_train=50
    )
    errors = np.array(score.errors)
    assert errors.shape == (5, 4)
    assert errors[0].tolist() == [-1.0, -2.0, -3.0, -4.0]
