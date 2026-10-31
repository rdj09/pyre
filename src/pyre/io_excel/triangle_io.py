from __future__ import annotations

from pathlib import Path

from ..claims.triangles import Triangle
from ._workbook import write_table


def write_triangle(triangle: Triangle, path: str | Path, sheet_name: str = "Triangle") -> None:
    """Write a Triangle's origin-year x dev-period grid to one sheet of an .xlsx workbook.

    Missing (origin_year, dev_period) combinations -- no claim data at that
    point -- are left as blank cells.
    """
    headers = ["origin_year"] + [str(period) for period in triangle.dev_periods]

    rows = []
    for year in triangle.origin_years:
        row: list = [year]
        for period in triangle.dev_periods:
            row.append(triangle.triangle.get(year, {}).get(period))
        rows.append(row)

    write_table(headers=headers, rows=rows, path=path, sheet_name=sheet_name)
