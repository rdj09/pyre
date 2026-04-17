import unittest

from pyre.claims.triangles import CurveType, Triangle


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




from datetime import date

import pytest

from pyre.claims.claims import (
    Claim,
    ClaimDevelopmentHistory,
    Claims,
    ClaimsMetaData,
    ClaimYearType,
)


def test_triangle_from_claims_builds_correctly():
    """Regression: from_claims() called claim.modelling_year (doesn't exist)
    and iterated dev_history.items() on a List[float]."""
    meta = ClaimsMetaData(
        claim_id="C1",
        currency="GBP",
        contract_limit=1_000_000.0,
        contract_deductible=0.0,
        claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=date(2020, 6, 1),
    )
    dev_hist = ClaimDevelopmentHistory(
        development_months=[12, 24, 36],
        cumulative_dev_paid=[100.0, 150.0, 175.0],
        cumulative_dev_incurred=[200.0, 220.0, 225.0],
    )
    claims = Claims([Claim(meta, dev_hist)])

    triangle = Triangle.from_claims(claims, value_type="incurred")

    assert triangle[2020, 12] == pytest.approx(200.0)
    assert triangle[2020, 24] == pytest.approx(220.0)
    assert triangle[2020, 36] == pytest.approx(225.0)


def test_triangle_from_claims_paid():
    meta = ClaimsMetaData(
        claim_id="C1",
        currency="GBP",
        contract_limit=1_000_000.0,
        contract_deductible=0.0,
        claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=date(2020, 6, 1),
    )
    dev_hist = ClaimDevelopmentHistory(
        development_months=[12, 24],
        cumulative_dev_paid=[100.0, 150.0],
        cumulative_dev_incurred=[200.0, 220.0],
    )
    claims = Claims([Claim(meta, dev_hist)])

    triangle = Triangle.from_claims(claims, value_type="paid")

    assert triangle[2020, 12] == pytest.approx(100.0)
    assert triangle[2020, 24] == pytest.approx(150.0)


def test_get_selected_development_pattern_returns_dict():
    from src.pyre.claims.triangles import CurveType, Triangle

    tri = Triangle(triangle={
        2018: {12: 100.0, 24: 160.0, 36: 190.0, 48: 200.0},
        2019: {12: 110.0, 24: 172.0, 36: 200.0},
        2020: {12: 120.0, 24: 185.0},
        2021: {12: 130.0},
    })
    pattern = tri.get_selected_development_pattern(
        curve_type=CurveType.EXPONENTIAL, tail_factor=1.05
    )
    assert isinstance(pattern, dict)
    for _dev, factor in pattern.items():
        assert factor >= 1.0
    dev_periods = sorted(pattern.keys())
    assert pattern[dev_periods[0]] >= pattern[dev_periods[-1]]


def test_get_selected_development_pattern_tail_factor_applied():
    import pytest

    from src.pyre.claims.triangles import CurveType, Triangle

    tri = Triangle(triangle={
        2018: {12: 100.0, 24: 160.0, 36: 200.0},
        2019: {12: 110.0, 24: 172.0},
        2020: {12: 120.0},
    })
    pattern_no_tail = tri.get_selected_development_pattern(
        curve_type=CurveType.EXPONENTIAL, tail_factor=1.0
    )
    pattern_with_tail = tri.get_selected_development_pattern(
        curve_type=CurveType.EXPONENTIAL, tail_factor=1.10
    )
    for dev in pattern_no_tail:
        assert pattern_with_tail[dev] == pytest.approx(
            pattern_no_tail[dev] * 1.10, rel=1e-6
        )


if __name__ == "__main__":
    unittest.main()
