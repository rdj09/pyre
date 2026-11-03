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

import json
import tempfile
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


class TestSimulationRequiredPremium(unittest.TestCase):
    def _run_sim(self, assumptions=None, retrocession_contract=None):
        freq_fit = _poisson_fit(2.0)
        sev_fit = _pareto_fit(alpha=5.0, x_m=10_000.0)
        contract = _xol_contract(occurrence_attachment=0.0, occurrence_limit=1e12)
        if assumptions is None:
            assumptions = ModellingAssumptions(cost_of_capital=0.1, required_rate_of_return=0.08)
        sim = Simulation(
            freq_fit,
            sev_fit,
            ri_contract=contract,
            assumptions=assumptions,
            n_simulations=2000,
            random_seed=99,
            retrocession_contract=retrocession_contract,
        )
        sim.run()
        return sim

    def test_required_premium_layer_exceeds_loss_cost_when_cost_of_capital_positive(self):
        sim = self._run_sim()
        loss_costs = sim.loss_cost()
        for layer_id in loss_costs:
            self.assertGreater(sim.required_premium_layer(layer_id), loss_costs[layer_id])

    def test_required_premium_programme_sums_across_layers(self):
        sim = self._run_sim()
        total = sim.required_premium_programme()
        layer_ids = sim.loss_cost().keys()
        self.assertAlmostEqual(
            total,
            sum(sim.required_premium_layer(lid) for lid in layer_ids),
            places=2,
        )

    def test_required_premium_layer_grosses_up_for_expense_ratios(self):
        """A 20% combined acquisition + brokerage expense ratio should gross
        up the "everything else" numerator by dividing by (1 - 0.2) = 0.8,
        i.e. required_premium ~= numerator / 0.8 = numerator * 1.25 --
        per the standard CAS expense-loading treatment (Werner & Modlin,
        Basic Ratemaking, 5th ed., CAS), not a simple additive expense.
        """
        base_assumptions = ModellingAssumptions(cost_of_capital=0.1, required_rate_of_return=0.08)
        loaded_assumptions = ModellingAssumptions(
            cost_of_capital=0.1,
            required_rate_of_return=0.08,
            acquisition_cost_ratio=0.1,
            brokerage_cost_ratio=0.1,
        )

        base_sim = self._run_sim(assumptions=base_assumptions)
        loaded_sim = self._run_sim(assumptions=loaded_assumptions)

        for layer_id in base_sim.loss_cost():
            numerator = base_sim.required_premium_layer(layer_id)
            expected_loaded = numerator / 0.8
            self.assertAlmostEqual(
                loaded_sim.required_premium_layer(layer_id), expected_loaded, places=6
            )

    def test_required_premium_layer_raises_when_expense_ratio_too_high(self):
        assumptions = ModellingAssumptions(
            cost_of_capital=0.1,
            required_rate_of_return=0.08,
            acquisition_cost_ratio=0.6,
            brokerage_cost_ratio=0.5,
        )
        sim = self._run_sim(assumptions=assumptions)
        with self.assertRaises(ValueError):
            sim.required_premium_layer(1)


class TestSimulationRetrocession(unittest.TestCase):
    def test_retrocession_benefits_zero_without_retrocession_contract(self):
        freq_fit = _poisson_fit(2.0)
        sev_fit = _pareto_fit(alpha=5.0, x_m=10_000.0)
        contract = _xol_contract(occurrence_attachment=0.0, occurrence_limit=1e12)
        assumptions = ModellingAssumptions(cost_of_capital=0.1, required_rate_of_return=0.08)
        sim = Simulation(
            freq_fit,
            sev_fit,
            ri_contract=contract,
            assumptions=assumptions,
            n_simulations=500,
            random_seed=11,
        )
        sim.run()
        benefits = sim.retrocession_benefits()
        self.assertEqual(set(benefits), {1})
        self.assertEqual(benefits[1], 0.0)
        costs = sim.retrocession_cost()
        self.assertEqual(costs[1], 0.0)

    def test_retrocession_benefits_positive_when_retro_attaches_below_ceded_loss(self):
        freq_fit = _poisson_fit(2.0)
        sev_fit = _pareto_fit(alpha=5.0, x_m=10_000.0)
        contract = _xol_contract(occurrence_attachment=0.0, occurrence_limit=1e12)

        # Retro layer with same layer_id=1, attaching at a low point so it
        # should pick up recoveries from the primary layer's aggregate
        # ceded loss most years.
        retro_contract = _xol_contract(occurrence_attachment=1_000.0, occurrence_limit=1e12)

        assumptions = ModellingAssumptions(
            cost_of_capital=0.1,
            required_rate_of_return=0.08,
            retrocession_premium_loading=0.1,
        )
        sim = Simulation(
            freq_fit,
            sev_fit,
            ri_contract=contract,
            assumptions=assumptions,
            n_simulations=2000,
            random_seed=21,
            retrocession_contract=retro_contract,
        )
        sim.run()
        benefits = sim.retrocession_benefits()
        self.assertGreater(benefits[1], 0.0)

        costs = sim.retrocession_cost()
        self.assertAlmostEqual(costs[1], 0.1 * benefits[1], places=6)

    def test_retrocession_benefits_zero_for_layer_id_without_matching_retro_layer(self):
        freq_fit = _poisson_fit(2.0)
        sev_fit = _pareto_fit(alpha=5.0, x_m=10_000.0)
        contract = _xol_contract(occurrence_attachment=0.0, occurrence_limit=1e12)

        # Retro contract whose layer has a different layer_id (99), so it
        # should not match primary layer_id=1.
        metadata = contract.contract_meta_data
        mismatched_layer = RILayer(
            layer_id=99,
            layer_name="Retro Layer",
            layer_type=ContractType.EXCESS_OF_LOSS,
            occurrence_attachment=0.0,
            occurrence_limit=1e12,
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
        retro_contract = RIContract(contract_meta_data=metadata, layers=[mismatched_layer])

        assumptions = ModellingAssumptions(cost_of_capital=0.1, required_rate_of_return=0.08)
        sim = Simulation(
            freq_fit,
            sev_fit,
            ri_contract=contract,
            assumptions=assumptions,
            n_simulations=500,
            random_seed=31,
            retrocession_contract=retro_contract,
        )
        sim.run()
        benefits = sim.retrocession_benefits()
        self.assertEqual(benefits[1], 0.0)


class TestSimulationOutputSave(unittest.TestCase):
    def test_save_and_reload_produces_equivalent_json(self):
        freq_fit = _poisson_fit(2.0)
        sev_fit = _pareto_fit(alpha=5.0, x_m=10_000.0)
        contract = _xol_contract(occurrence_attachment=0.0, occurrence_limit=1e12)
        assumptions = ModellingAssumptions(cost_of_capital=0.1, required_rate_of_return=0.08)
        sim = Simulation(
            freq_fit,
            sev_fit,
            ri_contract=contract,
            assumptions=assumptions,
            n_simulations=500,
            random_seed=55,
        )
        sim.run()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            sim.save(tmp_path)
            with open(tmp_path) as f:
                data = json.load(f)
            self.assertIn("required_premium_programme", data)
            self.assertAlmostEqual(
                data["required_premium_programme"], sim.required_premium_programme(), places=6
            )
            self.assertIn("loss_cost", data)
            self.assertEqual(
                {int(k): v for k, v in data["loss_cost"].items()}, sim.loss_cost()
            )
        finally:
            import os

            os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
