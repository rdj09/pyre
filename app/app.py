# app/app.py
"""pyre Shiny web application entry point."""
from __future__ import annotations

from shiny import App

from app.server import server
from app.ui import ui

app = App(ui, server)
