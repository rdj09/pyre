from typing import Any, List
from pyre.Models.Experience.experience_preparer import ExperienceModelData

class ExperienceModel():

    def __init__(self, model_data:ExperienceModelData):
        self._data = model_data

    @property
    def data(self):
        return self._data
    
    @data.setter
    def data(self, model_data:ExperienceModelData):
        self._data = model_data


def chainladder_method(data: float, development_factor: float) -> float:
    return data*development_factor

def bf_method(data: float, exposure:float, development_factor: float, a_priori:float):
    return data + (1 - (1/development_factor))*a_priori*exposure

#citation source Lyons, G., Forster, W., Kedney, P., Warren, R., & Wilkinson, H. (n.d.). Claims Reserving Working Party Paper.
# https://www.actuaries.org.uk/documents/claims-reserving-working-party-paper
def cape_cod_method():
        # determine expected loss ratio 
    #bf_method(derived_expected)
    return NotImplementedError

#citation source Lyons, G., Forster, W., Kedney, P., Warren, R., & Wilkinson, H. (n.d.). Claims Reserving Working Party Paper.
# https://www.actuaries.org.uk/documents/claims-reserving-working-party-paper
def generalised_cape_cod_method():
    # determine expected loss ratio with decay factor
    #bf_method(derived_expected)
    return NotImplementedError


def cape_cod_prior_algo(trend_factors: List[float],losses: List[float], development_factors: List[float],
                        exposures: List[float], decay_factor: float = 0.0,generalised:bool = False) -> Any | float:

    if generalised:
        # decay_factor
        return NotImplementedError("Generalised Cape Cod method is not implemented yet.")
    else:
        psuedo_claims = sum(trend_factors[i] * losses[i] * (development_factors[i] / exposures[i]) for i in range(len(trend_factors)))
        psuedo_exposures = sum(exposures[i] / development_factors[i] for i in range(len(exposures)))
        return psuedo_claims / psuedo_exposures