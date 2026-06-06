"""Triangle Analysis feature — ATA factors and IBNER pattern."""

from __future__ import annotations

from typing import Any

import pandas as pd
from shiny import Inputs, Outputs, Session, reactive, render, ui

from pyre.claims.triangles import Triangle

from ..services.model_service import ModelService


def triangle_ui() -> Any:
    return ui.page_sidebar(
        ui.sidebar(
            ui.h4("Triangle Analysis"),
            ui.p("Load a triangle in the Data Loader tab first.", class_="text-muted small"),
            ui.input_select(
                "tri_ata_method",
                "ATA Method",
                choices=["simple", "volume"],
                selected="volume",
            ),
            ui.input_action_button("tri_run_btn", "Run Analysis", class_="btn-primary w-100 mt-2"),
            ui.hr(),
            ui.output_text("tri_status"),
            width=280,
        ),
        ui.navset_tab(
            ui.nav_panel("Triangle Grid", ui.output_data_frame("tri_grid_table")),
            ui.nav_panel("ATA Factors", ui.output_data_frame("tri_ata_table")),
            ui.nav_panel("IBNER Pattern", ui.output_data_frame("tri_ibner_table")),
        ),
        fillable=True,
    )


def triangle_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    _triangle: reactive.Value[Triangle | None],
) -> None:
    _svc = ModelService()
    _ata: reactive.Value[dict[int, float]] = reactive.Value({})
    _ibner: reactive.Value[dict[int, float | None]] = reactive.Value({})
    _error: reactive.Value[str] = reactive.Value("")

    @reactive.effect
    @reactive.event(input.tri_run_btn)
    def _on_run() -> None:
        _error.set("")
        tri = _triangle.get()
        if tri is None:
            _error.set("No triangle loaded. Use the Data Loader tab first.")
            return
        try:
            ata = tri.get_average_age_to_age_factors(method=input.tri_ata_method())
            _ata.set(ata)
            ibner = _svc.extract_ibner(tri)
            _ibner.set(ibner)
        except Exception as exc:
            _error.set(f"Error: {exc}")

    @render.text
    def tri_status() -> str:
        err = _error.get()
        if err:
            return err
        tri = _triangle.get()
        if tri is None:
            return "No triangle loaded."
        return (
            f"Triangle: {len(tri.origin_years)} origin years x {len(tri.dev_periods)} dev periods."
        )

    @render.data_frame
    def tri_grid_table() -> pd.DataFrame:
        tri = _triangle.get()
        if tri is None:
            return pd.DataFrame()
        rows = []
        for oy in tri.origin_years:
            row: dict[str, Any] = {"origin_year": oy}
            for dp in tri.dev_periods:
                row[f"dev_{dp}"] = tri[oy, dp]
            rows.append(row)
        return pd.DataFrame(rows)

    @render.data_frame
    def tri_ata_table() -> pd.DataFrame:
        ata = _ata.get()
        if not ata:
            return pd.DataFrame()
        return pd.DataFrame([{"dev_period": k, "ata_factor": v} for k, v in sorted(ata.items())])

    @render.data_frame
    def tri_ibner_table() -> pd.DataFrame:
        ibner = _ibner.get()
        if not ibner:
            return pd.DataFrame()
        return pd.DataFrame(
            [{"dev_period": k, "ibner_pattern": v} for k, v in sorted(ibner.items())]
        )
