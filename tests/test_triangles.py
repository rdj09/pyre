import unittest
from datetime import date
from math import exp

from pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData
from pyre.claims.triangles import Triangle, CurveType

class TestTriangle(unittest.TestCase):
    """Test cases for the Triangle class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a sample triangle for testing
        self.triangle_data = {
            2020: {1: 100.0, 2: 150.0, 3: 175.0},
            2021: {1: 110.0, 2: 165.0},
            2022: {1: 120.0}
        }
        self.triangle = Triangle(
            triangle=self.triangle_data,
            origin_years=[2020, 2021, 2022],
            dev_periods=[1, 2, 3]
        )

    def test_init(self):
        """Test initialization of Triangle."""
        # Test with explicit parameters
        triangle = Triangle(
            triangle=self.triangle_data,
            origin_years=[2020, 2021, 2022],
            dev_periods=[1, 2, 3]
        )
        self.assertEqual(triangle.origin_years, [2020, 2021, 2022])
        self.assertEqual(triangle.dev_periods, [1, 2, 3])
        self.assertEqual(triangle.triangle, self.triangle_data)

        # Test with auto-derived parameters
        triangle = Triangle(triangle=self.triangle_data)
        self.assertEqual(triangle.origin_years, [2020, 2021, 2022])
        self.assertEqual(triangle.dev_periods, [1, 2, 3])
        self.assertEqual(triangle.triangle, self.triangle_data)

        # Test empty triangle
        empty_triangle = Triangle()
        self.assertEqual(empty_triangle.origin_years, [])
        self.assertEqual(empty_triangle.dev_periods, [])
        self.assertEqual(empty_triangle.triangle, {})

    def test_validate_triangle(self):
        """Test triangle validation."""
        # Valid triangle should not raise errors
        Triangle(triangle=self.triangle_data)

        # Invalid origin year type
        with self.assertRaises(ValueError):
            Triangle(triangle={"2020": {1: 100.0}})

        # Invalid development period type
        with self.assertRaises(ValueError):
            Triangle(triangle={2020: {"1": 100.0}})

        # Invalid value type
        with self.assertRaises(ValueError):
            Triangle(triangle={2020: {1: "100.0"}})

    def test_getitem(self):
        """Test __getitem__ method."""
        self.assertEqual(self.triangle[2020, 1], 100.0)
        self.assertEqual(self.triangle[2020, 2], 150.0)
        self.assertEqual(self.triangle[2020, 3], 175.0)
        self.assertEqual(self.triangle[2021, 1], 110.0)
        self.assertEqual(self.triangle[2021, 2], 165.0)
        self.assertIsNone(self.triangle[2021, 3])
        self.assertEqual(self.triangle[2022, 1], 120.0)
        self.assertIsNone(self.triangle[2022, 2])
        self.assertIsNone(self.triangle[2022, 3])
        self.assertIsNone(self.triangle[2023, 1])  # Non-existent origin year

    def test_setitem(self):
        """Test __setitem__ method."""
        # Update existing value
        self.triangle[2020, 1] = 105.0
        self.assertEqual(self.triangle[2020, 1], 105.0)

        # Add new value to existing origin year
        self.triangle[2022, 2] = 180.0
        self.assertEqual(self.triangle[2022, 2], 180.0)

        # Add new origin year
        self.triangle[2023, 1] = 130.0
        self.assertEqual(self.triangle[2023, 1], 130.0)
        self.assertIn(2023, self.triangle.origin_years)

        # Add new development period
        self.triangle[2020, 4] = 190.0
        self.assertEqual(self.triangle[2020, 4], 190.0)
        self.assertIn(4, self.triangle.dev_periods)

    def test_get_value(self):
        """Test get_value method."""
        self.assertEqual(self.triangle.get_value(2020, 1), 100.0)
        self.assertIsNone(self.triangle.get_value(2023, 1))

    def test_set_value(self):
        """Test set_value method."""
        self.triangle.set_value(2020, 1, 105.0)
        self.assertEqual(self.triangle.get_value(2020, 1), 105.0)

    def test_get_latest_diagonal(self):
        """Test get_latest_diagonal method."""
        latest_diagonal = self.triangle.get_latest_diagonal()
        self.assertEqual(latest_diagonal[2020], 175.0)
        self.assertEqual(latest_diagonal[2021], 165.0)
        self.assertEqual(latest_diagonal[2022], 120.0)

    def test_to_incremental(self):
        """Test to_incremental method."""
        incremental = self.triangle.to_incremental()
        self.assertEqual(incremental[2020, 1], 100.0)
        self.assertEqual(incremental[2020, 2], 50.0)  # 150 - 100
        self.assertEqual(incremental[2020, 3], 25.0)  # 175 - 150
        self.assertEqual(incremental[2021, 1], 110.0)
        self.assertEqual(incremental[2021, 2], 55.0)  # 165 - 110
        self.assertEqual(incremental[2022, 1], 120.0)

    def test_to_cumulative(self):
        """Test to_cumulative method."""
        # First create an incremental triangle
        incremental_data = {
            2020: {1: 100.0, 2: 50.0, 3: 25.0},
            2021: {1: 110.0, 2: 55.0},
            2022: {1: 120.0}
        }
        incremental = Triangle(triangle=incremental_data)

        # Convert to cumulative
        cumulative = incremental.to_cumulative()
        self.assertEqual(cumulative[2020, 1], 100.0)
        self.assertEqual(cumulative[2020, 2], 150.0)  # 100 + 50
        self.assertEqual(cumulative[2020, 3], 175.0)  # 150 + 25
        self.assertEqual(cumulative[2021, 1], 110.0)
        self.assertEqual(cumulative[2021, 2], 165.0)  # 110 + 55
        self.assertEqual(cumulative[2022, 1], 120.0)

    def test_str(self):
        """Test __str__ method."""
        string_repr = str(self.triangle)
        self.assertIn("Origin Year", string_repr)
        self.assertIn("2020", string_repr)
        self.assertIn("100.00", string_repr)

        # Test empty triangle
        empty_triangle = Triangle()
        self.assertEqual(str(empty_triangle), "Empty Triangle")

    def test_repr(self):
        """Test __repr__ method."""
        repr_str = repr(self.triangle)
        self.assertIn("Triangle", repr_str)
        self.assertIn("origin_years=[2020, 2021, 2022]", repr_str)
        self.assertIn("dev_periods=[1, 2, 3]", repr_str)

    def test_calculate_age_to_age_factors(self):
        """Test calculate_age_to_age_factors method."""
        factors = self.triangle.calculate_age_to_age_factors()

        # Check factors for 2020
        self.assertAlmostEqual(factors[2020][1], 1.5)  # 150 / 100
        self.assertAlmostEqual(factors[2020][2], 1.1667, places=4)  # 175 / 150

        # Check factors for 2021
        self.assertAlmostEqual(factors[2021][1], 1.5)  # 165 / 110

        # 2022 should only have one value, so no factors
        self.assertEqual(len(factors.get(2022, {})), 0)

    def test_get_average_age_to_age_factors(self):
        """Test get_average_age_to_age_factors method."""
        # Test simple average
        avg_factors = self.triangle.get_average_age_to_age_factors(method="simple")
        self.assertAlmostEqual(avg_factors[1], 1.5)  # (1.5 + 1.5) / 2
        self.assertAlmostEqual(avg_factors[2], 1.1667, places=4)  # Only one value

        # Test volume-weighted average
        avg_factors = self.triangle.get_average_age_to_age_factors(method="volume")
        self.assertAlmostEqual(avg_factors[1], 1.5)  # (150 + 165) / (100 + 110)
        self.assertAlmostEqual(avg_factors[2], 1.1667, places=4)  # 175 / 150

    def test_fit_curve(self):
        """Test fit_curve method."""
        # Create a triangle with more predictable development pattern
        triangle_data = {
            2020: {1: 100.0, 2: 150.0, 3: 180.0, 4: 195.0},
            2021: {1: 110.0, 2: 165.0, 3: 198.0},
            2022: {1: 120.0, 2: 180.0}
        }
        triangle = Triangle(triangle=triangle_data)

        # Test exponential fit
        params, metrics = triangle.fit_curve(curve_type=CurveType.EXPONENTIAL)
        self.assertIn("a", params)
        self.assertIn("b", params)
        self.assertIn("r_squared", metrics)
        self.assertIn("proportion_positive", metrics)

        # Test power fit
        params, metrics = triangle.fit_curve(curve_type=CurveType.POWER)
        self.assertIn("a", params)
        self.assertIn("b", params)
        self.assertIn("r_squared", metrics)

        # Test weibull fit
        params, metrics = triangle.fit_curve(curve_type=CurveType.WEIBULL)
        self.assertIn("a", params)
        self.assertIn("b", params)
        self.assertIn("r_squared", metrics)

        # Test inverse power fit
        params, metrics = triangle.fit_curve(curve_type=CurveType.INVERSE_POWER, c_values=[0.5, 1.0])
        self.assertIn("a", params)
        self.assertIn("b", params)
        self.assertIn("c", params)
        self.assertIn("r_squared", metrics)

        # Test invalid curve type
        with self.assertRaises(ValueError):
            triangle.fit_curve(curve_type="invalid_type")  # type: ignore


class TestGetSelectedDevelopmentPattern(unittest.TestCase):
    """Tests for Triangle.get_selected_development_pattern."""

    def _build_exponential_decay_triangle(self):
        """Build a synthetic triangle whose age-to-age factors follow an
        exact exponential decay (rj = 1 + exp(a + b * dp)), so the fitted
        curve recovers the pattern precisely regardless of averaging noise.
        """
        a_true, b_true = 0.0, -0.5
        dev_periods = [1, 2, 3, 4, 5, 6]

        # Age-to-age factor from each "from" period to the next one.
        ata = {dp: 1 + exp(a_true + b_true * dp) for dp in dev_periods[:-1]}

        # Full development chain starting at 100.0 for dev period 1.
        full_chain = {1: 100.0}
        for dp in dev_periods[1:]:
            full_chain[dp] = full_chain[dp - 1] * ata[dp - 1]

        # Classic triangle shape: origin year i (0-indexed) is observed
        # through period (len(dev_periods) - i), so every origin year's
        # observed factors match the same chain exactly.
        origin_years = [2015, 2016, 2017, 2018, 2019, 2020]
        triangle_data = {}
        for i, oy in enumerate(origin_years):
            max_dev = len(dev_periods) - i
            triangle_data[oy] = {dp: full_chain[dp] for dp in dev_periods if dp <= max_dev}

        return Triangle(triangle=triangle_data, origin_years=origin_years, dev_periods=dev_periods)

    def test_get_selected_development_pattern_returns_cumulative_factors(self):
        triangle = self._build_exponential_decay_triangle()

        pattern = triangle.get_selected_development_pattern(CurveType.EXPONENTIAL)
        dev_periods = sorted(pattern.keys())
        # Cumulative-to-ultimate factors decrease monotonically toward 1.0
        for earlier, later in zip(dev_periods, dev_periods[1:]):
            self.assertGreaterEqual(pattern[earlier], pattern[later])
        self.assertAlmostEqual(pattern[dev_periods[-1]], 1.0, places=2)

    def test_tail_factor_applied_to_final_development_period(self):
        triangle = self._build_exponential_decay_triangle()

        pattern = triangle.get_selected_development_pattern(
            CurveType.EXPONENTIAL, tail_factor=1.05
        )
        dev_periods = sorted(pattern.keys())
        self.assertAlmostEqual(pattern[dev_periods[-1]], 1.05, places=6)

    def test_get_selected_development_pattern_by_origin_year_maps_each_year_to_its_own_maturity(self):
        triangle = self._build_exponential_decay_triangle()

        pattern_by_year = triangle.get_selected_development_pattern_by_origin_year(
            CurveType.EXPONENTIAL
        )

        # (a) Keyed by origin_years, not dev periods.
        self.assertEqual(sorted(pattern_by_year.keys()), sorted(triangle.origin_years))

        # (b) Oldest (most mature) origin year's factor should be closer to
        # 1.0 (fully run-off, tail_factor default) than the newest (least
        # mature) origin year's factor, which should still be larger -- it
        # has the most development left to go.
        oldest_year = min(triangle.origin_years)
        newest_year = max(triangle.origin_years)
        oldest_factor = pattern_by_year[oldest_year]
        newest_factor = pattern_by_year[newest_year]

        self.assertLess(oldest_factor, newest_factor)
        self.assertAlmostEqual(oldest_factor, 1.0, places=2)

    def test_development_pattern_feeds_burn_cost_model_without_error(self):
        from pyre.models.Experience.burn_cost import BurnCostModel, ProjectionMethods
        from pyre.models.Experience.experience_preparer import ExperienceModelData
        from pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData
        from pyre.exposures.exposures import Exposure, ExposureMetaData, Exposures, ExposureValues
        from pyre.treaty.contracts import RIContract, RILayer
        from pyre.enums import ClaimTriggerBasis, ContractType, IndexationClauseType

        triangle = self._build_exponential_decay_triangle()
        pattern_by_year = triangle.get_selected_development_pattern_by_origin_year(
            CurveType.EXPONENTIAL
        )

        claim = Claim(
            ClaimsMetaData(
                claim_id="CLM001",
                currency="USD",
                contract_limit=2_000_000.0,
                loss_date=date(2020, 3, 1),
            ),
            ClaimDevelopmentHistory(
                development_months=[12],
                cumulative_dev_paid=[50000.0],
                cumulative_dev_incurred=[120000.0],
            ),
        )
        exposure = Exposure(
            ExposureMetaData(
                exposure_id="EXP2020",
                exposure_name="2020 Premium",
                exposure_period_start=date(2020, 1, 1),
                exposure_period_end=date(2020, 12, 31),
                currency="USD",
            ),
            ExposureValues(exposure_value=1_000_000.0, attachment_point=0.0, limit=1_000_000.0),
        )
        layer = RILayer(
            layer_id=1,
            layer_name="XOL Layer",
            layer_type=ContractType.EXCESS_OF_LOSS,
            occurrence_attachment=0.0,
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
        from pyre.treaty.contracts import RIContractMetadata

        contract_metadata = RIContractMetadata(
            contract_id="C-0001",
            contract_description="Test",
            cedent_name="Acme Re",
            trigger_basis=ClaimTriggerBasis.LOD,
            indexation_clause=IndexationClauseType.FULL_INDEXATION,
            indexation_margin=0.0,
            inception_date=date(2020, 1, 1),
            expiration_date=date(2020, 12, 31),
            fx_rates={"USD": 1.0},
        )
        contract = RIContract(contract_meta_data=contract_metadata, layers=[layer])

        model_data = ExperienceModelData(
            claims=Claims([claim]),
            exposures=Exposures([exposure]),
            ri_contract=contract,
        )

        # The claim's modelling year (2020) is the triangle's newest/least
        # mature origin year (only dev period 1 observed), so its own
        # cumulative-to-ultimate factor is large (still has lots of
        # development left) -- this should materially change the burn cost
        # versus the no-development-pattern default. Use the CHAINLADDER
        # projection method explicitly (ultimate = latest_incurred *
        # dev_factor) so the development pattern's effect is direct and
        # unambiguous, rather than getting diluted by the Cape Cod prior's
        # exposure normalisation.
        modelling_year = 2020
        projection_methods = {modelling_year: ProjectionMethods.CHAINLADDER}

        model_with_pattern = BurnCostModel(
            model_data,
            layer.layer_id,
            projection_methods=projection_methods,
            development_pattern=pattern_by_year,
        )
        burn_costs_with_pattern = model_with_pattern.calculate_burn_cost()
        self.assertIsInstance(burn_costs_with_pattern, dict)

        # Default: development_pattern omitted entirely -> BurnCostModel.__init__
        # falls back to {year: 1.0 for year in modelling_years}, i.e. no
        # development applied at all.
        model_without_pattern = BurnCostModel(
            model_data, layer.layer_id, projection_methods=projection_methods
        )
        burn_costs_without_pattern = model_without_pattern.calculate_burn_cost()

        self.assertIn(modelling_year, burn_costs_with_pattern)
        self.assertIn(modelling_year, burn_costs_without_pattern)

        # The year-keyed factor actually applied for 2020 should be
        # substantially above 1.0 (proving it's a real, non-trivial factor,
        # not accidentally falling back to the 1.0 default).
        self.assertGreater(pattern_by_year[modelling_year], 2.0)

        # Prove the development pattern is really being applied: the two
        # burn costs must differ by a clearly non-trivial amount, not just
        # floating-point noise.
        self.assertGreater(
            abs(
                burn_costs_with_pattern[modelling_year]
                - burn_costs_without_pattern[modelling_year]
            ),
            0.1,
        )


class TestTriangleFromClaims(unittest.TestCase):
    """Regression tests for Triangle.from_claims (previously raised
    AttributeError and then TypeError -- see claim.claims_meta_data.modelling_year
    and the flat dev_periods fix in Triangle.from_claims)."""

    def setUp(self):
        claim_2022 = Claim(
            ClaimsMetaData(
                claim_id="CL001",
                currency="USD",
                contract_limit=1_000_000,
                loss_date=date(2022, 3, 15),
            ),
            ClaimDevelopmentHistory(
                development_months=[0, 3, 6, 9, 12],
                cumulative_dev_paid=[0, 15000, 30000, 45000, 50000],
                cumulative_dev_incurred=[80000, 70000, 60000, 55000, 50000],
            ),
        )
        claim_2021 = Claim(
            ClaimsMetaData(
                claim_id="CL002",
                currency="EUR",
                contract_limit=1_000_000,
                loss_date=date(2021, 5, 10),
            ),
            ClaimDevelopmentHistory(
                development_months=[0, 3, 6],
                cumulative_dev_paid=[0, 5000, 10000],
                cumulative_dev_incurred=[20000, 15000, 12000],
            ),
        )
        self.claims = Claims([claim_2022, claim_2021])

    def test_from_claims_incurred(self):
        triangle = Triangle.from_claims(self.claims, value_type="incurred")
        self.assertEqual(
            triangle.triangle,
            {
                2021: {0: 20000.0, 3: 15000.0, 6: 12000.0},
                2022: {0: 80000.0, 3: 70000.0, 6: 60000.0, 9: 55000.0, 12: 50000.0},
            },
        )
        self.assertEqual(triangle.origin_years, [2021, 2022])
        self.assertEqual(triangle.dev_periods, [0, 3, 6, 9, 12])

    def test_from_claims_paid(self):
        triangle = Triangle.from_claims(self.claims, value_type="paid")
        self.assertEqual(
            triangle.triangle,
            {
                2021: {0: 0.0, 3: 5000.0, 6: 10000.0},
                2022: {0: 0.0, 3: 15000.0, 6: 30000.0, 9: 45000.0, 12: 50000.0},
            },
        )

    def test_from_claims_invalid_value_type(self):
        with self.assertRaises(ValueError):
            Triangle.from_claims(self.claims, value_type="bogus")


if __name__ == "__main__":
    unittest.main()
