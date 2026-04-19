# src/pyre/data_injector/adapters/csv_adapter.py
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


class CSVAdapter:
    def __init__(self, delimiter: str = ",", encoding: str = "utf-8") -> None:
        self._delimiter = delimiter
        self._encoding = encoding

    def load(self, source: str | Path) -> list[dict[str, Any]]:
        path = Path(source)
        with path.open(newline="", encoding=self._encoding) as fh:
            reader = csv.DictReader(fh, delimiter=self._delimiter)
            if reader.fieldnames is None:
                return []
            return [dict(row) for row in reader]
