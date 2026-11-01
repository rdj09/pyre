from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO, Sequence

from openpyxl import Workbook, load_workbook


def write_table(
    headers: list[str],
    rows: Sequence[Sequence[Any]],
    path: str | Path | BinaryIO,
    sheet_name: str = "Sheet1",
) -> None:
    """Write one header row + data rows to a sheet in an .xlsx workbook.

    `path` may be a filesystem path (str/Path) or any writable binary stream
    (e.g. io.BytesIO) -- used by the Panel app to serve a download without
    touching disk. If `path` already has content -- an existing file, or a
    stream a previous write_table call already wrote a workbook into -- the
    named sheet is replaced (re-running a report overwrites cleanly, and
    multiple calls on the same stream accumulate sheets) while any other
    existing sheets are preserved. An empty target (a new file, or a fresh
    stream) gets a new workbook.

    Warning: the merge path loads and re-saves the whole workbook via
    openpyxl, which does not round-trip every part of an .xlsx file --
    charts, images, and pivot tables already at `path` will be lost. Point
    these functions at dedicated output files, not at a workbook that
    already has charts/pivots you want to keep.
    """
    target: Path | BinaryIO
    if isinstance(path, (str, Path)):
        target = Path(path)
        has_existing_content = target.exists()
    else:
        target = path
        start = target.tell()
        target.seek(0, 2)
        has_existing_content = target.tell() > 0
        target.seek(start)

    if has_existing_content:
        workbook = load_workbook(target)
        if sheet_name in workbook.sheetnames:
            del workbook[sheet_name]
    else:
        workbook = Workbook()
        workbook.remove(workbook.active)

    worksheet = workbook.create_sheet(sheet_name)
    worksheet.append(headers)
    for row in rows:
        worksheet.append(list(row))

    if not isinstance(target, Path):
        target.seek(0)
        target.truncate()
    workbook.save(target)
