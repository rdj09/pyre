# app/features/data_loader_module.py
"""Data Loader feature — file/DB upload and domain object instantiation."""

from __future__ import annotations

from typing import Any

import pandas as pd
from shiny import Inputs, Outputs, Session, reactive, render, ui

from pyre.claims.claims import Claims
from pyre.claims.triangles import Triangle
from pyre.data_injector.exceptions import InjectionError
from pyre.exposures.exposures import Exposures

from ..services.domain_service import DomainService


def data_loader_ui() -> Any:
    return ui.page_sidebar(
        ui.sidebar(
            ui.h4("Data Loader"),
            ui.input_file(
                "dl_file_upload",
                "Upload File",
                accept=[".csv", ".xlsx", ".json", ".yaml", ".yml"],
                multiple=False,
            ),
            ui.input_select(
                "dl_source_type",
                "Data Source Type",
                choices=["csv", "excel", "json", "yaml", "db"],
                selected="csv",
            ),
            ui.input_select(
                "dl_domain_type",
                "Domain Object Type",
                choices=["Exposure", "Claim", "Triangle"],
                selected="Exposure",
            ),
            ui.panel_conditional(
                "input.dl_source_type === 'db'",
                ui.input_text(
                    "dl_db_connection_string",
                    "DB Connection String",
                    placeholder="sqlite:///path/to/file.db",
                ),
                ui.input_text_area(
                    "dl_db_query",
                    "SQL Query",
                    placeholder="SELECT * FROM exposures",
                    rows=3,
                ),
            ),
            ui.input_action_button("dl_load_btn", "Load Data", class_="btn-primary w-100 mt-2"),
            ui.hr(),
            ui.output_text("dl_status_message"),
            width=320,
        ),
        ui.navset_tab(
            ui.nav_panel("Data Preview", ui.output_data_frame("dl_raw_records_table")),
            ui.nav_panel("Domain Objects", ui.output_data_frame("dl_domain_objects_table")),
            ui.nav_panel("Summary Statistics", ui.output_ui("dl_summary_ui")),
        ),
        fillable=True,
    )


def data_loader_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    _claims: reactive.Value[Claims | None],
    _exposures: reactive.Value[Exposures | None],
    _triangle: reactive.Value[Triangle | None],
) -> None:
    _svc = DomainService()
    _raw_records: reactive.Value[list[dict[str, Any]]] = reactive.Value([])
    _domain_result: reactive.Value[Exposures | Claims | Triangle | None] = reactive.Value(None)
    _error_message: reactive.Value[str] = reactive.Value("")

    @reactive.effect
    @reactive.event(input.dl_load_btn)
    def _on_load() -> None:
        _error_message.set("")
        _raw_records.set([])
        _domain_result.set(None)
        _claims.set(None)
        _exposures.set(None)
        _triangle.set(None)

        source_type = input.dl_source_type()
        domain_type = input.dl_domain_type()

        if source_type == "db":
            source: Any = input.dl_db_connection_string()
            query = input.dl_db_query()
            if not source:
                _error_message.set("Please enter a DB connection string.")
                return
        else:
            file_info = input.dl_file_upload()
            if file_info is None or len(file_info) == 0:
                _error_message.set("Please upload a file first.")
                return
            source = file_info[0]["datapath"]
            query = ""

        try:
            if domain_type == "Exposure":
                result = _svc.load_exposures(source, source_type, query=query)
                _domain_result.set(result)
                _raw_records.set(_exposures_to_records(result))
                _exposures.set(result)
            elif domain_type == "Claim":
                result_claims = _svc.load_claims(source, source_type, query=query)
                _domain_result.set(result_claims)
                _raw_records.set(_claims_to_records(result_claims))
                _claims.set(result_claims)
            elif domain_type == "Triangle":
                result_tri = _svc.build_triangle(source, source_type)
                _domain_result.set(result_tri)
                _raw_records.set(_triangle_to_records(result_tri))
                _triangle.set(result_tri)
        except (InjectionError, ValueError, RuntimeError) as exc:
            _error_message.set(f"Error: {exc}")

    @render.text
    def dl_status_message() -> str:
        err = _error_message.get()
        if err:
            return err
        result = _domain_result.get()
        if result is None:
            return "Ready. Upload a file and click Load Data."
        if isinstance(result, (Exposures, Claims)):
            return f"Loaded {len(result)} record(s) successfully."
        if isinstance(result, Triangle):
            return (
                f"Triangle loaded: {len(result.origin_years)} origin year(s), "
                f"{len(result.dev_periods)} development period(s)."
            )
        return "Loaded successfully."

    @render.data_frame
    def dl_raw_records_table() -> pd.DataFrame:
        records = _raw_records.get()
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)

    @render.data_frame
    def dl_domain_objects_table() -> pd.DataFrame:
        result = _domain_result.get()
        if result is None:
            return pd.DataFrame()
        if isinstance(result, Exposures):
            return pd.DataFrame(_exposures_to_records(result))
        if isinstance(result, Claims):
            return pd.DataFrame(_claims_to_records(result))
        if isinstance(result, Triangle):
            return pd.DataFrame(_triangle_to_records(result))
        return pd.DataFrame()

    @render.ui
    def dl_summary_ui() -> Any:
        result = _domain_result.get()
        if result is None:
            return ui.p("No data loaded yet.")
        if isinstance(result, Exposures):
            return _render_summary_cards(_svc.exposure_summary(result))
        if isinstance(result, Claims):
            return _render_summary_cards(_svc.claim_summary(result))
        if isinstance(result, Triangle):
            return ui.div(
                ui.h5("Triangle Summary"),
                ui.tags.ul(
                    ui.tags.li(f"Origin years: {result.origin_years}"),
                    ui.tags.li(f"Development periods: {result.dev_periods}"),
                ),
            )
        return ui.p("No summary available.")


def _exposures_to_records(exposures: Exposures) -> list[dict[str, Any]]:
    return [
        {
            "exposure_id": e.exposure_meta.exposure_id,
            "exposure_name": e.exposure_meta.exposure_name,
            "period_start": str(e.exposure_meta.exposure_period_start),
            "period_end": str(e.exposure_meta.exposure_period_end),
            "currency": e.exposure_meta.currency,
            "exposure_value": e.exposure_values.exposure_value,
            "attachment_point": e.exposure_values.attachment_point,
            "limit": e.exposure_values.limit,
        }
        for e in exposures
    ]


def _claims_to_records(claims: Claims) -> list[dict[str, Any]]:
    return [
        {
            "claim_id": c.claims_meta_data.claim_id,
            "currency": c.claims_meta_data.currency,
            "loss_date": str(c.claims_meta_data.loss_date),
            "status": c.claims_meta_data.status,
            "latest_incurred": c.capped_claim_development_history.latest_incurred,
            "latest_paid": c.capped_claim_development_history.latest_paid,
        }
        for c in claims
    ]


def _triangle_to_records(triangle: Triangle) -> list[dict[str, Any]]:
    return [
        {"origin_year": oy, **{f"dev_{dp}": triangle[oy, dp] for dp in triangle.dev_periods}}
        for oy in triangle.origin_years
    ]


def _render_summary_cards(summary: dict[str, Any]) -> Any:
    items = [ui.tags.li(f"{k}: {v}") for k, v in summary.items()]
    return ui.div(ui.h5("Summary"), ui.tags.ul(*items))
