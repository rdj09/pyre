"""Tests for pareto_rating — Fackler Pareto extrapolation functions."""

import math

import pytest

from pyre.models.experience.pareto_rating import (
    average_layer_loss,
    frequency_extrapolate,
    risk_premium_extropolate,
)


def test_frequency_extrapolate_basic():
    # Moving from deductible 100 to 200 with alpha=2:  500 * (100/200)^2 = 125
    result = frequency_extrapolate(500.0, 100.0, 200.0, 2.0)
    assert result == pytest.approx(125.0)


def test_frequency_extrapolate_same_deductible():
    result = frequency_extrapolate(200.0, 100.0, 100.0, 1.5)
    assert result == pytest.approx(200.0)


def test_average_layer_loss_non_unity_alpha():
    # alpha != 1: use power formula
    result = average_layer_loss(alpha=2.0, deductible=100.0, excess=100.0)
    assert result > 0


def test_average_layer_loss_unity_alpha():
    # alpha == 1: use log formula
    result = average_layer_loss(alpha=1.0, deductible=100.0, excess=100.0)
    expected = 100.0 * math.log(1 + 100.0 / 100.0, 2)
    assert result == pytest.approx(expected)


def test_risk_premium_extropolate_non_unity_alpha():
    # Simple sanity check: result should be positive and finite
    result = risk_premium_extropolate(
        risk_premium_lower_layer=1000.0,
        excess_lower=100.0,
        deductible_lower=100.0,
        excess_upper=200.0,
        deductible_upper=200.0,
        alpha=2.0,
    )
    assert result > 0


def test_risk_premium_extropolate_unity_alpha():
    result = risk_premium_extropolate(
        risk_premium_lower_layer=1000.0,
        excess_lower=100.0,
        deductible_lower=100.0,
        excess_upper=200.0,
        deductible_upper=200.0,
        alpha=1.0,
    )
    assert result > 0
