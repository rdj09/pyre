# src/pyre/data_injector/adapters/dict_adapter.py
from __future__ import annotations

import dataclasses
from typing import Any


class DictAdapter:
    """Accepts dicts, lists, dataclass instances, or objects with __dict__."""

    def load(self, source: Any) -> list[dict[str, Any]]:
        if isinstance(source, list):
            return [self._to_dict(item) for item in source]
        return [self._to_dict(source)]

    @staticmethod
    def _to_dict(obj: Any) -> dict[str, Any]:
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "__dict__"):
            return vars(obj)
        raise TypeError(f"DictAdapter: cannot convert {type(obj).__name__} to dict")
