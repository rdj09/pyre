import unittest
from datetime import date
from pyre.treaty import (
    ContractType,
    RILayer,
    RIContractMetadata,
    RIContract,
    ClaimTriggerBasis,
    IndexationClauseType,
)
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


if __name__ == "__main__":
    unittest.main()
