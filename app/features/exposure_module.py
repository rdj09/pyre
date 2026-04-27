# app/features/exposure_module.py
"""Exposure Rating feature — MBBEFD / Mixed Exponential curve-based rating."""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from shiny import Inputs, Outputs, Session, reactive, render, ui

from ..services.model_service import ModelService
from pyre.exposures.exposures import Exposures
from pyre.treaty.contracts import RIContract


def exposure_ui() -> Any:
    return ui.page_sidebar(
        ui.sidebar(
            ui.h4("Exposure Rating"),
            ui.p("Load Exposures and build a Contract first.", class_="text-muted small"),
            ui.input_select(
                "expm_curve_type",
                "Exposure Curve",
                choices=["MBBEFD", "MIXED_EXPONENTIAL", "RIEBESELL"],
                selected="MBBEFD",
            ),
            ui.output_ui("expm_curve_params_ui"),
            ui.input_date("expm_analysis_date", "Analysis Date", value=str(date.today())),
            ui.input_action_button("expm_run_btn", "Run Exposure Rate", class_="btn-primary w-100 mt-2"),
            ui.hr(),
            ui.output_text("expm_status"),
            width=280,
        ),
        ui.navset_tab(
            ui.nav_panel("Rate Results", ui.output_data_frame("expm_results_table")),
            ui.nav_panel("Rate Chart", ui.output_plot("expm_rate_plot")),
        ),
        fillable=True,
    )


def exposure_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    _exposures: reactive.Value[Exposures | None],
    _contract: reactive.Value[RIContract | None],
) -> None:
    _svc = ModelService()
    _results: reactive.Value[dict[int, float]] = reactive.Value({})
    _error: reactive.Value[str] = reactive.Value("")

    @render.ui
    def expm_curve_params_ui() -> Any:
        curve = input.expm_curve_type()
        if curve == "MBBEFD":
            return ui.div(
                ui.input_numeric("expm_mbbefd_b", "b parameter", value=4.0, step=0.1),
                ui.input_numeric("expm_mbbefd_g", "g parameter", value=0.3, step=0.01),
            )
        if curve == "MIXED_EXPONENTIAL":
            return ui.div(
                ui.input_numeric("expm_me_alpha", "alpha", value=0.5, min=0, max=1, step=0.01),
                ui.input_numeric("expm_me_theta1", "theta1", value=100000, step=1000),
                ui.input_numeric("expm_me_theta2", "theta2", value=1000000, step=10000),
            )
        return ui.div(
            ui.input_numeric("expm_riebesell_c", "c parameter", value=0.5, step=0.01),
        )

    @reactive.effect
    @reactive.event(input.expm_run_btn)
    def _on_run() -> None:
        _error.set("")
        exposures = _exposures.get()
        contract = _contract.get()
        if exposures is None:
            _error.set("No exposures loaded. Use the Data Loader tab.")
            return
        if contract is None:
            _error.set("No contract built. Use the Contract Builder tab.")
            return
        try:
            curve = input.expm_curve_type()
            if curve == "MBBEFD":
                params: dict[str, Any] = {
                    "b": float(input.expm_mbbefd_b()),
                    "g": float(input.expm_mbbefd_g()),
                }
            elif curve == "MIXED_EXPONENTIAL":
                params = {
                    "alpha": float(input.expm_me_alpha()),
                    "theta1": float(input.expm_me_theta1()),
                    "theta2": float(input.expm_me_theta2()),
                }
            else:
                params = {"c": float(input.expm_riebesell_c())}

            model = _svc.build_exposure_model(
                exposures=exposures,
                contract=contract,
                curve_type_str=curve,
                curve_params=params,
            )
            analysis_date = date.fromisoformat(str(input.expm_analysis_date()))
            results = _svc.run_exposure_rate(model, analysis_date)
            _results.set(results)
        except Exception as exc:
            _error.set(f"Error: {exc}")

    @render.text
    def expm_status() -> str:
        err = _error.get()
        if err:
            return err
        r = _results.get()
        if not r:
            return "Ready. Configure curve and click Run Exposure Rate."
        return f"Exposure rating complete — {len(r)} layer(s)."

    @render.data_frame
    def expm_results_table() -> pd.DataFrame:
        r = _results.get()
        if not r:
            return pd.DataFrame()
        return pd.DataFrame([
            {"layer_id": lid, "exposure_rate": rate} for lid, rate in sorted(r.items())
        ])

    @render.plot
    def expm_rate_plot() -> Any:
        import matplotlib.pyplot as plt
        r = _results.get()
        if not r:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            return fig
        fig, ax = plt.subplots(figsize=(6, 4))
        layer_ids = [str(lid) for lid in sorted(r.keys())]
        rates = [r[lid] for lid in sorted(r.keys())]
        ax.bar(layer_ids, rates, color="steelblue")
        ax.set_xlabel("Layer ID")
        ax.set_ylabel("Exposure Rate")
        ax.set_title("Exposure Rate by Layer")
        fig.tight_layout()
        return fig
