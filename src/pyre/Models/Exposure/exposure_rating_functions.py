from enum import Enum, auto
from math import log, exp


class mixed_expo_curves(Enum):
    CURVE_ONE = {
        "parameter_mus":[10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 120.0, 130.0, 140.0, 150.0],
        "parameter_weights":[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        }
    CURVE_TWO = {
        "parameter_mus":[10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 120.0, 130.0, 140.0, 150.0],
        "parameter_weights":[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
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


def mixed_exponential_curve(paramaters_mus:list[float], parameter_weights:list[float], curve_position_value:float) -> float:
    """_summary_

    Args:
        paramaters_mus (list[float]): _description_
        parameter_weights (list[float]): _description_
        curve_position_value (float): _description_

    Returns:
        float: _description_
    """
    total_limited_severity = 0
    for mu, weight in zip(paramaters_mus, parameter_weights):
        if mu != 0:
            contributing_limiting_severity = (1 - exp((-1 / mu) * curve_position_value)) * mu
            total_limited_severity += contributing_limiting_severity * weight
    return total_limited_severity

def mbbefd_curve(swissRe_c_values: swissRe_c_values, curve_position: float) -> float:
    """_summary_

    Args:
        swissRe_c_values (swissRe_c_values): _description_
        curve_position (float): _description_

    Returns:
        float: _description_
    """
    b = exp(3.1 - 0.15 * (1 + swissRe_c_values.value) * swissRe_c_values.value)
    g = exp((0.78 + 0.12 * swissRe_c_values.value) * swissRe_c_values.value)
    return log(((g - 1) * b + (1 - b * g) * b ** curve_position) / (1 - b)) / log(b * g)

# print(mbbefd_curve(swissRe_c_values.LLOYDS_INDUSTRY,0.5))


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


def power_ilf(limit: float, basic_limit: float, power_parameter: float) -> float:
    if limit is None:
        return 0.0
    else:
        return (limit / basic_limit) ** power_parameter




class ExposureCurveType(Enum):
    RIEBESELL = auto()
    MIXED_EXPONENTIAL = auto()
    MBBEFD = auto()

exposure_curve_calculation = {
    ExposureCurveType.RIEBESELL: riebesell_curve,
    ExposureCurveType.MIXED_EXPONENTIAL: mixed_exponential_curve,
    ExposureCurveType.MBBEFD: mbbefd_curve
}