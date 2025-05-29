from enum import Enum, auto
from typing import Any, Dict, List
from pyre.Models.Experience.experience_preparer import ExperienceModelData

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

class ProjectionMethods(Enum):
    CHAINLADDER = auto()
    BF = auto()
    SIMPLE_CAPE_COD = auto()
    GENERALISED_CAPE_COD = auto()

projection_methods_fn = {
    ProjectionMethods.CHAINLADDER: chainladder_method,
    ProjectionMethods.BF: bf_method,
    ProjectionMethods.SIMPLE_CAPE_COD: cape_cod_method,
    ProjectionMethods.GENERALISED_CAPE_COD: generalised_cape_cod_method
    }

class BurnCostModel():
    def __init__(self,
                model_data: ExperienceModelData, 
                layer_id: Any, 
                years_weighting: None | Dict[int , float] = None, 
                projection_methods : None | Dict[int , ProjectionMethods] = None,
                development_pattern: None | Dict[int, float] = None,
                a_priori_assumption : None | Dict[int, float] = None) -> None:
        
        self._modelling_years = model_data.exposures.modelling_years
        self._years_weighting = years_weighting if years_weighting else {year: 1.0 for year in model_data.exposures.modelling_years}
        self._projection_methods = projection_methods if projection_methods else {year : ProjectionMethods.SIMPLE_CAPE_COD for year in model_data.exposures.modelling_years} # Default to simple cape cod method
        self._development_pattern = development_pattern if development_pattern else {year: 1.0 for year in model_data.exposures.modelling_years} # Default to no development pattern
        self._a_priori = a_priori_assumption if a_priori_assumption else {year: 0.0 for year in model_data.exposures.modelling_years} . # Default to no a priori assumption
        self._data = model_data
        self._layer_id = layer_id
    
    @property
    def modelling_years(self):
        return self._modelling_years

    @modelling_years.setter
    def modelling_years(self, years):
        self._modelling_years = years

    @property
    def years_weighting(self):
        return self._years_weighting

    @years_weighting.setter
    def years_weighting(self, weighting):
        self._years_weighting = weighting

    @property
    def projection_methods(self):
        return self._projection_methods

    @projection_methods.setter
    def projection_methods(self, methods):
        self._projection_methods = methods

    @property
    def development_pattern(self):
        return self._development_pattern

    @development_pattern.setter
    def development_pattern(self, pattern):
        self._development_pattern = pattern

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, model_data):
        self._data = model_data

    @property
    def layer_id(self):
        return self._layer_id

    @layer_id.setter
    def layer_id(self, lid):
        self._layer_id = lid

    @property
    def a_priori(self):
        return self._a_priori

    @a_priori.setter
    def a_priori(self, prior):
        self._a_priori = prior

    # def calculate_burn_cost(self) -> Dict[int, float]:  
    #     burn_costs = {}
    #     for year in self._modelling_years:
    #         claims = self._data.aggregate_subject_contract_claims[self._layer_id][year] # Further details as class carries many data items
    #         exposures = self._data.aggregate_exposures[year]

    #     return  {2010:0.0}
