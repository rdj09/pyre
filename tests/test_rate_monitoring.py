"""Tests for rate_monitoring — rate_change and rate_adequacy functions."""

import pytest

from pyre.rate_monitoring.rate_adequacy import rate_adequacy, rate_adequacy_change
from pyre.rate_monitoring.rate_change import rate_change_adjusted, rate_change_simple

# ---------------------------------------------------------------------------
# rate_change_simple
# ---------------------------------------------------------------------------


def test_rate_change_simple_increase():
    assert rate_change_simple(100.0, 110.0) == pytest.approx(0.10)


def test_rate_change_simple_decrease():
    assert rate_change_simple(100.0, 90.0) == pytest.approx(-0.10)


def test_rate_change_simple_flat():
    assert rate_change_simple(200.0, 200.0) == pytest.approx(0.0)


def test_rate_change_simple_zero_expiring_raises():
    with pytest.raises(ValueError, match="zero"):
        rate_change_simple(0.0, 100.0)


# ---------------------------------------------------------------------------
# rate_change_adjusted
# ---------------------------------------------------------------------------


def test_rate_change_adjusted_no_adjustment():
    assert rate_change_adjusted(100.0, 105.0) == pytest.approx(0.05)


def test_rate_change_adjusted_with_adjusted_expiring():
    # Exposure grew: adjust expiring up by 10% before comparison
    assert rate_change_adjusted(100.0, 105.0, adjusted_expiring_premium=95.0) == pytest.approx(
        (105.0 / 95.0) - 1
    )


def test_rate_change_adjusted_zero_base_raises():
    with pytest.raises(ValueError, match="zero"):
        rate_change_adjusted(0.0, 100.0)


def test_rate_change_adjusted_zero_adjusted_raises():
    with pytest.raises(ValueError, match="zero"):
        rate_change_adjusted(100.0, 100.0, adjusted_expiring_premium=0.0)


# ---------------------------------------------------------------------------
# rate_adequacy
# ---------------------------------------------------------------------------


def test_rate_adequacy_adequate():
    assert rate_adequacy(105.0, 100.0) == pytest.approx(1.05)


def test_rate_adequacy_inadequate():
    assert rate_adequacy(90.0, 100.0) == pytest.approx(0.90)


def test_rate_adequacy_exactly_adequate():
    assert rate_adequacy(100.0, 100.0) == pytest.approx(1.0)


def test_rate_adequacy_zero_indicated_raises():
    with pytest.raises(ValueError, match="zero"):
        rate_adequacy(100.0, 0.0)


# ---------------------------------------------------------------------------
# rate_adequacy_change
# ---------------------------------------------------------------------------


def test_rate_adequacy_change_improvement():
    # Prior: 90% adequate; Current: 100% adequate → change = +0.111
    change = rate_adequacy_change(90.0, 100.0, 100.0, 100.0)
    assert change == pytest.approx(1.0 - 0.9)


def test_rate_adequacy_change_deterioration():
    change = rate_adequacy_change(100.0, 100.0, 90.0, 100.0)
    assert change == pytest.approx(-0.10)


def test_rate_adequacy_change_stable():
    change = rate_adequacy_change(100.0, 100.0, 100.0, 100.0)
    assert change == pytest.approx(0.0)
