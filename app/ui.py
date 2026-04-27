# app/ui.py
"""Shiny UI — page_navbar with 7 feature tabs."""
from __future__ import annotations

from shiny import ui as _ui

from .features.contract_module import contract_ui
from .features.data_loader_module import data_loader_ui
from .features.experience_module import experience_ui
from .features.exposure_module import exposure_ui
from .features.rate_module import rate_ui
from .features.simulation_module import simulation_ui
from .features.triangle_module import triangle_ui

ui = _ui.page_navbar(
    _ui.nav_panel("Data Loader", data_loader_ui()),
    _ui.nav_panel("Triangle Analysis", triangle_ui()),
    _ui.nav_panel("Contract Builder", contract_ui()),
    _ui.nav_panel("Experience Pricing", experience_ui()),
    _ui.nav_panel("Exposure Rating", exposure_ui()),
    _ui.nav_panel("Rate Monitoring", rate_ui()),
    _ui.nav_panel("Simulation", simulation_ui()),
    title="pyre — Actuarial Pricing Tool",
    fillable=True,
)
