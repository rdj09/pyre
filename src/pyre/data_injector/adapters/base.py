# src/pyre/data_injector/adapters/base.py
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SourceAdapter(Protocol):
    """All adapters satisfy this protocol — no inheritance required."""

    def load(self, source: Any) -> list[dict[str, Any]]:
        """Return a normalised list of records from the source."""
        ...
