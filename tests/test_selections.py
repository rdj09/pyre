import inspect
import unittest
from datetime import date
from unittest.mock import Mock

from pyre import (
    Claim,
    ClaimDevelopmentHistory,
    Claims,
    ClaimsMetaData,
    Exposures,
    RIContract,
    RIContractMetadata,
    RILayer,
)
from pyre.models.AggregateFeatures.selections import CredibilityWeight, Selections
from pyre.models.Experience.experience_preparer import ExperienceModelData
from pyre.models.Exposure.exposure_rating_cost import ExposureModel
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType


def _build_model_data(claims, layers):
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
    contract = RIContract(contract_meta_data=metadata, layers=layers)
    return ExperienceModelData(claims=claims, exposures=Exposures([]), ri_contract=contract)


def _layer(layer_id: int = 1, layer_name: str = "XOL Layer"):
    return RILayer(
        layer_id=layer_id,
        layer_name=layer_name,
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=100_000.0,
        occurrence_limit=200_000.0,
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


def _claim(claim_id: str, year: int = 2022):
    return Claim(
        ClaimsMetaData(
            claim_id=claim_id,
            currency="USD",
            contract_limit=2_000_000.0,
            loss_date=date(year, 3, 1),
        ),
        ClaimDevelopmentHistory(
            development_months=[12, 24],
            cumulative_dev_paid=[50000.0, 90000.0],
            cumulative_dev_incurred=[120000.0, 250000.0],
        ),
    )


class TestCalculateExperienceWeight(unittest.TestCase):
    def setUp(self):
        self.experience_data = _build_model_data(
            Claims([_claim("CLM001"), _claim("CLM002")]), [_layer()]
        )
        self.exposure_data = Mock(spec=ExposureModel)
        self.selections = Selections(
            experience_data=self.experience_data, exposure_data=self.exposure_data
        )

    def test_greatest_accuracy_branch_does_not_raise_with_real_experience_data(self):
        weight = self.selections.calculate_experience_weight(
            method="greatest_accuracy", collective_mean=1.0
        )
        self.assertGreaterEqual(weight, 0.0)
        self.assertLessEqual(weight, 1.0)

    def test_bayesian_branch_does_not_raise_with_real_experience_data(self):
        weight = self.selections.calculate_experience_weight(
            method="bayesian", prior_mean=1.0, prior_variance=0.1
        )
        self.assertGreaterEqual(weight, 0.0)
        self.assertLessEqual(weight, 1.0)

    def test_limited_fluctuation_claim_count_sums_claims_across_all_layers(self):
        experience_data = _build_model_data(
            Claims([_claim("CLM001"), _claim("CLM002"), _claim("CLM003")]),
            [_layer(1, "Layer 1"), _layer(2, "Layer 2")],
        )
        selections = Selections(experience_data=experience_data, exposure_data=self.exposure_data)

        selections.calculate_experience_weight(method="limited_fluctuation")

        # 3 claims x 2 layers = 6 claims total across subject_contract_claims.values()
        expected_weight = (6 / 1082) ** 0.5
        self.assertAlmostEqual(selections._experience_weight, expected_weight)


class TestFullCredibilityStandard(unittest.TestCase):
    def test_full_credibility_standard_matches_cas_exam_5_standard(self):
        """1,082 claims is the well-known Poisson full-credibility standard for
        +/-5% at 95% confidence (Mahler & Dean, Ch.8, Foundations of Casualty
        Actuarial Science, 4th ed., CAS)."""
        cw = CredibilityWeight(experience_data=Mock(), exposure_data=Mock())
        default = inspect.signature(cw.limited_fluctuation_credibility).parameters[
            "full_credibility_standard"
        ].default
        self.assertEqual(default, 1082)


if __name__ == "__main__":
    unittest.main()
