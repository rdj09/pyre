# src/pyre/data_injector/adapters/json_adapter.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JSONAdapter:
    def load(self, source: str | Path | dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
        if isinstance(source, (str, Path)):
            raw = json.loads(Path(source).read_text(encoding="utf-8"))
        else:
            raw = source
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            return [raw]
        raise ValueError(f"JSONAdapter: expected dict or list at root, got {type(raw).__name__}")
