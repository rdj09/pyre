"""Pricing results page for the treaty pricing workbench."""

from __future__ import annotations

import pandas as pd
import panel as pn

from app.service import run_pricing
from app.state import WorkbenchState


def build_results_page(state: WorkbenchState) -> pn.Column:
    status = pn.pane.Alert(
        "Load data and configure a contract, then run pricing.", alert_type="warning"
    )
    run_button = pn.widgets.Button(name="Run pricing", button_type="primary")
    results_table = pn.widgets.Tabulator(pd.DataFrame(), show_index=False)
    exposures_table = pn.widgets.Tabulator(pd.DataFrame(), show_index=False)

    def _on_run(_event):
        if not state.is_ready_to_price():
            status.object = (
                "Load claims + exposures and configure a contract with at least one layer first."
            )
            status.alert_type = "danger"
            return
        try:
            contract = state.build_contract()
            state.results = run_pricing(state.claims, state.exposures, contract)
            results_table.value = state.results.by_layer_year
            exposures_table.value = state.results.exposures_by_year
            status.object = "Pricing run complete."
            status.alert_type = "success"
        except NotImplementedError as exc:
            status.object = f"Unsupported layer configuration: {exc}"
            status.alert_type = "danger"
        except ValueError as exc:
            status.object = f"Could not run pricing: {exc}"
            status.alert_type = "danger"

    run_button.on_click(_on_run)

    return pn.Column(
        "## Pricing results",
        run_button,
        status,
        "### Ceded loss by layer and modelling year",
        results_table,
        "### Exposures by modelling year",
        exposures_table,
    )
