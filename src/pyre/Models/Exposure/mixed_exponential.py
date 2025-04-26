from math import exp

def mixed_exponential_curve(paramaters_mus, parameter_weights, curve_position_value):
    total_limited_severity = 0
    for mu, weight in zip(paramaters_mus, parameter_weights):
        if mu != 0:  
            contributing_limiting_severity = (1 - exp((-1 / mu) * curve_position_value)) * mu
            total_limited_severity += contributing_limiting_severity * weight
    return total_limited_severity


#mus = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150]
#weights = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]   
#curve_position_value = 100000
