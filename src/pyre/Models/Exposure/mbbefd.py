from math import log, exp

def mbbefd_curve(c_value, curve_position):
    b = exp(3.1 - 0.15 * (1 + c_value) * c_value)
    g = exp((0.78 + 0.12 * c_value) * c_value)
    return log(((g - 1) * b + (1 - b * g) * b ^ curve_position) / (1 - b)) / log(b * g)



