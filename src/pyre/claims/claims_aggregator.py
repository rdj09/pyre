from collections import defaultdict
from typing import Callable, Dict, List
from pyre.claims.claims import Claim


class ClaimAggregator:
    def __init__(self, claims: List[Claim]):
        """
        Initialize the ClaimAggregator with a list of claims.

        Args:
            claims (List[Claim]): List of Claim objects to aggregate.
        """
        self.claims = claims

    @property
    def modelling_years(self) -> List:
        """
        Returns a list of modelling years for all claims.
        """
        return [claim.modelling_year for claim in self.claims]

    @property
    def currencies(self) -> List:
        """
        Returns a list of currencies for all claims.
        """
        return [claim.currency for claim in self.claims]

    def _calculate_mean(self, values: List[float]) -> None | float:
        """
        Calculate the mean of a list of values.

        Args:
            values (List[float]): List of numeric values.

        Returns:
            float: The mean value, or None if the list is empty.
        """
        if not values:
            return None
        return sum(values) / len(values)

    def _filter_claims_by_status(self, claims: List[Claim], status: str) -> List[Claim]:
        """
        Filter claims by their status.

        Args:
            claims (List[Claim]): List of claims.
            status (str): The status to filter by (e.g., "Open").

        Returns:
            List[Claim]: Filtered list of claims with the specified status.
        """
        return [claim for claim in claims if claim.status == status]

    def aggregate_by_attribute(self, attributes: List[str], aggregator: Callable = sum) -> Dict:
        """
        Aggregate claims data by specified attributes.

        Args:
            attributes (List[str]): List of attributes to group claims by.
            aggregator (Callable): Aggregation function (default is sum).

        Returns:
            Dict: Aggregated results grouped by the specified attributes.
        """
        grouped_claims = defaultdict(list)
        for claim in self.claims:
            key = tuple(getattr(claim, attr, None) for attr in attributes)
            grouped_claims[key].append(claim)

        aggregated_results = {}
        for key, claims in grouped_claims.items():
            open_claims = self._filter_claims_by_status(claims, "Open")
            aggregated_results[key] = {
                "total_paid": aggregator(claim.capped_claim_development_history.latest_paid for claim in claims),
                "total_incurred": aggregator(claim.capped_claim_development_history.latest_incurred for claim in claims),
                "number_of_claims": len(claims),
                "mean_payment_duration": self._calculate_mean([claim.capped_claim_development_history.mean_payment_duration for claim in claims]),
                "total_paid_open_claims": aggregator(claim.capped_claim_development_history.latest_paid for claim in open_claims),
                "total_incurred_open_claims": aggregator(claim.capped_claim_development_history.latest_incurred for claim in open_claims),
                "number_of_open_claims": len(open_claims),
            #    "mean_payment_duration_open_claims": self._calculate_mean([claim.capped_claim_development_history.mean_payment_duration for claim in open_claims]) # needs refining
            }
        return aggregated_results