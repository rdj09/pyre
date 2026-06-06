# app/app.py
"""pyre Shiny web application entry point."""

from __future__ import annotations

from shiny import App

from .server import server
from .ui import ui

app = App(ui, server)
