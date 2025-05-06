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
        return [incurred - paid for incurred, paid in zip(self.cumulative_dev_incurred, self.cumulative_dev_paid)]

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
    
    @staticmethod
    def incremental_dev(cumulative_dev: Sequence[float]) -> List[float]:
        incremental_dev = [cumulative_dev[0]]
        incremental_dev.extend([cumulative_dev[i] - cumulative_dev[i - 1] for i in range(1, len(cumulative_dev))])
        return incremental_dev
    @property
    def incremental_dev_incurred(self) -> List[float]:
        self.incremental_dev(self.cumulative_dev_incurred)
        return self.incremental_dev(self.cumulative_dev_incurred)
    
    @property #
    def incremental_dev_paid(self) -> List[float]:
        self.incremental_dev(self.cumulative_dev_paid)
        return self.incremental_dev(self.cumulative_dev_paid)

    @property
    def mean_payment_duration(self) -> Optional[float]:
        if self.latest_paid > 0:
            time_weighted_payments = sum(month * paid for month, paid in zip(self.development_months, self.incremental_dev_paid))
            return time_weighted_payments / self.latest_paid
        return None

@dataclass
class ClaimsMetaData:
    claim_id: str
    currency: str
    contract_limit: float = 0.0
    contract_deductible: float = 0.0
    claim_in_xs_of_deductible: bool = False
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
        self._uncapped_claim_development_history: Optional[ClaimDevelopmentHistory] = None
        self._capped_claim_development_history: Optional[ClaimDevelopmentHistory] = None
    
    @property
    def uncapped_claim_development_history(self) -> ClaimDevelopmentHistory:
        if self._claims_meta_data.claim_in_xs_of_deductible:
            uncapped_paid = self._claim_development_history.cumulative_dev_paid
            uncapped_incurred = self._claim_development_history.cumulative_dev_incurred
        else:
            uncapped_paid = [max(paid - self._claims_meta_data.contract_deductible, 0.0) for paid in self._claim_development_history.cumulative_dev_paid]
            uncapped_incurred = [max(incurred - self._claims_meta_data.contract_deductible, 0.0) for incurred in self._claim_development_history.cumulative_dev_incurred]
        self._uncapped_claim_development_history = ClaimDevelopmentHistory(self._claim_development_history.development_months, uncapped_paid, uncapped_incurred)
        return self._uncapped_claim_development_history

    @property
    def capped_claim_development_history(self) -> ClaimDevelopmentHistory:
        capped_paid = [min(paid, self._claims_meta_data.contract_limit) for paid in self.uncapped_claim_development_history.cumulative_dev_paid]
        capped_incurred = [min(incurred, self._claims_meta_data.contract_limit) for incurred in self.uncapped_claim_development_history.cumulative_dev_incurred]
        self._capped_claim_development_history = ClaimDevelopmentHistory(self._claim_development_history.development_months, capped_paid, capped_incurred)
        return self._capped_claim_development_history
    
    #TODO: exposed all underlying attributes of composing classes but need to review. Should be explicit about what's to be exposed.
    def __getattr__(self, name: str) -> object:
        return getattr(self._claims_meta_data, name) if hasattr(self._claims_meta_data, name) else getattr(self._claim_development_history, name) if hasattr(self._claim_development_history, name) else self.__getattribute__(name)
    
    def __repr__(self) -> str:
        return (
            f"claim_id={self._claims_meta_data.claim_id},modelling_year={self._claims_meta_data.modelling_year},latest_incurred={self._claim_development_history.latest_incurred},latest_capped_incurred={self.capped_claim_development_history.latest_incurred}"
        )





# claims_meta_data = ClaimsMetaData(
#     claim_id="123",
#     currency="USD",
#     contract_limit=100000.0,
#     contract_deductible=10000.0,
#     claim_in_xs_of_deductible=True
# )

# # Create a ClaimDevelopmentHistory object
# claim_development_history = ClaimDevelopmentHistory(
#     development_months=[1, 2, 3],
#     cumulative_dev_paid=[1000.0, 2000.0, 3000.0],
#     cumulative_dev_incurred=[1500.0, 2500.0, 3500.0]
# )


# # Create a Claim object
# claim = Claim(claims_meta_data, claim_development_history)
# print(claim)

#print(claim.capped_claim_development_history.cumulative_reserved_amount)

#print(claim.uncapped_claim_development_history.development_months) # Access development_months
# Access uncapped_claim_development_history.latest_paid
#print(claim.uncapped_claim_development_history.latest_incurred)  
#print(claim.capped_claim_development_history.latest_incurred)  

# claims_meta_data = ClaimsMetaData(
#     claim_id="123",
#     currency="USD",
#     contract_limit=100.0,
#     contract_deductible=5000.0,
#     claim_in_xs_of_deductible=True
# )

# # Create a ClaimDevelopmentHistory object
# claim_development_history = ClaimDevelopmentHistory(
#     development_months=[1, 2, 3],
#     cumulative_dev_paid=[1000.0, 2000.0, 3000.0],
#     cumulative_dev_incurred=[1500.0, 2500.0, 3500.0]
# )

# claim = Claim(claims_meta_data, claim_development_history)



