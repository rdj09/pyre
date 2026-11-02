"""Pricing results page for the treaty pricing workbench."""

from __future__ import annotations

import io
from typing import Callable, Optional

import pandas as pd
import panel as pn
from bokeh.models.widgets.tables import NumberFormatter

from app.db import (
    DB_PATH,
    IncompatibleSnapshotError,
    ModelSnapshot,
    load_version,
    save_results,
    save_version,
)
from app.service import run_pricing
from app.state import WorkbenchState
from pyre import Claims, ExperienceModelData, Exposures, RIContract
from pyre.io_excel import write_experience_rating_results
from pyre.io_excel._workbook import write_table
from pyre.io_excel.results_io import BY_LAYER_YEAR_COLUMNS
from pyre.models.Experience.experience_preparer import (
    summarize_by_layer_year,
    summarize_exposures_by_year,
)

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


def build_results_page(
    state: WorkbenchState, on_save: Optional[Callable[[], None]] = None
) -> pn.Column:
    status = pn.pane.Alert(
        "Load data and configure a contract, then run pricing.", alert_type="warning"
    )
    run_button = pn.widgets.Button(name="Run pricing", button_type="primary")
    version_label_input = pn.widgets.TextInput(name="Version label", value="")
    save_version_button = pn.widgets.Button(name="Save Version", button_type="default")
    recalculate_button = pn.widgets.Button(
        name="Recalculate",
        button_type="default",
        visible=state.loaded_version_id is not None,
    )
    results_table = pn.widgets.Tabulator(
        pd.DataFrame(), show_index=False, disabled=True, titles=TITLES, formatters=FORMATTERS
    )
    exposures_table = pn.widgets.Tabulator(
        pd.DataFrame(), show_index=False, disabled=True, titles=TITLES, formatters=FORMATTERS
    )

    # A version loaded elsewhere (the Saved Models tab) sets state.results
    # from its cached rows before this page is (re)built -- show them
    # immediately rather than the tables/status staying at their
    # never-run-yet defaults until the next click.
    if state.results is not None:
        results_table.value = state.results.by_layer_year
        exposures_table.value = state.results.exposures_by_year
        status.object = f"Showing cached results for loaded version #{state.loaded_version_id}."
        status.alert_type = "success"

    # Holds the ExperienceModelData from the last *successful* run, so a
    # click on "Export to Excel" always reflects the run that produced the
    # tables on screen -- never whatever is currently (possibly unsaved, or
    # since-changed) sitting in state.
    last_run_model_data: list[ExperienceModelData] = []

    def _export_results() -> io.BytesIO:
        buffer = io.BytesIO()
        # A loaded cached version with no live run this session exports
        # straight from its saved rows; a live run this session (whether or
        # not a version is also loaded) always reflects what's on screen.
        if state.loaded_version_id is not None and not last_run_model_data:
            try:
                _snapshot, by_layer_year, exposures_by_year = load_version(
                    DB_PATH, state.loaded_version_id
                )
            except IncompatibleSnapshotError as exc:
                status.object = str(exc)
                status.alert_type = "danger"
                return io.BytesIO(b"")
            write_table(
                headers=BY_LAYER_YEAR_COLUMNS,
                rows=[[row[col] for col in BY_LAYER_YEAR_COLUMNS] for row in by_layer_year],
                path=buffer,
                sheet_name="ByLayerYear",
            )
            write_table(
                headers=["modelling_year", "written", "earned"],
                rows=[
                    [row["modelling_year"], row["written"], row["earned"]]
                    for row in exposures_by_year
                ],
                path=buffer,
                sheet_name="ExposuresByYear",
            )
        else:
            write_experience_rating_results(last_run_model_data[0], buffer)
        buffer.seek(0)
        return buffer

    export_button = pn.widgets.FileDownload(
        label="Export to Excel",
        filename="pricing_results.xlsx",
        callback=_export_results,
        button_type="default",
        # Visible up front only when a cached version with actual results is
        # already loaded (e.g. on (re)building this page after loading one
        # elsewhere) -- a loaded *draft* (no results) has nothing to export.
        # A run/recalculate/save re-asserts this on success and clears it up
        # front on failure, same as before.
        visible=state.loaded_version_id is not None and state.results is not None,
    )

    def _run_pricing_and_refresh(
        claims: Claims, exposures: Exposures, contract: RIContract
    ) -> ExperienceModelData | None:
        """Runs pricing against the given inputs and refreshes the on-screen tables.

        Shared by "Run pricing" (live state) and "Recalculate" (the loaded
        version's own stored inputs, never live state -- see
        `_on_recalculate`) -- both need identical construction and error
        handling, just a different input source. Returns the
        ExperienceModelData used on success, or None on pricing failure
        (status has already been set).
        """
        try:
            model_data = ExperienceModelData(
                claims=claims, exposures=exposures, ri_contract=contract
            )
            state.results = run_pricing(claims, exposures, contract)
            results_table.value = state.results.by_layer_year
            exposures_table.value = state.results.exposures_by_year
            return model_data
        except NotImplementedError as exc:
            status.object = f"Unsupported layer configuration: {exc}"
            status.alert_type = "danger"
        except ValueError as exc:
            status.object = f"Could not run pricing: {exc}"
            status.alert_type = "danger"
        except Exception as exc:
            status.object = f"Pricing run failed: {exc}"
            status.alert_type = "danger"
        return None

    def _on_run(_event):
        # Hidden up front for every run: only the success path at the end
        # turns it back on, so no exception type -- caught below or not --
        # can leave a stale run's export live.
        export_button.visible = False
        if not state.is_ready_to_price():
            status.object = (
                "Load claims + exposures and configure a contract with at least one layer first."
            )
            status.alert_type = "danger"
            return
        contract = state.build_contract()
        model_data = _run_pricing_and_refresh(state.claims, state.exposures, contract)
        if model_data is None:
            return
        status.object = "Pricing run complete. See the tables below."
        status.alert_type = "success"
        last_run_model_data[:] = [model_data]
        export_button.visible = True

    def _on_save_version(_event):
        # Only a live run this session has an ExperienceModelData to derive
        # results from -- a draft-only save (no run yet) saves inputs alone.
        has_results_to_save = state.results is not None and last_run_model_data
        if has_results_to_save:
            # Build the snapshot from the *same* model_data that produced the
            # results being saved alongside it -- not live state, which may
            # have been edited (e.g. on "Configure contract") since that run.
            # This guarantees the saved inputs_blob always matches its own
            # saved results; there is no drift to be internally inconsistent.
            model_data = last_run_model_data[0]
            snapshot = ModelSnapshot(
                claims=model_data.claims,
                exposures=model_data.exposures,
                contract_metadata=model_data.ri_contract.contract_meta_data,
                layers=list(model_data.ri_contract.layers),
            )
        else:
            # No results to pair the snapshot with, so nothing to be
            # inconsistent with -- a plain draft save of live state.
            snapshot = ModelSnapshot(
                claims=state.claims,
                exposures=state.exposures,
                contract_metadata=state.contract_metadata,
                layers=state.layers,
            )
        new_version_id = save_version(
            DB_PATH,
            snapshot,
            label=version_label_input.value,
            parent_id=state.loaded_version_id,
        )
        if has_results_to_save:
            model_data = last_run_model_data[0]
            save_results(
                DB_PATH,
                new_version_id,
                summarize_by_layer_year(model_data),
                summarize_exposures_by_year(model_data),
            )
        state.loaded_version_id = new_version_id
        recalculate_button.visible = True
        # A draft-only save has no results to export -- only switch the
        # export button on when results were actually saved alongside it.
        export_button.visible = bool(has_results_to_save)
        status.object = f"Saved version #{new_version_id}."
        status.alert_type = "success"
        if on_save is not None:
            on_save()

    def _on_recalculate(_event):
        if state.loaded_version_id is None:
            return
        export_button.visible = False
        # Rebuilds from the *loaded version's own stored inputs*, never live
        # state -- state.layers/state.contract_metadata may have been edited
        # on "Configure contract" since this version was loaded, and
        # recalculating against that live (possibly-edited) state would
        # overwrite the version's cached results with numbers that no longer
        # match its own stored inputs_blob (the exact inconsistency
        # _on_save_version already guards against for the save path).
        try:
            snapshot, _, _ = load_version(DB_PATH, state.loaded_version_id)
        except IncompatibleSnapshotError as exc:
            status.object = str(exc)
            status.alert_type = "danger"
            return
        if (
            snapshot.claims is None
            or snapshot.exposures is None
            or snapshot.contract_metadata is None
            or not snapshot.layers
        ):
            status.object = (
                "This version has no complete claims/exposures/contract to recalculate from."
            )
            status.alert_type = "danger"
            return
        contract = RIContract(contract_meta_data=snapshot.contract_metadata, layers=snapshot.layers)
        model_data = _run_pricing_and_refresh(snapshot.claims, snapshot.exposures, contract)
        if model_data is None:
            return
        last_run_model_data[:] = [model_data]
        save_results(
            DB_PATH,
            state.loaded_version_id,
            summarize_by_layer_year(model_data),
            summarize_exposures_by_year(model_data),
        )
        status.object = (
            f"Recalculated and updated cached results for version #{state.loaded_version_id}."
        )
        status.alert_type = "success"
        export_button.visible = True

    run_button.on_click(_on_run)
    save_version_button.on_click(_on_save_version)
    recalculate_button.on_click(_on_recalculate)

    return pn.Column(
        "## Pricing results",
        run_button,
        status,
        "### Ceded loss by layer and modelling year",
        results_table,
        "### Exposures by modelling year",
        exposures_table,
        pn.Row(version_label_input, save_version_button, recalculate_button),
        export_button,
    )
