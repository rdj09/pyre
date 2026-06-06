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
from ..services.storage_service import StorageService


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
            ui.input_text(
                "dl_db_path",
                "SQLite Database Path",
                value="./pyre_data.db",
            ),
            ui.input_action_button("dl_load_btn", "Load Data", class_="btn-primary w-100 mt-2"),
            ui.hr(),
            ui.output_text("dl_status_message"),
            ui.hr(),
            ui.input_action_button("dl_save_btn", "Save to DB", class_="btn-secondary w-100"),
            ui.output_text("dl_save_status"),
            width=320,
        ),
        ui.navset_tab(
            ui.nav_panel("Data Preview", ui.output_data_frame("dl_raw_records_table")),
            ui.nav_panel("Domain Objects", ui.output_data_frame("dl_domain_objects_table")),
            ui.nav_panel("Summary Statistics", ui.output_ui("dl_summary_ui")),
            ui.nav_panel("Database", ui.output_ui("dl_db_status_ui")),
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
    _storage_svc = StorageService()
    _raw_records: reactive.Value[list[dict[str, Any]]] = reactive.Value([])
    _domain_result: reactive.Value[Exposures | Claims | Triangle | None] = reactive.Value(None)
    _error_message: reactive.Value[str] = reactive.Value("")
    _save_message: reactive.Value[str] = reactive.Value("")

    @reactive.effect
    @reactive.event(input.dl_load_btn)
    def _on_load() -> None:
        _error_message.set("")
        _raw_records.set([])
        _domain_result.set(None)

        source_type = input.dl_source_type()
        domain_type = input.dl_domain_type()

        if source_type == "db":
            db_path = input.dl_db_path().strip()
            if not db_path:
                _error_message.set("Please enter a SQLite database path.")
                return
            if domain_type == "Exposure":
                source: Any = f"sqlite:///{db_path}"
                query = "SELECT * FROM exposures"
            elif domain_type == "Claim":
                source = f"sqlite:///{db_path}"
                query = "SELECT * FROM claims"
            else:  # Triangle — build_triangle constructs sqlite:/// internally
                source = db_path
                query = ""
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

    @reactive.effect
    @reactive.event(input.dl_save_btn)
    def _on_save() -> None:
        _save_message.set("")
        result = _domain_result.get()
        db_path = input.dl_db_path().strip()
        if result is None:
            _save_message.set("Nothing to save — load data first.")
            return
        if not db_path:
            _save_message.set("Please enter a SQLite database path.")
            return
        if isinstance(result, Triangle):
            _save_message.set(
                "Triangle cannot be saved directly. Load Claims first, save those, "
                "then rebuild Triangle from DB."
            )
            return
        try:
            if isinstance(result, Exposures):
                _storage_svc.save_exposures(list(result), db_path)
                _save_message.set(f"Saved {len(result)} exposure(s) to {db_path}")
            elif isinstance(result, Claims):
                _storage_svc.save_claims(list(result), db_path)
                _save_message.set(f"Saved {len(result)} claim(s) to {db_path}")
        except Exception as exc:
            _save_message.set(f"Save failed: {exc}")

    @reactive.effect
    def _check_db_on_startup() -> None:
        with reactive.isolate():
            db_path = input.dl_db_path().strip()
        if not db_path:
            return
        exp_ids = _storage_svc.list_stored(db_path, "exposures")
        claim_ids = _storage_svc.list_stored(db_path, "claims")
        if not exp_ids and not claim_ids:
            return
        parts: list[str] = []
        if exp_ids:
            parts.append(f"{len(exp_ids)} exposure(s)")
        if claim_ids:
            parts.append(f"{len(claim_ids)} claim(s)")
        summary = " and ".join(parts)
        ui.modal_show(
            ui.modal(
                ui.p(f"Found {summary} in {db_path}."),
                ui.p("Load all data from the database now?"),
                title="Database data found",
                footer=ui.TagList(
                    ui.input_action_button(
                        "dl_modal_load_btn", "Load All", class_="btn-primary"
                    ),
                    ui.modal_button("Skip"),
                ),
                easy_close=True,
            )
        )

    @reactive.effect
    @reactive.event(input.dl_modal_load_btn)
    def _on_modal_load() -> None:
        ui.modal_remove()
        db_path = input.dl_db_path().strip()
        if not db_path:
            return
        errors: list[str] = []

        try:
            exp_ids = _storage_svc.list_stored(db_path, "exposures")
            if exp_ids:
                exposures = _svc.load_exposures(
                    f"sqlite:///{db_path}", "db", query="SELECT * FROM exposures"
                )
                _exposures.set(exposures)
        except Exception as exc:
            errors.append(f"Exposures: {exc}")

        try:
            claim_ids = _storage_svc.list_stored(db_path, "claims")
            if claim_ids:
                claims = _svc.load_claims(
                    f"sqlite:///{db_path}", "db", query="SELECT * FROM claims"
                )
                _claims.set(claims)
                triangle = _svc.build_triangle(db_path, "db")
                _triangle.set(triangle)
        except Exception as exc:
            errors.append(f"Claims/Triangle: {exc}")

        if errors:
            ui.notification_show(
                f"Partial load errors: {'; '.join(errors)}", type="warning", duration=6
            )
        else:
            ui.notification_show(
                "All data loaded from database.", type="success", duration=3
            )

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

    @render.text
    def dl_save_status() -> str:
        return _save_message.get()

    @render.ui
    def dl_db_status_ui() -> Any:
        _save_message.get()  # invalidate when save completes
        db_path = input.dl_db_path()
        if not db_path or not db_path.strip():
            return ui.p("Enter a SQLite database path in the sidebar.")
        path = db_path.strip()
        exp_ids = _storage_svc.list_stored(path, "exposures")
        claim_ids = _storage_svc.list_stored(path, "claims")
        return ui.div(
            ui.h5(f"Stored records in: {path}"),
            ui.h6(f"Exposures ({len(exp_ids)})"),
            ui.tags.ul(*[ui.tags.li(eid) for eid in exp_ids]) if exp_ids else ui.p("None"),
            ui.h6(f"Claims ({len(claim_ids)})"),
            ui.tags.ul(*[ui.tags.li(cid) for cid in claim_ids]) if claim_ids else ui.p("None"),
        )


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
