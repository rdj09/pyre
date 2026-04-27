import pytest

from pyre.claims.triangles import IBNERPatternExtractor, Triangle


def test_ibner_n_and_d_are_not_both_zero():
    """Regression: N and D triangles both evaluated to zero for every cell
    because D = prev - current and N = current - prev + D = 0."""
    tri = Triangle(
        triangle={
            2020: {12: 100.0, 24: 160.0, 36: 200.0},
            2021: {12: 110.0, 24: 170.0},
        }
    )
    extractor = IBNERPatternExtractor(tri)
    pattern = extractor.get_IBNER_pattern()

    # D at dev 12 should be None (no prior period)
    assert pattern[12] is None
    # D at dev 24 should be positive (IBNER development)
    assert pattern[24] is not None
    assert pattern[24] > 0
    # N at dev 24 should not be zero
    n_triangle = extractor.get_N_triangle()
    assert n_triangle[2020][24] != 0.0


def test_ibner_pattern_sums_to_total_development():
    """N + D at each period should equal total increment from prior period."""
    tri = Triangle(
        triangle={
            2020: {12: 100.0, 24: 160.0, 36: 190.0},
            2021: {12: 120.0, 24: 180.0},
        }
    )
    extractor = IBNERPatternExtractor(tri)
    n = extractor.get_N_triangle()
    d = extractor.get_D_triangle()

    # For origin year 2020, dev 24:
    # total increment = 160 - 100 = 60
    # N[2020][24] + D[2020][24] should = 60
    total = n[2020][24] + d[2020][24]
    assert total == pytest.approx(160.0 - 100.0, rel=1e-6)


def test_ibner_first_dev_period_d_is_none():
    """D is None for the first development period (no prior period to develop from)."""
    tri = Triangle(
        triangle={
            2020: {12: 100.0, 24: 150.0},
            2021: {12: 110.0},
        }
    )
    extractor = IBNERPatternExtractor(tri)
    d = extractor.get_D_triangle()
    assert d[2020][12] is None


def test_ibner_first_dev_period_n_equals_initial():
    """N at the first development period equals the initial triangle value."""
    tri = Triangle(
        triangle={
            2020: {12: 100.0, 24: 150.0},
            2021: {12: 110.0},
        }
    )
    extractor = IBNERPatternExtractor(tri)
    n = extractor.get_N_triangle()
    assert n[2020][12] == pytest.approx(100.0)
    assert n[2021][12] == pytest.approx(110.0)


def test_ibner_pattern_returns_dict_by_dev_period():
    """get_IBNER_pattern() returns a dict keyed by development period."""
    tri = Triangle(
        triangle={
            2020: {12: 100.0, 24: 150.0, 36: 175.0},
            2021: {12: 120.0, 24: 180.0},
        }
    )
    extractor = IBNERPatternExtractor(tri)
    pattern = extractor.get_IBNER_pattern()

    assert isinstance(pattern, dict)
    assert 12 in pattern
    assert 24 in pattern
    assert 36 in pattern


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
