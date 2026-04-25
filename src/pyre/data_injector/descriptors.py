# src/pyre/data_injector/descriptors.py
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .exceptions import InjectionError

_UNSET: Any = object()  # sentinel distinct from None and dataclasses.MISSING


@dataclass
class FieldDescriptor:
    """Declares how one field is sourced, coerced, and validated.

    Attributes:
        name:            Target class attribute name.
        source_key:      Key in the raw record (defaults to name).
        type_coerce:     Type or callable to convert the raw value.
        required:        Raise if missing and no default is set.
        default:         Static fallback value.
        default_factory: Callable producing a fresh default each time.
        validator:       Called with the final value; raise to reject.
        pre_process:     Transforms the raw value before coercion.
    """

    name: str
    source_key: str | None = None
    type_coerce: type | Callable[[Any], Any] | None = None
    required: bool = True
    default: Any = field(default_factory=lambda: _UNSET)
    default_factory: Callable[[], Any] | None = None
    validator: Callable[[Any], None] | None = None
    pre_process: Callable[[Any], Any] | None = None

    def __post_init__(self) -> None:
        if self.source_key is None:
            self.source_key = self.name

    def get_value(self, record: dict[str, Any]) -> Any:
        raw = record.get(self.source_key)  # type: ignore[arg-type]
        if raw is None:
            return self._resolve_missing()
        return self._transform(raw)

    def _resolve_missing(self) -> Any:
        if self.default_factory is not None:
            return self.default_factory()
        if self.default is not _UNSET:
            return self.default
        if not self.required:
            return None
        raise InjectionError(
            f"Required field '{self.name}' (source key: '{self.source_key}') "
            f"is absent in the record."
        )

    def _transform(self, value: Any) -> Any:
        if self.pre_process is not None:
            value = self.pre_process(value)

        if self.type_coerce is not None:
            already_correct = isinstance(self.type_coerce, type) and isinstance(
                value, self.type_coerce
            )
            if not already_correct:
                try:
                    value = self.type_coerce(value)
                except (ValueError, TypeError) as exc:
                    raise InjectionError(
                        f"Field '{self.name}': cannot coerce {value!r} "
                        f"using {self.type_coerce}: {exc}"
                    ) from exc

        if self.validator is not None:
            try:
                self.validator(value)
            except (ValueError, AssertionError) as exc:
                raise InjectionError(f"Field '{self.name}' failed validation: {exc}") from exc

        return value
