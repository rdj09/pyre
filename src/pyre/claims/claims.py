from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List, Dict
from collections import defaultdict

@dataclass
class ClaimDevelopmentHistory:
    development_months: List[int] = field(default_factory=list)
    cumulative_dev_paid: List[float] = field(default_factory=list)
    cumulative_dev_incurred: List[float] = field(default_factory=list)

    @property
    def cumulative_reserved_amount(self) -> list[float]:
        if len(self.cumulative_dev_incurred) != len(self.cumulative_dev_paid):
            raise ValueError("Both lists must have the same length.")
        return [cumulative_incurred - cumulative_paid for cumulative_incurred, cumulative_paid in zip(self.cumulative_dev_incurred, self.cumulative_dev_paid)]

    @property
    def latest_paid(self) -> float:
        return self.cumulative_dev_paid[-1] if self.cumulative_dev_paid else 0.0
    
    @property
    def latest_incurred(self) -> float:
        return self.cumulative_dev_incurred[-1] if self.cumulative_dev_incurred else 0.0

    @property
    def latest_reserved_amount(self) -> float:
        return self.cumulative_dev_incurred[-1] - self.cumulative_dev_paid[-1] if self.cumulative_dev_paid else 0.0
    
    @property
    def latest_development_month(self) -> int:
        return self.development_months[-1] if self.development_months else 0
    
    
@dataclass
class ClaimsMetaData:
    claim_id: str
    currency: str
    loss_date: Optional[date] = None
    policy_inception_date: Optional[date] = None
    report_date: Optional[date] = None
    line_of_business: Optional[str] = None
    status: Optional[str] = "Open"

    @property
    def accident_year (self) -> Optional[int]:
        if self.loss_date:
            return self.loss_date.year
        return None
    
    @property
    def underwriting_year (self) -> Optional[int]:
        if self.policy_inception_date:
            return self.policy_inception_date.year
        return None


class Claim:
    def __init__(self, ClaimsMetaData:ClaimsMetaData,ClaimDevelopmentHistory:ClaimDevelopmentHistory) -> None:
        self.claims_meta_data =  ClaimsMetaData
        self.claims_development_history = ClaimDevelopmentHistory



@dataclass
class AggregateClaims:
    """_summary_

    Returns:
        _type_: _description_
    """
    year: int
    total_paid: float
    total_reserved: float
    total_incurred: float
    claim_count: int
    dev_paid: List[float]  # Total paid per development month
    dev_incurred: List[float]  # Total incurred per development month

    @classmethod
    def from_claims(cls, claims: List["Claim"]) -> List["AggregateClaims"]:
        """_summary_

        Returns:
            _type_: _description_
        """
        yearly_data: Dict[int, List[Claim]] = defaultdict(list)

        # Group claims by the year of loss date
        for claim in claims:
            year = claim.loss_date.year
            yearly_data[year].append(claim)

        aggregates = []

        for year, year_claims in yearly_data.items():
            total_paid = sum(c.paid_amount for c in year_claims)
            total_reserved = sum(c.reserved_amount for c in year_claims)
            total_incurred = total_paid + total_reserved
            claim_count = len(year_claims)

            # Prepare lists to aggregate paid and incurred by development month
            max_dev_month = max(len(c.development_months) for c in year_claims)
            dev_paid = [0.0] * max_dev_month
            dev_incurred = [0.0] * max_dev_month

            # Aggregate development data
            for claim in year_claims:
                for i, month in enumerate(claim.development_months):
                    dev_paid[month] += claim.dev_paid[i]
                    dev_incurred[month] += claim.dev_incurred[i]

            aggregates.append(cls(
                year=year,
                total_paid=total_paid,
                total_reserved=total_reserved,
                total_incurred=total_incurred,
                claim_count=claim_count,
                dev_paid=dev_paid,
                dev_incurred=dev_incurred
            ))

        return aggregates