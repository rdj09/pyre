# app/features/simulation_module.py
"""Monte Carlo Simulation feature — DFA via frequency/severity fitting."""

from __future__ import annotations

from typing import Any

import pandas as pd
from shiny import Inputs, Outputs, Session, reactive, render, ui

from pyre.claims.claims import Claims
from pyre.claims.triangles import Triangle
from pyre.exposures.exposures import Exposures
from pyre.models.aggregate.aggregate_features import ModellingAssumptions
from pyre.models.aggregate.simulation_engine import SimulationResults
from pyre.treaty.contracts import RIContract

from ..services.model_service import ModelService


def simulation_ui() -> Any:
    return ui.page_sidebar(
        ui.sidebar(
            ui.h4("Monte Carlo Simulation"),
            ui.p(
                "Requires: Claims, Exposures, Contract (+ Triangle for IBNER).",
                class_="text-muted small",
            ),
            ui.input_numeric(
                "sim_n_sims", "Number of Simulations", value=10000, min=100, max=100000, step=100
            ),
            ui.input_numeric("sim_seed", "Random Seed (0=none)", value=42, min=0),
            ui.hr(),
            ui.h6("Financial Assumptions"),
            ui.input_numeric("sim_coc", "Cost of Capital", value=0.08, min=0, max=1, step=0.01),
            ui.input_numeric(
                "sim_ror", "Required Return on Equity", value=0.12, min=0, max=1, step=0.01
            ),
            ui.input_numeric(
                "sim_conf", "Capital Confidence Level", value=0.995, min=0.9, max=0.9999, step=0.001
            ),
            ui.input_switch("sim_use_tvar", "Use TVaR (vs VaR)", value=True),
            ui.input_numeric("sim_inv_yield", "Investment Yield", value=0.0, step=0.005),
            ui.input_numeric("sim_tax", "Tax Rate", value=0.0, step=0.01),
            ui.input_numeric("sim_acq_cost", "Acquisition Cost Ratio", value=0.0, step=0.01),
            ui.input_numeric("sim_brokerage", "Brokerage Ratio", value=0.0, step=0.01),
            ui.input_action_button(
                "sim_run_btn", "Run Simulation", class_="btn-primary w-100 mt-2"
            ),
            ui.hr(),
            ui.output_text("sim_status"),
            width=300,
        ),
        ui.navset_tab(
            ui.nav_panel("Results Summary", ui.output_data_frame("sim_results_table")),
            ui.nav_panel("Loss Distribution", ui.output_plot("sim_dist_plot")),
        ),
        fillable=True,
    )


def simulation_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    _claims: reactive.Value[Claims | None],
    _exposures: reactive.Value[Exposures | None],
    _contract: reactive.Value[RIContract | None],
    _triangle: reactive.Value[Triangle | None],
) -> None:
    _svc = ModelService()
    _results: reactive.Value[SimulationResults | None] = reactive.Value(None)
    _error: reactive.Value[str] = reactive.Value("")

    @reactive.effect
    @reactive.event(input.sim_run_btn)
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
            tri = _triangle.get()
            ibner_pattern = _svc.extract_ibner(tri) if tri is not None else {}
            model_data = _svc.build_experience_data(
                claims=claims,
                exposures=exposures,
                contract=contract,
                exposure_trends={y: 1.0 for y in exposures.modelling_years},
            )
            assumptions = ModellingAssumptions(
                cost_of_capital=float(input.sim_coc()),
                required_rate_of_return=float(input.sim_ror()),
                capital_confidence_level=float(input.sim_conf()),
                use_tvar=bool(input.sim_use_tvar()),
                investment_yield=float(input.sim_inv_yield()),
                tax_rate=float(input.sim_tax()),
                acquisition_cost_ratio=float(input.sim_acq_cost()),
                brokerage_cost_ratio=float(input.sim_brokerage()),
            )
            seed_val = int(input.sim_seed())
            results = _svc.run_simulation(
                experience_data=model_data,
                assumptions=assumptions,
                n_simulations=int(input.sim_n_sims()),
                random_seed=seed_val if seed_val > 0 else None,
                ibner_pattern=ibner_pattern,
            )
            _results.set(results)
        except Exception as exc:
            _error.set(f"Error: {exc}")

    @render.text
    def sim_status() -> str:
        err = _error.get()
        if err:
            return err
        r = _results.get()
        if r is None:
            return "Ready. Configure and click Run Simulation."
        return (
            f"Simulation complete — {r.n_simulations:,} trials, "
            f"total required premium: {r.required_premium_programme:,.0f}"
        )

    @render.data_frame
    def sim_results_table() -> pd.DataFrame:
        r = _results.get()
        contract = _contract.get()
        if r is None or contract is None:
            return pd.DataFrame()
        return _svc.simulation_results_to_df(r, contract)

    @render.plot
    def sim_dist_plot() -> Any:
        import matplotlib.pyplot as plt

        r = _results.get()
        if r is None:
            fig, ax = plt.subplots()
            ax.text(
                0.5, 0.5, "No simulation results", ha="center", va="center", transform=ax.transAxes
            )
            return fig
        n_layers = len(r.aggregate_loss_distribution)
        fig, axes = plt.subplots(
            1, max(n_layers, 1), figsize=(5 * max(n_layers, 1), 4), squeeze=False
        )
        for idx, (lid, losses) in enumerate(sorted(r.aggregate_loss_distribution.items())):
            ax = axes[0][idx]
            ax.hist(losses, bins=50, color="steelblue", edgecolor="white", alpha=0.8)
            ax.set_title(f"Layer {lid}")
            ax.set_xlabel("Aggregate Loss")
            ax.set_ylabel("Frequency")
        fig.tight_layout()
        return fig
