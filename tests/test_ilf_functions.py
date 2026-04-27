"""Tests for exposure ILF functions."""

import pytest

from pyre.models.exposure.exposure_ILF_functions import (
    pareto_ilf,
    pareto_limited_severity,
    power_ilf,
)


def test_pareto_limited_severity_zero_x():
    assert pareto_limited_severity(0, alpha=2.0) == pytest.approx(0.0)


def test_pareto_limited_severity_positive():
    result = pareto_limited_severity(100.0, alpha=2.0)
    assert 0.0 < result < 1.0


def test_pareto_limited_severity_negative_x():
    # x <= 0 → return 0.0
    assert pareto_limited_severity(-10.0, alpha=2.0) == pytest.approx(0.0)


def test_pareto_ilf_same_limits():
    # Ratio of the same limit = 1.0
    result = pareto_ilf(limit_1=500_000.0, limit_2=500_000.0, alpha=2.0)
    assert result == pytest.approx(1.0)


def test_pareto_ilf_higher_limit_greater_than_one():
    result = pareto_ilf(limit_1=500_000.0, limit_2=1_000_000.0, alpha=2.0)
    assert result > 1.0


def test_power_ilf_basic():
    # (limit / basic_limit)^power = (2m / 1m)^0.5 = sqrt(2)
    result = power_ilf(2_000_000.0, 1_000_000.0, 0.5)
    assert result == pytest.approx(2.0**0.5)


def test_power_ilf_none_limit():
    # None treated as no limit → 0.0
    assert power_ilf(None, 1_000_000.0, 0.5) == pytest.approx(0.0)  # type: ignore[arg-type]


def test_power_ilf_at_basic_limit():
    assert power_ilf(1_000_000.0, 1_000_000.0, 0.5) == pytest.approx(1.0)
