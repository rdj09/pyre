from typing import Dict, Optional, Union, List
from ..claims.claims import Claims, Claim, ClaimDevelopmentHistory
from ..exposures.exposures import Exposure, Exposures, ExposureMetaData, ExposureValues


class Trending:
    """
    A class for trending insurance data (claims and exposures) to a common base year.

    This class provides methods to apply trend factors to claims and exposures,
    adjusting their values to account for inflation or other time-based changes.

    Attributes:
        exposure_trend_factors (Dict[int, float]): Mapping of year to annual trend factor for exposures
            (e.g., {2020: 1.02, 2021: 1.03, ...}).
        claim_trend_factors (Dict[int, float]): Mapping of year to annual trend factor for claims
            (e.g., {2020: 1.02, 2021: 1.03, ...}).
        base_year (int): The year to which all data will be trended.
    """

    def __init__(self, exposure_trend_factors: Dict[int, float], claim_trend_factors: Dict[int, float] = None, trend_factors: Dict[int, float] = None, base_year: int = None):
        """
        Initialize the Trending class with trend factors and a base year.

        Args:
            exposure_trend_factors (Dict[int, float]): Mapping of year to annual trend factor for exposures
                (e.g., {2020: 1.02, 2021: 1.03, ...}).
            claim_trend_factors (Dict[int, float], optional): Mapping of year to annual trend factor for claims.
                If None, exposure_trend_factors will be used for claims as well.
            trend_factors (Dict[int, float], optional): For backward compatibility. If provided, both
                exposure_trend_factors and claim_trend_factors will be set to this value.
            base_year (int): The year to which all data will be trended.
        """
        self.exposure_trend_factors = exposure_trend_factors
        self.claim_trend_factors = claim_trend_factors
        self.base_year = base_year
        self._validate_inputs()

    def _validate_inputs(self) -> None:
        """
        Validate the trend factors and base year.

        Raises:
            ValueError: If trend factors dictionaries are empty or base_year is not an integer.
        """
        if not self.exposure_trend_factors:
            raise ValueError("Exposure trend factors dictionary cannot be empty")
        if not self.claim_trend_factors:
            raise ValueError("Claim trend factors dictionary cannot be empty")
        if not isinstance(self.base_year, int):
            raise ValueError("Base year must be an integer")

    def calculate_trend_factor(self, origin_year: int, for_claims: bool = False) -> float:
        """
        Calculate the trend factor between the origin year and the base year.

        Args:
            origin_year (int): The year from which to trend.
            for_claims (bool, optional): If True, use claim trend factors. If False, use exposure trend factors.
                Defaults to False.

        Returns:
            float: The calculated trend factor.
        """
        # Select the appropriate trend factors based on the for_claims parameter
        trend_factors = self.claim_trend_factors if for_claims else self.exposure_trend_factors

        if origin_year == self.base_year:
            return 1.0
        elif origin_year < self.base_year:
            factor = 1.0
            for year in range(origin_year, self.base_year):
                factor *= trend_factors.get(year, 1.0)
            return factor
        else:
            factor = 1.0
            for year in range(self.base_year, origin_year):
                factor /= trend_factors.get(year, 1.0)
            return factor

    def trend_exposures(self, exposures: Exposures) -> Exposures:
        """
        Apply trend factors to a collection of exposures.

        Args:
            exposures (Exposures): The original Exposures object.

        Returns:
            Exposures: A new Exposures object with trended values.
        """
        trended_exposures = []

        for exposure in exposures:
            # Get the modelling year and exposure value
            origin_year = exposure.modelling_year()

            # Create a new exposure with trended values
            # Use exposure trend factors (for_claims=False is the default)
            trend_factor = self.calculate_trend_factor(origin_year, for_claims=False)

            # Get the original exposure values
            original_values = exposure.exposure_values()
            trended_value = original_values.exposure_value * trend_factor

            # Create new ExposureValues with the trended value
            new_values = ExposureValues(
                exposure_value=trended_value,
                attachment_point=original_values.attachment_point,
                limit=original_values.limit
            )

            # Create a new Exposure with the same metadata but trended values
            new_exposure = Exposure(
                exposure_meta=exposure.exposure_meta,
                exposure_values=new_values
            )

            trended_exposures.append(new_exposure)

        return Exposures(trended_exposures)

    def get_trend_factors(self) -> Dict[str, Dict[int, float]]:
        """
        Get the trend factors from this Trending instance.

        Returns:
            Dict[str, Dict[int, float]]: A dictionary with keys 'exposure' and 'claim', each mapping to
                their respective trend factors dictionary.
        """
        return {
            'exposure': self.exposure_trend_factors,
            'claim': self.claim_trend_factors
        }

    def trend_claims(self, claims: Claims) -> Claims:
        """
        Apply trend factors to a collection of claims.

        Args:
            claims (Claims): The original Claims object.

        Returns:
            Claims: A new Claims object with trended ClaimDevelopmentHistory for each claim.
        """
        trended_claims = []

        for claim in claims.claims:
            # Get the modelling year for trending
            origin_year = claim.claims_meta_data.modelling_year
            # Use claim trend factors (for_claims=True)
            trend_factor = self.calculate_trend_factor(origin_year, for_claims=True)

            # Get the development history
            dev_hist = claim.uncapped_claim_development_history

            # Trend all paid and incurred values in the development history
            trended_paid = [x * trend_factor for x in dev_hist.cumulative_dev_paid]
            trended_incurred = [x * trend_factor for x in dev_hist.cumulative_dev_incurred]

            # Create a new development history with trended values
            trended_dev_hist = ClaimDevelopmentHistory(
                development_months=dev_hist.development_months,
                cumulative_dev_paid=trended_paid,
                cumulative_dev_incurred=trended_incurred,
            )

            # Create a new Claim with the same metadata and trended development history
            trended_claim = Claim(
                claims_meta_data=claim.claims_meta_data, 
                claims_development_history=trended_dev_hist
            )

            trended_claims.append(trended_claim)

        return Claims(trended_claims)


# For backward compatibility
def calculate_trend_factor(origin_year: int, base_year: int, trend_factors: Dict[int, float], for_claims: bool = False) -> float:
    """
    Calculate the trend factor between the origin year and the base year.

    Args:
        origin_year (int): The year from which to trend.
        base_year (int): The year to which to trend.
        trend_factors (Dict[int, float]): Mapping of year to annual trend factor.
        for_claims (bool, optional): If True, use as claim trend factors. If False, use as exposure trend factors.
            Defaults to False.

    Returns:
        float: The calculated trend factor.
    """
    if for_claims:
        trending = Trending(exposure_trend_factors=trend_factors, claim_trend_factors=trend_factors, base_year=base_year)
        return trending.calculate_trend_factor(origin_year, for_claims=True)
    else:
        trending = Trending(exposure_trend_factors=trend_factors, claim_trend_factors=trend_factors, base_year=base_year)
        return trending.calculate_trend_factor(origin_year, for_claims=False)


def trend_exposures(exposures: Exposures, trend_factors: Dict[int, float], base_year: int) -> Exposures:
    """
    Apply trend factors to a collection of exposures.

    Args:
        exposures (Exposures): The original Exposures object.
        trend_factors (Dict[int, float]): Mapping of year to annual trend factor.
        base_year (int): The year to which all exposures will be trended.

    Returns:
        Exposures: A new Exposures object with trended values.
    """
    trending = Trending(exposure_trend_factors=trend_factors, claim_trend_factors=trend_factors, base_year=base_year)
    return trending.trend_exposures(exposures)


def trend_claims(claims: Claims, trend_factors: Dict[int, float], base_year: int) -> Claims:
    """
    Apply trend factors to a collection of claims.

    Args:
        claims (Claims): The original Claims object.
        trend_factors (Dict[int, float]): Mapping of year to annual trend factor.
        base_year (int): The year to which all claims will be trended.

    Returns:
        Claims: A new Claims object with trended ClaimDevelopmentHistory for each claim.
    """
    trending = Trending(exposure_trend_factors=trend_factors, claim_trend_factors=trend_factors, base_year=base_year)
    return trending.trend_claims(claims)


def get_trend_factors(trending_instance: Trending) -> Dict[str, Dict[int, float]]:
    """
    Get the trend factors from a Trending instance.

    Args:
        trending_instance (Trending): The Trending instance to get trend factors from.

    Returns:
        Dict[str, Dict[int, float]]: A dictionary with keys 'exposure' and 'claim', each mapping to
            their respective trend factors dictionary.
    """
    return {
        'exposure': trending_instance.exposure_trend_factors,
        'claim': trending_instance.claim_trend_factors
    }


# Source citation: 
# Deters, I. (2017). The Mathematics of On-Leveling. 
# https://www.casact.org/sites/default/files/database/forum_17spforum_03-deters.pdf
