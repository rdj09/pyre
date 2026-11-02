from dataclasses import dataclass
from math import log, pi, sqrt
from statistics import mean, pvariance
from typing import Any, Dict, List, Union

from ...enums import FrequencyDistribution, SeverityDistribution
from ...models.Experience.experience_preparer import ExperienceModelData


@dataclass
class FitResult:
    """Result of fitting a single distribution to data.

    Shared between ``SeverityFit.fit()`` (severity distributions) and the
    later ``FrequencyFit.fit()`` (frequency distributions) — ``distribution``
    is typed as the union of both enums so neither fitter needs its own
    result type.
    """

    distribution: Union[SeverityDistribution, FrequencyDistribution]
    parameters: Dict[str, float]
    log_likelihood: float
    aic: float


class SeverityFit:
    def __init__(self, distributions: List[SeverityDistribution], data : ExperienceModelData, ibner_dev_pattern: Dict[int, float], ground_up:bool = True):
        self.data = data
        self.ground_up_model = ground_up
        self.ibner_dev_pattern = ibner_dev_pattern # could pass IBNERPatternExtractor().getIBNERPATTERN as outputs Dict[int,float] if needed
        self.distributions = distributions

    @property
    def _individual_projected_claims(self) -> Any | List[float]:
        if self.ground_up_model:
            # Return list of IBNER-projected incurred amounts for each claim
            return [claim.capped_claim_development_history.latest_incurred * self.ibner_dev_pattern[claim.claims_meta_data.modelling_year] for claim in self.data.trended_claims.claims]
        else:
            raise NotImplementedError("non ground up fitting hasn't been implemented yet")

    def fit(self) -> List[FitResult]:
        """Fit each distribution in ``self.distributions`` to the individual
        IBNER-projected claim severities (``self._individual_projected_claims``).

        Estimation methods follow Klugman, Panjer & Willmot, *Loss Models:
        From Data to Decisions*, 4th ed., Ch. 13 "Parameter Estimation",
        §13.2 "Method of Moments" (and the accompanying maximum likelihood
        treatment of the single-parameter Pareto in that chapter):

        - ``SeverityDistribution.LOGNORMAL``: method of moments. With sample
          mean ``m`` and variance ``v`` of the claim amounts,
          ``mu = log(m**2 / sqrt(v + m**2))`` and
          ``sigma = sqrt(log(v / m**2 + 1))``.
        - ``SeverityDistribution.PARETO`` (single-parameter Pareto,
          ``f(x) = alpha * x_m**alpha / x**(alpha + 1)`` for ``x >= x_m``):
          maximum likelihood. ``x_m = min(data)`` and
          ``alpha = n / sum(log(xi / x_m) for xi in data)``.

        Returns one :class:`FitResult` per entry in ``self.distributions``,
        in the same order, carrying the fitted parameters plus the resulting
        log-likelihood and AIC (``aic = 2*k - 2*log_likelihood``, with
        ``k = 2`` parameters for both distributions here).

        Raises:
            NotImplementedError: for any distribution other than
                ``LOGNORMAL`` or ``PARETO`` (e.g. ``SeverityDistribution.OTHER``).
        """
        data = self._individual_projected_claims
        results: List[FitResult] = []
        for distribution in self.distributions:
            if distribution == SeverityDistribution.LOGNORMAL:
                results.append(self._fit_lognormal(data))
            elif distribution == SeverityDistribution.PARETO:
                results.append(self._fit_pareto(data))
            else:
                raise NotImplementedError(
                    f"Fitting for severity distribution {distribution} has not been implemented yet"
                )
        return results

    @staticmethod
    def _fit_lognormal(data: List[float]) -> FitResult:
        """Method-of-moments fit of the lognormal distribution.

        See Klugman, Panjer & Willmot, *Loss Models*, 4th ed., Ch. 13 §13.2.
        """
        m = mean(data)
        v = pvariance(data, mu=m)
        mu = log(m**2 / sqrt(v + m**2))
        sigma = sqrt(log(v / m**2 + 1))
        log_likelihood = sum(
            -log(x) - log(sigma) - 0.5 * log(2 * pi) - (log(x) - mu) ** 2 / (2 * sigma**2)
            for x in data
        )
        aic = 2 * 2 - 2 * log_likelihood
        return FitResult(
            distribution=SeverityDistribution.LOGNORMAL,
            parameters={"mu": mu, "sigma": sigma},
            log_likelihood=log_likelihood,
            aic=aic,
        )

    @staticmethod
    def _fit_pareto(data: List[float]) -> FitResult:
        """Maximum likelihood fit of the single-parameter Pareto distribution.

        See Klugman, Panjer & Willmot, *Loss Models*, 4th ed., Ch. 13 §13.2.
        """
        n = len(data)
        x_m = min(data)
        alpha = n / sum(log(x / x_m) for x in data)
        log_likelihood = (
            n * log(alpha) + n * alpha * log(x_m) - (alpha + 1) * sum(log(x) for x in data)
        )
        aic = 2 * 2 - 2 * log_likelihood
        return FitResult(
            distribution=SeverityDistribution.PARETO,
            parameters={"alpha": alpha, "x_m": x_m},
            log_likelihood=log_likelihood,
            aic=aic,
        )
