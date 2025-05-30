from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union, Callable
from pyre.Models.Experience.experience_preparer import ExperienceModelData

def chainladder_method(data: float, development_factor: float) -> float:
    """
    Apply the Chain Ladder method to project ultimate claims.

    Args:
        data (float): The current claim amount.
        development_factor (float): The development factor to apply.

    Returns:
        float: The projected ultimate claim amount.
    """
    return data * development_factor

def bf_method(data: float, exposure: float, development_factor: float, a_priori: float) -> float:
    """
    Apply the Bornhuetter-Ferguson method to project ultimate claims.

    Args:
        data (float): The current claim amount.
        exposure (float): The exposure amount.
        development_factor (float): The development factor to apply.
        a_priori (float): The a priori expected loss ratio.

    Returns:
        float: The projected ultimate claim amount.
    """
    return data + (1 - (1/development_factor)) * a_priori * exposure

# Citation source: Lyons, G., Forster, W., Kedney, P., Warren, R., & Wilkinson, H. (n.d.). Claims Reserving Working Party Paper.
# https://www.actuaries.org.uk/documents/claims-reserving-working-party-paper
def cape_cod_method(data: float, exposure: float, development_factor: float, a_priori: float) -> float:
    """
    Apply the Cape Cod method to project ultimate claims.

    Args:
        data (float): The current claim amount.
        exposure (float): The exposure amount.
        development_factor (float): The development factor to apply.
        a_priori (float): The a priori expected loss ratio.

    Returns:
        float: The projected ultimate claim amount.

    Note:
        This method is currently not implemented and will raise NotImplementedError.
    """
    # determine expected loss ratio 
    # bf_method(derived_expected)
    raise NotImplementedError("Cape Cod method is not implemented yet.")

def generalised_cape_cod_method(data: float, exposure: float, development_factor: float, a_priori: float) -> float:
    """
    Apply the Generalised Cape Cod method to project ultimate claims.

    Args:
        data (float): The current claim amount.
        exposure (float): The exposure amount.
        development_factor (float): The development factor to apply.
        a_priori (float): The a priori expected loss ratio.

    Returns:
        float: The projected ultimate claim amount.

    Note:
        This method is currently not implemented and will raise NotImplementedError.
    """
    # determine expected loss ratio with decay factor
    # bf_method(derived_expected)
    raise NotImplementedError("Generalised Cape Cod method is not implemented yet.")

def cape_cod_prior_algo(trend_factors: List[float], losses: List[float], development_factors: List[float],
                        exposures: List[float], decay_factor: float = 0.0, generalised: bool = False) -> Union[Any, float]:
    """
    Calculate the a priori expected loss ratio using the Cape Cod algorithm.

    Args:
        trend_factors (List[float]): List of trend factors for each year.
        losses (List[float]): List of losses for each year.
        development_factors (List[float]): List of development factors for each year.
        exposures (List[float]): List of exposures for each year.
        decay_factor (float, optional): Decay factor for the generalised method. Defaults to 0.0.
        generalised (bool, optional): Whether to use the generalised method. Defaults to False.

    Returns:
        Union[Any, float]: The a priori expected loss ratio.

    Note:
        If generalised is True, this method will raise NotImplementedError.
    """
    if generalised:
        # decay_factor
        raise NotImplementedError("Generalised Cape Cod method is not implemented yet.")
    else:
        psuedo_claims = sum(trend_factors[i] * losses[i] * (development_factors[i] / exposures[i]) for i in range(len(trend_factors)))
        psuedo_exposures = sum(exposures[i] / development_factors[i] for i in range(len(exposures)))
        return psuedo_claims / psuedo_exposures

class ProjectionMethods(Enum):
    """
    Enumeration of available projection methods for burn cost calculations.
    """
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

class BurnCostModel:
    """
    BurnCostModel is a class that calculates burn costs for a reinsurance contract layer.

    It uses various projection methods to estimate ultimate claims and calculate burn costs
    based on historical claims and exposures data.

    Attributes:
        _modelling_years (List[int]): The years to be used in the modelling.
        _years_weighting (Dict[int, float]): Weighting factors for each modelling year.
        _projection_methods (Dict[int, ProjectionMethods]): Projection method to use for each modelling year.
        _development_pattern (Dict[int, float]): Development factors for each modelling year.
        _a_priori (Dict[int, float]): A priori expected loss ratios for each modelling year.
        _data (ExperienceModelData): The claims and exposures data for the reinsurance contract.
        _layer_id (Any): The identifier for the reinsurance contract layer.
    """
    def __init__(self,
                model_data: ExperienceModelData, 
                layer_id: Any, 
                years_weighting: Optional[Dict[int, float]] = None, 
                projection_methods: Optional[Dict[int, ProjectionMethods]] = None,
                development_pattern: Optional[Dict[int, float]] = None,
                a_priori_assumption: Optional[Dict[int, float]] = None) -> None:
        """
        Initialize a BurnCostModel instance.

        Args:
            model_data (ExperienceModelData): The claims and exposures data for the reinsurance contract.
            layer_id (Any): The identifier for the reinsurance contract layer.
            years_weighting (Optional[Dict[int, float]], optional): Weighting factors for each modelling year.
                If None, equal weights of 1.0 will be used for all years. Defaults to None.
            projection_methods (Optional[Dict[int, ProjectionMethods]], optional): Projection method to use for each modelling year.
                If None, SIMPLE_CAPE_COD will be used for all years. Defaults to None.
            development_pattern (Optional[Dict[int, float]], optional): Development factors for each modelling year.
                If None, factors of 1.0 will be used for all years (no development). Defaults to None.
            a_priori_assumption (Optional[Dict[int, float]], optional): A priori expected loss ratios for each modelling year.
                If None, values of 0.0 will be used for all years (no a priori assumption). Defaults to None.
        """
        self._modelling_years = model_data.exposures.modelling_years
        self._years_weighting = years_weighting if years_weighting else {year: 1.0 for year in model_data.exposures.modelling_years}
        self._projection_methods = projection_methods if projection_methods else {year: ProjectionMethods.SIMPLE_CAPE_COD for year in model_data.exposures.modelling_years}  # Default to simple cape cod method
        self._development_pattern = development_pattern if development_pattern else {year: 1.0 for year in model_data.exposures.modelling_years}  # Default to no development pattern
        self._a_priori = a_priori_assumption if a_priori_assumption else {year: 0.0 for year in model_data.exposures.modelling_years}  # Default to no a priori assumption
        self._data = model_data
        self._layer_id = layer_id

    @property
    def modelling_years(self) -> List[int]:
        """
        Get the years to be used in the modelling.

        Returns:
            List[int]: The modelling years.
        """
        return self._modelling_years

    @modelling_years.setter
    def modelling_years(self, years: List[int]) -> None:
        """
        Set the years to be used in the modelling.

        Args:
            years (List[int]): The new modelling years.
        """
        self._modelling_years = years

    @property
    def years_weighting(self) -> Dict[int, float]:
        """
        Get the weighting factors for each modelling year.

        Returns:
            Dict[int, float]: Mapping of modelling year to weighting factor.
        """
        return self._years_weighting

    @years_weighting.setter
    def years_weighting(self, weighting: Dict[int, float]) -> None:
        """
        Set the weighting factors for each modelling year.

        Args:
            weighting (Dict[int, float]): Mapping of modelling year to weighting factor.
        """
        self._years_weighting = weighting

    @property
    def projection_methods(self) -> Dict[int, ProjectionMethods]:
        """
        Get the projection method to use for each modelling year.

        Returns:
            Dict[int, ProjectionMethods]: Mapping of modelling year to projection method.
        """
        return self._projection_methods

    @projection_methods.setter
    def projection_methods(self, methods: Dict[int, ProjectionMethods]) -> None:
        """
        Set the projection method to use for each modelling year.

        Args:
            methods (Dict[int, ProjectionMethods]): Mapping of modelling year to projection method.
        """
        self._projection_methods = methods

    @property
    def development_pattern(self) -> Dict[int, float]:
        """
        Get the development factors for each modelling year.

        Returns:
            Dict[int, float]: Mapping of modelling year to development factor.
        """
        return self._development_pattern

    @development_pattern.setter
    def development_pattern(self, pattern: Dict[int, float]) -> None:
        """
        Set the development factors for each modelling year.

        Args:
            pattern (Dict[int, float]): Mapping of modelling year to development factor.
        """
        self._development_pattern = pattern

    @property
    def data(self) -> ExperienceModelData:
        """
        Get the claims and exposures data for the reinsurance contract.

        Returns:
            ExperienceModelData: The claims and exposures data.
        """
        return self._data

    @data.setter
    def data(self, model_data: ExperienceModelData) -> None:
        """
        Set the claims and exposures data for the reinsurance contract.

        Args:
            model_data (ExperienceModelData): The new claims and exposures data.
        """
        self._data = model_data

    @property
    def layer_id(self) -> Any:
        """
        Get the identifier for the reinsurance contract layer.

        Returns:
            Any: The layer identifier.
        """
        return self._layer_id

    @layer_id.setter
    def layer_id(self, lid: Any) -> None:
        """
        Set the identifier for the reinsurance contract layer.

        Args:
            lid (Any): The new layer identifier.
        """
        self._layer_id = lid

    @property
    def a_priori(self) -> Dict[int, float]:
        """
        Get the a priori expected loss ratios for each modelling year.

        Returns:
            Dict[int, float]: Mapping of modelling year to a priori expected loss ratio.
        """
        return self._a_priori

    @a_priori.setter
    def a_priori(self, prior: Dict[int, float]) -> None:
        """
        Set the a priori expected loss ratios for each modelling year.

        Args:
            prior (Dict[int, float]): Mapping of modelling year to a priori expected loss ratio.
        """
        self._a_priori = prior

    def calculate_burn_cost(self) -> Dict[int, float]:
        """
        Calculate the burn cost for each modelling year.

        This method applies the specified projection method for each modelling year
        to calculate the burn cost based on the claims and exposures data.

        Returns:
            Dict[int, float]: Mapping of modelling year to calculated burn cost.
        """
        burn_costs = {}
        for year in self._modelling_years:
            # Skip years that don't have data in the aggregate claims or exposures
            if (self._layer_id not in self._data.aggregate_subject_contract_claims or
                year not in self._data.aggregate_subject_contract_claims[self._layer_id] or
                year not in self._data.aggregate_exposures):
                continue

            # Get claims and exposures data for the year
            claims_data = self._data.aggregate_subject_contract_claims[self._layer_id][year]
            exposures_data = self._data.aggregate_exposures[year]

            # Get the latest incurred claims amount
            latest_incurred = claims_data.get("latest_incurred", 0.0)

            # Get the earned exposure value
            earned_exposure = exposures_data.get("earned", 0.0)

            # Skip years with zero exposure to avoid division by zero
            if earned_exposure == 0.0:
                continue

            # Get the projection method, development factor, and a priori for the year
            method = self._projection_methods.get(year, ProjectionMethods.SIMPLE_CAPE_COD)
            dev_factor = self._development_pattern.get(year, 1.0)
            a_priori_value = self._a_priori.get(year, 0.0)

            # Apply the projection method
            projection_fn = projection_methods_fn.get(method)
            try:
                if method == ProjectionMethods.CHAINLADDER:
                    ultimate_claims = projection_fn(latest_incurred, dev_factor)
                else:  # BF, SIMPLE_CAPE_COD, GENERALISED_CAPE_COD
                    ultimate_claims = projection_fn(latest_incurred, earned_exposure, dev_factor, a_priori_value)

                # Calculate burn cost as ultimate claims divided by earned exposure
                burn_costs[year] = ultimate_claims / earned_exposure if earned_exposure > 0 else 0.0

            except NotImplementedError:
                # If the method is not implemented, use the chainladder method as fallback
                ultimate_claims = chainladder_method(latest_incurred, dev_factor)
                burn_costs[year] = ultimate_claims / earned_exposure if earned_exposure > 0 else 0.0

        return burn_costs
