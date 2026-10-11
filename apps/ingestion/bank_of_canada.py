"""Client for the Bank of Canada Valet API (free, no API key)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

VALET_URL = "https://www.bankofcanada.ca/valet/observations/{series}/json"


class ValetError(Exception):
    """Raised when the Valet API cannot be reached or returns an error."""


@dataclass(frozen=True)
class Point:
    series: str
    date: date
    value: Decimal


def build_session() -> requests.Session:
    """A session that retries transient failures with backoff."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def parse_observations(payload: dict, series_codes: list[str]) -> list[Point]:
    """Turn a Valet JSON payload into points, skipping missing or non-numeric values."""
    points: list[Point] = []
    for row in payload.get("observations", []):
        observed_on = date.fromisoformat(row["d"])
        for code in series_codes:
            cell = row.get(code)
            if not cell:
                continue
            try:
                value = Decimal(cell["v"])
            except (InvalidOperation, KeyError, TypeError):
                continue
            points.append(Point(series=code, date=observed_on, value=value))
    return points


def fetch_observations(
    series_codes: list[str],
    start_date: date | None = None,
    end_date: date | None = None,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> list[Point]:
    """Fetch observations for one or more series between two optional dates."""
    session = session or build_session()
    params: dict[str, str] = {}
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()
    url = VALET_URL.format(series=",".join(series_codes))
    try:
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ValetError(f"Valet request failed for {series_codes}: {exc}") from exc
    return parse_observations(payload, series_codes)
