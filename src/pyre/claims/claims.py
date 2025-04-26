from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List, Dict
from collections import defaultdict
from enum import Enum, auto
from uuid import uuid4

class ClaimDataType(Enum):
    """_summary_

    Args:
        Enum (_type_): _description_
    """
    INCREMENTAL = auto()
    CUMULATIVE = auto()

@dataclass
class ClaimDevelopmentHistory:
    """_summary_

    Returns:
        _type_: _description_
    """
    paid_amount: float
    reserved_amount: float
    data_type: Optional[ClaimDataType] = ClaimDataType.CUMULATIVE
    development_months: List[int] = field(default_factory=list)
    dev_paid: List[float] = field(default_factory=list)
    dev_incurred: List[float] = field(default_factory=list)

    @property
    def total_incurred(self) -> float:
        """_summary_

        Returns:
        _type_: _description_
        """
        return self.paid_amount + self.reserved_amount

    def add_development_point(self, month: int, paid: float, incurred: float):
        """_summary_

        Args:
            month (int): _description_
            paid (float): _description_
            incurred (float): _description_
        """
        self.development_months.append(month)
        self.dev_paid.append(paid)
        self.dev_incurred.append(incurred)

    def cumulative_dev_paid(self) -> float:
        """_summary_

        Returns:
            float: _description_
        """
        return sum(self.dev_paid)

    def cumulative_dev_incurred(self) -> float:
        """_summary_

        Returns:
            float: _description_
        """
        return sum(self.dev_incurred)

@dataclass
class ClaimsMetaData:
    """_summary_
    """
    claim_id: str
    policy_id: str
    cedent_name: str
    currency: str
    loss_date: Optional[date] = None
    report_date: Optional[date] = None
    loss_cause: Optional[str] = None
    line_of_business: Optional[str] = None
    status: Optional[str] = "Open"


@dataclass
class Claim:
    """_summary_

    Returns:
        _type_: _description_
    """
    claims_uuid = uuid4()
    claims_meta_data = ClaimsMetaData
    claims_development_history = ClaimDevelopmentHistory



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