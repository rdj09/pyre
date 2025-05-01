import unittest
from datetime import date

from src.pyre.claims.claims import (
    ClaimYearType,
    ClaimDevelopmentHistory,
    ClaimsMetaData,
    Claim,
)

class TestClaimDevelopmentHistory(unittest.TestCase):
    def setUp(self):
        self.history = ClaimDevelopmentHistory(
            development_months=[1, 2, 3],
            cumulative_dev_paid=[1000.0, 2000.0, 3000.0],
            cumulative_dev_incurred=[1500.0, 2500.0, 3500.0],
        )

    def test_cumulative_reserved_amount(self):
        self.assertEqual(self.history.cumulative_reserved_amount, [500.0, 500.0, 500.0])

    def test_latest_paid(self):
        self.assertEqual(self.history.latest_paid, 3000.0)

    def test_latest_incurred(self):
        self.assertEqual(self.history.latest_incurred, 3500.0)

    def test_latest_reserved_amount(self):
        self.assertEqual(self.history.latest_reserved_amount, 500.0)

    def test_latest_development_month(self):
        self.assertEqual(self.history.latest_development_month, 3)

    def test_incremental_dev_paid(self):
        self.assertEqual(self.history.incremental_dev_paid, [1000.0,1000.0, 1000.0])

    def test_incremental_dev_incurred(self):
        self.assertEqual(self.history.incremental_dev_incurred, [1500.0,1000.0, 1000.0])

    def test_mean_payment_duration(self):
        self.assertEqual(self.history.mean_payment_duration, 2.0)


class TestClaimsMetaData(unittest.TestCase):
    def setUp(self):
        self.meta_data = ClaimsMetaData(
            claim_id="123",
            currency="USD",
            contract_limit=100000.0,
            contract_deductible=10000.0,
            claim_in_xs_of_deductible=True,
            claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
            loss_date=date(2020, 1, 1),
            policy_inception_date=date(2019, 1, 1),
            report_date=date(2021, 1, 1),
        )

    def test_modelling_year_accident_year(self):
        self.assertEqual(self.meta_data.modelling_year, 2020)

    def test_modelling_year_underwriting_year(self):
        self.meta_data.claim_year_basis = ClaimYearType.UNDERWRITING_YEAR
        self.assertEqual(self.meta_data.modelling_year, 2019)

    def test_modelling_year_reported_year(self):
        self.meta_data.claim_year_basis = ClaimYearType.REPORTED_YEAR
        self.assertEqual(self.meta_data.modelling_year, 2021)


class TestClaim(unittest.TestCase):
    def setUp(self):
        self.meta_data = ClaimsMetaData(
            claim_id="123",
            currency="USD",
            contract_limit=100000.0,
            contract_deductible=100.0,
            claim_in_xs_of_deductible=False,
        )
        self.history = ClaimDevelopmentHistory(
            development_months=[1, 2, 3],
            cumulative_dev_paid=[1000.0, 2000.0, 3000.0],
            cumulative_dev_incurred=[1500.0, 2500.0, 3500.0],
        )
        self.claim = Claim(self.meta_data, self.history)

    def test_uncapped_claim_development_history(self):
        uncapped = self.claim.uncapped_claim_development_history
        self.assertEqual(uncapped.cumulative_dev_paid, [900.0, 1900.0, 2900.0])
        self.assertEqual(uncapped.cumulative_dev_incurred, [1400.0, 2400.0, 3400.0])

    def test_capped_claim_development_history(self):
        capped = self.claim.capped_claim_development_history
        self.assertEqual(capped.cumulative_dev_paid, [900.0, 1900.0, 2900.0])
        self.assertEqual(capped.cumulative_dev_incurred, [1400.0, 2400.0, 3400.0])

    def test_repr(self):
        repr_str = repr(self.claim)
        self.assertIn("claim_id=123", repr_str)
        self.assertIn("modelling_year=0", repr_str)
        self.assertIn("latest_incurred=3500.0", repr_str)


if __name__ == "__main__":
    unittest.main()