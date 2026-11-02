"""Contract + layer configuration page for the treaty pricing workbench."""

from __future__ import annotations

from datetime import date

import pandas as pd
import panel as pn
from bokeh.models.widgets.tables import NumberFormatter

from app.service import build_contract_metadata, build_layer
from app.state import WorkbenchState
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType

SELECTABLE_LAYER_TYPES = [
    ContractType.EXCESS_OF_LOSS,
    ContractType.FRANCHISE_DEDUCTIBLE,
    ContractType.AGGREGATE_STOP_LOSS,
    ContractType.QUOTA_SHARE,
    ContractType.SURPLUS_SHARE,
]

LAYER_TITLES = {
    "layer_id": "Layer ID",
    "layer_name": "Layer",
    "layer_type": "Type",
    "occurrence_attachment": "Attachment",
    "occurrence_limit": "Limit",
    "full_subject_premium": "Subject premium",
    "written_line": "Written line",
    "signed_line": "Signed line",
}
_AMOUNT = NumberFormatter(format="0,0", text_align="right")
_LINE = NumberFormatter(format="0.0%", text_align="right")
LAYER_FORMATTERS = {
    "occurrence_attachment": _AMOUNT,
    "occurrence_limit": _AMOUNT,
    "full_subject_premium": _AMOUNT,
    "written_line": _LINE,
    "signed_line": _LINE,
}

LAYER_COLUMNS = [
    "layer_id",
    "layer_name",
    "layer_type",
    "occurrence_attachment",
    "occurrence_limit",
    "full_subject_premium",
    "written_line",
    "signed_line",
]


def build_contract_config_page(state: WorkbenchState) -> pn.Column:
    status = pn.pane.Alert("Contract not yet configured.", alert_type="warning")

    contract_id = pn.widgets.TextInput(name="Contract ID", value="C-0001")
    contract_description = pn.widgets.TextInput(name="Description", value="")
    cedent_name = pn.widgets.TextInput(name="Cedent", value="")
    trigger_basis = pn.widgets.Select(
        name="Trigger basis",
        options=[t.name for t in ClaimTriggerBasis],
        value=ClaimTriggerBasis.LOD.name,
    )
    indexation_clause = pn.widgets.Select(
        name="Indexation clause",
        options=[t.name for t in IndexationClauseType],
        value=IndexationClauseType.FULL_INDEXATION.name,
    )
    indexation_margin = pn.widgets.FloatInput(name="Indexation margin", value=0.0)
    inception_date = pn.widgets.DatePicker(name="Inception date", value=date.today())
    expiration_date = pn.widgets.DatePicker(name="Expiration date", value=date.today())

    layer_rows: list[dict] = []
    layer_table = pn.widgets.Tabulator(
        pd.DataFrame(layer_rows, columns=LAYER_COLUMNS),
        show_index=False,
        disabled=True,
        name="Layers",
        titles=LAYER_TITLES,
        formatters=LAYER_FORMATTERS,
    )

    layer_id = pn.widgets.IntInput(name="Layer ID", value=1)
    layer_name = pn.widgets.TextInput(name="Layer name", value="Layer 1")
    layer_type = pn.widgets.Select(
        name="Layer type",
        options=[t.name for t in SELECTABLE_LAYER_TYPES],
        value=ContractType.EXCESS_OF_LOSS.name,
    )
    occurrence_attachment = pn.widgets.FloatInput(name="Occurrence attachment", value=0.0)
    occurrence_limit = pn.widgets.FloatInput(name="Occurrence limit", value=0.0)
    full_subject_premium = pn.widgets.FloatInput(name="Full subject premium", value=0.0)
    written_line = pn.widgets.FloatInput(name="Written line", value=1.0)
    signed_line = pn.widgets.FloatInput(name="Signed line", value=1.0)
    sum_insured = pn.widgets.FloatInput(name="Sum insured (SURPLUS_SHARE only)", value=0.0)

    add_layer_button = pn.widgets.Button(name="Add layer", button_type="default")
    save_contract_button = pn.widgets.Button(name="Save contract metadata", button_type="primary")

    def _on_add_layer(_event):
        form = {
            "layer_id": layer_id.value,
            "layer_name": layer_name.value,
            "layer_type": layer_type.value,
            "occurrence_attachment": occurrence_attachment.value,
            "occurrence_limit": occurrence_limit.value,
            "full_subject_premium": full_subject_premium.value,
            "written_line": written_line.value,
            "signed_line": signed_line.value,
            "sum_insured": sum_insured.value or None,
        }
        state.layers.append(build_layer(form))
        layer_rows.append({col: form.get(col) for col in LAYER_COLUMNS})
        layer_table.value = pd.DataFrame(layer_rows, columns=LAYER_COLUMNS)
        layer_id.value = layer_id.value + 1
        layer_name.value = f"Layer {layer_id.value}"

    def _on_save_contract(_event):
        form = {
            "contract_id": contract_id.value,
            "contract_description": contract_description.value,
            "cedent_name": cedent_name.value,
            "trigger_basis": trigger_basis.value,
            "indexation_clause": indexation_clause.value,
            "indexation_margin": indexation_margin.value,
            "inception_date": inception_date.value,
            "expiration_date": expiration_date.value,
        }
        state.contract_metadata = build_contract_metadata(form)
        if state.layers:
            status.object = (
                f"Contract '{contract_id.value}' saved with {len(state.layers)} layer(s). "
                'Continue to "3. Run pricing".'
            )
            status.alert_type = "success"
        else:
            status.object = (
                f"Contract '{contract_id.value}' saved, but it has no layers yet -- "
                "add at least one layer above before running pricing."
            )
            status.alert_type = "warning"

    add_layer_button.on_click(_on_add_layer)
    save_contract_button.on_click(_on_save_contract)

    return pn.Column(
        "## Contract metadata",
        pn.Row(contract_id, contract_description, cedent_name),
        pn.Row(trigger_basis, indexation_clause, indexation_margin),
        pn.Row(inception_date, expiration_date),
        "## Layers",
        pn.pane.Markdown(
            "Excess of loss, franchise deductible, aggregate stop loss, quota share, "
            "and surplus share layers are supported.",
            margin=(0, 0, 10, 0),
        ),
        pn.Row(layer_id, layer_name, layer_type),
        pn.Row(occurrence_attachment, occurrence_limit, full_subject_premium),
        pn.Row(written_line, signed_line, sum_insured),
        add_layer_button,
        pn.pane.Markdown("*Add one or more layers above, then click Save contract metadata.*"),
        layer_table,
        save_contract_button,
        status,
    )
