from collections.abc import Callable
from math import exp
from typing import Any

from ...enums import ProjectionMethods
from ...models.experience.experience_preparer import ExperienceModelData


def chainladder_method(data: float, development_factor: float) -> float:
    """Apply the Chain Ladder method to project ultimate claims."""
    return data * development_factor


def bf_method(data: float, exposure: float, development_factor: float, a_priori: float) -> float:
    """Apply the Bornhuetter-Ferguson method to project ultimate claims."""
    return data + (1 - (1 / development_factor)) * a_priori * exposure


# Citation source: Lyons, G., Forster, W., Kedney, P., Warren, R., & Wilkinson, H. (n.d.). Claims Reserving Working Party Paper.
# https://www.actuaries.org.uk/documents/claims-reserving-working-party-paper
def cape_cod_method(
    data: float,
    exposure: float,
    development_factor: float,
    trend_factors: list[float] | None = None,
    losses: list[float] | None = None,
    development_factors: list[float] | None = None,
    exposures: list[float] | None = None,
) -> float:
    """Apply the Cape Cod method to project ultimate claims."""
    if trend_factors is None or losses is None or development_factors is None or exposures is None:
        raise ValueError(
            "Cape Cod method requires trend_factors, losses, development_factors, and exposures"
        )
    cape_cod_prior = cape_cod_prior_algo(
        trend_factors=trend_factors,
        losses=losses,
        development_factors=development_factors,
        exposures=exposures,
        generalised=False,
    )
    return bf_method(data, exposure, development_factor, a_priori=cape_cod_prior)


def generalised_cape_cod_method(
    data: float,
    exposure: float,
    development_factor: float,
    trend_factors: list[float] | None = None,
    losses: list[float] | None = None,
    development_factors: list[float] | None = None,
    exposures: list[float] | None = None,
    decay_factor: float = 0.0,
) -> float:
    """Apply the Generalised Cape Cod method to project ultimate claims."""
    if trend_factors is None or losses is None or development_factors is None or exposures is None:
        raise ValueError(
            "Generalised Cape Cod method requires trend_factors, losses, development_factors, and exposures"
        )
    generalised_cape_cod_prior = cape_cod_prior_algo(
        trend_factors=trend_factors,
        losses=losses,
        development_factors=development_factors,
        exposures=exposures,
        decay_factor=decay_factor,
        generalised=True,
    )
    return bf_method(data, exposure, development_factor, a_priori=generalised_cape_cod_prior)


def cape_cod_prior_algo(
    trend_factors: list[float],
    losses: list[float],
    development_factors: list[float],
    exposures: list[float],
    decay_factor: float = 0.0,
    generalised: bool = False,
) -> float:
    """Calculate the a priori expected loss ratio using the Cape Cod algorithm."""
    if generalised:
        weights = [exp(-decay_factor * i) for i in range(len(trend_factors))]
        pseudo_claims = sum(
            weights[i] * trend_factors[i] * losses[i] * (development_factors[i] / exposures[i])
            for i in range(len(trend_factors))
        )
        pseudo_exposures = sum(
            weights[i] * exposures[i] / development_factors[i] for i in range(len(exposures))
        )
    else:
        pseudo_claims = sum(
            trend_factors[i] * losses[i] * (development_factors[i] / exposures[i])
            for i in range(len(trend_factors))
        )
        pseudo_exposures = sum(exposures[i] / development_factors[i] for i in range(len(exposures)))
    return pseudo_claims / pseudo_exposures


projection_methods_fn: dict[ProjectionMethods, Callable[..., Any]] = {
    ProjectionMethods.CHAINLADDER: chainladder_method,
    ProjectionMethods.BF: bf_method,
    ProjectionMethods.SIMPLE_CAPE_COD: cape_cod_method,
    ProjectionMethods.GENERALISED_CAPE_COD: generalised_cape_cod_method,
}


class BurnCostModel:
    """Calculates burn costs for a reinsurance contract layer.

    Uses various projection methods (Chain Ladder, BF, Cape Cod) to estimate
    ultimate claims and compute burn costs from historical claims and exposures.

    Attributes:
        modelling_years: Years used in the modelling.
        years_weighting: Weighting factor per modelling year.
        projection_methods: Projection method per modelling year.
        development_pattern: Development factor per modelling year.
        a_priori: A priori expected loss ratio per modelling year.
        data: Claims and exposures data for the contract.
        layer_id: Identifier for the reinsurance contract layer.
    """

    def __init__(
        self,
        model_data: ExperienceModelData,
        layer_id: int,
        years_weighting: dict[int, float] | None = None,
        projection_methods: dict[int, ProjectionMethods] | None = None,
        development_pattern: dict[int, float] | None = None,
        a_priori_assumption: dict[int, float] | None = None,
    ) -> None:
        years = model_data.exposures.modelling_years
        self.modelling_years: list[int] = years
        self.years_weighting: dict[int, float] = (
            years_weighting if years_weighting else {yr: 1.0 for yr in years}
        )
        self.projection_methods: dict[int, ProjectionMethods] = (
            projection_methods
            if projection_methods
            else {yr: ProjectionMethods.SIMPLE_CAPE_COD for yr in years}
        )
        self.development_pattern: dict[int, float] = (
            development_pattern if development_pattern else {yr: 1.0 for yr in years}
        )
        self.a_priori: dict[int, float] = (
            a_priori_assumption if a_priori_assumption else {yr: 0.0 for yr in years}
        )
        self.data: ExperienceModelData = model_data
        self.layer_id: int = layer_id

    def _collect_cape_cod_data(
        self,
    ) -> tuple[list[float], list[float], list[float], list[float]]:
        """Gather per-year arrays needed by the Cape Cod prior algorithm."""
        trend_factors: list[float] = []
        losses: list[float] = []
        dev_factors: list[float] = []
        exposures_list: list[float] = []
        for yr in self.modelling_years:
            yr_claims = self.data.aggregate_subject_contract_claims.get(self.layer_id, {}).get(yr)
            yr_exposures = self.data.aggregate_exposures.get(yr)
            if yr_claims is None or yr_exposures is None:
                continue
            trend_factors.append(1.0)
            losses.append(yr_claims.get("latest_incurred", 0.0))
            dev_factors.append(self.development_pattern.get(yr, 1.0))
            exposures_list.append(yr_exposures.get("earned", 0.0))
        return trend_factors, losses, dev_factors, exposures_list

    def calculate_burn_cost(self) -> dict[int, float]:
        """Calculate the burn cost for each modelling year.

        Returns:
            Mapping of modelling year to burn cost (ultimate claims / earned exposure).
        """
        burn_costs: dict[int, float] = {}
        cc_data: tuple[list[float], list[float], list[float], list[float]] | None = None

        for year in self.modelling_years:
            layer_claims = self.data.aggregate_subject_contract_claims.get(self.layer_id, {})
            if year not in layer_claims or year not in self.data.aggregate_exposures:
                continue

            claims_data = layer_claims[year]
            exposures_data = self.data.aggregate_exposures[year]
            latest_incurred = claims_data.get("latest_incurred", 0.0)
            earned_exposure = exposures_data.get("earned", 0.0)

            if earned_exposure == 0.0:
                continue

            method = self.projection_methods.get(year, ProjectionMethods.SIMPLE_CAPE_COD)
            dev_factor = self.development_pattern.get(year, 1.0)
            a_priori_value = self.a_priori.get(year, 0.0)

            projection_fn = projection_methods_fn[method]
            try:
                if method == ProjectionMethods.CHAINLADDER:
                    ultimate = projection_fn(latest_incurred, dev_factor)
                elif method == ProjectionMethods.BF:
                    ultimate = projection_fn(latest_incurred, earned_exposure, dev_factor, a_priori_value)
                else:
                    # SIMPLE_CAPE_COD or GENERALISED_CAPE_COD — build shared data once
                    if cc_data is None:
                        cc_data = self._collect_cape_cod_data()
                    tf, lo, df, ex = cc_data
                    if method == ProjectionMethods.SIMPLE_CAPE_COD:
                        ultimate = projection_fn(
                            latest_incurred, earned_exposure, dev_factor, tf, lo, df, ex
                        )
                    else:
                        ultimate = projection_fn(
                            latest_incurred, earned_exposure, dev_factor, tf, lo, df, ex
                        )

                burn_costs[year] = ultimate / earned_exposure

            except (ValueError, ZeroDivisionError, ArithmeticError, RuntimeError) as e:
                raise ValueError(
                    f"Projection failed for year {year}, layer {self.layer_id}: {e}"
                ) from e

        return burn_costs
