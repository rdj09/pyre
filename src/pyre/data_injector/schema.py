# src/pyre/data_injector/schema.py
from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from .descriptors import FieldDescriptor

T = TypeVar("T")


@dataclasses.dataclass
class Schema(Generic[T]):
    """Describes how a normalised dict maps onto target class T.

    Attributes:
        target_class: The class to construct.
        fields:       Ordered list of field descriptors.
        nested:       Maps attribute name -> Schema for nested objects.
        pre_hooks:    Transform the raw record before field extraction.
        post_hooks:   Transform the constructed instance before returning.
    """

    target_class: type[T]
    fields: list[FieldDescriptor]
    nested: dict[str, Schema[Any]] = dataclasses.field(default_factory=dict)
    pre_hooks: list[Callable[[dict[str, Any]], dict[str, Any]]] = dataclasses.field(
        default_factory=list
    )
    post_hooks: list[Callable[[T], T]] = dataclasses.field(default_factory=list)

    @classmethod
    def from_dataclass(cls, dc: type[T], **overrides: FieldDescriptor) -> Schema[T]:
        """Auto-derive a Schema from a dataclass's declared fields.

        Pass keyword arguments named after fields to supply custom
        FieldDescriptors that override the auto-derived ones.
        """
        if not dataclasses.is_dataclass(dc):
            raise TypeError(f"{dc!r} is not a dataclass")

        fields: list[FieldDescriptor] = []
        for f in dataclasses.fields(dc):
            if f.name in overrides:
                fields.append(overrides[f.name])
                continue

            has_default = f.default is not dataclasses.MISSING
            has_factory = f.default_factory is not dataclasses.MISSING

            # Build kwargs — omit 'default' entirely when there is none,
            # so FieldDescriptor's _UNSET sentinel applies automatically.
            fd_kwargs: dict[str, Any] = {
                "name": f.name,
                "required": not has_default and not has_factory,
            }
            if has_default:
                fd_kwargs["default"] = f.default
            if has_factory:
                fd_kwargs["default_factory"] = f.default_factory

            fields.append(FieldDescriptor(**fd_kwargs))
        return cls(target_class=dc, fields=fields)
