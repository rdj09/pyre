"""Frequency and severity distribution fitting for experience pricing."""

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Union

from ...models.experience.experience_preparer import ExperienceModelData
from ...enums import SeverityDistribution, FrequencyDistribution


# ---------------------------------------------------------------------------
# FitResult
# ---------------------------------------------------------------------------

@dataclass
class FitResult:
    """Result of fitting a distribution to data.

    Attributes:
        distribution: The distribution that was fitted.
        parameters: Dict of parameter name → estimated value.
        log_likelihood: Log-likelihood at the estimated parameters.
        aic: Akaike Information Criterion = 2k - 2 ln(L).
    """
    distribution: Union[SeverityDistribution, FrequencyDistribution]
    parameters: Dict[str, float]
    log_likelihood: float
    aic: float


# ---------------------------------------------------------------------------
# Internal fitting functions
# ---------------------------------------------------------------------------

def _fit_lognormal(data: List[float]) -> Dict[str, float]:
    """Fit lognormal distribution by method of moments.

    mu = log(mean^2 / sqrt(variance + mean^2))
    sigma = sqrt(log(variance / mean^2 + 1))

    Args:
        data: Observed positive loss values.

    Returns:
        Dict with keys "mu" and "sigma".

    Raises:
        ValueError: If data has fewer than 2 elements.
    """
    if len(data) < 2:
        raise ValueError("Lognormal fitting requires at least 2 observations.")

    n = len(data)
    mean = sum(data) / n
    variance = sum((x - mean) ** 2 for x in data) / (n - 1)

    if mean <= 0 or variance <= 0:
        raise ValueError("Data must have positive mean and variance for lognormal fitting.")

    sigma2 = math.log(variance / (mean ** 2) + 1.0)
    mu = math.log(mean ** 2 / math.sqrt(variance + mean ** 2))

    return {"mu": mu, "sigma": math.sqrt(sigma2)}


def _fit_pareto(data: List[float]) -> Dict[str, float]:
    """Fit single-parameter Pareto by maximum likelihood.

    x_m = min(data)
    alpha = n / sum(log(xi / x_m))

    Citation: Klugman, Panjer & Willmot, Loss Models (4th ed.), Ch. 4.

    Args:
        data: Observed positive loss values.

    Returns:
        Dict with keys "alpha" and "x_m".

    Raises:
        ValueError: If data is empty.
    """
    if len(data) < 1:
        raise ValueError("Pareto fitting requires at least 1 observation.")

    x_m = min(data)
    if x_m <= 0:
        raise ValueError("All observations must be positive for Pareto fitting.")

    n = len(data)
    log_sum = sum(math.log(x / x_m) for x in data)

    if log_sum == 0:
        raise ValueError("All observations are equal; Pareto alpha is undefined.")

    alpha = n / log_sum
    return {"alpha": alpha, "x_m": x_m}


def _fit_poisson(counts: List[int]) -> Dict[str, float]:
    """Fit Poisson distribution by MLE (lambda = sample mean).

    Args:
        counts: Non-negative integer claim counts.

    Returns:
        Dict with key "lambda_".

    Raises:
        ValueError: If counts is empty.
    """
    if not counts:
        raise ValueError("Poisson fitting requires at least 1 observation.")
    return {"lambda_": sum(counts) / len(counts)}


def _fit_negative_binomial(counts: List[int]) -> Dict[str, float]:
    """Fit Negative Binomial by method of moments.

    mean = r * (1-p) / p
    variance = r * (1-p) / p^2

    Solving: p = mean / variance, r = mean * p / (1 - p)

    Args:
        counts: Non-negative integer claim counts.

    Returns:
        Dict with keys "r" and "p".

    Raises:
        ValueError: If counts has fewer than 2 elements or variance <= mean.
    """
    if len(counts) < 2:
        raise ValueError("Negative Binomial fitting requires at least 2 observations.")

    n = len(counts)
    mean = sum(counts) / n
    variance = sum((x - mean) ** 2 for x in counts) / (n - 1)

    if variance <= mean:
        raise ValueError(
            "Sample variance is not greater than mean; "
            "Negative Binomial is not identifiable (use Poisson instead)."
        )

    p = mean / variance
    r = mean * p / (1.0 - p)
    return {"r": r, "p": p}


# ---------------------------------------------------------------------------
# SeverityFit
# ---------------------------------------------------------------------------

class SeverityFit:
    """Fit severity distributions to projected individual claims.

    Args:
        distributions: List of distributions to fit.
        data: Experience model data containing claims.
        ibner_dev_pattern: Dict mapping modelling year to IBNER development factor.
        ground_up: If True, fit to ground-up (capped) claims. Defaults to True.
    """

    def __init__(
        self,
        distributions: List[SeverityDistribution],
        data: ExperienceModelData,
        ibner_dev_pattern: Dict[int, float],
        ground_up: bool = True,
    ) -> None:
        self.distributions = distributions
        self.data = data
        self.ibner_dev_pattern = ibner_dev_pattern
        self.ground_up = ground_up

    @property
    def _individual_projected_claims(self) -> List[float]:
        """Individual projected ultimate claims using IBNER development factors."""
        if self.ground_up:
            return [
                claim.capped_claim_development_history.latest_incurred
                * self.ibner_dev_pattern.get(claim.claims_meta_data.modelling_year, 1.0)
                for claim in self.data.trended_claims.claims
            ]
        raise NotImplementedError("Non-ground-up fitting has not been implemented yet")

    def fit(self) -> Dict[str, Dict[str, float]]:
        """Fit each distribution in self.distributions to the projected claims.

        Returns:
            Dict mapping distribution name to fitted parameter dict.
        """
        claims = self._individual_projected_claims
        results: Dict[str, Dict[str, float]] = {}
        for dist in self.distributions:
            if dist == SeverityDistribution.LOGNORMAL:
                results["lognormal"] = _fit_lognormal(claims)
            elif dist == SeverityDistribution.PARETO:
                results["pareto"] = _fit_pareto(claims)
        return results


# ---------------------------------------------------------------------------
# FrequencyFit
# ---------------------------------------------------------------------------

class FrequencyFit:
    """Fit frequency distributions to claim counts by modelling year.

    Args:
        distributions: List of frequency distributions to fit.
        data: Experience model data.
    """

    def __init__(
        self,
        distributions: List[FrequencyDistribution],
        data: ExperienceModelData,
    ) -> None:
        self.distributions = distributions
        self.data = data

    @property
    def _claim_counts_by_year(self) -> Dict[int, int]:
        """Claim count per modelling year from subject_contract_claims."""
        counts: Dict[int, int] = {}
        for layer_claims in self.data.subject_contract_claims.values():
            for claim in layer_claims.claims:
                year = claim.claims_meta_data.modelling_year
                counts[year] = counts.get(year, 0) + 1
            break  # Use first layer only for frequency — avoid double-counting
        return counts

    def fit(self) -> Dict[str, Dict[str, float]]:
        """Fit each distribution to claim counts across modelling years.

        Returns:
            Dict mapping distribution name to fitted parameter dict.
        """
        counts_by_year = self._claim_counts_by_year
        counts = list(counts_by_year.values())

        results: Dict[str, Dict[str, float]] = {}
        for dist in self.distributions:
            if dist == FrequencyDistribution.POISSON:
                results["poisson"] = _fit_poisson(counts)
            elif dist == FrequencyDistribution.NEGATIVE_BINOMIAL:
                results["negative_binomial"] = _fit_negative_binomial(counts)
        return results
