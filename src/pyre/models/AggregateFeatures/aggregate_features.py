from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional

from ...enums import FrequencyDistribution, SeverityDistribution
from ...treaty.contracts import RIContract
from ..Experience.experience_preparer import ExperienceModelData
from ..Experience.frequency_severity import FitResult, FrequencyFit, SeverityFit
from ..Exposure.exposure_rating_cost import ExposureModel
from .selections import Selections

if TYPE_CHECKING:
    from .simulation_engine import SimulationResults


@dataclass
class ModellingAssumptions:
    """Pricing assumptions driving a :class:`Simulation` and its downstream
    required-premium calculation.

    ``capital_confidence_level`` defaults to 0.995 -- a commonly used
    convention in practice (e.g. Solvency II's 1-in-200 standard) -- rather
    than a figure mandated by any particular capital-allocation methodology.
    ``use_tvar`` selects between TVaR (expected shortfall, the default) and
    VaR for the tail statistic underlying :meth:`Simulation.required_capital`.

    ``mean_payment_duration_years`` is typically derived from the underlying
    claims' ``ClaimDevelopmentHistory.mean_payment_duration`` by the caller
    (e.g. an ``AggregateFeatures`` orchestrator with access to the real
    claims data) and supplied here as a single assumption, since
    ``Simulation`` itself works from a fitted distribution, not individual
    claims. ``profit_commission_rate`` and ``retrocession_premium_loading``
    default to 0.0 -- no profit commission and no retrocession loading
    unless explicitly configured (safe/conservative defaults).
    """

    cost_of_capital: float
    required_rate_of_return: float
    capital_confidence_level: float = 0.995
    use_tvar: bool = True
    investment_yield: float = 0.0
    tax_rate: float = 0.0
    acquisition_cost_ratio: float = 0.0
    brokerage_cost_ratio: float = 0.0
    mean_payment_duration_years: float = 0.0
    profit_commission_rate: float = 0.0
    retrocession_premium_loading: float = 0.0


class AggregateFeatures:
    """Orchestrates a frequency/severity fit from experience data into a
    Monte Carlo :class:`Simulation` and returns its
    :class:`SimulationResults`.

    ``exposure_data`` and ``selections`` are accepted for interface
    completeness -- this orchestrator is meant to eventually blend
    experience and exposure indications via :class:`Selections`' credibility
    weighting -- but are NOT yet used inside :meth:`run`. That
    credibility-blended run is a larger, separate piece of work this class
    does not scope; they are stored as ``self._exposure_data`` /
    ``self._selections`` as currently-unused placeholders for it, not
    silently-broken dead parameters.
    """

    def __init__(
        self,
        experience_data: ExperienceModelData,
        exposure_data: ExposureModel,
        selections: Selections,
        assumptions: ModellingAssumptions,
        ibner_dev_pattern: Optional[Dict[int, float]] = None,
    ) -> None:
        self._experience_data = experience_data
        self._exposure_data = exposure_data
        self._selections = selections
        self._assumptions = assumptions
        self._ibner_dev_pattern = ibner_dev_pattern

    @property
    def experience_data(self) -> ExperienceModelData:
        return self._experience_data

    @property
    def ri_contract(self) -> RIContract:
        return self._experience_data.ri_contract

    def _claim_counts_by_modelling_year(self) -> Dict[int, int]:
        claims_by_year: Dict[int, int] = {}
        for claim in self._experience_data.trended_claims.claims:
            year = claim.claims_meta_data.modelling_year
            claims_by_year[year] = claims_by_year.get(year, 0) + 1
        return claims_by_year

    def _ibner_pattern(self) -> Dict[int, float]:
        """Return the IBNER development pattern to use for the severity
        fit.

        Defaults to a no-op pattern (every year's IBNER factor is 1.0)
        since ``AggregateFeatures`` has no triangle-based IBNER extraction
        wired in; pass an explicit ``ibner_dev_pattern`` (e.g. from
        ``IBNERPatternExtractor.get_IBNER_pattern()``) for a real IBNER
        adjustment.
        """
        if self._ibner_dev_pattern is not None:
            return self._ibner_dev_pattern
        return {year: 1.0 for year in self._experience_data.trended_claims.modelling_years}

    def _fit_best_severity(self, ibner_dev_pattern: Dict[int, float]) -> FitResult:
        results = []
        for distribution in (SeverityDistribution.LOGNORMAL, SeverityDistribution.PARETO):
            try:
                results.extend(
                    SeverityFit(
                        distributions=[distribution],
                        data=self._experience_data,
                        ibner_dev_pattern=ibner_dev_pattern,
                    ).fit()
                )
            except (ValueError, NotImplementedError):
                continue
        if not results:
            raise ValueError("No severity distribution could be fit to the experience data")
        return min(results, key=lambda r: r.aic)

    def _fit_best_frequency(self, claim_counts) -> FitResult:
        results = []
        for distribution in (
            FrequencyDistribution.POISSON,
            FrequencyDistribution.NEGATIVE_BINOMIAL,
        ):
            try:
                results.extend(FrequencyFit([distribution], claim_counts).fit())
            except (ValueError, NotImplementedError):
                # e.g. Negative Binomial requires overdispersed data; skip
                # if that's not met and fall back to whichever other
                # distribution(s) did succeed (typically Poisson-only).
                continue
        if not results:
            raise ValueError("No frequency distribution could be fit to the experience data")
        return min(results, key=lambda r: r.aic)

    def run(self, n_simulations: int = 10_000) -> "SimulationResults":
        from .simulation_engine import Simulation

        claim_counts = list(self._claim_counts_by_modelling_year().values())
        ibner_dev_pattern = self._ibner_pattern()

        best_severity = self._fit_best_severity(ibner_dev_pattern)
        best_frequency = self._fit_best_frequency(claim_counts)

        simulation = Simulation(
            frequency_fit=best_frequency,
            severity_fit=best_severity,
            ri_contract=self._experience_data.ri_contract,
            assumptions=self._assumptions,
            n_simulations=n_simulations,
        )
        simulation.run()
        return simulation.output()
