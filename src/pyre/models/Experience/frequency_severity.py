from dataclasses import dataclass
from math import lgamma, log, pi, sqrt
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


class FrequencyFit:
    def __init__(self, distributions: List[FrequencyDistribution], claim_counts: List[int]):
        self.distributions = distributions
        self.claim_counts = claim_counts

    def fit(self) -> List[FitResult]:
        """Fit each distribution in ``self.distributions`` to
        ``self.claim_counts``.

        Estimation methods follow Klugman, Panjer & Willmot, *Loss Models:
        From Data to Decisions*, 4th ed., Ch. 13 "Parameter Estimation",
        §13.2 "Method of Moments":

        - ``FrequencyDistribution.POISSON``: maximum likelihood (which for
          the Poisson coincides with the method of moments).
          ``lambda_hat = mean(counts)``.
        - ``FrequencyDistribution.NEGATIVE_BINOMIAL``: method of moments.
          See :meth:`_fit_negative_binomial` for the derivation.

        Returns one :class:`FitResult` per entry in ``self.distributions``,
        in the same order, carrying the fitted parameters plus the resulting
        log-likelihood and AIC (``aic = 2*k - 2*log_likelihood``, with
        ``k = 1`` parameter for Poisson and ``k = 2`` for Negative Binomial).

        Raises:
            NotImplementedError: for any distribution other than ``POISSON``
                or ``NEGATIVE_BINOMIAL`` (e.g. ``FrequencyDistribution.OTHER``).
            ValueError: from :meth:`_fit_negative_binomial` if the sample is
                not overdispersed (``variance <= mean``).
        """
        data = self.claim_counts
        results: List[FitResult] = []
        for distribution in self.distributions:
            if distribution == FrequencyDistribution.POISSON:
                results.append(self._fit_poisson(data))
            elif distribution == FrequencyDistribution.NEGATIVE_BINOMIAL:
                results.append(self._fit_negative_binomial(data))
            else:
                raise NotImplementedError(
                    f"Fitting for frequency distribution {distribution} has not been "
                    "implemented yet"
                )
        return results

    @staticmethod
    def _fit_poisson(data: List[int]) -> FitResult:
        """Maximum likelihood fit of the Poisson distribution.

        ``lambda_hat = mean(counts)`` — the Poisson's single parameter is
        simultaneously its mean, so MLE and method-of-moments coincide.

        See Klugman, Panjer & Willmot, *Loss Models*, 4th ed., Ch. 13 §13.2.
        """
        lambda_hat = mean(data)
        log_likelihood = sum(-lambda_hat + k * log(lambda_hat) - lgamma(k + 1) for k in data)
        aic = 2 * 1 - 2 * log_likelihood
        return FitResult(
            distribution=FrequencyDistribution.POISSON,
            parameters={"lambda": lambda_hat},
            log_likelihood=log_likelihood,
            aic=aic,
        )

    @staticmethod
    def _fit_negative_binomial(data: List[int]) -> FitResult:
        """Method-of-moments fit of the Negative Binomial distribution.

        Standard actuarial parameterization (Klugman, Panjer & Willmot,
        *Loss Models*, 4th ed., Ch. 13 §13.2): ``mean = r*(1-p)/p`` and
        ``variance = r*(1-p)/p**2``.

        Derivation: dividing variance by mean cancels ``r*(1-p)``, leaving
        ``variance/mean = 1/p``, so ``p_hat = m / v`` for sample mean ``m``
        and sample variance ``v``. Substituting ``p_hat`` back into
        ``mean = r*(1-p)/p`` and solving for ``r`` gives
        ``r_hat = m * p_hat / (1 - p_hat)``, which simplifies (substituting
        ``p_hat = m/v`` and ``1 - p_hat = (v-m)/v``) to the equivalent
        closed form ``r_hat = m**2 / (v - m)``.

        This is only valid when ``v > m`` (overdispersion — otherwise
        ``p_hat`` falls outside ``(0, 1)`` and ``r_hat`` is non-positive).
        Raises ``ValueError`` when the sample is not overdispersed.
        """
        m = mean(data)
        v = pvariance(data, mu=m)
        if v <= m:
            raise ValueError(
                "Negative Binomial method-of-moments fit requires overdispersed "
                f"data (sample variance {v} must exceed sample mean {m})"
            )
        p_hat = m / v
        r_hat = m * p_hat / (1 - p_hat)
        log_likelihood = sum(
            lgamma(r_hat + k)
            - lgamma(r_hat)
            - lgamma(k + 1)
            + r_hat * log(p_hat)
            + k * log(1 - p_hat)
            for k in data
        )
        aic = 2 * 2 - 2 * log_likelihood
        return FitResult(
            distribution=FrequencyDistribution.NEGATIVE_BINOMIAL,
            parameters={"r": r_hat, "p": p_hat},
            log_likelihood=log_likelihood,
            aic=aic,
        )
