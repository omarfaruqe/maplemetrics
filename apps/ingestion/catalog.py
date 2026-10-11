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
