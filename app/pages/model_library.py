"""Saved Models page for the treaty pricing workbench.

Catalog of saved pricing versions (Task 1-8's `app/db.py` repository layer)
with Load / Copy / Delete / Mark Final actions. Loading a version mutates
the shared `WorkbenchState` and then calls the `on_load` callback so the
caller (`app/main.py`) can rebuild the other tabs against the newly-loaded
state. Copy and Delete change the *set* of saved versions (not just this
page's own catalog), so they additionally call the optional `on_change`
callback -- letting the caller (e.g. the Compare tab's version picker)
refresh its own stale options too. Mark Final only flips a boolean flag on
an existing version, so it does not call `on_change`.
"""

from __future__ import annotations

from typing import Callable, Optional, cast

import pandas as pd
import panel as pn

from app.db import (
    DB_PATH,
    VersionSummary,
    copy_version,
    delete_version,
    list_versions,
    load_version,
    set_final,
)
from app.service import PricingResults
from app.state import WorkbenchState

CATALOG_COLUMNS = [
    "label",
    "is_final",
    "contract_id",
    "cedent_name",
    "inception_date",
    "expiration_date",
    "created_at",
]

CATALOG_TITLES = {
    "label": "Label",
    "is_final": "Final",
    "contract_id": "Contract ID",
    "cedent_name": "Cedent",
    "inception_date": "Inception",
    "expiration_date": "Expiration",
    "created_at": "Created",
}


def _summaries_to_frame(summaries: list[VersionSummary]) -> pd.DataFrame:
    rows = [{col: getattr(summary, col) for col in CATALOG_COLUMNS} for summary in summaries]
    return pd.DataFrame(rows, columns=CATALOG_COLUMNS)


def _version_options(summaries: list[VersionSummary]) -> dict[str, int]:
    # Keys are the display label shown in the Select; values are the int
    # version id actually needed by load_version/copy_version/etc. -- no
    # string-parsing of the selected label required.
    return {f"{summary.id}: {summary.label}": summary.id for summary in summaries}


def build_model_library_page(
    state: WorkbenchState,
    on_load: Callable[[], None],
    on_change: Optional[Callable[[], None]] = None,
) -> pn.Column:
    status = pn.pane.Alert(
        "Select a version below to Load, Copy, Delete, or mark Final.", alert_type="warning"
    )

    summaries = list_versions(DB_PATH)

    count_pane = pn.pane.Markdown(f"{len(summaries)} saved version(s)")
    catalog_table = pn.widgets.Tabulator(
        _summaries_to_frame(summaries),
        show_index=False,
        disabled=True,
        titles=CATALOG_TITLES,
    )
    version_select = pn.widgets.Select(name="Version", options=_version_options(summaries))
    mark_final_checkbox = pn.widgets.Checkbox(name="Mark as final", value=False)
    copy_label_input = pn.widgets.TextInput(name="New label (for Copy)", value="")

    load_button = pn.widgets.Button(name="Load", button_type="primary")
    copy_button = pn.widgets.Button(name="Copy", button_type="default")
    delete_button = pn.widgets.Button(name="Delete", button_type="danger")
    mark_final_button = pn.widgets.Button(name="Apply final status", button_type="default")

    def _selected_id() -> Optional[int]:
        return cast(Optional[int], version_select.value)

    def _refresh_catalog() -> None:
        refreshed = list_versions(DB_PATH)
        catalog_table.value = _summaries_to_frame(refreshed)
        count_pane.object = f"{len(refreshed)} saved version(s)"
        version_select.options = _version_options(refreshed)

    def _on_load(_event):
        version_id = _selected_id()
        if version_id is None:
            status.object = "Select a version to load first."
            status.alert_type = "warning"
            return
        snapshot, by_layer_year, exposures_by_year = load_version(DB_PATH, version_id)
        state.claims = snapshot.claims
        state.exposures = snapshot.exposures
        state.contract_metadata = snapshot.contract_metadata
        state.layers = snapshot.layers
        state.loaded_version_id = version_id
        if by_layer_year or exposures_by_year:
            state.results = PricingResults(
                by_layer_year=pd.DataFrame(by_layer_year),
                exposures_by_year=pd.DataFrame(exposures_by_year),
            )
        else:
            state.results = None
        status.object = f"Loaded version #{version_id}. See tabs 1-3 for the loaded contract."
        status.alert_type = "success"
        on_load()

    def _on_copy(_event):
        version_id = _selected_id()
        if version_id is None:
            status.object = "Select a version to copy first."
            status.alert_type = "warning"
            return
        new_label = copy_label_input.value.strip() or f"Copy of #{version_id}"
        new_id = copy_version(DB_PATH, version_id, new_label=new_label)
        _refresh_catalog()
        status.object = f"Copied version #{version_id} to new version #{new_id} ('{new_label}')."
        status.alert_type = "success"
        if on_change is not None:
            on_change()

    def _on_delete(_event):
        version_id = _selected_id()
        if version_id is None:
            status.object = "Select a version to delete first."
            status.alert_type = "warning"
            return
        delete_version(DB_PATH, version_id)
        if state.loaded_version_id == version_id:
            state.loaded_version_id = None
        _refresh_catalog()
        status.object = f"Deleted version #{version_id}."
        status.alert_type = "success"
        if on_change is not None:
            on_change()

    def _on_mark_final(_event):
        version_id = _selected_id()
        if version_id is None:
            status.object = "Select a version to mark first."
            status.alert_type = "warning"
            return
        set_final(DB_PATH, version_id, mark_final_checkbox.value)
        _refresh_catalog()
        final_word = "final" if mark_final_checkbox.value else "not final"
        status.object = f"Version #{version_id} marked {final_word}."
        status.alert_type = "success"

    load_button.on_click(_on_load)
    copy_button.on_click(_on_copy)
    delete_button.on_click(_on_delete)
    mark_final_button.on_click(_on_mark_final)

    return pn.Column(
        "## Saved models",
        count_pane,
        catalog_table,
        pn.Row(version_select, mark_final_checkbox, mark_final_button),
        pn.Row(load_button, copy_label_input, copy_button, delete_button),
        status,
    )
