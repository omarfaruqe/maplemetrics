"""CSV responses that open correctly in Excel and cannot be turned into spreadsheet formulas.

Files always use English column names, ISO dates and a dot for decimals, whatever language the
site is shown in, so a script or a spreadsheet reads them the same way every time.
"""

import csv
from collections.abc import Iterable, Sequence

from django.http import HttpResponse

STATCAN = "Statistics Canada; Open Government Licence - Canada"
BANK_OF_CANADA = "Bank of Canada; Open Government Licence - Canada"
BOTH = "Bank of Canada and Statistics Canada; Open Government Licence - Canada"

_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def cell(value: object) -> str:
    """One CSV cell: four decimals at most, and text that could run as a formula is quoted."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{round(value, 4):.4f}".rstrip("0").rstrip(".") or "0"
    if isinstance(value, int):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value)
    return "'" + text if text.startswith(_FORMULA_STARTS) else text


def csv_response(filename: str, header: Sequence[str], rows: Iterable[Sequence[object]]):
    """A download. The byte order mark lets Excel read accents; the name is plain ASCII."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")
    writer = csv.writer(response)
    writer.writerow(header)
    for row in rows:
        writer.writerow([cell(value) for value in row])
    return response
