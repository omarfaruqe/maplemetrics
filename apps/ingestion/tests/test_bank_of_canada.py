from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest
import requests

from apps.ingestion.bank_of_canada import ValetError, fetch_observations, parse_observations

PAYLOAD = {
    "observations": [
        {"d": "2026-10-07", "V39079": {"v": "2.25"}, "FXUSDCAD": {"v": "1.4257"}},
        {"d": "2026-10-05", "V39079": {"v": "2.25"}},
        {"d": "2026-10-08", "FXUSDCAD": {"v": "not-a-number"}},
    ]
}


def test_parse_skips_missing_and_non_numeric_values():
    points = parse_observations(PAYLOAD, ["FXUSDCAD", "V39079"])
    assert [(p.series, p.date, p.value) for p in points] == [
        ("FXUSDCAD", date(2026, 10, 7), Decimal("1.4257")),
        ("V39079", date(2026, 10, 7), Decimal("2.25")),
        ("V39079", date(2026, 10, 5), Decimal("2.25")),
    ]


def test_fetch_sends_dates_and_returns_points():
    session = Mock()
    session.get.return_value.json.return_value = PAYLOAD
    points = fetch_observations(
        ["FXUSDCAD", "V39079"], start_date=date(2026, 10, 1), session=session
    )
    assert len(points) == 3
    args, kwargs = session.get.call_args
    assert args[0].endswith("/FXUSDCAD,V39079/json")
    assert kwargs["params"] == {"start_date": "2026-10-01"}


def test_fetch_wraps_http_errors():
    session = Mock()
    session.get.side_effect = requests.ConnectionError("boom")
    with pytest.raises(ValetError):
        fetch_observations(["FXUSDCAD"], session=session)
