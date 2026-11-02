from enum import Enum, auto
from math import log, exp
from typing import Any, Dict, Union


class ExposureCurveType(Enum):
    RIEBESELL = auto()
    MIXED_EXPONENTIAL = auto()
    MBBEFD = auto()


class mixed_expo_curves(Enum):
    CURVE_ONE = {
        "parameter_mus": [
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
        "parameter_weights": [
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
        ],
    }
    CURVE_TWO = {
        "parameter_mus": [
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
        "parameter_weights": [
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
        ],
    }


class swissRe_c_values(Enum):
    """_summary_
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


def mixed_exponential_curve(
    parameters_mus: list[float], parameter_weights: list[float], curve_position_value: float
) -> float:
    """_summary_

        citation: https://www.casact.org/sites/default/files/database/proceed_proceed99_99578.pdf
    Args:
        parameters_mus (list[float]): _description_
        parameter_weights (list[float]): _description_
        curve_position_value (float): _description_

    Returns:
        float: _description_
    """
    total_limited_severity = 0
    for mu, weight in zip(parameters_mus, parameter_weights):
        if mu != 0:
            contributing_limiting_severity = (1 - exp((-1 / mu) * curve_position_value)) * mu
            total_limited_severity += contributing_limiting_severity * weight
    return total_limited_severity


def mbbefd_curve(curve: Union[swissRe_c_values, float], curve_position: float) -> float:
    """Calculate the MBBEFD curve value.

    citation: https://www.casact.org/sites/default/files/2021-03/8_Bernegger.pdf

    Args:
        curve (Union[swissRe_c_values, float]): Either a swissRe_c_values enum or a manual c-value as float
        curve_position (float): Position on the curve

    Returns:
        float: The calculated curve value
    """
    # Extract the c-value - either from enum or use the float directly
    c_value = curve.value if isinstance(curve, swissRe_c_values) else curve

    # Calculate using the c-value
    b = exp(3.1 - 0.15 * (1 + c_value) * c_value)
    g = exp((0.78 + 0.12 * c_value) * c_value)
    return log(((g - 1) * b + (1 - b * g) * b**curve_position) / (1 - b)) / log(b * g)


def riebesell_curve(attachment: float, limit: float, z_value: float, base_limit: float):
    """_summary_

    Args:
        attachment (float): _description_
        limit (float): _description_
        z_value (float): _description_
        base_limit (float): _description_

    Returns:
        _type_: _description_
    """
    if limit is None:
        return ((attachment) / base_limit) ** log(1 + z_value, 2)
    else:
        return ((attachment + limit) / base_limit) ** log(1 + z_value, 2)


exposure_curve_calculation = {
    ExposureCurveType.RIEBESELL: riebesell_curve,
    ExposureCurveType.MIXED_EXPONENTIAL: mixed_exponential_curve,
    ExposureCurveType.MBBEFD: mbbefd_curve,
}

def calculate_curve(
    curve_type: ExposureCurveType, parameters: Dict[str, Any], position: float
) -> float:
    """Calculate curve value based on curve type and parameters.

    Uniform `(curve_type, parameters, position) -> float` adapter over the three
    underlying curve functions, which do NOT share a common signature:

    - `mbbefd_curve(curve, curve_position)` already matches directly -- `position`
      is passed straight through as `curve_position`.
    - `mixed_exponential_curve(parameters_mus, parameter_weights,
      curve_position_value)` takes the same ratio but under a differently-named
      parameter (`curve_position_value`, not `curve_position`).
    - `riebesell_curve(attachment, limit, z_value, base_limit)` has no
      `curve_position`-shaped parameter at all -- its natural domain is
      attachment/limit *amounts*, not a [0, 1] position ratio. See the docstring
      below for the semantic mapping chosen for RIEBESELL.

    Args:
        curve_type: Type of curve to use
        parameters: Dictionary containing curve-specific parameters
        position: Position on the curve, as a ratio (typically in [0, 1])

    Returns:
        float: Calculated curve value

    Raises:
        ValueError: if curve_type is not a recognised ExposureCurveType member
    """
    if curve_type not in exposure_curve_calculation:
        raise ValueError(f"Unsupported curve type: {curve_type}")

    if curve_type == ExposureCurveType.MBBEFD:
        return mbbefd_curve(curve=parameters["curve"], curve_position=position)

    if curve_type == ExposureCurveType.MIXED_EXPONENTIAL:
        return mixed_exponential_curve(
            parameters_mus=parameters["parameters_mus"],
            parameter_weights=parameters["parameter_weights"],
            curve_position_value=position,
        )

    if curve_type == ExposureCurveType.RIEBESELL:
        # Riebesell's own formula is expressed in attachment/limit *amounts*
        # relative to a `base_limit`, not in a [0, 1] "curve_position" ratio the
        # way mbbefd_curve and mixed_exponential_curve are. To give RIEBESELL a
        # position-based evaluation that is comparable to the other two curve
        # types (so callers like ExposureModel._calculate_single_exposure_share
        # can treat all three uniformly), we adopt this reading: `position` is
        # the fraction of `base_limit` at which the curve is evaluated, i.e. an
        # attachment point `position * base_limit` with no limit above it
        # (`limit=None`) -- this is exactly Riebesell's "loss at attachment"
        # formula, `((attachment) / base_limit) ** log2(1 + z_value)`, which is
        # the same shape of calculation mbbefd_curve/mixed_exponential_curve
        # perform for a given position. Any `attachment`/`limit` values present
        # in `parameters` are therefore NOT used by this adapter -- only
        # `z_value` and `base_limit` are -- since a direct attachment/limit pair
        # would conflict with a position-driven evaluation. This is a
        # deliberate, documented choice of the most natural reading, not a
        # citation-grade derivation.
        return riebesell_curve(
            attachment=position * parameters["base_limit"],
            limit=None,
            z_value=parameters["z_value"],
            base_limit=parameters["base_limit"],
        )

    raise ValueError(f"Unsupported curve type: {curve_type}")
