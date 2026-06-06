import unittest
from datetime import date
from pyre.Models.trending import (
    Trending,
    calculate_trend_factor,
    trend_exposures,
    trend_claims,
    get_trend_factors
)
from pyre.claims.claims import (
    ClaimYearType,
    ClaimDevelopmentHistory,
    ClaimsMetaData,
    Claim,
    Claims,
)
from pyre.exposures.exposures import (
    ExposureBasis,
    ExposureMetaData,
    ExposureValues,
    Exposure,
    Exposures,
)

class TestTrending(unittest.TestCase):
    def setUp(self):
        # Create trend factors for testing
        self.exposure_trend_factors = {2020: 1.0, 2021: 1.05, 2022: 1.1, 2023: 1.15}
        self.claim_trend_factors = {2020: 1.0, 2021: 1.08, 2022: 1.16, 2023: 1.25}
        
        # Create a Trending instance
        self.trending = Trending(
            exposure_trend_factors=self.exposure_trend_factors,
            claim_trend_factors=self.claim_trend_factors,
            base_year=2020
        )
        
        # Create sample claims for testing
        self.claim_meta_1 = ClaimsMetaData(
            claim_id="CLM001",
            currency="USD",
            claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
            loss_date=date(2021, 6, 15)
        )
        self.claim_dev_1 = ClaimDevelopmentHistory(
            development_months=[12, 24],
            cumulative_dev_paid=[50000, 75000],
            cumulative_dev_incurred=[100000, 110000]
        )
        self.claim_1 = Claim(self.claim_meta_1, self.claim_dev_1)
        
        self.claim_meta_2 = ClaimsMetaData(
            claim_id="CLM002",
            currency="USD",
            claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
            loss_date=date(2022, 3, 10)
        )
        self.claim_dev_2 = ClaimDevelopmentHistory(
            development_months=[12],
            cumulative_dev_paid=[30000],
            cumulative_dev_incurred=[80000]
        )
        self.claim_2 = Claim(self.claim_meta_2, self.claim_dev_2)
        
        self.claims = Claims([self.claim_1, self.claim_2])
        
        # Create sample exposures for testing
        self.exposure_meta_1 = ExposureMetaData(
            exposure_id="EXP001",
            exposure_name="Exposure 1",
            exposure_period_start=date(2021, 1, 1),
            exposure_period_end=date(2021, 12, 31),
            currency="USD"
        )
        self.exposure_values_1 = ExposureValues(
            exposure_value=1000000,
            attachment_point=0,
            limit=1000000
        )
        self.exposure_1 = Exposure(self.exposure_meta_1, self.exposure_values_1)
        
        self.exposure_meta_2 = ExposureMetaData(
            exposure_id="EXP002",
            exposure_name="Exposure 2",
            exposure_period_start=date(2022, 1, 1),
            exposure_period_end=date(2022, 12, 31),
            currency="USD"
        )
        self.exposure_values_2 = ExposureValues(
            exposure_value=1200000,
            attachment_point=0,
            limit=1200000
        )
        self.exposure_2 = Exposure(self.exposure_meta_2, self.exposure_values_2)
        
        self.exposures = Exposures([self.exposure_1, self.exposure_2])
    
    def test_validate_inputs(self):
        # Test with valid inputs
        self.trending._validate_inputs()  # Should not raise any exceptions
        
        # Test with invalid inputs (missing base_year)
        trending_no_base = Trending(
            exposure_trend_factors=self.exposure_trend_factors,
            claim_trend_factors=self.claim_trend_factors
        )
        with self.assertRaises(ValueError):
            trending_no_base._validate_inputs()
    
    def test_calculate_trend_factor(self):
        # Test exposure trend factor calculation
        factor = self.trending.calculate_trend_factor(2021, for_claims=False)
        self.assertEqual(factor, 1.05)
        
        # Test claim trend factor calculation
        factor = self.trending.calculate_trend_factor(2022, for_claims=True)
        self.assertEqual(factor, 1.16)
        
        # Test with year not in trend factors
        with self.assertRaises(KeyError):
            self.trending.calculate_trend_factor(2019, for_claims=False)
    
    def test_trend_exposures(self):
        # Trend the exposures
        trended_exposures = self.trending.trend_exposures(self.exposures)
        
        # Check that we got an Exposures object back
        self.assertIsInstance(trended_exposures, Exposures)
        
        # Check that the exposure values were trended correctly
        self.assertAlmostEqual(trended_exposures[0].exposure_values.exposure_value, 1000000 / 1.05)
        self.assertAlmostEqual(trended_exposures[1].exposure_values.exposure_value, 1200000 / 1.1)
    
    def test_trend_claims(self):
        # Trend the claims
        trended_claims = self.trending.trend_claims(self.claims)
        
        # Check that we got a Claims object back
        self.assertIsInstance(trended_claims, Claims)
        
        # Check that the claim values were trended correctly
        # For claim 1 (2021), the trend factor is 1.08
        self.assertAlmostEqual(
            trended_claims[0].uncapped_claim_development_history.cumulative_dev_paid[0],
            50000 / 1.08
        )
        self.assertAlmostEqual(
            trended_claims[0].uncapped_claim_development_history.cumulative_dev_incurred[0],
            100000 / 1.08
        )
        
        # For claim 2 (2022), the trend factor is 1.16
        self.assertAlmostEqual(
            trended_claims[1].uncapped_claim_development_history.cumulative_dev_paid[0],
            30000 / 1.16
        )
        self.assertAlmostEqual(
            trended_claims[1].uncapped_claim_development_history.cumulative_dev_incurred[0],
            80000 / 1.16
        )
    
    def test_get_trend_factors(self):
        # Get the trend factors
        factors = self.trending.get_trend_factors()
        
        # Check that we got a dictionary back
        self.assertIsInstance(factors, dict)
        
        # Check that the dictionary contains the expected keys
        self.assertIn('exposure', factors)
        self.assertIn('claim', factors)
        self.assertIn('base_year', factors)
        
        # Check that the values are correct
        self.assertEqual(factors['exposure'], self.exposure_trend_factors)
        self.assertEqual(factors['claim'], self.claim_trend_factors)
        self.assertEqual(factors['base_year'], 2020)

class TestStandaloneFunctions(unittest.TestCase):
    def setUp(self):
        # Create trend factors for testing
        self.trend_factors = {2020: 1.0, 2021: 1.05, 2022: 1.1, 2023: 1.15}
        self.base_year = 2020
        
        # Create sample claims for testing
        self.claim_meta_1 = ClaimsMetaData(
            claim_id="CLM001",
            currency="USD",
            claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
            loss_date=date(2021, 6, 15)
        )
        self.claim_dev_1 = ClaimDevelopmentHistory(
            development_months=[12, 24],
            cumulative_dev_paid=[50000, 75000],
            cumulative_dev_incurred=[100000, 110000]
        )
        self.claim_1 = Claim(self.claim_meta_1, self.claim_dev_1)
        
        self.claim_meta_2 = ClaimsMetaData(
            claim_id="CLM002",
            currency="USD",
            claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
            loss_date=date(2022, 3, 10)
        )
        self.claim_dev_2 = ClaimDevelopmentHistory(
            development_months=[12],
            cumulative_dev_paid=[30000],
            cumulative_dev_incurred=[80000]
        )
        self.claim_2 = Claim(self.claim_meta_2, self.claim_dev_2)
        
        self.claims = Claims([self.claim_1, self.claim_2])
        
        # Create sample exposures for testing
        self.exposure_meta_1 = ExposureMetaData(
            exposure_id="EXP001",
            exposure_name="Exposure 1",
            exposure_period_start=date(2021, 1, 1),
            exposure_period_end=date(2021, 12, 31),
            currency="USD"
        )
        self.exposure_values_1 = ExposureValues(
            exposure_value=1000000,
            attachment_point=0,
            limit=1000000
        )
        self.exposure_1 = Exposure(self.exposure_meta_1, self.exposure_values_1)
        
        self.exposure_meta_2 = ExposureMetaData(
            exposure_id="EXP002",
            exposure_name="Exposure 2",
            exposure_period_start=date(2022, 1, 1),
            exposure_period_end=date(2022, 12, 31),
            currency="USD"
        )
        self.exposure_values_2 = ExposureValues(
            exposure_value=1200000,
            attachment_point=0,
            limit=1200000
        )
        self.exposure_2 = Exposure(self.exposure_meta_2, self.exposure_values_2)
        
        self.exposures = Exposures([self.exposure_1, self.exposure_2])
        
        # Create a Trending instance for testing get_trend_factors
        self.trending = Trending(
            exposure_trend_factors=self.trend_factors,
            claim_trend_factors=self.trend_factors,
            base_year=self.base_year
        )
    
    def test_calculate_trend_factor_function(self):
        # Test the standalone calculate_trend_factor function
        factor = calculate_trend_factor(2021, self.base_year, self.trend_factors)
        self.assertEqual(factor, 1.05)
        
        # Test with year not in trend factors
        with self.assertRaises(KeyError):
            calculate_trend_factor(2019, self.base_year, self.trend_factors)
    
    def test_trend_exposures_function(self):
        # Test the standalone trend_exposures function
        trended_exposures = trend_exposures(self.exposures, self.trend_factors, self.base_year)
        
        # Check that we got an Exposures object back
        self.assertIsInstance(trended_exposures, Exposures)
        
        # Check that the exposure values were trended correctly
        self.assertAlmostEqual(trended_exposures[0].exposure_values.exposure_value, 1000000 / 1.05)
        self.assertAlmostEqual(trended_exposures[1].exposure_values.exposure_value, 1200000 / 1.1)
    
    def test_trend_claims_function(self):
        # Test the standalone trend_claims function
        trended_claims = trend_claims(self.claims, self.trend_factors, self.base_year)
        
        # Check that we got a Claims object back
        self.assertIsInstance(trended_claims, Claims)
        
        # Check that the claim values were trended correctly
        # For claim 1 (2021), the trend factor is 1.05
        self.assertAlmostEqual(
            trended_claims[0].uncapped_claim_development_history.cumulative_dev_paid[0],
            50000 / 1.05
        )
        self.assertAlmostEqual(
            trended_claims[0].uncapped_claim_development_history.cumulative_dev_incurred[0],
            100000 / 1.05
        )
        
        # For claim 2 (2022), the trend factor is 1.1
        self.assertAlmostEqual(
            trended_claims[1].uncapped_claim_development_history.cumulative_dev_paid[0],
            30000 / 1.1
        )
        self.assertAlmostEqual(
            trended_claims[1].uncapped_claim_development_history.cumulative_dev_incurred[0],
            80000 / 1.1
        )
    
    def test_get_trend_factors_function(self):
        # Test the standalone get_trend_factors function
        factors = get_trend_factors(self.trending)
        
        # Check that we got a dictionary back
        self.assertIsInstance(factors, dict)
        
        # Check that the dictionary contains the expected keys
        self.assertIn('exposure_trend_factors', factors)
        self.assertIn('claim_trend_factors', factors)
        self.assertIn('base_year', factors)
        
        # Check that the values are correct
        self.assertEqual(factors['exposure_trend_factors'], self.trend_factors)
        self.assertEqual(factors['claim_trend_factors'], self.trend_factors)
        self.assertEqual(factors['base_year'], self.base_year)

if __name__ == "__main__":
    unittest.main()