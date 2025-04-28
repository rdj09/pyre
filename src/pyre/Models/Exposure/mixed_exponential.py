from math import exp

from enum import Enum

#TODO generalise to data class and protol method for "curve parameters" so can adjust source
class mixed_expo_curves(Enum):
    CURVE_ONE = {
        "parameter_mus":[10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 120.0, 130.0, 140.0, 150.0],
        "parameter_weights":[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0] 
        }
    CURVE_TWO = {
        "parameter_mus":[10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 120.0, 130.0, 140.0, 150.0],
        "parameter_weights":[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0] 
        }


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


#mus = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150]
#weights = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]   
#curve_position_value = 100000
#print(mixed_expo_curves.CURVE_ONE.value['parameter_mus'])
#print(mixed_expo_curves.CURVE_TWO.value['parameter_weights'])

#print(mixed_exponential_curve(paramaters_mus= mixed_expo_curves.CURVE_ONE.value["parameter_mus"],parameter_weights= mixed_expo_curves.CURVE_ONE.value["parameter_weights"],curve_position_value=100000))