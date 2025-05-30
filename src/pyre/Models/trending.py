from typing import Dict
from pyre.claims.claims import Claims, Claim, ClaimDevelopmentHistory
from pyre.exposures.exposures import Exposure, Exposures

def calculate_trend_factor(origin_year: int, base_year:int, trend_factors: Dict[int, float]) -> float:
    if origin_year == base_year:
        return 1.0
    elif origin_year < base_year:
        factor = 1.0
        for year in range(origin_year, base_year):
            factor *= trend_factors.get(year, 1.0)
        return factor
    else:
        factor = 1.0
        for year in range(base_year, origin_year):
            factor /= trend_factors.get(year, 1.0)
        return factor

def trend_exposures(exposures: Exposures,trend_factors: Dict[int, float], base_year: int) -> Exposures:
    trended_exposures = []
    for exposure in exposures:
        # Assume each exposure has an attribute 'exposure_year' and 'value'
        origin_year = getattr(exposure, "exposure_year", None)
        value = getattr(exposure, "value", None)
        if origin_year is not None and value is not None:
            trend_factor = calculate_trend_factor(origin_year=origin_year, trend_factors=trend_factors, base_year=base_year)
            trended_value = value * trend_factor
            # Create a new Exposure object with the trended value, copying other attributes
            new_exposure = Exposure(
                **{**exposure.__dict__, "value": trended_value}
            )
            trended_exposures.append(new_exposure)
        else:
            trended_exposures.append(exposure)  # If missing data, keep as is

    return Exposures(trended_exposures)

def trend_claims(claims: Claims,trend_factors: Dict[int, float],base_year: int) -> Claims:
    """
    Returns a new Claims object with each claim's development history trended to the base_year.

    Args:
        claims (Claims): The original Claims object.
        trend_factors (Dict[int, float]): Mapping of year to annual trend factor (e.g., {2020: 1.02, 2021: 1.03, ...}).
        base_year (int): The year to which all claims will be trended.

    Returns:
        Claims: A new Claims object with trended ClaimDevelopmentHistory for each claim.
    """
    trended_claims = []
    for claim in claims.claims:
        # Get the modelling year for trending
        origin_year = claim._claims_meta_data.modelling_year
        trend_factor = calculate_trend_factor(origin_year=origin_year, trend_factors=trend_factors, base_year=base_year)

        # Trend all paid and incurred values in the development history
        dev_hist = claim._claim_development_history
        trended_paid = [x * trend_factor for x in dev_hist.cumulative_dev_paid]
        trended_incurred = [x * trend_factor for x in dev_hist.cumulative_dev_incurred]
        trended_dev_hist = ClaimDevelopmentHistory(
            development_months=dev_hist.development_months,
            cumulative_dev_paid=trended_paid,
            cumulative_dev_incurred=trended_incurred,
        )
        # Create a new Claim with the same metadata and trended development history
        trended_claim = Claim(claims_meta_data=claim.claims_meta_data, claims_development_history=trended_dev_hist)
        trended_claims.append(trended_claim)
    return Claims(trended_claims)


#source citation: 
# Deters, I. (2017). The Mathematics of On-Leveling. 
# https://www.casact.org/sites/default/files/database/forum_17spforum_03-deters.pdf
