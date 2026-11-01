"""Pricing results page for the treaty pricing workbench."""

from __future__ import annotations

import pandas as pd
import panel as pn
from bokeh.models.widgets.tables import NumberFormatter

from app.service import run_pricing
from app.state import WorkbenchState

AMOUNT = NumberFormatter(format="0,0", text_align="right")
TITLES = {
    "layer_id": "Layer ID",
    "layer_name": "Layer",
    "modelling_year": "Modelling year",
    "ceded_paid": "Ceded paid",
    "ceded_incurred": "Ceded incurred",
    "claim_count": "Claims",
    "earned_premium": "Earned premium",
    "loss_ratio": "Loss ratio",
    "written": "Written",
    "earned": "Earned",
}
FORMATTERS = {
    "modelling_year": NumberFormatter(format="0"),
    "ceded_paid": AMOUNT,
    "ceded_incurred": AMOUNT,
    "claim_count": NumberFormatter(format="0", text_align="right"),
    "earned_premium": AMOUNT,
    "loss_ratio": NumberFormatter(format="0.0%", text_align="right"),
    "written": AMOUNT,
    "earned": AMOUNT,
}


def build_results_page(state: WorkbenchState) -> pn.Column:
    status = pn.pane.Alert(
        "Load data and configure a contract, then run pricing.", alert_type="warning"
    )
    run_button = pn.widgets.Button(name="Run pricing", button_type="primary")
    results_table = pn.widgets.Tabulator(
        pd.DataFrame(), show_index=False, disabled=True, titles=TITLES, formatters=FORMATTERS
    )
    exposures_table = pn.widgets.Tabulator(
        pd.DataFrame(), show_index=False, disabled=True, titles=TITLES, formatters=FORMATTERS
    )

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
            status.object = "Pricing run complete. See the tables below."
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
