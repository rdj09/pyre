from typing import Dict, List, Optional, Union, Any
import math
from pyre.Models.Experience.experience_preparer import ExperienceModelData
from pyre.Models.Exposure.exposure_preparer import ExposureModelData

class CredibilityWeight:
    def __init__(self, experience_data: ExperienceModelData, exposure_data: ExposureModelData) -> None:
        """
        Initialize the CredibilityWeight class with experience and exposure data.

        Args:
            experience_data: Experience model data containing claims and exposures
            exposure_data: Exposure model data containing exposures
        """
        self.experience_data = experience_data
        self.exposure_data = exposure_data

    def calculate_sample_variance(self, data: List[float]) -> float:
        """
        Calculate the sample variance of a list of data points.

        Args:
            data: List of observed values

        Returns:
            Sample variance of the data
        """
        if not data or len(data) < 2:
            return 0.0

        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / (len(data) - 1)  # Using n-1 for sample variance

        return variance

    def calculate_data_variance(self, data: List[float], method: str = "sample") -> float:
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
            # Sample variance (unbiased estimator)
            return sum((x - mean) ** 2 for x in data) / (len(data) - 1)
        elif method == "population":
            # Population variance
            return sum((x - mean) ** 2 for x in data) / len(data)
        elif method == "process":
            # Process variance estimate for credibility calculations
            # This is often the within-variance component
            return sum((x - mean) ** 2 for x in data) / len(data)
        else:
            raise ValueError(f"Invalid variance calculation method: {method}")

    def estimate_process_variance(self, data_by_group: Dict[Any, List[float]]) -> float:
        """
        Estimate the process variance (within variance) from grouped data.
        This is useful for Bühlmann and Bühlmann-Straub credibility methods.

        Args:
            data_by_group: Dictionary mapping group identifiers to lists of observed values

        Returns:
            Estimated process variance
        """
        if not data_by_group:
            return 0.0

        total_variance = 0.0
        total_weight = 0.0

        for group, values in data_by_group.items():
            if len(values) < 2:
                continue

            # Calculate within-group variance
            group_mean = sum(values) / len(values)
            group_variance = sum((x - group_mean) ** 2 for x in values) / len(values)

            # Weight by group size
            weight = len(values)
            total_variance += group_variance * weight
            total_weight += weight

        if total_weight <= 0:
            return 0.0

        return total_variance / total_weight

    def estimate_variance_of_hypothetical_means(self, data_by_group: Dict[Any, List[float]]) -> float:
        """
        Estimate the variance of hypothetical means (between variance) from grouped data.
        This is useful for Bühlmann and Bühlmann-Straub credibility methods.

        Args:
            data_by_group: Dictionary mapping group identifiers to lists of observed values

        Returns:
            Estimated variance of hypothetical means
        """
        if not data_by_group:
            return 0.0

        # Calculate overall mean
        all_values = []
        for values in data_by_group.values():
            all_values.extend(values)

        if not all_values:
            return 0.0

        overall_mean = sum(all_values) / len(all_values)

        # Calculate group means
        group_means = {}
        group_sizes = {}

        for group, values in data_by_group.items():
            if not values:
                continue

            group_means[group] = sum(values) / len(values)
            group_sizes[group] = len(values)

        # Calculate variance of group means
        weighted_sum_squared_diff = 0.0
        total_weight = 0.0

        for group, mean in group_means.items():
            weight = group_sizes[group]
            weighted_sum_squared_diff += weight * ((mean - overall_mean) ** 2)
            total_weight += weight

        if total_weight <= 0:
            return 0.0

        # Calculate raw between variance
        raw_between_variance = weighted_sum_squared_diff / total_weight

        # Adjust for within-group variance
        process_variance = self.estimate_process_variance(data_by_group)

        # Calculate average group size
        avg_group_size = sum(group_sizes.values()) / len(group_sizes) if group_sizes else 0

        # Adjust between variance by removing the expected contribution from process variance
        adjusted_between_variance = max(0, raw_between_variance - (process_variance / avg_group_size))

        return adjusted_between_variance

    def limited_fluctuation_credibility(self, claim_count: int, full_credibility_standard: int = 1082) -> float:
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

    def buhlmann_credibility(self, claim_count: int, expected_process_variance: float, 
                             variance_of_hypothetical_means: float) -> float:
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
        if claim_count <= 0 or expected_process_variance <= 0 or variance_of_hypothetical_means <= 0:
            return 0.0

        k = expected_process_variance / variance_of_hypothetical_means
        credibility = claim_count / (claim_count + k)

        return min(max(credibility, 0.0), 1.0)

    def buhlmann_straub_credibility(self, exposures: List[float], claim_counts: List[int], 
                                   expected_process_variance: float, 
                                   variance_of_hypothetical_means: float) -> float:
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

    def greatest_accuracy_credibility(self, data: List[float], collective_mean: float) -> float:
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

        # Calculate individual mean and variance
        individual_mean = sum(data) / len(data)
        if individual_mean <= 0:
            return 0.0

        # Use the helper function to calculate variance
        individual_variance = self.calculate_data_variance(data, method="population")

        # Calculate between variance (estimate of variance of hypothetical means)
        between_variance = max(0, individual_variance - (collective_mean / len(data)))

        # Calculate credibility
        if between_variance <= 0:
            return 0.0

        credibility = between_variance / (between_variance + (individual_variance / len(data)))

        return min(max(credibility, 0.0), 1.0)

    def bayesian_credibility(self, prior_mean: float, prior_variance: float, 
                            data: List[float], data_variance: float) -> float:
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

        # Bayesian credibility formula
        credibility = (n * prior_variance) / (n * prior_variance + data_variance)

        return min(max(credibility, 0.0), 1.0)


class Selections:
    def __init__(self, experience_data: ExperienceModelData, exposure_data: ExposureModelData, 
                 credibility_weight: Optional[CredibilityWeight] = None) -> None:
        """
        Initialize the Selections class with experience and exposure data.

        Args:
            experience_data: Experience model data containing claims and exposures
            exposure_data: Exposure model data containing exposures
            credibility_weight: Optional CredibilityWeight object for calculating weights
        """
        self.experience_data = experience_data
        self.exposure_data = exposure_data
        self.credibility_weight = credibility_weight or CredibilityWeight(experience_data, exposure_data)
        self._experience_weight = 0.5  # Default weight
        self._exposure_weight = 0.5    # Default weight

    def calculate_experience_weight(self, method: str = "limited_fluctuation", **kwargs) -> float:
        """
        Calculate the weight to assign to experience rating.

        Args:
            method: Credibility method to use ("limited_fluctuation", "buhlmann", 
                   "buhlmann_straub", "greatest_accuracy", or "bayesian")
            **kwargs: Additional parameters for the credibility method

        Returns:
            Weight for experience rating between 0 and 1
        """
        # Get claim count if not provided
        if 'claim_count' not in kwargs and hasattr(self.experience_data, 'subject_contract_claims'):
            kwargs['claim_count'] = len(self.experience_data.subject_contract_claims())

        # Calculate credibility based on the selected method
        if method == "limited_fluctuation":
            weight = self.credibility_weight.limited_fluctuation_credibility(
                kwargs.get('claim_count', 0), 
                kwargs.get('full_credibility_standard', 1082)
            )
        elif method == "buhlmann":
            # Get claim count if not already provided
            claim_count = kwargs.get('claim_count', 0)

            # Get or calculate process variance and variance of hypothetical means
            if 'data_by_group' in kwargs:
                data_by_group = kwargs.get('data_by_group', {})

                # Calculate variances if not provided
                if 'expected_process_variance' not in kwargs:
                    kwargs['expected_process_variance'] = self.credibility_weight.estimate_process_variance(data_by_group)

                if 'variance_of_hypothetical_means' not in kwargs:
                    kwargs['variance_of_hypothetical_means'] = self.credibility_weight.estimate_variance_of_hypothetical_means(data_by_group)

            weight = self.credibility_weight.buhlmann_credibility(
                claim_count,
                kwargs.get('expected_process_variance', 1.0),
                kwargs.get('variance_of_hypothetical_means', 0.1)
            )
        elif method == "buhlmann_straub":
            # Get exposures and claim counts
            exposures = kwargs.get('exposures', [])
            claim_counts = kwargs.get('claim_counts', [])

            # Get or calculate process variance and variance of hypothetical means
            if 'data_by_group' in kwargs:
                data_by_group = kwargs.get('data_by_group', {})

                # Calculate variances if not provided
                if 'expected_process_variance' not in kwargs:
                    kwargs['expected_process_variance'] = self.credibility_weight.estimate_process_variance(data_by_group)

                if 'variance_of_hypothetical_means' not in kwargs:
                    kwargs['variance_of_hypothetical_means'] = self.credibility_weight.estimate_variance_of_hypothetical_means(data_by_group)

            weight = self.credibility_weight.buhlmann_straub_credibility(
                exposures,
                claim_counts,
                kwargs.get('expected_process_variance', 1.0),
                kwargs.get('variance_of_hypothetical_means', 0.1)
            )
        elif method == "greatest_accuracy":
            # Get loss data if not provided
            if 'data' not in kwargs and hasattr(self.experience_data, 'subject_contract_claims'):
                kwargs['data'] = [claim.amount for claim in self.experience_data.subject_contract_claims()]

            # Get data for easier access
            data = kwargs.get('data', [])

            weight = self.credibility_weight.greatest_accuracy_credibility(
                data,
                kwargs.get('collective_mean', 1.0)
            )
        elif method == "bayesian":
            # Get loss data if not provided
            if 'data' not in kwargs and hasattr(self.experience_data, 'subject_contract_claims'):
                kwargs['data'] = [claim.amount for claim in self.experience_data.subject_contract_claims()]

            # Calculate data variance if not provided
            data = kwargs.get('data', [])
            if 'data_variance' not in kwargs and data:
                kwargs['data_variance'] = self.credibility_weight.calculate_data_variance(data, method="sample")

            weight = self.credibility_weight.bayesian_credibility(
                kwargs.get('prior_mean', 1.0),
                kwargs.get('prior_variance', 0.1),
                data,
                kwargs.get('data_variance', 1.0)
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
        return (experience_result * self._experience_weight + 
                exposure_result * self._exposure_weight)

    def make_selection(self, experience_result: float, exposure_result: float, 
                      method: str = "limited_fluctuation", **kwargs) -> float:
        """
        Make a selection by calculating weights and combining results.

        Args:
            experience_result: Result from experience rating method
            exposure_result: Result from exposure rating method
            method: Credibility method to use
            **kwargs: Additional parameters for the credibility method

        Returns:
            Selected result based on weighted average
        """
        # Calculate weights
        self.calculate_experience_weight(method, **kwargs)

        # Return weighted average
        return self.unlimited_selection(experience_result, exposure_result)
