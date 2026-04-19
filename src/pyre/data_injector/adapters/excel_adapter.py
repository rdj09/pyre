# src/pyre/data_injector/adapters/excel_adapter.py
from __future__ import annotations

from pathlib import Path
from typing import Any


class ExcelAdapter:
    def __init__(self, sheet_name: str | int = 0) -> None:
        self._sheet_name = sheet_name

    def load(self, source: str | Path) -> list[dict[str, Any]]:
        try:
            import openpyxl
        except ImportError as exc:
            raise ImportError(
                "openpyxl is required for Excel support: pip install openpyxl"
            ) from exc
        wb = openpyxl.load_workbook(source, read_only=True, data_only=True)
        ws = (
            wb.worksheets[self._sheet_name]
            if isinstance(self._sheet_name, int)
            else wb[self._sheet_name]
        )
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [
            str(h) if h is not None else f"col_{i}"
            for i, h in enumerate(rows[0])
        ]
        return [dict(zip(headers, row)) for row in rows[1:]]
