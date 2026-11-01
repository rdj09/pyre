"""Compare page for the treaty pricing workbench.

Lets the user pick exactly two saved versions (Task 1-8's `app/db.py`
repository layer) and renders the `diff_versions` result: the layer-field
changes, the per-layer/year results changes (with a computed
`ceded_incurred_delta` column), and a claims/exposures summary.

Deliberately stateless with respect to `WorkbenchState` beyond matching the
other `build_*_page(state)` signatures -- the diff is driven entirely by the
two selected version ids, not by whatever is currently loaded into the
editable tabs.
"""

from __future__ import annotations

import dataclasses

import pandas as pd
import panel as pn

from app.db import (
    DB_PATH,
    LayerFieldChange,
    ResultsRowDiff,
    VersionDiff,
    VersionSummary,
    diff_versions,
    list_versions,
)
from app.state import WorkbenchState

LAYER_CHANGES_COLUMNS = [field.name for field in dataclasses.fields(LayerFieldChange)]
RESULTS_CHANGES_COLUMNS = [field.name for field in dataclasses.fields(ResultsRowDiff)] + [
    "ceded_incurred_delta"
]


def _version_options(summaries: list[VersionSummary]) -> dict[str, int]:
    # Keys are the display label shown in the MultiChoice; values are the int
    # version id actually needed by diff_versions -- no string-parsing of the
    # selected label required. Matches the "{id}: {label}" style used by the
    # Saved Models tab.
    return {f"{summary.id}: {summary.label}": summary.id for summary in summaries}


def _empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _layer_changes_frame(layer_changes: list[LayerFieldChange]) -> pd.DataFrame:
    rows = [dataclasses.asdict(change) for change in layer_changes]
    return pd.DataFrame(rows, columns=LAYER_CHANGES_COLUMNS)


def _results_changes_frame(results_changes: list[ResultsRowDiff]) -> pd.DataFrame:
    rows = []
    for row in results_changes:
        row_dict = dataclasses.asdict(row)
        row_dict["ceded_incurred_delta"] = (
            row_dict["ceded_incurred_new"] - row_dict["ceded_incurred_old"]
        )
        rows.append(row_dict)
    return pd.DataFrame(rows, columns=RESULTS_CHANGES_COLUMNS)


def _order_old_new(
    id_a: int, summary_a: VersionSummary, id_b: int, summary_b: VersionSummary
) -> tuple[int, int]:
    # The older of the two selected versions (lower created_at, falling back
    # to the lower id if created_at ties) is id_old -- diff_versions' argument
    # order determines which side of the diff is "old" vs "new".
    key_a = (summary_a.created_at, id_a)
    key_b = (summary_b.created_at, id_b)
    if key_a <= key_b:
        return id_a, id_b
    return id_b, id_a


def _summary_markdown(diff: VersionDiff) -> str:
    return (
        f"**Claims:** {diff.claims_count_old} -> {diff.claims_count_new}, "
        f"total incurred {diff.claims_total_incurred_old:,.0f} -> "
        f"{diff.claims_total_incurred_new:,.0f}\n\n"
        f"**Exposures:** {diff.exposures_count_old} -> {diff.exposures_count_new}, "
        f"total value {diff.exposures_total_value_old:,.0f} -> "
        f"{diff.exposures_total_value_new:,.0f}"
    )


def build_compare_page(state: WorkbenchState) -> pn.Column:
    status = pn.pane.Alert(
        "Select exactly two versions below, then click Compare.", alert_type="warning"
    )

    summaries = list_versions(DB_PATH)
    version_picker = pn.widgets.MultiChoice(
        name="Versions to compare (select exactly two)",
        options=_version_options(summaries),
    )
    compare_button = pn.widgets.Button(name="Compare", button_type="primary")

    layer_changes_table = pn.widgets.Tabulator(
        _empty_frame(LAYER_CHANGES_COLUMNS),
        show_index=False,
        disabled=True,
    )
    results_changes_table = pn.widgets.Tabulator(
        _empty_frame(RESULTS_CHANGES_COLUMNS),
        show_index=False,
        disabled=True,
    )
    summary_pane = pn.pane.Markdown("")

    def _on_compare(_event):
        selected = list(version_picker.value)
        if len(selected) != 2:
            status.object = (
                f"Select exactly two versions to compare (currently {len(selected)} selected)."
            )
            status.alert_type = "warning"
            return

        current_summaries = list_versions(DB_PATH)
        by_id = {summary.id: summary for summary in current_summaries}
        id_a, id_b = selected
        summary_a = by_id.get(id_a)
        summary_b = by_id.get(id_b)
        if summary_a is None or summary_b is None:
            status.object = "One of the selected versions no longer exists. Refresh and retry."
            status.alert_type = "danger"
            return

        id_old, id_new = _order_old_new(id_a, summary_a, id_b, summary_b)
        diff = diff_versions(DB_PATH, id_old, id_new)

        layer_changes_table.value = _layer_changes_frame(diff.layer_changes)
        results_changes_table.value = _results_changes_frame(diff.results_changes)
        summary_pane.object = _summary_markdown(diff)

        status.object = f"Compared version #{id_old} (older) against #{id_new} (newer)."
        status.alert_type = "success"

    compare_button.on_click(_on_compare)

    return pn.Column(
        "## Compare versions",
        version_picker,
        compare_button,
        status,
        "### Layer changes",
        layer_changes_table,
        "### Results changes",
        results_changes_table,
        "### Claims / exposures summary",
        summary_pane,
    )
