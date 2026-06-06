from typing import Dict, List, Any, Optional
from ...Models.trending import Trending
from ...claims.claims import Claim, ClaimDevelopmentHistory, Claims
from ...exposures.exposures import Exposure, Exposures
from ...treaty.contracts import RIContract


class ExperienceModelData:
    """
    ExperienceModelData is a data class that holds the claims and exposures data for a reinsurance contract.    
    It provides methods to trend claims and exposures, apply reinsurance contract layers, and aggregate results by modelling year and layer.

    Attributes:
        _claims (Claims): The claims data for the reinsurance contract.
        _exposures (Exposures): The exposures data for the reinsurance contract.
        _ri_contract (RIContract): The reinsurance contract with layers and metadata.
    """
    def __init__(self, claims: Claims, exposures: Exposures, ri_contract: RIContract, 
                 exposure_trend_factors: Dict[int, float] = None, claim_trend_factors: Dict[int, float] = None) -> None:
        """
        Initialize an ExperienceModelData instance.

        Args:
            claims (Claims): The claims data for the reinsurance contract.
            exposures (Exposures): The exposures data for the reinsurance contract.
            ri_contract (RIContract): The reinsurance contract with layers and metadata.
            exposure_trend_factors (Dict[int, float], optional): Mapping of year to annual trend factor for exposures.
                If None, default trend factors will be used.
            claim_trend_factors (Dict[int, float], optional): Mapping of year to annual trend factor for claims.
                If None, default trend factors will be used.
        """
        self._claims = claims
        self._exposures = exposures
        self._ri_contract = ri_contract

        # Initialize trending with provided or default trend factors
        base_year = self.ri_contract.contract_meta_data.inception_date.year
        default_trend_factors = {year: 1.0 for year in range(base_year - 10, base_year + 1)}

        # Use provided trend factors or default ones
        exposure_factors = exposure_trend_factors if exposure_trend_factors is not None else default_trend_factors
        claim_factors = claim_trend_factors if claim_trend_factors is not None else default_trend_factors

        self._trending = Trending(exposure_trend_factors=exposure_factors, claim_trend_factors=claim_factors, base_year=base_year)

    @property
    def claims(self) -> Claims:
        """
        Get the claims data for the reinsurance contract.

        Returns:
            Claims: The claims data.
        """
        return self._claims

    @claims.setter
    def claims(self, value: Claims) -> None:
        """
        Set the claims data for the reinsurance contract.

        Args:
            value (Claims): The new claims data.
        """
        self._claims = value

    @property
    def exposures(self) -> Exposures:
        """
        Get the exposures data for the reinsurance contract.

        Returns:
            Exposures: The exposures data.
        """
        return self._exposures

    @exposures.setter
    def exposures(self, value: Exposures) -> None:
        """
        Set the exposures data for the reinsurance contract.

        Args:
            value (Exposures): The new exposures data.
        """
        self._exposures = value

    @property
    def ri_contract(self) -> RIContract:
        """
        Get the reinsurance contract.

        Returns:
            RIContract: The reinsurance contract with layers and metadata.
        """
        return self._ri_contract

    @ri_contract.setter
    def ri_contract(self, value: RIContract) -> None:
        """
        Set the reinsurance contract.

        Args:
            value (RIContract): The new reinsurance contract.
        """
        self._ri_contract = value

    @property
    def trending(self) -> Trending:
        """
        Get the Trending instance used for trending claims and exposures.

        Returns:
            Trending: The Trending instance.
        """
        return self._trending

    def update_trend_factors(self, exposure_trend_factors: Dict[int, float] = None, claim_trend_factors: Dict[int, float] = None, base_year: int = None) -> None:
        """
        Update the trend factors used for trending claims and exposures.

        Args:
            exposure_trend_factors (Dict[int, float], optional): New mapping of year to annual trend factor for exposures.
                If None, the existing exposure trend factors will be kept.
            claim_trend_factors (Dict[int, float], optional): New mapping of year to annual trend factor for claims.
                If None, the existing claim trend factors will be kept.
            base_year (int, optional): New base year to which all data will be trended.
                If None, the existing base year will be kept.
        """
        # Get current values if new ones are not provided
        if exposure_trend_factors is None:
            exposure_trend_factors = self._trending.exposure_trend_factors
        if claim_trend_factors is None:
            claim_trend_factors = self._trending.claim_trend_factors
        if base_year is None:
            base_year = self._trending.base_year

        # Create a new Trending instance with the updated values
        self._trending = Trending(
            exposure_trend_factors=exposure_trend_factors,
            claim_trend_factors=claim_trend_factors,
            base_year=base_year
        )

    @property
    def trended_claims(self) -> Claims:
        """
        Get the claims data trended to the contract inception year.

        Returns:
            Claims: The trended claims data.

        Note:
            This method uses the Trending instance initialized in __init__ with trend factors.
            The trend factors are a dictionary mapping years to annual trend factors (e.g., {2020: 1.02, 2021: 1.03, ...}).
        """
        return self._trending.trend_claims(self.claims)

    @property
    def subject_contract_claims(self) -> Dict[int, Claims]:
        """
        Returns a dictionary mapping layer IDs to Claims objects where each claim's cumulative_dev_paid 
        and cumulative_dev_incurred have had the RI contract's loss_to_layer_fn applied for that layer.

        This property uses the trended_claims and ri_contract properties to calculate the ceded claims
        for each layer in the reinsurance contract.

        Returns:
            Dict[int, Claims]: Dictionary mapping layer IDs to Claims objects with ceded values.
        """
        ceded_claims_dict = {}
        for layer in self.ri_contract.layers:
            layer_ceded_claims = []
            for claim in self.trended_claims.claims:
                new_dev_hist = ClaimDevelopmentHistory(
                    development_months=claim.capped_claim_development_history.development_months,
                    cumulative_dev_paid=[layer.loss_to_layer_fn(paid) for paid in claim.capped_claim_development_history.cumulative_dev_paid],
                    cumulative_dev_incurred=[layer.loss_to_layer_fn(incurred) for incurred in claim.capped_claim_development_history.cumulative_dev_incurred]
                )
                new_claim = Claim(
                    claims_meta_data=claim.claims_meta_data,
                    claims_development_history=new_dev_hist,
                )
                layer_ceded_claims.append(new_claim)

            ceded_claims_dict[layer.layer_id] = Claims(layer_ceded_claims)

        return ceded_claims_dict # returns dictionary of Claims objects by layer id that can be used to create aggregate numbers

    @property
    def trended_exposures(self) -> Exposures:
        """
        Get the exposures data trended to the contract inception year.

        Returns:
            Exposures: The trended exposures data.

        Note:
            This method uses the Trending instance initialized in __init__ with trend factors.
            The trend factors are a dictionary mapping years to annual trend factors (e.g., {2020: 1.02, 2021: 1.03, ...}).
        """
        return self._trending.trend_exposures(self.exposures)

    @property
    def aggregate_subject_contract_claims(self) -> Dict[int, Dict[int, Dict[str, Any]]]:
        """
        Aggregates the output of subject_contract_claims by modelling year and layer, and also returns claim counts by layer, modelling year, claim status, and total count.

        Returns:
            Dict[int, Dict[int, Dict[str, Any]]]: A nested dictionary with the following structure:
                {
                    layer_id: {
                        modelling_year: {
                            "latest_paid": float,
                            "latest_incurred": float,
                            "claim_counts": {
                                status: count,
                                ...
                            },
                            "total_count": int
                        }, ...
                    }, ...
                }
        """
        subject_claims_by_year = {}
        for layer_id, claims_obj in self.subject_contract_claims.items():
            year_agg = {}
            for claim in claims_obj.claims:
                year = claim.claims_meta_data.modelling_year
                status = getattr(claim.claims_meta_data, "status", "Unknown")
                latest_paid = claim.capped_claim_development_history.latest_paid
                latest_incurred = claim.capped_claim_development_history.latest_incurred

                if year not in year_agg:
                    year_agg[year] = {
                        "latest_paid": 0.0,
                        "latest_incurred": 0.0,
                        "claim_counts": {},
                        "total_count": 0
                    }

                year_agg[year]["latest_paid"] += latest_paid
                year_agg[year]["latest_incurred"] += latest_incurred

                if status not in year_agg[year]["claim_counts"]:
                    year_agg[year]["claim_counts"][status] = 0

                year_agg[year]["claim_counts"][status] += 1
                year_agg[year]["total_count"] += 1

            subject_claims_by_year[layer_id] = year_agg

        return subject_claims_by_year

    @property
    def aggregate_exposures(self) -> Dict[int, Dict[str, float]]:
        """
        Aggregates the trended exposures by modelling year, summing the written and earned exposure values.

        This property uses the trended_exposures property to calculate the aggregate exposure values
        for each modelling year.

        Returns:
            Dict[int, Dict[str, float]]: A dictionary mapping modelling year to exposure values:
                {
                    modelling_year: {
                        "written": total_written,
                        "earned": total_earned
                    }, ...
                }
        """
        exposures_by_year = {}
        # Use current date for exposure value calculations
        analysis_date = self.ri_contract.contract_meta_data.inception_date

        for exposure in self.trended_exposures:
            year = exposure.modelling_year

            # Calculate written and earned values using Exposure methods
            written_val = exposure.written_exposure_value(analysis_date)
            earned_val = exposure.earned_exposure_value(analysis_date)

            if year not in exposures_by_year:
                exposures_by_year[year] = {"written": 0.0, "earned": 0.0}

            exposures_by_year[year]["written"] += written_val
            exposures_by_year[year]["earned"] += earned_val

        return exposures_by_year
