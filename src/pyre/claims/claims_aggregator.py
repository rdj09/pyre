from pyre.claims.claims import Claim
from typing import List, Dict, Any


class ClaimAggregator:
    def __init__(self, claims: List[Claim]) -> None:
        self.claims = claims

    @property
    def total_paid_by_year(self) -> float:
        return sum(claim.uncapped_claim_development_history.latest_paid for claim in self.claims)

    @property
    def total_incurred_by_year(self) -> float:
        return sum(claim.uncapped_claim_development_history.latest_incurred for claim in self.claims)
    
    def number_of_claims_by_year(self, by_year:bool) -> Any:
        if by_year:
            return None
        return len(self.claims)
    
    def number_of_open_claims_by_year(self, by_year:bool) -> Any:
        if by_year:
            return None 
        return len([claim for claim in self.claims if claim._claims_meta_data.status == "Open"])
    
    def number_of_closed_claims(self, by_year:bool) -> Any:
        # held a s a balance but should have validation in place to ensure that the number of closed claims is equal to the total number of claims minus the total number of open claims
        if by_year:
            return None
        return None


