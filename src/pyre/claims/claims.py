from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List, Sequence
from enum import Enum, auto

class ClaimYearType(Enum):
    ACCIDENT_YEAR = auto()
    UNDERWRITING_YEAR = auto()
    REPORTED_YEAR = auto()

@dataclass
class ClaimDevelopmentHistory:
    development_months: Sequence[int] = field(default_factory=list)
    cumulative_dev_paid: Sequence[float] = field(default_factory=list)
    cumulative_dev_incurred: Sequence[float] = field(default_factory=list)

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
    
    @property
    def incremental_dev_paid(self) -> List[float]:
        return [self.cumulative_dev_paid[i] - self.cumulative_dev_paid[i - 1] for i in range(1, len(self.cumulative_dev_paid))]
    
    @property
    def incremental_dev_incurred(self) -> List[float]:
        return [self.cumulative_dev_incurred[i] - self.cumulative_dev_incurred[i - 1] for i in range(1, len(self.cumulative_dev_incurred))]

    @property
    def mean_payment_duration(self) -> Optional[float]:
        if self.latest_paid > 0:
            time_weighted_payments = sum(month * paid for month, paid in zip(self.development_months, self.cumulative_dev_paid))
            return time_weighted_payments / self.latest_paid
        return None
    
@dataclass
class ClaimsMetaData:
    claim_id: str
    currency: str
    contract_limit: float = 0.0
    contract_deductible: float = 0.0
    xs_deductible: bool = False
    from_ground_up: bool = True
    claim_year_basis: ClaimYearType = ClaimYearType.ACCIDENT_YEAR
    loss_date: Optional[date] = None
    policy_inception_date: Optional[date] = None
    report_date: Optional[date] = None
    line_of_business: Optional[str] = None
    status: Optional[str] = "Open"

    @property
    def modelling_year (self) -> int:
        if self.claim_year_basis == ClaimYearType.ACCIDENT_YEAR:
            return self.loss_date.year if self.loss_date else 0
        elif self.claim_year_basis == ClaimYearType.UNDERWRITING_YEAR:
            return self.policy_inception_date.year if self.policy_inception_date else 0
        elif self.claim_year_basis == ClaimYearType.REPORTED_YEAR:
            return self.report_date.year if self.report_date else 0
        else:
            return 0

class Claim:
    def __init__(self, claims_meta_data: ClaimsMetaData, claims_development_history: ClaimDevelopmentHistory) -> None:
        self._claims_meta_data = claims_meta_data
        self._claim_development_history = claims_development_history
    

class AggregateClaimsByYear:
    def __init__(self, claims: List[Claim]) -> None:
        self._claims = claims