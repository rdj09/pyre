from collections.abc import Callable
from enum import Enum
from math import exp, log
from typing import Any

from ...enums import ExposureCurveType

MIXED_EXPO_CURVE_ONE = {
    "parameters_mus": [
        10.0,
        20.0,
        30.0,
        40.0,
        50.0,
        60.0,
        70.0,
        80.0,
        90.0,
        100.0,
        110.0,
        120.0,
        130.0,
        140.0,
        150.0,
    ],
    "parameter_weights": [1.0] * 15,
}

MIXED_EXPO_CURVE_TWO = {
    "parameters_mus": [
        10.0,
        20.0,
        30.0,
        40.0,
        50.0,
        60.0,
        70.0,
        80.0,
        90.0,
        100.0,
        110.0,
        120.0,
        130.0,
        140.0,
        150.0,
    ],
    "parameter_weights": [1.0] * 15,
}


class SwissReCValues(Enum):
    """
    https://www.swissre.com/dam/jcr:7137dac0-83a6-4cfa-80a4-93d33c35562f/exposure-rating-brochure.pdf
    """

    PERSONAL_LINES = 1.5
    COMMERCIAL_LINES_SMALL = 2.0
    COMMERCIAL_LINES_MEDIUM = 3.0
    CAPTIVE_BI = 2.1
    CAPTIVE_PD = 3.8
    CAPTIVE_BI_PD = 3.4
    INDUSTRIAL_LARGE_COMMERCIAL = 4.0
    LLOYDS_INDUSTRY = 5.0


# Backward-compatibility alias
swissRe_c_values = SwissReCValues


def mixed_exponential_curve(
    parameters_mus: list[float], parameter_weights: list[float], curve_position: float
) -> float:
    """Calculate mixed exponential curve value.

    Citation: https://www.casact.org/sites/default/files/database/proceed_proceed99_99578.pdf

    Args:
        parameters_mus (list[float]): Mean parameters for each exponential component.
        parameter_weights (list[float]): Weights for each component.
        curve_position (float): Position on the curve.

    Returns:
        float: Curve value at curve_position.
    """
    total_limited_severity = 0.0
    for mu, weight in zip(parameters_mus, parameter_weights, strict=False):
        if mu != 0:
            contributing_limiting_severity = (1 - exp((-1 / mu) * curve_position)) * mu
            total_limited_severity += contributing_limiting_severity * weight
    return total_limited_severity


def mbbefd_curve(curve: SwissReCValues | float, curve_position: float) -> float:
    """Calculate the MBBEFD curve value.

    Citation: https://www.casact.org/sites/default/files/2021-03/8_Bernegger.pdf

    Args:
        curve (Union[SwissReCValues, float]): Either a SwissReCValues enum or a manual c-value as float.
        curve_position (float): Position on the curve.

    Returns:
        float: The calculated curve value.
    """
    c_value = curve.value if isinstance(curve, SwissReCValues) else curve
    b = exp(3.1 - 0.15 * (1 + c_value) * c_value)
    g = exp((0.78 + 0.12 * c_value) * c_value)
    return log(((g - 1) * b + (1 - b * g) * b**curve_position) / (1 - b)) / log(b * g)


def riebesell_curve(curve_position: float, z_value: float, base_limit: float, **_: Any) -> float:
    """Calculate Riebesell curve value.

    Args:
        curve_position (float): Position on the curve.
        z_value (float): Riebesell z parameter.
        base_limit (float): Base limit for normalisation.

    Returns:
        float: Curve value.
    """
    return float((curve_position / base_limit) ** log(1 + z_value, 2))


exposure_curve_calculation: dict[ExposureCurveType, Callable[..., float]] = {
    ExposureCurveType.RIEBESELL: riebesell_curve,
    ExposureCurveType.MIXED_EXPONENTIAL: mixed_exponential_curve,
    ExposureCurveType.MBBEFD: mbbefd_curve,
}


def calculate_curve(
    curve_type: ExposureCurveType,
    parameters: dict[str, Any],
    position: float,
) -> float:
    """Calculate an exposure curve value at a given position.

    Args:
        curve_type: Which curve family to use.
        parameters: Curve-specific keyword arguments passed to the curve function.
        position: Position on the curve (typically loss / total insured value).

    Returns:
        Curve value at `position`.

    Raises:
        ValueError: If curve_type is not in exposure_curve_calculation.
    """
    if curve_type not in exposure_curve_calculation:
        raise ValueError(f"Unsupported curve type: {curve_type}")
    func = exposure_curve_calculation[curve_type]
    return float(func(**parameters, curve_position=position))
