import math
from dataclasses import dataclass, field
from typing import Any

from ...models.experience.experience_preparer import ExperienceModelData
from ...models.exposure.exposure_rating_cost import ExposureModel


@dataclass
class CredibilityConfig:
    """Configuration for credibility weight calculation."""

    method: str = "buhlmann"
    full_credibility_standard: int = 1082
    claim_count: int = 0
    expected_process_variance: float = 1.0
    variance_of_hypothetical_means: float = 0.1
    data_by_group: dict[Any, list[float]] = field(default_factory=dict)
    exposures: list[float] = field(default_factory=list)
    claim_counts: list[int] = field(default_factory=list)
    data: list[float] = field(default_factory=list)
    collective_mean: float = 1.0
    prior_mean: float = 1.0
    prior_variance: float = 0.1
    data_variance: float = 1.0


class _VarianceEstimator:
    """Internal: variance calculations used by credibility methods."""

    @staticmethod
    def sample_variance(data: list[float]) -> float:
        if len(data) < 2:
            return 0.0
        mean = sum(data) / len(data)
        return sum((x - mean) ** 2 for x in data) / (len(data) - 1)

    @staticmethod
    def process_variance(claims_by_year: dict[Any, list[float]]) -> float:
        """Estimate the process variance (within variance) from grouped data."""
        if not claims_by_year:
            return 0.0

        total_variance = 0.0
        total_weight = 0.0

        for _group, values in claims_by_year.items():
            if len(values) < 2:
                continue

            group_mean = sum(values) / len(values)
            group_variance = sum((x - group_mean) ** 2 for x in values) / len(values)

            weight = len(values)
            total_variance += group_variance * weight
            total_weight += weight

        if total_weight <= 0:
            return 0.0

        return total_variance / total_weight

    @staticmethod
    def variance_of_hypothetical_means(claims_by_year: dict[Any, list[float]]) -> float:
        """Estimate the variance of hypothetical means (between variance) from grouped data."""
        if not claims_by_year:
            return 0.0

        all_values: list[float] = []
        for values in claims_by_year.values():
            all_values.extend(values)

        if not all_values:
            return 0.0

        overall_mean = sum(all_values) / len(all_values)

        group_means: dict[Any, float] = {}
        group_sizes: dict[Any, int] = {}

        for group, values in claims_by_year.items():
            if not values:
                continue
            group_means[group] = sum(values) / len(values)
            group_sizes[group] = len(values)

        weighted_sum_squared_diff = 0.0
        total_weight = 0.0

        for group, mean in group_means.items():
            weight = group_sizes[group]
            weighted_sum_squared_diff += weight * ((mean - overall_mean) ** 2)
            total_weight += weight

        if total_weight <= 0:
            return 0.0

        raw_between_variance = weighted_sum_squared_diff / total_weight

        pv = _VarianceEstimator.process_variance(claims_by_year)

        avg_group_size = sum(group_sizes.values()) / len(group_sizes) if group_sizes else 0

        adjusted_between_variance = max(0, raw_between_variance - (pv / avg_group_size))

        return adjusted_between_variance


class CredibilityWeight:
    def __init__(self, experience_data: ExperienceModelData, exposure_data: ExposureModel) -> None:
        """
        Initialize the CredibilityWeight class with experience and exposure data.

        Args:
            experience_data: Experience model data containing claims and exposures
            exposure_data: Exposure model data containing exposures
        """
        self.experience_data = experience_data
        self.exposure_data = exposure_data

    def calculate_sample_variance(self, data: list[float]) -> float:
        """
        Calculate the sample variance of a list of data points.

        Args:
            data: List of observed values

        Returns:
            Sample variance of the data
        """
        if not data or len(data) < 2:
            return 0.0
        return _VarianceEstimator.sample_variance(data)

    def calculate_data_variance(self, data: list[float], method: str = "sample") -> float:
        """
        Calculate the variance of data using different methods.

        Args:
            data: List of observed values
            method: Method to use for variance calculation:
                   "sample" - standard sample variance
                   "population" - population variance
                   "process" - estimate of process variance for credibility

        Returns:
            Variance of the data based on the specified method
        """
        if not data or len(data) < 2:
            return 0.0

        mean = sum(data) / len(data)

        if method == "sample":
            return sum((x - mean) ** 2 for x in data) / (len(data) - 1)
        elif method in ("population", "process"):
            return sum((x - mean) ** 2 for x in data) / len(data)
        else:
            raise ValueError(f"Invalid variance calculation method: {method}")

    def estimate_process_variance(self, data_by_group: dict[Any, list[float]]) -> float:
        """
        Estimate the process variance (within variance) from grouped data.

        Args:
            data_by_group: Dictionary mapping group identifiers to lists of observed values

        Returns:
            Estimated process variance
        """
        return _VarianceEstimator.process_variance(data_by_group)

    def estimate_variance_of_hypothetical_means(
        self, data_by_group: dict[Any, list[float]]
    ) -> float:
        """
        Estimate the variance of hypothetical means (between variance) from grouped data.

        Args:
            data_by_group: Dictionary mapping group identifiers to lists of observed values

        Returns:
            Estimated variance of hypothetical means
        """
        return _VarianceEstimator.variance_of_hypothetical_means(data_by_group)

    def limited_fluctuation_credibility(
        self, claim_count: int, full_credibility_standard: int = 1082
    ) -> float:
        """
        Calculate credibility using the Limited Fluctuation (Classical) Credibility method.
        Based on the formula Z = min(sqrt(n/n_full), 1) where n_full is the full credibility standard.

        The default full_credibility_standard of 1082 corresponds to a 95% confidence level
        with a 5% margin of error assuming a Poisson frequency process.

        Args:
            claim_count: Number of claims
            full_credibility_standard: Number of claims needed for full credibility

        Returns:
            Credibility factor between 0 and 1
        """
        if claim_count <= 0 or full_credibility_standard <= 0:
            return 0.0

        credibility = math.sqrt(claim_count / full_credibility_standard)
        return min(credibility, 1.0)

    def buhlmann_credibility(
        self,
        claim_count: int,
        expected_process_variance: float,
        variance_of_hypothetical_means: float,
    ) -> float:
        """
        Calculate credibility using the Bühlmann Credibility method.
        Based on the formula Z = n / (n + k) where k = EPV / VHM.

        Args:
            claim_count: Number of claims
            expected_process_variance: Expected value of the process variance (EPV)
            variance_of_hypothetical_means: Variance of the hypothetical means (VHM)

        Returns:
            Credibility factor between 0 and 1
        """
        if (
            claim_count <= 0
            or expected_process_variance <= 0
            or variance_of_hypothetical_means <= 0
        ):
            return 0.0

        k = expected_process_variance / variance_of_hypothetical_means
        credibility = claim_count / (claim_count + k)

        return min(max(credibility, 0.0), 1.0)

    def buhlmann_straub_credibility(
        self,
        exposures: list[float],
        claim_counts: list[int],
        expected_process_variance: float,
        variance_of_hypothetical_means: float,
    ) -> float:
        """
        Calculate credibility using the Bühlmann-Straub Credibility method.
        This extends the Bühlmann method to account for varying exposure sizes.

        Args:
            exposures: List of exposure values
            claim_counts: List of claim counts corresponding to each exposure
            expected_process_variance: Expected value of the process variance (EPV)
            variance_of_hypothetical_means: Variance of the hypothetical means (VHM)

        Returns:
            Credibility factor between 0 and 1
        """
        if not exposures or not claim_counts or len(exposures) != len(claim_counts):
            return 0.0

        if expected_process_variance <= 0 or variance_of_hypothetical_means <= 0:
            return 0.0

        total_exposure = sum(exposures)
        if total_exposure <= 0:
            return 0.0

        k = expected_process_variance / variance_of_hypothetical_means
        credibility = total_exposure / (total_exposure + k)

        return min(max(credibility, 0.0), 1.0)

    def greatest_accuracy_credibility(self, data: list[float], collective_mean: float) -> float:
        """
        Calculate credibility using the Greatest Accuracy Credibility method.
        This method aims to minimize the mean squared error.

        Args:
            data: List of observed values
            collective_mean: The collective mean (a priori estimate)

        Returns:
            Credibility factor between 0 and 1
        """
        if not data or collective_mean <= 0:
            return 0.0

        individual_mean = sum(data) / len(data)
        if individual_mean <= 0:
            return 0.0

        individual_variance = self.calculate_data_variance(data, method="population")

        between_variance = max(0, individual_variance - (collective_mean / len(data)))

        if between_variance <= 0:
            return 0.0

        credibility = between_variance / (between_variance + (individual_variance / len(data)))

        return min(max(credibility, 0.0), 1.0)

    def bayesian_credibility(
        self, prior_mean: float, prior_variance: float, data: list[float], data_variance: float
    ) -> float:
        """
        Calculate credibility using Bayesian Credibility approach.

        Args:
            prior_mean: Mean of the prior distribution
            prior_variance: Variance of the prior distribution
            data: List of observed values
            data_variance: Variance of the data

        Returns:
            Credibility factor between 0 and 1
        """
        if not data or prior_variance <= 0 or data_variance <= 0:
            return 0.0

        n = len(data)
        if n <= 0:
            return 0.0

        credibility = (n * prior_variance) / (n * prior_variance + data_variance)

        return min(max(credibility, 0.0), 1.0)


class Selections:
    def __init__(
        self,
        experience_data: ExperienceModelData,
        exposure_data: ExposureModel,
        credibility_weight: CredibilityWeight | None = None,
    ) -> None:
        """
        Initialize the Selections class with experience and exposure data.

        Args:
            experience_data: Experience model data containing claims and exposures
            exposure_data: Exposure model data containing exposures
            credibility_weight: Optional CredibilityWeight object for calculating weights
        """
        self.experience_data = experience_data
        self.exposure_data = exposure_data
        self.credibility_weight = credibility_weight or CredibilityWeight(
            experience_data, exposure_data
        )
        self._experience_weight = 0.5  # Default weight
        self._exposure_weight = 0.5  # Default weight

    def calculate_experience_weight(
        self,
        claims_by_year: dict[int, list[float]] | None = None,
        config: CredibilityConfig | None = None,
    ) -> float:
        """
        Calculate the weight to assign to experience rating.

        Args:
            claims_by_year: Optional dict mapping year to list of claim amounts
            config: CredibilityConfig specifying method and parameters

        Returns:
            Weight for experience rating between 0 and 1
        """
        if config is None:
            config = CredibilityConfig()

        method = config.method
        full_credibility_standard = config.full_credibility_standard

        # Derive claim_count from experience_data if not set in config
        claim_count = config.claim_count
        if claim_count == 0 and hasattr(self.experience_data, "subject_contract_claims"):
            claim_count = sum(
                len(claims_obj.claims)
                for claims_obj in self.experience_data.subject_contract_claims.values()
            )

        data_by_group: dict[Any, list[float]] = (
            claims_by_year if claims_by_year is not None else config.data_by_group
        )

        if method == "limited_fluctuation":
            weight = self.credibility_weight.limited_fluctuation_credibility(
                claim_count, full_credibility_standard
            )
        elif method == "buhlmann":
            epv = config.expected_process_variance
            vhm = config.variance_of_hypothetical_means

            if data_by_group:
                epv = self.credibility_weight.estimate_process_variance(data_by_group)
                vhm = self.credibility_weight.estimate_variance_of_hypothetical_means(data_by_group)

            weight = self.credibility_weight.buhlmann_credibility(claim_count, epv, vhm)
        elif method == "buhlmann_straub":
            epv = config.expected_process_variance
            vhm = config.variance_of_hypothetical_means

            if data_by_group:
                epv = self.credibility_weight.estimate_process_variance(data_by_group)
                vhm = self.credibility_weight.estimate_variance_of_hypothetical_means(data_by_group)

            weight = self.credibility_weight.buhlmann_straub_credibility(
                config.exposures,
                config.claim_counts,
                epv,
                vhm,
            )
        elif method == "greatest_accuracy":
            data = config.data
            if not data and hasattr(self.experience_data, "subject_contract_claims"):
                data = [
                    claim.capped_claim_development_history.latest_incurred
                    for claims_obj in self.experience_data.subject_contract_claims.values()
                    for claim in claims_obj.claims
                ]

            weight = self.credibility_weight.greatest_accuracy_credibility(
                data, config.collective_mean
            )
        elif method == "bayesian":
            data = config.data
            if not data and hasattr(self.experience_data, "subject_contract_claims"):
                data = [
                    claim.capped_claim_development_history.latest_incurred
                    for claims_obj in self.experience_data.subject_contract_claims.values()
                    for claim in claims_obj.claims
                ]

            data_variance = config.data_variance
            if data_variance == 1.0 and data:
                data_variance = self.credibility_weight.calculate_data_variance(
                    data, method="sample"
                )

            weight = self.credibility_weight.bayesian_credibility(
                config.prior_mean,
                config.prior_variance,
                data,
                data_variance,
            )
        else:
            raise ValueError(f"Invalid credibility method: {method}")

        self._experience_weight = weight
        self._exposure_weight = 1.0 - weight

        return weight

    def exposure_weight(self) -> float:
        """
        Get the weight to assign to exposure rating.

        Returns:
            Weight for exposure rating between 0 and 1
        """
        return self._exposure_weight

    def unlimited_selection(self, experience_result: float, exposure_result: float) -> float:
        """
        Selects the unlimited option for the subject contract by combining
        experience and exposure results based on their weights.

        Args:
            experience_result: Result from experience rating method
            exposure_result: Result from exposure rating method

        Returns:
            Weighted average of experience and exposure results
        """
        return experience_result * self._experience_weight + exposure_result * self._exposure_weight

    def make_selection(
        self,
        experience_result: float,
        exposure_result: float,
        method: str = "limited_fluctuation",
        config: CredibilityConfig | None = None,
    ) -> float:
        """
        Make a selection by calculating weights and combining results.

        Args:
            experience_result: Result from experience rating method
            exposure_result: Result from exposure rating method
            method: Credibility method to use (ignored if config is provided)
            config: CredibilityConfig specifying method and parameters

        Returns:
            Selected result based on weighted average
        """
        if config is None:
            config = CredibilityConfig(method=method)

        self.calculate_experience_weight(config=config)

        return self.unlimited_selection(experience_result, exposure_result)
