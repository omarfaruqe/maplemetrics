# Forecasting methods

This page explains how the forecasts are made, how they are scored and what they cannot tell you.

## The question

What will this monthly series look like over the next twelve months, and how far off might that be?
Only three series are forecast: the unemployment rate, retail sales and the consumer price index,
each for Canada and the provinces.

## Methods

Six methods share one interface: a training array and a horizon go in, forecasts come out.

| Method | Idea |
|---|---|
| `naive` | Repeat the last value |
| `seasonal_naive` | Repeat the same month of last year |
| `drift` | Continue the average monthly change over the training window |
| `ets` | Exponential smoothing with a damped trend, so trends fade out |
| `ets_seasonal` | The same, with additive monthly seasonality |
| `arima` | ARIMA(p, 1, q) with drift, with p and q from 0 to 2 chosen by AIC |

The three simple methods are baselines. A model only earns a place by beating them out of sample.

Retail sales and the consumer price index grow proportionally, so they are modelled on the
logarithm and converted back. The unemployment rate is modelled as it is.

## Scoring: rolling-origin backtest

For each of several past dates (the origins), the method is fitted using only data up to that date,
forecasts twelve months ahead, and is compared with what happened. Training windows hold at most
240 months and at least 60, so old regimes fade out. Three measures are reported:

- **MAE** and **RMSE** at each horizon from one to twelve months, in the series' own units.
- **MASE**: the average absolute error over all horizons divided by the average one-step error of
  the no-change forecast over the recent training window. Below 1 beats no change.
- **vs naive**: the method's error divided by the no-change forecast's error on the same origins.
  This is the number the Forecasts page uses for its plain-language verdict.

## What was chosen, and why

The method for each series was picked from the backtest leaderboards (`evaluate_forecasts`):

| Series | Method | Backtest result on the data loaded in October 2026 |
|---|---|---|
| Unemployment rate | `ets` | About 0.95 of the no-change error: effectively a tie |
| Retail sales | `ets` | About 0.76 of the no-change error |
| Consumer price index | `drift` | About 0.42 of the no-change error (ARIMA was close at 0.44) |

These figures come from the data as loaded at the time and will move as new months arrive and old
months are revised. Run `evaluate_forecasts` to see the current ones.

## Prediction ranges

The shaded band is built from the backtest itself. For each horizon, take the absolute errors the
chosen method made at that horizon across all origins, and use their 80% quantile as the
half-width. Half-widths never narrow as the horizon grows, the band is symmetric around the point
forecast, and it is clipped at zero.

"80%" therefore means: in past backtests, 80% of this method's forecasts at that horizon landed
within this distance of the actual value. No distribution is assumed.

## What the forecasts cannot do

- **They only see one series.** Interest rate decisions, trade shocks, strikes and pandemics are
  invisible until they show up in the data.
- **The backtest is kinder than reality.** Statistics Canada revises past values, and the backtest
  uses today's revised history, not what a forecaster would have had at each date.
- **The method was chosen on the same data it is scored on.** Picking the best of several methods
  from backtests builds in some optimism.
- **The range is empirical, not a guarantee.** With a few dozen origins that overlap, the quantile
  is rough, and a regime change can push actuals outside it.
- **Unemployment is close to a random walk.** The model adds little over assuming no change, which
  is why that page tells you to read the line as "about where it is now" and the band as the
  useful part.

## Reproducing the results

```bash
docker compose run --rm web python manage.py evaluate_forecasts LFS_UNEMPLOYMENT_RATE
docker compose run --rm web python manage.py evaluate_forecasts RETAIL_SALES --origins 12
docker compose run --rm web python manage.py evaluate_forecasts CPI_ALL_ITEMS
docker compose run --rm web python manage.py run_forecasts
```