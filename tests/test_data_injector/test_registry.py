# tests/test_data_injector/test_registry.py
from typing import Any

import pytest

from pyre.data_injector.registry import AdapterRegistry


class TestAdapterRegistry:
    def setup_method(self) -> None:
        # Clear any registrations from previous tests
        AdapterRegistry._adapters.clear()

    def test_register_and_retrieve(self):
        @AdapterRegistry.register("custom")
        class CustomAdapter:
            def load(self, source: Any) -> list[dict[str, Any]]:
                return [{"from": "custom"}]

        cls = AdapterRegistry.get("custom")
        assert cls is CustomAdapter

    def test_get_unknown_raises_key_error(self):
        with pytest.raises(KeyError, match="No adapter registered for 'parquet'"):
            AdapterRegistry.get("parquet")

    def test_available_lists_registered_names(self):
        @AdapterRegistry.register("alpha")
        class A:
            def load(self, source: Any) -> list[dict[str, Any]]:
                return []

        @AdapterRegistry.register("beta")
        class B:
            def load(self, source: Any) -> list[dict[str, Any]]:
                return []

        assert AdapterRegistry.available() == ["alpha", "beta"]

    def test_register_decorator_returns_class_unchanged(self):
        @AdapterRegistry.register("passthrough")
        class PT:
            def load(self, source: Any) -> list[dict[str, Any]]:
                return []

        assert PT.__name__ == "PT"
