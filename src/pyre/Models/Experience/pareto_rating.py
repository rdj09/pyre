# source citation
# Fackler, Michael, Reinventing Pareto: Fits for All Losses, Small and Large (October 24, 2022). 
# Available at SSRN: https://ssrn.com/abstract=3775007 or http://dx.doi.org/10.2139/ssrn.3775007 

from math import log

def frequency_extrapolate(frequency_deductible_one:float,deductible_one:float,deductible_two:float, alpha:float) ->float:
    return frequency_deductible_one * ((deductible_one/deductible_two)**alpha)

def average_layer_loss(alpha:float, deductible:float, excess:float)->float:
    if alpha == 1.0:
        return deductible*log(1+excess/deductible,2)
    else:
        return (deductible/(alpha + 1))*(1-((1+excess/deductible)**(1-alpha)))

def risk_premium_extropolate(risk_premium_lower_layer:float, excess_lower:float, deductible_lower:float,excess_upper:float, deductible_upper:float,alpha:float)->float:
    if alpha == 1.0:
        return risk_premium_lower_layer*(
            ((excess_upper+deductible_upper)*log(1+excess_upper/deductible_upper,2) - deductible_upper*log(1+excess_upper/deductible_upper,2))
            /
            ((excess_lower+deductible_lower)*log(1+excess_lower/deductible_lower,2) - deductible_lower*log(1+excess_lower/deductible_lower,2))
        )
    else:
        return risk_premium_lower_layer*(
        (((excess_upper+deductible_upper)**(1-alpha)) - deductible_upper**(1-alpha))
    /
    (((excess_lower+deductible_lower)**(1-alpha)) - deductible_lower**(1-alpha)))

    