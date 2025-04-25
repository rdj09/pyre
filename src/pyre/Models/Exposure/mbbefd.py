from math import log, exp
from enum import Enum

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

def mbbefd_curve(swissRe_c_values, curve_position):
    b = exp(3.1 - 0.15 * (1 + swissRe_c_values.value) * swissRe_c_values.value)
    g = exp((0.78 + 0.12 * swissRe_c_values.value) * swissRe_c_values.value)
    return log(((g - 1) * b + (1 - b * g) * b ** curve_position) / (1 - b)) / log(b * g)



