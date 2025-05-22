from dataclasses import dataclass, field
from datetime import date
import operator
from typing import Optional, List, Sequence, Set
from enum import Enum, auto

from pyre.exceptions.exceptions import ClaimsException

class ClaimYearType(Enum):
    """Enumeration of claim year types used in insurance data analysis.

    Attributes:
        ACCIDENT_YEAR: Represents the year in which the insured event (accident) occurred.
        UNDERWRITING_YEAR: Represents the year in which the insurance policy was underwritten or issued.
        REPORTED_YEAR: Represents the year in which the claim was reported to the insurer.
    """
    ACCIDENT_YEAR = auto()
    UNDERWRITING_YEAR = auto()
    REPORTED_YEAR = auto()

@dataclass
class ClaimDevelopmentHistory:
    """Represents the development history of an insurance claim, tracking cumulative and incremental paid and incurred amounts over development months.
    
    Attributes:
        development_months (Sequence[int]): List of development months corresponding to each data point.
        cumulative_dev_paid (Sequence[float]): Cumulative paid amounts at each development month.
        cumulative_dev_incurred (Sequence[float]): Cumulative incurred amounts at each development month.
    
    Properties:
        cumulative_reserved_amount (list[float]): List of reserved amounts (incurred minus paid) at each development month.
        latest_paid (float): Most recent cumulative paid amount, or 0.0 if no data.
        latest_incurred (float): Most recent cumulative incurred amount, or 0.0 if no data.
        latest_reserved_amount (float): Most recent reserved amount (incurred minus paid), or 0.0 if no data.
        latest_development_month (int): Most recent development month, or 0 if no data.
        incremental_dev_incurred (List[float]): List of incremental incurred amounts at each development month.
        incremental_dev_paid (List[float]): List of incremental paid amounts at each development month.
        mean_payment_duration (Optional[float]): Weighted average development month of payments, or None if no payments.
    
    Methods:
        incremental_dev(cumulative_dev: Sequence[float]) -> List[float]:
            Converts a sequence of cumulative values into incremental values.
    """
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
    """Metadata for an insurance claim, including key dates, financial limits, and classification details.
    
    Attributes:
        claim_id (str): Unique identifier for the claim.
        currency (str): Currency code for the claim amounts.
        contract_limit (float): Maximum limit of the insurance contract. Defaults to 0.0.
        contract_deductible (float): Deductible amount for the contract. Defaults to 0.0.
        claim_in_xs_of_deductible (bool): Indicates if the claim is in excess of the deductible. Defaults to False.
        claim_year_basis (ClaimYearType): Basis for determining the claim year (e.g., accident, underwriting, reported). Defaults to ClaimYearType.ACCIDENT_YEAR.
        loss_date (date): Date of loss occurrence. Defaults to 1900-01-01.
        policy_inception_date (date): Policy inception date. Defaults to 1900-01-01.
        report_date (date): Date the claim was reported. Defaults to 1900-01-01.
        line_of_business (Optional[str]): Line of business associated with the claim. Defaults to None.
        status (Optional[str]): Status of the claim (e.g., "Open", "Closed"). Defaults to "Open".
    
    Properties:
        modelling_year (ClaimsException | int): Returns the modelling year based on the claim_year_basis, or raises ClaimsException if required date is missing.
    """
    claim_id: str
    currency: str
    contract_limit: float = 0.0
    contract_deductible: float = 0.0
    claim_in_xs_of_deductible: bool = False
    claim_year_basis: ClaimYearType = ClaimYearType.ACCIDENT_YEAR
    loss_date: date = date(day=1,month=1,year= 1900)
    policy_inception_date: date = date(day=1,month=1,year= 1900)
    report_date: date = date(day=1,month=1,year= 1900)
    line_of_business: Optional[str] = None
    status: Optional[str] = "Open"

    @property
    def modelling_year (self) -> ClaimsException | int:
        _modeling_basis_years={
            ClaimYearType.ACCIDENT_YEAR: self.loss_date.year,
            ClaimYearType.UNDERWRITING_YEAR: self.policy_inception_date.year,
            ClaimYearType.REPORTED_YEAR: self.report_date.year
        }
        if self.claim_year_basis in _modeling_basis_years:
            return _modeling_basis_years[self.claim_year_basis]
        else: 
            return ClaimsException(
                claim_id=self.claim_id, 
                message="Required date missing from data"
                )


class Claim:
    """Represents an insurance claim with associated metadata and development history.
    
    This class provides access to the claim's metadata, uncapped and capped development histories,
    and a string representation for easy inspection. The uncapped and capped development histories
    are calculated based on the contract deductible and limit specified in the claim's metadata.
    
    Attributes:
        _claims_meta_data (ClaimsMetaData): Metadata associated with the claim, such as claim ID, deductible, and limit.
        _claim_development_history (ClaimDevelopmentHistory): The development history of the claim, including paid and incurred amounts over time.
    
    Properties:
        claims_meta_data: Returns the claim's metadata.
        uncapped_claim_development_history: Returns the claim's development history after applying the deductible, but before applying the contract limit.
        capped_claim_development_history: Returns the claim's development history after applying both the deductible and the contract limit.
    
    Args:
        claims_meta_data (ClaimsMetaData): Metadata for the claim.
        claims_development_history (ClaimDevelopmentHistory): Development history for the claim.
    
    Example:
        >>> claim = Claim(meta_data, dev_history)
        >>> print(claim.capped_claim_development_history)
    """
    def __init__(self, claims_meta_data: ClaimsMetaData, claims_development_history: ClaimDevelopmentHistory) -> None:
        self._claims_meta_data = claims_meta_data
        self._claim_development_history = claims_development_history
        
    @property
    def claims_meta_data(self):
        return self._claims_meta_data
    
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

    
    def __repr__(self) -> str:
        return (
            f"claim_id={self._claims_meta_data.claim_id},modelling_year={self._claims_meta_data.modelling_year},latest_incurred={self._claim_development_history.latest_incurred},latest_capped_incurred={self.capped_claim_development_history.latest_incurred}"
        )
    


class Claims:
    """A container class for managing a collection of Claim objects.
    
    This class provides convenient accessors and methods for working with a list of claims,
    including retrieving modelling years, development periods, and currencies represented in the claims.
    It also supports list-like behaviors such as indexing, slicing, appending, and iteration.
    
    Attributes:
        claims (list[Claim]): The list of Claim objects managed by this container.
    
    Properties:
        modelling_years (List): Sorted list of unique modelling years across all claims.
        development_periods (List): Sorted list of unique development periods (in months) across all claims.
        currencies (Set): Set of unique currencies represented in the claims.
    
    Methods:
        append(claim: Claim): Appends a Claim object to the collection.
        __getitem__(key): Supports indexing and slicing to access claims.
        __iter__(): Returns an iterator over the claims.
        __len__(): Returns the number of claims in the collection.
    """
    def __init__(self, claims: list[Claim]) -> None:
        self._claims = claims

    @property
    def claims(self):
        return self._claims
    
    @claims.setter
    def claims(self, list_of_claim_classes:list[Claim]):
        self._claims = list_of_claim_classes

    @property
    def modelling_years(self) -> List:
        """
        Returns a list of modelling years for all claims.
        """
        years = {claim.claims_meta_data.modelling_year for claim in self.claims}
        return sorted(years)

    @property
    def development_periods(self) -> List:
        """
        Returns a list of modelling years for all claims.
        """
        dev_periods = {claim.capped_claim_development_history.development_months for claim in self.claims}
        return sorted(dev_periods)
    
    @property
    def currencies(self) -> Set:
        """
        Returns a list of currencies for all claims.
        """
        return {claim.claims_meta_data.currency for claim in self.claims}

    def append(self, claim: Claim):
        self._claims.append(claim)
    
    def __getitem__(self, key):
        if isinstance(key,slice):
            cls = type(self)
            return cls(self._claims[key])
        index = operator.index(key)
        return self._claims[index]

    def __iter__(self):
        return iter(self._claims)
    
    def __len__(self):
        return len(self._claims)

    