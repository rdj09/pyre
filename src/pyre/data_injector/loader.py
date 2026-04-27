# src/pyre/data_injector/loader.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Generic, TypeVar

from .descriptors import FieldDescriptor
from .injector import Injector
from .registry import AdapterRegistry
from .schema import Schema

T = TypeVar("T")


class Loader(Generic[T]):
    """High-level facade: picks the right adapter and runs the injector.

    Typical usage::

        loader = Loader(my_schema)
        instances = loader.from_json("data.json")

    Or for simple dataclasses without nesting::

        loader = Loader.for_class(MyClass)
        instances = loader.from_csv("data.csv")
    """

    def __init__(self, schema: Schema[T]) -> None:
        self._schema = schema
        self._injector = Injector(schema)

    @classmethod
    def for_class(cls, target: type[T], **overrides: FieldDescriptor) -> Loader[T]:
        """Auto-derive schema from a dataclass and return a ready Loader."""
        return cls(Schema.from_dataclass(target, **overrides))

    # ── generic dispatcher ────────────────────────────────────────────────────

    def from_source(self, source_type: str, source: Any, **adapter_kwargs: Any) -> list[T]:
        """Load records using the adapter registered for *source_type*.

        Args:
            source_type: Registered adapter key (e.g. ``"csv"``, ``"json"``).
            source: Passed to ``adapter.load(source)`` — file path, dict, etc.
            **adapter_kwargs: Forwarded to the adapter constructor.
        """
        adapter_cls = AdapterRegistry.get(source_type)
        records = adapter_cls(**adapter_kwargs).load(source)
        return self._injector.inject_many(records)

    # ── named helpers (thin wrappers over from_source) ────────────────────────

    def from_json(self, source: str | Path | dict[str, Any] | list[Any]) -> list[T]:
        return self.from_source("json", source)

    def from_csv(self, source: str | Path, **csv_kwargs: Any) -> list[T]:
        return self.from_source("csv", source, **csv_kwargs)

    def from_yaml(self, source: str | Path) -> list[T]:
        return self.from_source("yaml", source)

    def from_excel(self, source: str | Path, sheet_name: str | int = 0) -> list[T]:
        return self.from_source("excel", source, sheet_name=sheet_name)

    def from_dict(self, source: Any) -> list[T]:
        return self.from_source("dict", source)

    def from_db(self, connection_string: str, query: str) -> list[T]:
        """Load records from a SQL database and inject into T.

        Args:
            connection_string: sqlite:/// or postgresql:// URL.
            query: SQL SELECT statement.
        """
        return self.from_source("db", query, connection_string=connection_string)

    def from_one(self, record: dict[str, Any]) -> T:
        return self._injector.inject(record)
