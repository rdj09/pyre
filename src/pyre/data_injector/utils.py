# src/pyre/data_injector/utils.py
from __future__ import annotations

from collections.abc import Callable
from typing import Any


def unflatten(record: dict[str, Any], separator: str = ".") -> dict[str, Any]:
    """Expand dot-notation keys into nested dicts.

    {'address.city': 'London'} -> {'address': {'city': 'London'}}
    """
    result: dict[str, Any] = {}
    for key, value in record.items():
        parts = key.split(separator)
        node = result
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return result


def parse_bool(value: Any) -> bool:
    """Coerce common string representations to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalised = value.strip().lower()
        if normalised in {"true", "yes", "1"}:
            return True
        if normalised in {"false", "no", "0"}:
            return False
    raise ValueError(f"Cannot parse {value!r} as bool")


def underscore_to_dotted(
    record: dict[str, Any], prefixes: tuple[str, ...]
) -> dict[str, Any]:
    """Convert underscore-namespaced DB column names to dot-notation.

    Example: ``exposure_meta_exposure_id`` with prefix ``"exposure_meta_"``
    becomes ``exposure_meta.exposure_id``, ready for :func:`unflatten`.
    """
    result: dict[str, Any] = {}
    for key, value in record.items():
        for prefix in prefixes:
            if key.startswith(prefix):
                namespace = prefix.rstrip("_")
                result[f"{namespace}.{key[len(prefix):]}"] = value
                break
        else:
            result[key] = value
    return result


def parse_list(sep: str = ",") -> Callable[[Any], list[str]]:
    """Return a callable that splits a string on *sep* into a stripped list."""

    def _parse(value: Any) -> list[str]:
        if isinstance(value, list):
            return value
        return [v.strip() for v in str(value).split(sep)]

    return _parse
