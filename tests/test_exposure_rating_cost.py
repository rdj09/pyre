import unittest
from datetime import date

from pyre import (
    Exposure,
    ExposureMetaData,
    Exposures,
    ExposureValues,
    RIContract,
    RIContractMetadata,
    RILayer,
)
from pyre.models.Exposure.exposure_curve_functions import ExposureCurveType, mbbefd_curve
from pyre.models.Exposure.exposure_rating_cost import ExposureModel
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType


def _build_contract(layers):
    metadata = RIContractMetadata(
        contract_id="C-0001",
        contract_description="Test",
        cedent_name="Acme Re",
        trigger_basis=ClaimTriggerBasis.LOD,
        indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0,
        inception_date=date(2023, 1, 1),
        expiration_date=date(2023, 12, 31),
        fx_rates={"USD": 1.0},
    )
    return RIContract(contract_meta_data=metadata, layers=layers)


def _build_layer(layer_id, occurrence_attachment, occurrence_limit):
    return RILayer(
        layer_id=layer_id,
        layer_name=f"Layer {layer_id}",
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


def _build_exposure(exposure_id, attachment_point, limit):
    meta = ExposureMetaData(
        exposure_id=exposure_id,
        exposure_name=exposure_id,
        exposure_period_start=date(2023, 1, 1),
        exposure_period_end=date(2023, 12, 31),
        currency="USD",
    )
    values = ExposureValues(
        exposure_value=attachment_point + limit,
        attachment_point=attachment_point,
        limit=limit,
    )
    return Exposure(exposure_meta=meta, exposure_values=values)


class TestCalculateAllShares(unittest.TestCase):
    def setUp(self):
        # Policy: attachment 0, limit 1,000,000 -> total_insured_value 1,000,000.
        self.exposure = _build_exposure("EXP001", attachment_point=0.0, limit=1_000_000.0)
        self.exposures = Exposures([self.exposure])
        self.curve_param = 3.0

    def test_layer_fitting_inside_policy_limit_is_included(self):
        # 400,000 + 100,000 = 500,000 < 1,000,000 policy limit -> "if" branch,
        # previously never added to shares_by_layer at all.
        layer = _build_layer(
            layer_id=1, occurrence_attachment=100_000.0, occurrence_limit=400_000.0
        )
        contract = _build_contract([layer])
        model = ExposureModel(
            exposures=self.exposures,
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": self.curve_param},
        )

        shares = model.calculate_all_shares()

        self.assertIn("EXP001", shares)
        self.assertIn(1, shares["EXP001"])

        expected = (
            mbbefd_curve(self.curve_param, 500_000.0 / 1_000_000.0)
            - mbbefd_curve(self.curve_param, 100_000.0 / 1_000_000.0)
        ) / (
            mbbefd_curve(self.curve_param, 1.0) - mbbefd_curve(self.curve_param, 0.0)
        )
        self.assertAlmostEqual(shares["EXP001"][1], expected)

    def test_layer_exceeding_policy_limit_is_included(self):
        # 600,000 + 500,000 = 1,100,000 >= 1,000,000 policy limit -> "else" branch.
        layer = _build_layer(
            layer_id=2, occurrence_attachment=500_000.0, occurrence_limit=600_000.0
        )
        contract = _build_contract([layer])
        model = ExposureModel(
            exposures=self.exposures,
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": self.curve_param},
        )

        shares = model.calculate_all_shares()

        expected = (
            mbbefd_curve(self.curve_param, 1.0)
            - mbbefd_curve(self.curve_param, 500_000.0 / 1_000_000.0)
        ) / (
            mbbefd_curve(self.curve_param, 1.0) - mbbefd_curve(self.curve_param, 0.0)
        )
        self.assertAlmostEqual(shares["EXP001"][2], expected)

    def test_both_layer_types_present_simultaneously(self):
        layer_inside = _build_layer(
            layer_id=1, occurrence_attachment=100_000.0, occurrence_limit=400_000.0
        )
        layer_outside = _build_layer(
            layer_id=2, occurrence_attachment=500_000.0, occurrence_limit=600_000.0
        )
        contract = _build_contract([layer_inside, layer_outside])
        model = ExposureModel(
            exposures=self.exposures,
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": self.curve_param},
        )

        shares = model.calculate_all_shares()

        self.assertEqual(set(shares["EXP001"].keys()), {1, 2})

    def test_empty_exposures_returns_empty_dict(self):
        layer = _build_layer(
            layer_id=1, occurrence_attachment=100_000.0, occurrence_limit=400_000.0
        )
        contract = _build_contract([layer])
        model = ExposureModel(
            exposures=Exposures([]),
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": self.curve_param},
        )

        self.assertEqual(model.calculate_all_shares(), {})

    def test_zero_layers_gives_empty_share_dict_per_exposure(self):
        contract = _build_contract([])
        model = ExposureModel(
            exposures=self.exposures,
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": self.curve_param},
        )

        self.assertEqual(model.calculate_all_shares(), {"EXP001": {}})

    def test_duplicate_exposure_id_raises_instead_of_silently_dropping(self):
        duplicate_a = _build_exposure("E1", attachment_point=0.0, limit=500_000.0)
        duplicate_b = _build_exposure("E1", attachment_point=0.0, limit=500_000.0)
        contract = _build_contract(
            [_build_layer(layer_id=1, occurrence_attachment=0.0, occurrence_limit=500_000.0)]
        )
        model = ExposureModel(
            exposures=Exposures([duplicate_a, duplicate_b]),
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": self.curve_param},
        )

        with self.assertRaises(ValueError):
            model.calculate_all_shares()


if __name__ == "__main__":
    unittest.main()
