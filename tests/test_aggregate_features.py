"""Tests for the ``AggregateFeatures`` orchestrator.

``AggregateFeatures.run()`` fits frequency/severity distributions from
experience data (via ``FrequencyFit``/``SeverityFit``), selects the
better-fitting distribution of each kind by AIC, builds a ``Simulation``
with the real Task 19/20 constructor, runs it, and returns its
``SimulationResults``. These tests cover the orchestration end-to-end
(Step 1's smoke test from the brief) plus the Negative-Binomial-not-
overdispersed fallback (Ruling 3).
"""

import io
import unittest
from datetime import date

from app.service import (
    build_contract_metadata,
    build_layer,
    parse_claims_csv,
    parse_exposures_csv,
)
from pyre import (
    Claim,
    ClaimDevelopmentHistory,
    Claims,
    ClaimsMetaData,
    Exposure,
    ExposureMetaData,
    Exposures,
    ExposureValues,
    RIContract,
    RIContractMetadata,
    RILayer,
)
from pyre.models.AggregateFeatures.aggregate_features import AggregateFeatures, ModellingAssumptions
from pyre.models.AggregateFeatures.selections import Selections
from pyre.models.Exposure.exposure_curve_functions import ExposureCurveType
from pyre.models.Exposure.exposure_rating_cost import ExposureModel
from pyre.models.Experience.experience_preparer import ExperienceModelData
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType
from tests.test_app_service import CLAIMS_CSV, EXPOSURES_CSV


def _ri_contract():
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
        occurrence_attachment=50_000.0,
        occurrence_limit=1_000_000.0,
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


def _claim(claim_id: str, year: int, latest_incurred: float) -> Claim:
    return Claim(
        ClaimsMetaData(
            claim_id=claim_id,
            currency="USD",
            contract_limit=5_000_000.0,
            loss_date=date(year, 6, 1),
        ),
        ClaimDevelopmentHistory(
            development_months=[12],
            cumulative_dev_paid=[latest_incurred],
            cumulative_dev_incurred=[latest_incurred],
        ),
    )


def _exposure(year: int) -> Exposure:
    return Exposure(
        ExposureMetaData(
            exposure_id=f"EXP{year}",
            exposure_name=f"{year} Premium",
            exposure_period_start=date(year, 1, 1),
            exposure_period_end=date(year, 12, 31),
            currency="USD",
        ),
        ExposureValues(exposure_value=1_000_000.0, attachment_point=0.0, limit=1_000_000.0),
    )


def _experience_model_data(claims_list, exposures_list):
    return ExperienceModelData(
        claims=Claims(claims_list),
        exposures=Exposures(exposures_list),
        ri_contract=_ri_contract(),
    )


def _exposure_model(exposures_list):
    return ExposureModel(
        exposures=Exposures(exposures_list),
        ri_contract=_ri_contract(),
        selected_curve=ExposureCurveType.RIEBESELL,
        curve_parameters={},
    )


class TestAggregateFeaturesRun(unittest.TestCase):
    def test_run_returns_well_formed_results(self):
        """Varying claim counts per year (overdispersed) and varying
        severities -- a realistic small experience dataset -- should let
        AggregateFeatures fit both frequency and severity, run the
        simulation, and return a non-negative required programme premium.
        """
        severities = [
            75_000.0, 120_000.0, 95_000.0, 200_000.0, 60_000.0,
            150_000.0, 110_000.0, 300_000.0, 80_000.0, 175_000.0,
            90_000.0, 130_000.0, 250_000.0, 70_000.0,
        ]
        years = [2018, 2018, 2018, 2019, 2019, 2019, 2019, 2019,
                 2020, 2020, 2021, 2021, 2021, 2021]
        claims_list = [
            _claim(f"CLM{i:03d}", year, severity)
            for i, (year, severity) in enumerate(zip(years, severities))
        ]
        exposures_list = [_exposure(year) for year in sorted(set(years))]

        experience_data = _experience_model_data(claims_list, exposures_list)
        exposure_data = _exposure_model(exposures_list)
        selections = Selections(experience_data=experience_data, exposure_data=exposure_data)
        assumptions = ModellingAssumptions(cost_of_capital=0.1, required_rate_of_return=0.08)

        af = AggregateFeatures(
            experience_data=experience_data,
            exposure_data=exposure_data,
            selections=selections,
            assumptions=assumptions,
        )
        results = af.run(n_simulations=500)

        self.assertGreaterEqual(results.required_premium_programme, 0.0)

    def test_run_falls_back_to_poisson_when_claim_counts_not_overdispersed(self):
        """Equal claim counts per year (variance <= mean) make the
        Negative Binomial method-of-moments fit raise ValueError;
        AggregateFeatures should catch that and still complete via the
        Poisson-only fallback, rather than propagating the error.
        """
        years = [2019, 2019, 2020, 2020, 2021, 2021, 2022, 2022]
        severities = [
            100_000.0, 150_000.0, 90_000.0, 200_000.0,
            130_000.0, 175_000.0, 80_000.0, 160_000.0,
        ]
        claims_list = [
            _claim(f"CLM{i:03d}", year, severity)
            for i, (year, severity) in enumerate(zip(years, severities))
        ]
        exposures_list = [_exposure(year) for year in sorted(set(years))]

        experience_data = _experience_model_data(claims_list, exposures_list)
        exposure_data = _exposure_model(exposures_list)
        selections = Selections(experience_data=experience_data, exposure_data=exposure_data)
        assumptions = ModellingAssumptions(cost_of_capital=0.1, required_rate_of_return=0.08)

        af = AggregateFeatures(
            experience_data=experience_data,
            exposure_data=exposure_data,
            selections=selections,
            assumptions=assumptions,
        )
        results = af.run(n_simulations=500)

        self.assertGreaterEqual(results.required_premium_programme, 0.0)


class TestAggregateFeaturesPricingPathE2E(unittest.TestCase):
    """End-to-end wiring test: the real CSV-parsing fixtures from
    ``tests/test_app_service.py`` (``CLAIMS_CSV``/``EXPOSURES_CSV``, parsed
    via ``app.service.parse_claims_csv``/``parse_exposures_csv``) flow
    through the full ``AggregateFeatures`` -> ``Simulation`` pricing path
    (Tasks 19-21's finalized stack).

    Scoped to structural correctness and sane bounds, not an exact figure --
    Simulation output is inherently stochastic, so no independent textbook
    number exists to check against (same reasoning as Tasks 19-20's test
    gaps). ``AggregateFeatures.run()`` has no ``random_seed`` passed through
    to ``Simulation``, so two runs are NOT bit-for-bit reproducible -- the
    second run below only checks that re-running still produces a
    well-formed, non-negative result, not numeric equality with the first.
    """

    def test_aggregate_features_pricing_path_structural_e2e(self):
        claims = parse_claims_csv(io.StringIO(CLAIMS_CSV))
        exposures = parse_exposures_csv(io.StringIO(EXPOSURES_CSV))

        metadata = build_contract_metadata(
            {
                "contract_id": "C-0001",
                "trigger_basis": "LOD",
                "indexation_clause": "FULL_INDEXATION",
                "inception_date": date(2023, 1, 1),
                "expiration_date": date(2023, 12, 31),
            }
        )
        layer = build_layer(
            {
                "layer_id": 1,
                "layer_name": "XOL Layer",
                "layer_type": "EXCESS_OF_LOSS",
                "occurrence_attachment": 100_000,
                "occurrence_limit": 200_000,
            }
        )
        contract = RIContract(contract_meta_data=metadata, layers=[layer])

        experience_data = ExperienceModelData(
            claims=claims, exposures=exposures, ri_contract=contract
        )
        exposure_model = ExposureModel(
            exposures=exposures,
            ri_contract=contract,
            selected_curve=ExposureCurveType.RIEBESELL,
            curve_parameters={},
        )
        selections = Selections(experience_data=experience_data, exposure_data=exposure_model)
        assumptions = ModellingAssumptions(cost_of_capital=0.15, required_rate_of_return=0.1)

        af = AggregateFeatures(
            experience_data=experience_data,
            exposure_data=exposure_model,
            selections=selections,
            assumptions=assumptions,
        )
        results = af.run(n_simulations=1000)

        # Structural correctness: every per-layer dict is keyed by the
        # contract's one layer_id (1), and per-layer figures are
        # non-negative.
        self.assertEqual(set(results.loss_cost), {1})
        self.assertEqual(set(results.required_capital), {1})
        self.assertEqual(set(results.required_premium_layer), {1})
        self.assertGreaterEqual(results.loss_cost[1], 0.0)
        self.assertGreaterEqual(results.required_capital[1], 0.0)

        # Sane bounds: a positive cost_of_capital (0.15) loads a capital
        # charge on top of loss cost, so required premium must be at least
        # the loss cost, and strictly greater whenever there is any tail
        # risk (required_capital > 0) above the simulated mean.
        loss_cost_total = sum(results.loss_cost.values())
        self.assertGreaterEqual(results.required_premium_programme, loss_cost_total)
        if results.required_capital[1] > 0.0:
            self.assertGreater(results.required_premium_programme, loss_cost_total)

        # Re-running (fresh AggregateFeatures/Simulation, unseeded Monte
        # Carlo) should still produce a well-formed, non-negative result.
        af2 = AggregateFeatures(
            experience_data=experience_data,
            exposure_data=exposure_model,
            selections=selections,
            assumptions=assumptions,
        )
        results2 = af2.run(n_simulations=1000)
        self.assertGreaterEqual(results2.required_premium_programme, 0.0)


if __name__ == "__main__":
    unittest.main()
