import unittest
from datetime import date

import pytest

from pyre.claims.claims import ClaimYearType  # Ensure this import is correct
from pyre.treaty import (
    ClaimTriggerBasis,
    ContractType,
    IndexationClauseType,
    RIContract,
    RIContractMetadata,
    RILayer,
)
from pyre.treaty.layer_loss_functions import (
    franchise_calculation,
    qs_calculation,
    surplus_share_calculation,
    xol_calculation,
)


class TestRILayer(unittest.TestCase):
    def setUp(self):
        self.layer = RILayer(
            layer_id=1,
            layer_name="Layer 1",
            layer_type=ContractType.QUOTA_SHARE,
            occurrence_attachment=100000,
            occurrence_limit=500000,
            aggregate_attachment=200000,
            aggregate_limit=1000000,
            subject_lines_of_business=["LOB1", "LOB2"],
            subject_lob_exposure_amounts=[1000000, 2000000],
            full_subject_premium=50000,
            written_line=0.8,
            signed_line=0.7,
            number_of_reinstatements=2,
            reinstatement_cost={1: 1.0, 2: 1.25},
            cession=0.9,
        )

    def test_written_line_premium(self):
        self.assertAlmostEqual(self.layer.written_line_premium, 36000)

    def test_signed_line_premium(self):
        self.assertAlmostEqual(self.layer.signed_line_premium, 31500)


class TestRIContractMetadata(unittest.TestCase):
    def setUp(self):
        self.metadata = RIContractMetadata(
            contract_id=101,
            contract_description="Test Contract",
            cedent_name="Test Cedent",
            trigger_basis=ClaimTriggerBasis.RAD,
            indexation_clause=IndexationClauseType.FULL_INDEXATION,
            indexation_margin=0.05,
            inception_date=date(2025, 1, 1),
            expiration_date=date(2025, 12, 31),
            fx_rates={"GBP": 1.0, "USD": 1.25},
        )

    def test_claim_year_basis(self):
        self.assertEqual(self.metadata.claim_year_basis, ClaimYearType.UNDERWRITING_YEAR)

    def test_fx_rates(self):
        self.assertEqual(self.metadata.fx_rates["USD"], 1.25)


class TestRIContract(unittest.TestCase):
    def setUp(self):
        self.metadata = RIContractMetadata(
            contract_id=101,
            contract_description="Test Contract",
            cedent_name="Test Cedent",
            trigger_basis=ClaimTriggerBasis.RAD,
            indexation_clause=IndexationClauseType.FULL_INDEXATION,
            indexation_margin=0.05,
            inception_date=date(2025, 1, 1),
            expiration_date=date(2025, 12, 31),
            fx_rates={"GBP": 1.0, "USD": 1.25},
        )
        self.layers = [
            RILayer(
                layer_id=1,
                layer_name="Layer 1",
                layer_type=ContractType.QUOTA_SHARE,
                occurrence_attachment=100000,
                occurrence_limit=500000,
                aggregate_attachment=200000,
                aggregate_limit=1000000,
                subject_lines_of_business=["LOB1", "LOB2"],
                subject_lob_exposure_amounts=[1000000, 2000000],
                full_subject_premium=50000,
                written_line=0.8,
                signed_line=0.7,
                number_of_reinstatements=2,
                reinstatement_cost={1: 1.0, 2: 1.25},
                cession=0.9,
            )
        ]
        self.contract = RIContract(contract_meta_data=self.metadata, layers=self.layers)

    def test_contract_metadata(self):
        self.assertEqual(self.contract._contract_meta_data.contract_id, 101)

    def test_contract_layers(self):
        self.assertEqual(len(self.contract._layers), 1)
        self.assertEqual(self.contract._layers[0].layer_id, 1)
        self.assertEqual(self.contract._layers[0].layer_name, "Layer 1")


def _make_xol_layer() -> RILayer:
    return RILayer(
        layer_id=1,
        layer_name="1m xs 1m",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=1_000_000.0,
        occurrence_limit=1_000_000.0,
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[10_000_000.0],
        full_subject_premium=500_000.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=1,
        reinstatement_cost={1: 1.0},
    )


def test_loss_to_layer_fn_xol_below_attachment():
    layer = _make_xol_layer()
    assert layer.loss_to_layer_fn(500_000.0) == pytest.approx(0.0)


def test_loss_to_layer_fn_xol_in_layer():
    layer = _make_xol_layer()
    assert layer.loss_to_layer_fn(1_500_000.0) == pytest.approx(500_000.0)


def test_loss_to_layer_fn_xol_above_limit():
    layer = _make_xol_layer()
    assert layer.loss_to_layer_fn(5_000_000.0) == pytest.approx(1_000_000.0)


def test_loss_to_layer_fn_quota_share_passes_through():
    layer = RILayer(
        layer_id=2,
        layer_name="QS",
        layer_type=ContractType.QUOTA_SHARE,
        occurrence_attachment=0.0,
        occurrence_limit=float("inf"),
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[1_000_000.0],
        full_subject_premium=100_000.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=0,
        reinstatement_cost={},
    )
    assert layer.loss_to_layer_fn(250_000.0) == pytest.approx(250_000.0)


def test_loss_to_layer_fn_surplus_share_raises():
    layer = RILayer(
        layer_id=3,
        layer_name="SS",
        layer_type=ContractType.SURPLUS_SHARE,
        occurrence_attachment=0.0,
        occurrence_limit=float("inf"),
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=[],
        subject_lob_exposure_amounts=[],
        full_subject_premium=0.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=0,
        reinstatement_cost={},
    )
    with pytest.raises(NotImplementedError):
        layer.loss_to_layer_fn(100_000.0)


def test_loss_to_layer_fn_franchise_above_attachment():
    layer = RILayer(
        layer_id=4,
        layer_name="Franchise",
        layer_type=ContractType.FRANCHISE_DEDUCTIBLE,
        occurrence_attachment=500_000.0,
        occurrence_limit=2_000_000.0,
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[5_000_000.0],
        full_subject_premium=200_000.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=0,
        reinstatement_cost={},
    )
    # Above attachment — full gross amount paid up to limit
    assert layer.loss_to_layer_fn(1_000_000.0) == pytest.approx(1_000_000.0)


def test_loss_to_layer_fn_franchise_below_attachment():
    layer = RILayer(
        layer_id=4,
        layer_name="Franchise",
        layer_type=ContractType.FRANCHISE_DEDUCTIBLE,
        occurrence_attachment=500_000.0,
        occurrence_limit=2_000_000.0,
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[5_000_000.0],
        full_subject_premium=200_000.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=0,
        reinstatement_cost={},
    )
    # Below attachment — zero recovery
    assert layer.loss_to_layer_fn(400_000.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Direct tests for layer_loss_functions (bring coverage above 80%)
# ---------------------------------------------------------------------------


def test_xol_calculation_in_layer():
    assert xol_calculation(1_500_000.0, 1_000_000.0, 1_000_000.0) == pytest.approx(500_000.0)


def test_xol_calculation_above_limit():
    assert xol_calculation(3_000_000.0, 1_000_000.0, 1_000_000.0) == pytest.approx(1_000_000.0)


def test_xol_calculation_below_attachment():
    assert xol_calculation(500_000.0, 1_000_000.0, 1_000_000.0) == pytest.approx(0.0)


def test_qs_calculation():
    assert qs_calculation(1_000_000.0, 0.5) == pytest.approx(500_000.0)


def test_qs_calculation_zero_gross():
    assert qs_calculation(0.0, 0.3) == pytest.approx(0.0)


def test_franchise_calculation_above():
    assert franchise_calculation(800_000.0, 500_000.0, 2_000_000.0) == pytest.approx(800_000.0)


def test_franchise_calculation_above_limit():
    assert franchise_calculation(3_000_000.0, 500_000.0, 2_000_000.0) == pytest.approx(2_000_000.0)


def test_franchise_calculation_below_attachment():
    assert franchise_calculation(300_000.0, 500_000.0, 2_000_000.0) == pytest.approx(0.0)


def test_surplus_share_no_surplus():
    # sum_insured <= attachment: no cession
    assert surplus_share_calculation(1_000_000.0, 500_000.0, 500_000.0) == pytest.approx(0.0)


def test_surplus_share_with_surplus():
    # sum_insured = 2m, attachment = 1m → share = 50%
    result = surplus_share_calculation(1_000_000.0, 2_000_000.0, 1_000_000.0)
    assert result == pytest.approx(500_000.0)


if __name__ == "__main__":
    unittest.main()
