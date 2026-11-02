import unittest
from datetime import date
from pyre.treaty import (
    ContractType,
    RILayer,
    RIContractMetadata,
    RIContract,
    ClaimTriggerBasis,
    IndexationClauseType,
    xol_calculation,
    franchise_calculation,
)
from pyre.treaty.layer_loss_functions import surplus_share_calculation
from pyre.claims.claims import ClaimYearType  # Ensure this import is correct

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


class TestSurplusShareCalculation(unittest.TestCase):
    def test_matches_clark_worked_example(self):
        """Golden value from Clark, D.R. (1996/2014), Basics of Reinsurance
        Pricing, CAS Study Note, p.3:
        Retained line $100,000; 1st Surplus 4 lines ($400,000).
        sum_insured -> expected cession %:
          50,000 -> 0%; 100,000 -> 0%; 250,000 -> 60%; 500,000 -> 80%;
          1,000,000 -> 40%; 10,000,000 -> 4%
        """
        cases = [
            (50_000, 0.0), (100_000, 0.0), (250_000, 0.60),
            (500_000, 0.80), (1_000_000, 0.40), (10_000_000, 0.04),
        ]
        for sum_insured, expected_pct in cases:
            with self.subTest(sum_insured=sum_insured):
                result = surplus_share_calculation(
                    gross_amount=1.0, sum_insured=sum_insured,
                    retained_line=100_000, surplus_limit=400_000,
                )
                self.assertAlmostEqual(result, expected_pct, places=4)


def _build_layer(layer_type, sum_insured=None, occurrence_attachment=100000,
                  occurrence_limit=200000, **overrides):
    """Module-level RILayer builder for loss_to_layer_fn tests, with
    sensible defaults for fields unrelated to the test in question."""
    fields = dict(
        layer_id=1,
        layer_name="Layer 1",
        layer_type=layer_type,
        occurrence_attachment=occurrence_attachment,
        occurrence_limit=occurrence_limit,
        aggregate_attachment=200000,
        aggregate_limit=1000000,
        subject_lines_of_business=["LOB1"],
        subject_lob_exposure_amounts=[1000000],
        full_subject_premium=50000,
        written_line=0.8,
        signed_line=0.7,
        number_of_reinstatements=2,
        reinstatement_cost={1: 1.0},
        sum_insured=sum_insured,
    )
    fields.update(overrides)
    return RILayer(**fields)


class TestRILayerLossToLayerFn(unittest.TestCase):
    def _make_layer(self, layer_type):
        return _build_layer(layer_type)

    def test_xol_loss_to_layer_fn_returns_computed_value(self):
        layer = self._make_layer(ContractType.EXCESS_OF_LOSS)
        result = layer.loss_to_layer_fn(250000)
        self.assertEqual(result, xol_calculation(250000, 100000, 200000))
        self.assertIsInstance(result, (int, float))

    def test_franchise_loss_to_layer_fn_returns_computed_value(self):
        layer = self._make_layer(ContractType.FRANCHISE_DEDUCTIBLE)
        result = layer.loss_to_layer_fn(250000)
        self.assertEqual(result, franchise_calculation(250000, 100000, 200000))
        self.assertIsInstance(result, (int, float))

    def test_aggregate_stop_loss_loss_to_layer_fn_returns_computed_value(self):
        layer = self._make_layer(ContractType.AGGREGATE_STOP_LOSS)
        result = layer.loss_to_layer_fn(250000)
        self.assertEqual(result, xol_calculation(250000, 100000, 200000))
        self.assertIsInstance(result, (int, float))

    def test_quota_share_loss_to_layer_fn_returns_gross_unchanged(self):
        layer = self._make_layer(ContractType.QUOTA_SHARE)
        self.assertEqual(layer.loss_to_layer_fn(123456), 123456)

    def test_loss_to_layer_fn_surplus_share_without_sum_insured_raises(self):
        layer = _build_layer(layer_type=ContractType.SURPLUS_SHARE, sum_insured=None)
        with self.assertRaises(ValueError):
            layer.loss_to_layer_fn(50_000)

    def test_loss_to_layer_fn_surplus_share_applies_cession_to_gross_loss(self):
        # Clark risk 5: sum_insured=1,000,000, retained_line=100,000,
        # surplus_limit=400,000 -> 40% cession.
        layer = _build_layer(
            layer_type=ContractType.SURPLUS_SHARE, sum_insured=1_000_000,
            occurrence_attachment=100_000, occurrence_limit=400_000,
        )
        self.assertAlmostEqual(layer.loss_to_layer_fn(50_000), 20_000, places=2)


if __name__ == "__main__":
    unittest.main()
