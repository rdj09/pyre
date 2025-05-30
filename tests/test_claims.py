import unittest
from datetime import date

from src.pyre.claims.claims import (
    ClaimYearType,
    ClaimDevelopmentHistory,
    ClaimsMetaData,
    Claim,
    Claims,
)
from pyre.exceptions.exceptions import ClaimsException

class TestClaimDevelopmentHistory(unittest.TestCase):
    def setUp(self):
        self.history = ClaimDevelopmentHistory(
            development_months=[1, 2, 3],
            cumulative_dev_paid=[1000.0, 2000.0, 3000.0],
            cumulative_dev_incurred=[1500.0, 2500.0, 3500.0],
        )

    def test_properties_and_setters(self):
        # Test property setters and getters
        self.history.development_months = [2, 4, 6]
        self.assertEqual(self.history.development_months, [2, 4, 6])
        self.history.cumulative_dev_paid = [10.0, 20.0, 30.0]
        self.assertEqual(self.history.cumulative_dev_paid, [10.0, 20.0, 30.0])
        self.history.cumulative_dev_incurred = [15.0, 25.0, 35.0]
        self.assertEqual(self.history.cumulative_dev_incurred, [15.0, 25.0, 35.0])

    def test_cumulative_reserved_amount(self):
        self.assertEqual(self.history.cumulative_reserved_amount, [500.0, 500.0, 500.0])

    def test_cumulative_reserved_amount_error(self):
        hist = ClaimDevelopmentHistory([1,2], [1.0,2.0], [1.0])
        with self.assertRaises(ValueError):
            _ = hist.cumulative_reserved_amount

    def test_latest_paid(self):
        self.assertEqual(self.history.latest_paid, 3000.0)
        empty = ClaimDevelopmentHistory()
        self.assertEqual(empty.latest_paid, 0.0)

    def test_latest_incurred(self):
        self.assertEqual(self.history.latest_incurred, 3500.0)
        empty = ClaimDevelopmentHistory()
        self.assertEqual(empty.latest_incurred, 0.0)

    def test_latest_reserved_amount(self):
        self.assertEqual(self.history.latest_reserved_amount, 500.0)
        empty = ClaimDevelopmentHistory()
        self.assertEqual(empty.latest_reserved_amount, 0.0)

    def test_latest_development_month(self):
        self.assertEqual(self.history.latest_development_month, 3)
        empty = ClaimDevelopmentHistory()
        self.assertEqual(empty.latest_development_month, 0)

    def test_incremental_dev_paid(self):
        self.assertEqual(self.history.incremental_dev_paid, [1000.0, 1000.0, 1000.0])

    def test_incremental_dev_incurred(self):
        self.assertEqual(self.history.incremental_dev_incurred, [1500.0, 1000.0, 1000.0])

    def test_incremental_dev_static(self):
        result = ClaimDevelopmentHistory.incremental_dev([2.0, 5.0, 9.0])
        self.assertEqual(result, [2.0, 3.0, 4.0])

    def test_mean_payment_duration(self):
        self.assertEqual(self.history.mean_payment_duration, 2.0)
        empty = ClaimDevelopmentHistory()
        self.assertIsNone(empty.mean_payment_duration)

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
            line_of_business="LOB",
            status="Closed"
        )

    def test_property_setters_and_getters(self):
        self.meta_data.claim_id = "456"
        self.assertEqual(self.meta_data.claim_id, "456")
        self.meta_data.currency = "GBP"
        self.assertEqual(self.meta_data.currency, "GBP")
        self.meta_data.contract_limit = 50000.0
        self.assertEqual(self.meta_data.contract_limit, 50000.0)
        self.meta_data.contract_deductible = 500.0
        self.assertEqual(self.meta_data.contract_deductible, 500.0)
        self.meta_data.claim_in_xs_of_deductible = False
        self.assertFalse(self.meta_data.claim_in_xs_of_deductible)
        self.meta_data.claim_year_basis = ClaimYearType.UNDERWRITING_YEAR
        self.assertEqual(self.meta_data.claim_year_basis, ClaimYearType.UNDERWRITING_YEAR)
        self.meta_data.loss_date = date(2022, 2, 2)
        self.assertEqual(self.meta_data.loss_date, date(2022, 2, 2))
        self.meta_data.policy_inception_date = date(2023, 3, 3)
        self.assertEqual(self.meta_data.policy_inception_date, date(2023, 3, 3))
        self.meta_data.report_date = date(2024, 4, 4)
        self.assertEqual(self.meta_data.report_date, date(2024, 4, 4))
        self.meta_data.line_of_business = "NEWLOB"
        self.assertEqual(self.meta_data.line_of_business, "NEWLOB")
        self.meta_data.status = "Open"
        self.assertEqual(self.meta_data.status, "Open")

    def test_modelling_year_accident_year(self):
        self.meta_data.claim_year_basis = ClaimYearType.ACCIDENT_YEAR
        self.assertEqual(self.meta_data.modelling_year, 2022)

    def test_modelling_year_underwriting_year(self):
        self.meta_data.claim_year_basis = ClaimYearType.UNDERWRITING_YEAR
        self.assertEqual(self.meta_data.modelling_year, 2023)

    def test_modelling_year_reported_year(self):
        self.meta_data.claim_year_basis = ClaimYearType.REPORTED_YEAR
        self.assertEqual(self.meta_data.modelling_year, 2024)

    def test_modelling_year_invalid_basis(self):
        class DummyYearType:
            pass
        self.meta_data.claim_year_basis = DummyYearType()
        with self.assertRaises(ClaimsException) as context:
            _ = self.meta_data.modelling_year
        self.assertEqual(context.exception.claim_id, self.meta_data.claim_id)
        self.assertEqual(context.exception.message, "Required date missing from data")

class TestClaim(unittest.TestCase):
    def setUp(self):
        self.meta_data = ClaimsMetaData(
            claim_id="123",
            currency="USD",
            contract_limit=100000.0,
            contract_deductible=100.0,
            claim_in_xs_of_deductible=False,
            loss_date=date(2020, 1, 1),
            policy_inception_date=date(2019, 1, 1),
            report_date=date(2021, 1, 1),
        )
        self.history = ClaimDevelopmentHistory(
            development_months=[1, 2, 3],
            cumulative_dev_paid=[1000.0, 2000.0, 3000.0],
            cumulative_dev_incurred=[1500.0, 2500.0, 3500.0],
        )
        self.claim = Claim(self.meta_data, self.history)

    def test_claims_meta_data_property(self):
        self.assertIs(self.claim.claims_meta_data, self.meta_data)

    def test_uncapped_claim_development_history(self):
        uncapped = self.claim.uncapped_claim_development_history
        self.assertEqual(uncapped.cumulative_dev_paid, [900.0, 1900.0, 2900.0])
        self.assertEqual(uncapped.cumulative_dev_incurred, [1400.0, 2400.0, 3400.0])

    def test_uncapped_claim_development_history_xs(self):
        self.meta_data.claim_in_xs_of_deductible = True
        uncapped = self.claim.uncapped_claim_development_history
        self.assertEqual(uncapped.cumulative_dev_paid, [1000.0, 2000.0, 3000.0])
        self.assertEqual(uncapped.cumulative_dev_incurred, [1500.0, 2500.0, 3500.0])

    def test_capped_claim_development_history(self):
        capped = self.claim.capped_claim_development_history
        self.assertEqual(capped.cumulative_dev_paid, [900.0, 1900.0, 2900.0])
        self.assertEqual(capped.cumulative_dev_incurred, [1400.0, 2400.0, 3400.0])

    def test_capped_claim_development_history_with_limit(self):
        self.meta_data.contract_limit = 2000.0
        capped = self.claim.capped_claim_development_history
        self.assertEqual(capped.cumulative_dev_paid, [900.0, 1900.0, 2000.0])
        self.assertEqual(capped.cumulative_dev_incurred, [1400.0, 2000.0, 2000.0])

    def test_repr(self):
        repr_str = repr(self.claim)
        self.assertIn("claim_id=123", repr_str)
        self.assertIn("modelling_year=2020", repr_str)
        self.assertIn("latest_incurred=3500.0", repr_str)
        self.assertIn("latest_capped_incurred=", repr_str)

class TestClaims(unittest.TestCase):
    def setUp(self):
        meta1 = ClaimsMetaData(
            claim_id="1",
            currency="USD",
            contract_limit=1000.0,
            contract_deductible=100.0,
            claim_in_xs_of_deductible=False,
            loss_date=date(2020, 1, 1),
            policy_inception_date=date(2019, 1, 1),
            report_date=date(2021, 1, 1),
        )
        meta2 = ClaimsMetaData(
            claim_id="2",
            currency="EUR",
            contract_limit=2000.0,
            contract_deductible=200.0,
            claim_in_xs_of_deductible=True,
            loss_date=date(2021, 1, 1),
            policy_inception_date=date(2020, 1, 1),
            report_date=date(2022, 1, 1),
        )
        hist1 = ClaimDevelopmentHistory(
            development_months=[1, 2],
            cumulative_dev_paid=[500.0, 900.0],
            cumulative_dev_incurred=[700.0, 1100.0],
        )
        hist2 = ClaimDevelopmentHistory(
            development_months=[1, 2, 3],
            cumulative_dev_paid=[1000.0, 1500.0, 2000.0],
            cumulative_dev_incurred=[1200.0, 1700.0, 2200.0],
        )
        self.claim1 = Claim(meta1, hist1)
        self.claim2 = Claim(meta2, hist2)
        self.claims = Claims([self.claim1, self.claim2])

    def test_claims_property(self):
        self.assertEqual(self.claims.claims, [self.claim1, self.claim2])
        self.claims.claims = [self.claim1]
        self.assertEqual(self.claims.claims, [self.claim1])

    def test_modelling_years(self):
        years = self.claims.modelling_years
        self.assertEqual(years, [2020, 2021])

    def test_development_periods(self):
        periods = self.claims.development_periods
        self.assertIn([1, 2], periods)
        self.assertIn([1, 2, 3], periods)

    def test_currencies(self):
        self.assertEqual(self.claims.currencies, {"USD", "EUR"})

    def test_append_and_len(self):
        meta3 = ClaimsMetaData(
            claim_id="3",
            currency="GBP",
            contract_limit=3000.0,
            contract_deductible=300.0,
            claim_in_xs_of_deductible=False,
            loss_date=date(2022, 1, 1),
            policy_inception_date=date(2021, 1, 1),
            report_date=date(2023, 1, 1),
        )
        hist3 = ClaimDevelopmentHistory(
            development_months=[1],
            cumulative_dev_paid=[100.0],
            cumulative_dev_incurred=[150.0],
        )
        claim3 = Claim(meta3, hist3)
        self.claims.append(claim3)
        self.assertEqual(len(self.claims), 2)

    def test_getitem_and_slice(self):
        self.assertIs(self.claims[0], self.claim1)
        sliced = self.claims[:1]
        self.assertIsInstance(sliced, Claims)
        self.assertEqual(len(sliced), 1)
        self.assertIs(sliced[0], self.claim1)

    def test_iter(self):
        claims_list = list(iter(self.claims))
        self.assertEqual(claims_list[0], self.claim1)
        self.assertEqual(claims_list[1], self.claim2)

if __name__ == "__main__":
    unittest.main()
