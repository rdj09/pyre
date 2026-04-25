# src/pyre/data_injector/registry.py
from __future__ import annotations

from collections.abc import Callable


class AdapterRegistry:
    """Class-level registry for third-party and user-defined adapters.

    Usage::

        @AdapterRegistry.register("parquet")
        class ParquetAdapter:
            def load(self, source): ...

        cls = AdapterRegistry.get("parquet")
        records = cls().load("data.parquet")
    """

    _adapters: dict[str, type] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[type], type]:
        def decorator(adapter_cls: type) -> type:
            cls._adapters[name] = adapter_cls
            return adapter_cls

        return decorator

    @classmethod
    def get(cls, name: str) -> type:
        if name not in cls._adapters:
            available = ", ".join(sorted(cls._adapters)) or "(none)"
            raise KeyError(f"No adapter registered for '{name}'. Available: {available}")
        return cls._adapters[name]

    @classmethod
    def available(cls) -> list[str]:
        return sorted(cls._adapters)
