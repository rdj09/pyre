# src/pyre/data_injector/adapters/yaml_adapter.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..registry import AdapterRegistry


@AdapterRegistry.register("yaml")
class YAMLAdapter:
    def load(self, source: str | Path) -> list[dict[str, Any]]:
        try:
            import yaml
        except ImportError as exc:
            raise ImportError("PyYAML is required for YAML support: pip install pyyaml") from exc
        raw = yaml.safe_load(Path(source).read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            return [raw]
        raise ValueError(f"YAMLAdapter: unexpected root type {type(raw).__name__}")
