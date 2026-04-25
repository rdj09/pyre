# src/pyre/data_injector/loader.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Generic, TypeVar

from .adapters.csv_adapter import CSVAdapter
from .adapters.db_adapter import DBAdapter
from .adapters.dict_adapter import DictAdapter
from .adapters.excel_adapter import ExcelAdapter
from .adapters.json_adapter import JSONAdapter
from .adapters.yaml_adapter import YAMLAdapter
from .descriptors import FieldDescriptor
from .injector import Injector
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

    # ── source methods ────────────────────────────────────────────────────────

    def from_json(self, source: str | Path | dict | list) -> list[T]:
        return self._injector.inject_many(JSONAdapter().load(source))

    def from_csv(self, source: str | Path, **csv_kwargs: Any) -> list[T]:
        return self._injector.inject_many(CSVAdapter(**csv_kwargs).load(source))

    def from_yaml(self, source: str | Path) -> list[T]:
        return self._injector.inject_many(YAMLAdapter().load(source))

    def from_excel(self, source: str | Path, sheet_name: str | int = 0) -> list[T]:
        return self._injector.inject_many(ExcelAdapter(sheet_name).load(source))

    def from_dict(self, source: Any) -> list[T]:
        return self._injector.inject_many(DictAdapter().load(source))

    def from_db(self, connection_string: str, query: str) -> list[T]:
        """Load records from a SQL database and inject into T.

        Args:
            connection_string: sqlite:/// or postgresql:// URL.
            query: SQL SELECT statement.
        """
        return self._injector.inject_many(DBAdapter(connection_string).load(query))

    def from_one(self, record: dict[str, Any]) -> T:
        return self._injector.inject(record)
