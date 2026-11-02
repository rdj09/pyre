"""Tests for ``Simulation`` (Monte Carlo aggregate-loss simulation).

Monte Carlo output has no textbook golden value -- every run is inherently
stochastic. These tests instead check:

1. Reproducibility: the same ``random_seed`` yields identical output.
2. Analytical sanity bounds: a known frequency x known (near-degenerate)
   severity through an unlimited layer has an analytically derivable
   expected loss cost, which the simulated loss cost must fall within a
   documented, wide Monte Carlo tolerance of.
3. Definitional inequalities: TVaR >= VaR at the same confidence level,
   which must hold regardless of simulation noise.
"""

import unittest
from datetime import date

from pyre import ContractType, RIContract, RIContractMetadata, RILayer
from pyre.models.AggregateFeatures.aggregate_features import ModellingAssumptions
from pyre.models.AggregateFeatures.simulation_engine import Simulation
from pyre.models.Experience.frequency_severity import FitResult
from pyre.enums import FrequencyDistribution, SeverityDistribution
from pyre.treaty import ClaimTriggerBasis, IndexationClauseType


def _xol_contract(occurrence_attachment: float = 100_000.0, occurrence_limit: float = 200_000.0):
    metadata = RIContractMetadata(
        contract_id="C-0001",
        contract_description="Test",
        cedent_name="Acme Re",
        trigger_basis=ClaimTriggerBasis.LOD,
        indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0,
        inception_date=date(2022, 1, 1),
        expiration_date=date(2022, 12, 31),
        fx_rates={"USD": 1.0},
    )
    layer = RILayer(
        layer_id=1,
        layer_name="XOL Layer",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=occurrence_attachment,
        occurrence_limit=occurrence_limit,
        aggregate_attachment=0.0,
        aggregate_limit=0.0,
        subject_lines_of_business=[],
        subject_lob_exposure_amounts=[],
        full_subject_premium=0.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=0,
        reinstatement_cost={},
    )
    return RIContract(contract_meta_data=metadata, layers=[layer])


def _poisson_fit(lam: float) -> FitResult:
    return FitResult(
        distribution=FrequencyDistribution.POISSON,
        parameters={"lambda": lam},
        log_likelihood=0.0,
        aic=0.0,
    )


def _pareto_fit(alpha: float, x_m: float) -> FitResult:
    return FitResult(
        distribution=SeverityDistribution.PARETO,
        parameters={"alpha": alpha, "x_m": x_m},
        log_likelihood=0.0,
        aic=0.0,
    )


class TestSimulationDeterminism(unittest.TestCase):
    def test_run_is_deterministic_with_same_random_seed(self):
        freq_fit = _poisson_fit(2.0)
        sev_fit = _pareto_fit(alpha=50.0, x_m=10_000.0)
        contract = _xol_contract()
        assumptions = ModellingAssumptions(cost_of_capital=0.1, required_rate_of_return=0.08)

        sim = Simulation(
            freq_fit,
            sev_fit,
            ri_contract=contract,
            assumptions=assumptions,
            n_simulations=1000,
            random_seed=42,
        )
        sim.run()
        first = sim.loss_cost()

        sim2 = Simulation(
            freq_fit,
            sev_fit,
            ri_contract=contract,
            assumptions=assumptions,
            n_simulations=1000,
            random_seed=42,
        )
        sim2.run()
        second = sim2.loss_cost()

        self.assertEqual(first, second)


class TestSimulationLossCost(unittest.TestCase):
    def test_loss_cost_converges_to_analytical_expectation(self):
        """Poisson(lambda=2) x a near-degenerate Pareto severity (very high
        alpha concentrates mass near x_m=10,000, so E[severity] ~= 10,000)
        through an unlimited XOL layer (occurrence_attachment=0, a very
        large occurrence_limit) -> analytically E[loss] ~= 2 * 10,000 =
        20,000. Asserted within a documented Monte Carlo tolerance
        (n_simulations=20,000, tolerance=+/-5%) -- not a textbook golden
        value (inherently stochastic), but an analytically derivable
        sanity bound.
        """
        lam = 2.0
        x_m = 10_000.0
        alpha = 500.0  # very high alpha -> Pareto mean = alpha*x_m/(alpha-1) ~= x_m
        freq_fit = _poisson_fit(lam)
        sev_fit = _pareto_fit(alpha=alpha, x_m=x_m)
        contract = _xol_contract(occurrence_attachment=0.0, occurrence_limit=1e12)
        assumptions = ModellingAssumptions(cost_of_capital=0.1, required_rate_of_return=0.08)

        sim = Simulation(
            freq_fit,
            sev_fit,
            ri_contract=contract,
            assumptions=assumptions,
            n_simulations=20_000,
            random_seed=123,
        )
        sim.run()
        loss_cost = sim.loss_cost()

        expected_severity_mean = alpha * x_m / (alpha - 1)
        analytical_expectation = lam * expected_severity_mean

        observed = loss_cost[1]
        tolerance = 0.05 * analytical_expectation
        self.assertAlmostEqual(observed, analytical_expectation, delta=tolerance)

        # Stash for reporting purposes.
        self.observed_loss_cost = observed
        self.analytical_expectation = analytical_expectation


class TestSimulationRequiredCapital(unittest.TestCase):
    def test_required_capital_tvar_is_at_least_var_same_confidence(self):
        freq_fit = _poisson_fit(3.0)
        sev_fit = _pareto_fit(alpha=5.0, x_m=10_000.0)
        contract = _xol_contract(occurrence_attachment=0.0, occurrence_limit=1e12)

        tvar_assumptions = ModellingAssumptions(
            cost_of_capital=0.1,
            required_rate_of_return=0.08,
            capital_confidence_level=0.995,
            use_tvar=True,
        )
        var_assumptions = ModellingAssumptions(
            cost_of_capital=0.1,
            required_rate_of_return=0.08,
            capital_confidence_level=0.995,
            use_tvar=False,
        )

        sim_tvar = Simulation(
            freq_fit,
            sev_fit,
            ri_contract=contract,
            assumptions=tvar_assumptions,
            n_simulations=5000,
            random_seed=7,
        )
        sim_tvar.run()
        tvar_capital = sim_tvar.required_capital()

        sim_var = Simulation(
            freq_fit,
            sev_fit,
            ri_contract=contract,
            assumptions=var_assumptions,
            n_simulations=5000,
            random_seed=7,
        )
        sim_var.run()
        var_capital = sim_var.required_capital()

        self.assertEqual(set(tvar_capital), set(var_capital))
        for layer_id in tvar_capital:
            self.assertGreaterEqual(tvar_capital[layer_id], var_capital[layer_id])


if __name__ == "__main__":
    unittest.main()
