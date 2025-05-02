import unittest
from datetime import date
from pyre.claims.claims import Claim, ClaimsMetaData, ClaimDevelopmentHistory
from pyre.claims.claims_aggregator import ClaimAggregator


class TestClaimAggregator(unittest.TestCase):
    def setUp(self):
        # Create sample ClaimsMetaData objects
        self.claims_meta_data_1 = ClaimsMetaData(
            claim_id="001",
            currency="USD",
            contract_limit=100000.0,
            contract_deductible=5000.0,
            claim_in_xs_of_deductible=True,
            loss_date=date(2023, 1, 1),
            status="Open"
        )

        self.claims_meta_data_2 = ClaimsMetaData(
            claim_id="002",
            currency="EUR",
            contract_limit=50000.0,
            contract_deductible=10000.0,
            claim_in_xs_of_deductible=False,
            loss_date=date(2023, 1, 1),
            status="Closed"
        )

        self.claims_meta_data_3 = ClaimsMetaData(
            claim_id="003",
            currency="USD",
            contract_limit=75000.0,
            contract_deductible=2000.0,
            claim_in_xs_of_deductible=True,
            loss_date=date(2024, 1, 1),
            status="Open"
        )

        # Create sample ClaimDevelopmentHistory objects
        self.claim_dev_history_1 = ClaimDevelopmentHistory(
            development_months=[1, 2, 3],
            cumulative_dev_paid=[1000.0, 2000.0, 3000.0],
            cumulative_dev_incurred=[1500.0, 2500.0, 3500.0]
        )

        self.claim_dev_history_2 = ClaimDevelopmentHistory(
            development_months=[1, 2, 3],
            cumulative_dev_paid=[2000.0, 3000.0, 4000.0],
            cumulative_dev_incurred=[2500.0, 3500.0, 4500.0]
        )

        self.claim_dev_history_3 = ClaimDevelopmentHistory(
            development_months=[1, 2, 3],
            cumulative_dev_paid=[500.0, 1500.0, 2500.0],
            cumulative_dev_incurred=[1000.0, 2000.0, 3000.0]
        )

        # Create Claim objects
        self.claim_1 = Claim(self.claims_meta_data_1, self.claim_dev_history_1)
        self.claim_2 = Claim(self.claims_meta_data_2, self.claim_dev_history_2)
        self.claim_3 = Claim(self.claims_meta_data_3, self.claim_dev_history_3)

        # Create ClaimAggregator
        self.aggregator = ClaimAggregator([self.claim_1, self.claim_2, self.claim_3])

    def test_aggregate_by_currency(self):
        result = self.aggregator.aggregate_by_attribute(["currency"])
        self.assertIn(("USD",), result)
        self.assertIn(("EUR",), result)
        self.assertEqual(result[("USD",)]["number_of_claims"], 2)
        self.assertEqual(result[("EUR",)]["number_of_claims"], 1)

    def test_aggregate_by_modelling_year(self):
        result = self.aggregator.aggregate_by_attribute(["modelling_year"])
        self.assertIn((2023,), result)
        self.assertIn((2024,), result)
        self.assertEqual(result[(2023,)]["number_of_claims"], 2)
        self.assertEqual(result[(2024,)]["number_of_claims"], 1)

    def test_aggregate_by_currency_and_year(self):
        result = self.aggregator.aggregate_by_attribute(["currency", "modelling_year"])
        self.assertIn(("USD", 2023), result)
        self.assertIn(("EUR", 2023), result)
        self.assertIn(("USD", 2024), result)
        self.assertEqual(result[("USD", 2023)]["number_of_claims"], 1)
        self.assertEqual(result[("EUR", 2023)]["number_of_claims"], 1)
        self.assertEqual(result[("USD", 2024)]["number_of_claims"], 1)

    def test_total_paid_aggregation(self):
        result = self.aggregator.aggregate_by_attribute(["currency"])
        self.assertAlmostEqual(result[("USD",)]["total_paid"], 3000.0 + 2500.0)
        self.assertAlmostEqual(result[("EUR",)]["total_paid"], 4000.0)

    def test_total_incurred_aggregation(self):
        result = self.aggregator.aggregate_by_attribute(["modelling_year"])
        self.assertAlmostEqual(result[(2023,)]["total_incurred"], 3500.0 + 4500.0)
        self.assertAlmostEqual(result[(2024,)]["total_incurred"], 3000.0)


if __name__ == "__main__":
    unittest.main()