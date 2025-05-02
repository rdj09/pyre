from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import mean
from typing import Callable, Dict, List

from pyre.claims.claims import Claim, ClaimDevelopmentHistory, ClaimsMetaData


@dataclass
class ClaimAggregator:
    claims: List[Claim]

    @property
    def modelling_years(self) -> List:
        return [claim.modelling_year for claim in self.claims]
    
    @property
    def currencies(self) -> List:
        return [claim.currency for claim in self.claims]
    

    def aggregate_by_attribute(self, attributes: List[str], aggregator: Callable = sum) -> Dict:
        grouped_claims = defaultdict(list)
        for claim in self.claims:
            key = tuple(getattr(claim, attr, None) for attr in attributes)
            grouped_claims[key].append(claim)

        aggregated_results = {}
        for key, claims in grouped_claims.items():
            aggregated_results[key] = {
                "total_paid": aggregator(claim.capped_claim_development_history.latest_paid for claim in claims),
                "total_incurred": aggregator(claim.capped_claim_development_history.latest_incurred for claim in claims),
                "number_of_claims": len(claims),
                "mean_payment_duration": mean(claim.capped_claim_development_history.mean_payment_duration for claim in claims) if claims else None,
                "total_paid_open_claims": aggregator(claim.capped_claim_development_history.latest_paid for claim in claims if claim.status == "Open"),
                "total_incurred_open_claims": aggregator(claim.capped_claim_development_history.latest_incurred for claim in claims if claim.status == "Open"),
                "number_of_open_claims": len([claim for claim in claims if claim.status == "Open"]),
               # "mean_payment_duration_open_claims": mean(claim.capped_claim_development_history.mean_payment_duration for claim in claims if claim.status == "Open") Need to produce further work here
            }
        return aggregated_results
