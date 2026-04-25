# app/ui.py
"""Shiny UI layout for the pyre data loader web application."""

from __future__ import annotations

from shiny import ui as _ui

ui = _ui.page_sidebar(
    _ui.sidebar(
        _ui.h4("Data Loader"),
        _ui.input_file(
            "file_upload",
            "Upload File",
            accept=[".csv", ".xlsx", ".json", ".yaml", ".yml"],
            multiple=False,
        ),
        _ui.input_select(
            "source_type",
            "Data Source Type",
            choices=["csv", "excel", "json", "yaml", "db"],
            selected="csv",
        ),
        _ui.input_select(
            "domain_type",
            "Domain Object Type",
            choices=["Exposure", "Claim", "Triangle"],
            selected="Exposure",
        ),
        _ui.panel_conditional(
            "input.source_type === 'db'",
            _ui.input_text(
                "db_connection_string",
                "DB Connection String",
                placeholder="sqlite:///path/to/file.db",
            ),
            _ui.input_text_area(
                "db_query",
                "SQL Query",
                placeholder="SELECT * FROM exposures",
                rows=3,
            ),
        ),
        _ui.input_action_button("load_btn", "Load Data", class_="btn-primary w-100 mt-2"),
        _ui.hr(),
        _ui.output_text("status_message"),
        width=320,
    ),
    _ui.navset_tab(
        _ui.nav_panel(
            "Data Preview",
            _ui.output_data_frame("raw_records_table"),
        ),
        _ui.nav_panel(
            "Domain Objects",
            _ui.output_data_frame("domain_objects_table"),
        ),
        _ui.nav_panel(
            "Summary Statistics",
            _ui.output_ui("summary_ui"),
        ),
    ),
    title="pyre — Actuarial Data Loader",
    fillable=True,
)
