# app/features/contract_module.py
"""Contract Builder feature — form-based and JSON import."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from shiny import Inputs, Outputs, Session, reactive, render, ui

from pyre.treaty.contracts import RIContract

from ..services.model_service import ModelService


def contract_ui() -> Any:
    return ui.page_sidebar(
        ui.sidebar(
            ui.h4("Contract Builder"),
            ui.input_radio_buttons(
                "ctr_input_mode",
                "Input mode",
                choices={"form": "Form", "json": "JSON Upload"},
                selected="form",
            ),
            ui.panel_conditional(
                "input.ctr_input_mode === 'json'",
                ui.input_file("ctr_json_file", "Upload JSON", accept=[".json"]),
            ),
            ui.panel_conditional(
                "input.ctr_input_mode === 'form'",
                ui.input_text("ctr_contract_id", "Contract ID", value="CTR-001"),
                ui.input_text("ctr_description", "Description", value=""),
                ui.input_text("ctr_cedent", "Cedent Name", value=""),
                ui.input_select(
                    "ctr_trigger_basis",
                    "Trigger Basis",
                    choices=["LOD", "RAD", "CMB"],
                    selected="LOD",
                ),
                ui.input_select(
                    "ctr_indexation",
                    "Indexation Clause",
                    choices=["FULL_INDEXATION", "FIC", "SIC"],
                    selected="FULL_INDEXATION",
                ),
                ui.input_numeric(
                    "ctr_indexation_margin", "Indexation Margin", value=0.0, step=0.01
                ),
                ui.input_date("ctr_inception", "Inception Date", value="2024-01-01"),
                ui.input_date("ctr_expiration", "Expiration Date", value="2024-12-31"),
                ui.input_text(
                    "ctr_fx_rates", "FX Rates", value="GBP:1.0", placeholder="GBP:1.0,USD:1.25"
                ),
                ui.hr(),
                ui.input_numeric("ctr_n_layers", "Number of Layers", value=1, min=1, max=5, step=1),
                ui.output_ui("ctr_layer_forms"),
            ),
            ui.input_action_button(
                "ctr_build_btn", "Build Contract", class_="btn-primary w-100 mt-2"
            ),
            ui.hr(),
            ui.output_text("ctr_status"),
            width=340,
        ),
        ui.navset_tab(
            ui.nav_panel("Contract Summary", ui.output_ui("ctr_summary_ui")),
            ui.nav_panel("Layers", ui.output_data_frame("ctr_layers_table")),
        ),
        fillable=True,
    )


def contract_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    _contract: reactive.Value[RIContract | None],
) -> None:
    _svc = ModelService()
    _error: reactive.Value[str] = reactive.Value("")

    @render.ui
    def ctr_layer_forms() -> Any:
        n = int(input.ctr_n_layers())
        forms = []
        for i in range(1, n + 1):
            forms.append(ui.h6(f"Layer {i}"))
            forms.append(ui.input_text(f"ctr_l{i}_name", "Name", value=f"Layer {i}"))
            forms.append(
                ui.input_select(
                    f"ctr_l{i}_type",
                    "Type",
                    choices=["EXCESS_OF_LOSS", "QUOTA_SHARE", "AGGREGATE_STOP_LOSS"],
                    selected="EXCESS_OF_LOSS",
                )
            )
            forms.append(ui.input_numeric(f"ctr_l{i}_occ_attach", "Occurrence Attachment", value=0))
            forms.append(ui.input_numeric(f"ctr_l{i}_occ_limit", "Occurrence Limit", value=1000000))
            forms.append(ui.input_numeric(f"ctr_l{i}_agg_attach", "Agg Attachment", value=0))
            forms.append(
                ui.input_numeric(f"ctr_l{i}_agg_limit", "Agg Limit (0=unlimited)", value=0)
            )
            forms.append(ui.input_text(f"ctr_l{i}_lob", "Subject LOBs (comma)", value="ALL"))
            forms.append(ui.input_text(f"ctr_l{i}_lob_amounts", "LOB Amounts (comma)", value="0"))
            forms.append(ui.input_numeric(f"ctr_l{i}_fsp", "Full Subject Premium", value=0))
            forms.append(
                ui.input_numeric(f"ctr_l{i}_written", "Written Line", value=1.0, step=0.01)
            )
            forms.append(ui.input_numeric(f"ctr_l{i}_signed", "Signed Line", value=1.0, step=0.01))
            forms.append(ui.input_numeric(f"ctr_l{i}_reinst", "No. Reinstatements", value=1, min=0))
            forms.append(
                ui.input_text(f"ctr_l{i}_reinst_cost", "Reinstatement Costs", value="1:1.0")
            )
            forms.append(ui.hr())
        return ui.div(*forms)

    @reactive.effect
    @reactive.event(input.ctr_build_btn)
    def _on_build() -> None:
        _error.set("")
        try:
            if input.ctr_input_mode() == "json":
                file_info = input.ctr_json_file()
                if not file_info:
                    _error.set("Please upload a JSON file.")
                    return
                with open(file_info[0]["datapath"], "rb") as f:
                    contract = _svc.build_contract_from_json(f.read())
            else:
                n = int(input.ctr_n_layers())
                layers_data = []
                for i in range(1, n + 1):
                    layers_data.append(
                        {
                            "layer_name": input[f"ctr_l{i}_name"](),
                            "layer_type": input[f"ctr_l{i}_type"](),
                            "occurrence_attachment": input[f"ctr_l{i}_occ_attach"](),
                            "occurrence_limit": input[f"ctr_l{i}_occ_limit"](),
                            "aggregate_attachment": input[f"ctr_l{i}_agg_attach"](),
                            "aggregate_limit": input[f"ctr_l{i}_agg_limit"](),
                            "subject_lob": input[f"ctr_l{i}_lob"](),
                            "subject_lob_amounts": input[f"ctr_l{i}_lob_amounts"](),
                            "full_subject_premium": input[f"ctr_l{i}_fsp"](),
                            "written_line": input[f"ctr_l{i}_written"](),
                            "signed_line": input[f"ctr_l{i}_signed"](),
                            "number_of_reinstatements": input[f"ctr_l{i}_reinst"](),
                            "reinstatement_cost": input[f"ctr_l{i}_reinst_cost"](),
                        }
                    )
                contract = _svc.build_contract(
                    contract_id=input.ctr_contract_id(),
                    contract_description=input.ctr_description(),
                    cedent_name=input.ctr_cedent(),
                    trigger_basis=input.ctr_trigger_basis(),
                    indexation_clause=input.ctr_indexation(),
                    indexation_margin=float(input.ctr_indexation_margin()),
                    inception_date=date.fromisoformat(str(input.ctr_inception())),
                    expiration_date=date.fromisoformat(str(input.ctr_expiration())),
                    fx_rates_text=input.ctr_fx_rates(),
                    layers_data=layers_data,
                )
            _contract.set(contract)
        except Exception as exc:
            _error.set(f"Error: {exc}")

    @render.text
    def ctr_status() -> str:
        err = _error.get()
        if err:
            return err
        c = _contract.get()
        if c is None:
            return "No contract built yet."
        return f"Contract '{c.contract_meta_data.contract_id}' — {len(c.layers)} layer(s)."

    @render.ui
    def ctr_summary_ui() -> Any:
        c = _contract.get()
        if c is None:
            return ui.p("No contract built yet.")
        meta = c.contract_meta_data
        return ui.div(
            ui.h5("Contract Metadata"),
            ui.tags.ul(
                ui.tags.li(f"ID: {meta.contract_id}"),
                ui.tags.li(f"Description: {meta.contract_description}"),
                ui.tags.li(f"Cedent: {meta.cedent_name}"),
                ui.tags.li(f"Trigger: {meta.trigger_basis.value}"),
                ui.tags.li(f"Inception: {meta.inception_date}"),
                ui.tags.li(f"Expiration: {meta.expiration_date}"),
                ui.tags.li(f"Layers: {len(c.layers)}"),
            ),
        )

    @render.data_frame
    def ctr_layers_table() -> pd.DataFrame:
        c = _contract.get()
        if c is None:
            return pd.DataFrame()
        return pd.DataFrame(
            [
                {
                    "id": layer.layer_id,
                    "name": layer.layer_name,
                    "type": layer.layer_type.name,
                    "occ_attach": layer.occurrence_attachment,
                    "occ_limit": layer.occurrence_limit,
                    "agg_attach": layer.aggregate_attachment,
                    "agg_limit": layer.aggregate_limit,
                    "fsp": layer.full_subject_premium,
                    "written_line": layer.written_line,
                    "signed_line": layer.signed_line,
                }
                for layer in c.layers
            ]
        )
