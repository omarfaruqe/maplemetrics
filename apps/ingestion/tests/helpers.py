"""Build tiny Statistics Canada style zips for tests."""

import csv
import io
import zipfile
from pathlib import Path

HEADER = [
    "REF_DATE",
    "GEO",
    "DGUID",
    "Labour force characteristics",
    "Gender",
    "UOM",
    "UOM_ID",
    "SCALAR_FACTOR",
    "SCALAR_ID",
    "VECTOR",
    "COORDINATE",
    "VALUE",
    "STATUS",
    "SYMBOL",
    "TERMINATED",
    "DECIMALS",
]


def row(ref_date, geo, characteristic, gender, value):
    return {
        "REF_DATE": ref_date,
        "GEO": geo,
        "DGUID": "x",
        "Labour force characteristics": characteristic,
        "Gender": gender,
        "UOM": "Percent",
        "UOM_ID": "239",
        "SCALAR_FACTOR": "units",
        "SCALAR_ID": "0",
        "VECTOR": "v1",
        "COORDINATE": "1.1",
        "VALUE": value,
        "STATUS": "",
        "SYMBOL": "",
        "TERMINATED": "",
        "DECIMALS": "1",
    }


def make_zip_bytes(rows, table_id="14100287") -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=HEADER)
    writer.writeheader()
    writer.writerows(rows)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        # Statistics Canada files start with a byte order mark; the reader must cope.
        archive.writestr(f"{table_id}.csv", "\ufeff" + buffer.getvalue())
        archive.writestr(f"{table_id}_MetaData.csv", "Cube Title\nsomething\n")
    return out.getvalue()


def make_zip(directory: Path, rows, table_id="14100287") -> Path:
    target = directory / f"{table_id}.zip"
    target.write_bytes(make_zip_bytes(rows, table_id))
    return target
