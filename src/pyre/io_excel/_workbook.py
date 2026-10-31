from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from openpyxl import Workbook, load_workbook


def write_table(
    headers: list[str],
    rows: Sequence[Sequence[Any]],
    path: str | Path,
    sheet_name: str = "Sheet1",
) -> None:
    """Write one header row + data rows to a sheet in an .xlsx workbook.

    If `path` already exists, the named sheet is replaced (re-running a
    report overwrites cleanly) while any other existing sheets in the
    workbook are preserved -- this is how write_experience_rating_results
    puts two sheets in one file via two calls to this function.

    Warning: this loads and re-saves the whole workbook at `path` via
    openpyxl, which does not round-trip every part of an .xlsx file --
    charts, images, and pivot tables in an existing file at `path` will be
    lost. Point these functions at dedicated output files, not at a
    workbook that already has charts/pivots you want to keep.
    """
    path = Path(path)

    if path.exists():
        workbook = load_workbook(path)
        if sheet_name in workbook.sheetnames:
            del workbook[sheet_name]
    else:
        workbook = Workbook()
        workbook.remove(workbook.active)

    worksheet = workbook.create_sheet(sheet_name)
    worksheet.append(headers)
    for row in rows:
        worksheet.append(list(row))

    workbook.save(path)
