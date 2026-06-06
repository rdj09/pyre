# tests/test_app/test_app_structure.py
from __future__ import annotations

import pytest

pytest.importorskip("shiny", reason="shiny not installed; run: uv sync --group webapp")
pytest.importorskip("pandas", reason="pandas not installed; run: uv sync --group webapp")


class TestAppImports:
    def test_app_module_imports(self) -> None:
        from app.app import app  # noqa: F401

        assert app is not None

    def test_ui_module_imports(self) -> None:
        from app.ui import ui  # noqa: F401

        assert ui is not None

    def test_server_module_imports(self) -> None:
        from app import server  # noqa: F401

        assert server is not None

    def test_domain_service_imports(self) -> None:
        from app.services.domain_service import DomainService

        assert DomainService is not None

    def test_app_is_shiny_app(self) -> None:
        from shiny import App

        from app.app import app

        assert isinstance(app, App)
