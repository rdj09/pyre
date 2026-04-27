# app/features/experience_module.py
"""Experience Pricing feature — burn cost with trending and projection methods."""

from __future__ import annotations

from typing import Any

import pandas as pd
from shiny import Inputs, Outputs, Session, reactive, render, ui

from pyre.claims.claims import Claims
from pyre.exposures.exposures import Exposures
from pyre.treaty.contracts import RIContract

from ..services.model_service import ModelService


def experience_ui() -> Any:
    return ui.page_sidebar(
        ui.sidebar(
            ui.h4("Experience Pricing"),
            ui.p("Load Claims + Exposures and build a Contract first.", class_="text-muted small"),
            ui.input_select(
                "exp_layer_id",
                "Layer ID",
                choices=["1"],
                selected="1",
            ),
            ui.input_select(
                "exp_projection_method",
                "Projection Method",
                choices=["CHAINLADDER", "BF", "SIMPLE_CAPE_COD", "GENERALISED_CAPE_COD"],
                selected="SIMPLE_CAPE_COD",
            ),
            ui.input_text(
                "exp_exposure_trends",
                "Exposure Trend Factors (year:factor,...)",
                value="",
                placeholder="2020:1.0,2021:1.02",
            ),
            ui.input_text(
                "exp_claim_trends",
                "Claim Trend Factors (year:factor,...)",
                value="",
                placeholder="leave blank for default",
            ),
            ui.input_text(
                "exp_dev_pattern",
                "Dev Pattern (year:factor,...)",
                value="",
                placeholder="leave blank for no development",
            ),
            ui.input_text(
                "exp_a_priori",
                "A Priori LR (year:factor,...)",
                value="",
                placeholder="leave blank to omit",
            ),
            ui.input_action_button("exp_run_btn", "Run Burn Cost", class_="btn-primary w-100 mt-2"),
            ui.hr(),
            ui.output_text("exp_status"),
            width=300,
        ),
        ui.navset_tab(
            ui.nav_panel("Burn Cost Results", ui.output_data_frame("exp_results_table")),
            ui.nav_panel("Aggregate Claims", ui.output_data_frame("exp_claims_table")),
        ),
        fillable=True,
    )


def experience_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    _claims: reactive.Value[Claims | None],
    _exposures: reactive.Value[Exposures | None],
    _contract: reactive.Value[RIContract | None],
) -> None:
    _svc = ModelService()
    _results: reactive.Value[dict[int, float]] = reactive.Value({})
    _agg_claims: reactive.Value[dict[Any, Any]] = reactive.Value({})
    _error: reactive.Value[str] = reactive.Value("")

    @reactive.effect
    @reactive.event(_contract)
    def _update_layer_choices() -> None:
        c = _contract.get()
        if c is not None:
            choices = {
                str(layer.layer_id): f"Layer {layer.layer_id}: {layer.layer_name}"
                for layer in c.layers
            }
            ui.update_select("exp_layer_id", choices=choices)

    @reactive.effect
    @reactive.event(input.exp_run_btn)
    def _on_run() -> None:
        _error.set("")
        claims = _claims.get()
        exposures = _exposures.get()
        contract = _contract.get()
        if claims is None:
            _error.set("No claims loaded. Use the Data Loader tab.")
            return
        if exposures is None:
            _error.set("No exposures loaded. Use the Data Loader tab.")
            return
        if contract is None:
            _error.set("No contract built. Use the Contract Builder tab.")
            return
        try:
            exp_trends_text = input.exp_exposure_trends().strip()
            exp_trends = _svc.parse_year_factors(exp_trends_text) if exp_trends_text else None
            clm_trends_text = input.exp_claim_trends().strip()
            clm_trends = _svc.parse_year_factors(clm_trends_text) if clm_trends_text else None
            dev_text = input.exp_dev_pattern().strip()
            dev_pattern = _svc.parse_year_factors(dev_text) if dev_text else {}
            ap_text = input.exp_a_priori().strip()
            a_priori = _svc.parse_year_factors(ap_text) if ap_text else None

            model_data = _svc.build_experience_data(
                claims=claims,
                exposures=exposures,
                contract=contract,
                exposure_trends=exp_trends or {y: 1.0 for y in exposures.modelling_years},
                claim_trends=clm_trends,
            )
            layer_id = int(input.exp_layer_id())
            results = _svc.run_burn_cost(
                model_data=model_data,
                layer_id=layer_id,
                projection_method=input.exp_projection_method(),
                dev_pattern=dev_pattern,
                a_priori=a_priori,
            )
            _results.set(results)
            _agg_claims.set(model_data.aggregate_subject_contract_claims.get(layer_id, {}))
        except Exception as exc:
            _error.set(f"Error: {exc}")

    @render.text
    def exp_status() -> str:
        err = _error.get()
        if err:
            return err
        r = _results.get()
        if not r:
            return "Ready. Configure parameters and click Run Burn Cost."
        total = sum(r.values()) / len(r) if r else 0
        return f"Burn cost complete — {len(r)} year(s), avg loss ratio: {total:.4f}"

    @render.data_frame
    def exp_results_table() -> pd.DataFrame:
        r = _results.get()
        if not r:
            return pd.DataFrame()
        return pd.DataFrame(
            [{"modelling_year": y, "burn_cost_loss_ratio": v} for y, v in sorted(r.items())]
        )

    @render.data_frame
    def exp_claims_table() -> pd.DataFrame:
        agg = _agg_claims.get()
        if not agg:
            return pd.DataFrame()
        rows = []
        for year, data in sorted(agg.items()):
            rows.append(
                {
                    "modelling_year": year,
                    "latest_incurred": data.get("latest_incurred", 0),
                    "latest_paid": data.get("latest_paid", 0),
                    "total_count": data.get("total_count", 0),
                }
            )
        return pd.DataFrame(rows)
