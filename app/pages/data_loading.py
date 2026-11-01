"""Claims/exposures data loading page for the treaty pricing workbench."""

from __future__ import annotations

import io
from pathlib import Path

import panel as pn

from app.service import (
    CLAIMS_REQUIRED_COLUMNS,
    EXPOSURES_REQUIRED_COLUMNS,
    parse_claims_csv,
    parse_exposures_csv,
)
from app.state import WorkbenchState

DEMO_DIR = Path(__file__).resolve().parent.parent.parent / "examples" / "panel_demo"
DEMO_CLAIMS_CSV = DEMO_DIR / "claims_demo.csv"
DEMO_EXPOSURES_CSV = DEMO_DIR / "exposures_demo.csv"


def build_data_loading_page(state: WorkbenchState) -> pn.Column:
    status = pn.pane.Alert("No data loaded yet.", alert_type="warning")

    claims_file = pn.widgets.FileInput(name="Claims CSV", accept=".csv")
    exposures_file = pn.widgets.FileInput(name="Exposures CSV", accept=".csv")
    load_demo_button = pn.widgets.Button(name="Load demo data", button_type="primary")

    def _refresh_status():
        n_claims = len(state.claims) if state.claims is not None else 0
        n_exposures = len(state.exposures) if state.exposures is not None else 0
        if state.claims is not None and state.exposures is not None:
            status.object = (
                f"Loaded {n_claims} claim(s) and {n_exposures} exposure(s). "
                "Ready to configure a contract."
            )
            status.alert_type = "success"
        elif state.claims is not None:
            status.object = (
                f"Loaded {n_claims} claim(s). Upload an exposures CSV "
                "(or click Load demo data) to continue."
            )
            status.alert_type = "warning"
        else:
            status.object = (
                f"Loaded {n_exposures} exposure(s). Upload a claims CSV "
                "(or click Load demo data) to continue."
            )
            status.alert_type = "warning"

    def _on_claims_upload(_event):
        if claims_file.value is None:
            return
        try:
            state.claims = parse_claims_csv(io.BytesIO(claims_file.value))
            _refresh_status()
        except ValueError as exc:
            status.object = f"Failed to load claims CSV: {exc}"
            status.alert_type = "danger"

    def _on_exposures_upload(_event):
        if exposures_file.value is None:
            return
        try:
            state.exposures = parse_exposures_csv(io.BytesIO(exposures_file.value))
            _refresh_status()
        except ValueError as exc:
            status.object = f"Failed to load exposures CSV: {exc}"
            status.alert_type = "danger"

    def _on_load_demo(_event):
        try:
            state.claims = parse_claims_csv(DEMO_CLAIMS_CSV)
            state.exposures = parse_exposures_csv(DEMO_EXPOSURES_CSV)
            _refresh_status()
        except (ValueError, FileNotFoundError) as exc:
            status.object = f"Failed to load demo data: {exc}"
            status.alert_type = "danger"

    claims_file.param.watch(_on_claims_upload, "value")
    exposures_file.param.watch(_on_exposures_upload, "value")
    load_demo_button.on_click(_on_load_demo)

    return pn.Column(
        "## Load claims and exposures",
        pn.Row(
            pn.Column(
                claims_file,
                pn.pane.Markdown(
                    f"*Required columns: {', '.join(CLAIMS_REQUIRED_COLUMNS)}*",
                    margin=(0, 0, 10, 0),
                    sizing_mode="stretch_width",
                ),
                width=400,
            ),
            pn.Column(
                exposures_file,
                pn.pane.Markdown(
                    f"*Required columns: {', '.join(EXPOSURES_REQUIRED_COLUMNS)}*",
                    margin=(0, 0, 10, 0),
                    sizing_mode="stretch_width",
                ),
                width=400,
            ),
        ),
        load_demo_button,
        status,
    )
