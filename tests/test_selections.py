import math

import pytest

from pyre.models.aggregate.selections import CredibilityWeight


def _cw():
    return CredibilityWeight(experience_data=None, exposure_data=None)


def test_limited_fluctuation_full_credibility():
    cw = _cw()
    result = cw.limited_fluctuation_credibility(1082, 1082)
    assert result == pytest.approx(1.0)


def test_limited_fluctuation_partial_credibility():
    cw = _cw()
    result = cw.limited_fluctuation_credibility(100, 1082)
    assert result == pytest.approx(math.sqrt(100 / 1082))


def test_limited_fluctuation_zero_claims():
    cw = _cw()
    assert cw.limited_fluctuation_credibility(0, 1082) == pytest.approx(0.0)


def test_buhlmann_credibility_high_claims():
    cw = _cw()
    # k = EPV / VHM = 1.0 / 1.0 = 1.0
    # Z = n / (n + k) → 1000 / 1001 ≈ 0.999
    result = cw.buhlmann_credibility(1000, 1.0, 1.0)
    assert result > 0.99


def test_buhlmann_credibility_zero_vhm():
    cw = _cw()
    assert cw.buhlmann_credibility(100, 1.0, 0.0) == pytest.approx(0.0)


def test_buhlmann_straub_uses_total_exposure():
    cw = _cw()
    exposures = [100.0, 200.0, 300.0]
    counts = [3, 6, 9]
    result = cw.buhlmann_straub_credibility(exposures, counts, 1.0, 1.0)
    # k = 1.0; Z = 600 / (600 + 1) ≈ 0.998
    assert result > 0.99


def test_greatest_accuracy_returns_between_0_and_1():
    cw = _cw()
    data = [0.05, 0.08, 0.07, 0.06, 0.09]
    result = cw.greatest_accuracy_credibility(data, collective_mean=0.10)
    assert 0.0 <= result <= 1.0


def test_bayesian_credibility_high_prior_variance():
    cw = _cw()
    data = [100.0, 110.0, 90.0]
    result = cw.bayesian_credibility(
        prior_mean=100.0, prior_variance=1000.0,
        data=data, data_variance=50.0,
    )
    assert 0.0 <= result <= 1.0


def test_calculate_sample_variance():
    cw = _cw()
    data = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    # Known sample variance = 4.571...
    result = cw.calculate_sample_variance(data)
    assert result == pytest.approx(4.5714, rel=1e-3)
