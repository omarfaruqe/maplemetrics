# Data dictionary

## Sources

| Source | Access | Refresh |
|---|---|---|
| Bank of Canada | Valet JSON API, per series | Incremental from the latest stored date |
| Statistics Canada | Full table download, filtered to chosen dimension values | Full reload, so revisions are picked up |

## Indicators

Geographies: Bank of Canada series are national and stored under `Canada`. Statistics Canada
measures are stored for `Canada` and the ten provinces (the territories are not loaded).

| Code | Source | Frequency | Unit | Geographies | What it is |
|---|---|---|---|---|---|
| `FXUSDCAD` | Bank of Canada | Daily | CAD per USD | Canada | US dollar in Canadian dollars, daily average |
| `V39079` | Bank of Canada | Daily | percent | Canada | Target for the overnight rate (the policy rate) |
| `STATIC_ATABLE_V41690973` | Bank of Canada | Monthly | percent | Canada | Total CPI inflation, year over year |
| `CPI_TRIM` | Bank of Canada | Monthly | percent | Canada | CPI-trim, a core inflation measure |
| `CPI_MEDIAN` | Bank of Canada | Monthly | percent | Canada | CPI-median, a core inflation measure |
| `LFS_UNEMPLOYMENT_RATE` | Statistics Canada, table 14-10-0287 | Monthly | percent | Canada and provinces | Unemployment rate, seasonally adjusted, 15 years and over, both genders |
| `RETAIL_SALES` | Statistics Canada, table 20-10-0056 | Monthly | thousands of CAD | Canada and provinces | Total retail trade sales, seasonally adjusted |
| `CPI_ALL_ITEMS` | Statistics Canada, table 18-10-0004 | Monthly | index (2002=100) | Canada and provinces | Consumer Price Index, all items |

Monthly observations are dated on the first day of the month they describe.

## Tables

### `warehouse.Indicator`

| Field | Type | Meaning |
|---|---|---|
| `code` | text, unique | Stable identifier used everywhere, including the API |
| `source` | `boc` or `statcan` | Where the data comes from |
| `name_en`, `name_fr` | text | Display names in each language |
| `unit` | text | Unit of the values |
| `frequency` | `daily`, `monthly`, `quarterly`, `annual` | How often it is observed |

### `warehouse.Observation`

| Field | Type | Meaning |
|---|---|---|
| `indicator` | foreign key | The series |
| `geography` | text | `Canada` or a province name, in English |
| `date` | date | The day, or first day of the month, observed |
| `value` | decimal(20, 6) | The value, in the indicator's unit |
| `ingested_at` | timestamp | When this row was last written |

Unique on (`indicator`, `geography`, `date`).

### `forecasting.Forecast`

The current forecast for one indicator and geography. Unique on (`indicator`, `geography`).

| Field | Meaning |
|---|---|
| `method` | The forecasting method used (`ets` or `drift` today) |
| `trained_through` | The last month of data the model saw |
| `interval_level` | Coverage of the stored range (0.8) |
| `backtest_origins` | How many past forecast dates the method was scored on |
| `mase` | Backtest error scaled by a naive one-step error; below 1 beats it |
| `vs_naive` | The method's backtest error divided by the no-change forecast's; below 1 is better |
| `updated_at` | When the forecast was last rebuilt |

### `forecasting.ForecastPoint`

One row per forecast month. Unique on (`forecast`, `date`).

| Field | Meaning |
|---|---|
| `date` | The forecast month |
| `value` | The point forecast, in the indicator's unit |
| `lower`, `upper` | The range that past forecasts of this method stayed within, at that horizon |

## API fields

`/api/v1/indicators/` adds `name` (in the language of the request), `observation_count`,
`first_date` and `latest_date`. `/api/v1/observations/` returns `indicator` (the code),
`geography`, `date` and `value` as a number. `/api/v1/forecasts/` returns the forecast fields above
with its `points` nested.