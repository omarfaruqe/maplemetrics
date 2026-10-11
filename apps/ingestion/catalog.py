"""The series we ingest, with bilingual names for the EN/FR interface."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SeriesSpec:
    code: str
    name_en: str
    name_fr: str
    unit: str
    frequency: str


BOC_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec(
        code="FXUSDCAD",
        name_en="US dollar in Canadian dollars (daily average)",
        name_fr="Dollar américain en dollars canadiens (moyenne quotidienne)",
        unit="CAD per USD",
        frequency="daily",
    ),
    SeriesSpec(
        code="V39079",
        name_en="Target for the overnight rate (policy rate)",
        name_fr="Cible du taux du financement à un jour (taux directeur)",
        unit="percent",
        frequency="daily",
    ),
    SeriesSpec(
        code="STATIC_ATABLE_V41690973",
        name_en="Total CPI inflation, year over year",
        name_fr="Inflation de l'IPC total, sur douze mois",
        unit="percent",
        frequency="monthly",
    ),
    SeriesSpec(
        code="CPI_TRIM",
        name_en="CPI-trim (core inflation)",
        name_fr="IPC-tronq (inflation de base)",
        unit="percent",
        frequency="monthly",
    ),
    SeriesSpec(
        code="CPI_MEDIAN",
        name_en="CPI-median (core inflation)",
        name_fr="IPC-méd (inflation de base)",
        unit="percent",
        frequency="monthly",
    ),
)


@dataclass(frozen=True)
class StatCanMeasure(SeriesSpec):
    """A Statistics Canada table slice: one table plus the dimension values that pick the series."""

    table_id: str  # eight digits, for example "14100287"
    value_filters: tuple[tuple[str, str], ...]  # (column name, exact value) pairs


# National figure plus the ten provinces, spelled as Statistics Canada spells them in GEO.
STATCAN_GEOGRAPHIES: tuple[str, ...] = (
    "Canada",
    "Newfoundland and Labrador",
    "Prince Edward Island",
    "Nova Scotia",
    "New Brunswick",
    "Quebec",
    "Ontario",
    "Manitoba",
    "Saskatchewan",
    "Alberta",
    "British Columbia",
)

STATCAN_MEASURES: tuple[StatCanMeasure, ...] = (
    StatCanMeasure(
        code="LFS_UNEMPLOYMENT_RATE",
        name_en="Unemployment rate (seasonally adjusted, 15 years and over)",
        name_fr="Taux de chômage (désaisonnalisé, 15 ans et plus)",
        unit="percent",
        frequency="monthly",
        table_id="14100287",
        value_filters=(
            ("Labour force characteristics", "Unemployment rate"),
            ("Gender", "Total - Gender"),
            ("Age group", "15 years and over"),
            ("Statistics", "Estimate"),
            ("Data type", "Seasonally adjusted"),
        ),
    ),
    StatCanMeasure(
        code="RETAIL_SALES",
        name_en="Retail trade sales (seasonally adjusted)",
        name_fr="Ventes du commerce de détail (désaisonnalisées)",
        unit="thousands of CAD",
        frequency="monthly",
        table_id="20100056",
        value_filters=(
            ("North American Industry Classification System (NAICS)", "Retail trade [44-45]"),
            ("Sales", "Total retail sales"),
            ("Adjustments", "Seasonally adjusted"),
        ),
    ),
    StatCanMeasure(
        code="CPI_ALL_ITEMS",
        name_en="Consumer Price Index, all items (2002=100)",
        name_fr="Indice des prix à la consommation, ensemble (2002=100)",
        unit="index (2002=100)",
        frequency="monthly",
        table_id="18100004",
        value_filters=(("Products and product groups", "All-items"),),
    ),
)
