# app/features/rate_module.py
"""Rate Monitoring feature — adequacy and rate change calculators."""

from __future__ import annotations

from typing import Any

from shiny import Inputs, Outputs, Session, reactive, render, ui

from pyre.rate_monitoring.rate_adequacy import rate_adequacy, rate_adequacy_change
from pyre.rate_monitoring.rate_change import rate_change_adjusted, rate_change_simple


def rate_ui() -> Any:
    return ui.div(
        ui.h4("Rate Monitoring"),
        ui.layout_columns(
            ui.card(
                ui.card_header("Rate Adequacy"),
                ui.input_numeric("rm_premium", "Actual Premium", value=1000000, step=1000),
                ui.input_numeric("rm_indicated", "Indicated Premium", value=950000, step=1000),
                ui.input_action_button("rm_adequacy_btn", "Calculate", class_="btn-primary"),
                ui.output_text("rm_adequacy_result"),
            ),
            ui.card(
                ui.card_header("Rate Adequacy Change"),
                ui.input_numeric("rm_prior_prem", "Prior Premium", value=900000, step=1000),
                ui.input_numeric("rm_prior_ind", "Prior Indicated", value=950000, step=1000),
                ui.input_numeric("rm_curr_prem", "Current Premium", value=1000000, step=1000),
                ui.input_numeric("rm_curr_ind", "Current Indicated", value=980000, step=1000),
                ui.input_action_button("rm_adq_change_btn", "Calculate", class_="btn-primary"),
                ui.output_text("rm_adq_change_result"),
            ),
            ui.card(
                ui.card_header("Simple Rate Change"),
                ui.input_numeric("rm_expiring_prem", "Expiring Premium", value=900000, step=1000),
                ui.input_numeric("rm_renewed_prem", "Renewed Premium", value=1000000, step=1000),
                ui.input_action_button("rm_simple_btn", "Calculate", class_="btn-primary"),
                ui.output_text("rm_simple_result"),
            ),
            ui.card(
                ui.card_header("Adjusted Rate Change"),
                ui.input_numeric("rm_adj_expiring", "Expiring Premium", value=900000, step=1000),
                ui.input_numeric("rm_adj_renewed", "Renewed Premium", value=1000000, step=1000),
                ui.input_numeric(
                    "rm_adj_adjusted", "Adjusted Expiring (0=use expiring)", value=0, step=1000
                ),
                ui.input_action_button("rm_adj_btn", "Calculate", class_="btn-primary"),
                ui.output_text("rm_adj_result"),
            ),
            col_widths=[6, 6, 6, 6],
        ),
    )


def rate_server(
    input: Inputs,
    output: Outputs,
    session: Session,
) -> None:

    @render.text
    @reactive.event(input.rm_adequacy_btn)
    def rm_adequacy_result() -> str:
        try:
            result = rate_adequacy(float(input.rm_premium()), float(input.rm_indicated()))
            pct = (result - 1) * 100
            direction = "adequate" if result >= 1 else "inadequate"
            return f"Rate adequacy: {result:.4f} ({abs(pct):.2f}% {direction})"
        except Exception as exc:
            return f"Error: {exc}"

    @render.text
    @reactive.event(input.rm_adq_change_btn)
    def rm_adq_change_result() -> str:
        try:
            result = rate_adequacy_change(
                float(input.rm_prior_prem()),
                float(input.rm_prior_ind()),
                float(input.rm_curr_prem()),
                float(input.rm_curr_ind()),
            )
            return f"Adequacy change: {result:+.4f} ({result * 100:+.2f}%)"
        except Exception as exc:
            return f"Error: {exc}"

    @render.text
    @reactive.event(input.rm_simple_btn)
    def rm_simple_result() -> str:
        try:
            result = rate_change_simple(
                float(input.rm_expiring_prem()), float(input.rm_renewed_prem())
            )
            return f"Simple rate change: {result:+.4f} ({result * 100:+.2f}%)"
        except Exception as exc:
            return f"Error: {exc}"

    @render.text
    @reactive.event(input.rm_adj_btn)
    def rm_adj_result() -> str:
        try:
            adj = float(input.rm_adj_adjusted())
            result = rate_change_adjusted(
                float(input.rm_adj_expiring()),
                float(input.rm_adj_renewed()),
                adjusted_expiring_premium=adj if adj != 0 else None,
            )
            return f"Adjusted rate change: {result:+.4f} ({result * 100:+.2f}%)"
        except Exception as exc:
            return f"Error: {exc}"
