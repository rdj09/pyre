# src/pyre/data_injector/injector.py
from __future__ import annotations

from typing import Any, Generic, TypeVar

from .exceptions import InjectionError
from .schema import Schema

T = TypeVar("T")


class Injector(Generic[T]):
    """Walks a Schema and constructs instances of T from normalised records."""

    def __init__(self, schema: Schema[T]) -> None:
        self._schema = schema

    def inject(self, record: dict[str, Any]) -> T:
        for hook in self._schema.pre_hooks:
            record = hook(record)

        kwargs: dict[str, Any] = {}
        for fd in self._schema.fields:
            if fd.name in self._schema.nested:
                kwargs[fd.name] = self._inject_nested(fd, record)
            else:
                kwargs[fd.name] = fd.get_value(record)

        try:
            instance: T = self._schema.target_class(**kwargs)
        except TypeError as exc:
            raise InjectionError(
                f"Could not construct {self._schema.target_class.__name__}: {exc}"
            ) from exc

        for hook in self._schema.post_hooks:
            instance = hook(instance)

        return instance

    def inject_many(self, records: list[dict[str, Any]]) -> list[T]:
        results: list[T] = []
        errors: list[str] = []
        for i, record in enumerate(records):
            try:
                results.append(self.inject(record))
            except InjectionError as exc:
                errors.append(f"  Record {i}: {exc}")
        if errors:
            raise InjectionError(
                f"Injection failed for {len(errors)} of {len(records)} record(s):\n"
                + "\n".join(errors)
            )
        return results

    def _inject_nested(self, fd: Any, record: dict[str, Any]) -> Any:
        nested_schema = self._schema.nested[fd.name]
        sub = record.get(fd.source_key or fd.name)
        if sub is None:
            return fd._resolve_missing()
        if not isinstance(sub, dict):
            raise InjectionError(
                f"Field '{fd.name}' expected a dict for nested injection, "
                f"got {type(sub).__name__}"
            )
        return Injector(nested_schema).inject(sub)
