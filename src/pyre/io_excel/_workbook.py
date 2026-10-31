from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from openpyxl import Workbook, load_workbook


def write_table(
    headers: list[str],
    rows: list[Sequence[Any]],
    path: str | Path,
    sheet_name: str = "Sheet1",
) -> None:
    """Write one header row + data rows to a sheet in an .xlsx workbook.

    If `path` already exists, the named sheet is replaced (re-running a
    report overwrites cleanly) while any other existing sheets in the
    workbook are preserved -- this is how write_experience_rating_results
    puts two sheets in one file via two calls to this function.
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
