import operator
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Union

from ..enums import ClaimYearType
from ..exceptions.exceptions import ClaimsException


@dataclass
class ClaimDevelopmentHistory:
    """Development history of an insurance claim.

    Attributes:
        development_months: Development month at each data point.
        cumulative_dev_paid: Cumulative paid at each development month.
        cumulative_dev_incurred: Cumulative incurred at each development month.
    """

    development_months: list[int] = field(default_factory=list)
    cumulative_dev_paid: list[float] = field(default_factory=list)
    cumulative_dev_incurred: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._validate_list_lengths()

    def _validate_list_lengths(self) -> None:
        if not (
            len(self.development_months)
            == len(self.cumulative_dev_paid)
            == len(self.cumulative_dev_incurred)
        ):
            raise ValueError(
                "All development lists (months, paid, incurred) must have the same length."
            )

    @property
    def cumulative_reserved_amount(self) -> list[float]:
        return [
            i - p
            for i, p in zip(self.cumulative_dev_incurred, self.cumulative_dev_paid, strict=False)
        ]

    @property
    def latest_paid(self) -> float:
        return self.cumulative_dev_paid[-1] if self.cumulative_dev_paid else 0.0

    @property
    def latest_incurred(self) -> float:
        return self.cumulative_dev_incurred[-1] if self.cumulative_dev_incurred else 0.0

    @property
    def latest_reserved_amount(self) -> float:
        return (
            self.cumulative_dev_incurred[-1] - self.cumulative_dev_paid[-1]
            if self.cumulative_dev_paid
            else 0.0
        )

    @property
    def latest_development_month(self) -> int:
        return self.development_months[-1] if self.development_months else 0

    @staticmethod
    def incremental_dev(cumulative_dev: Sequence[float]) -> list[float]:
        if not cumulative_dev:
            return []
        result = [cumulative_dev[0]]
        result.extend(
            cumulative_dev[i] - cumulative_dev[i - 1] for i in range(1, len(cumulative_dev))
        )
        return result

    @property
    def incremental_dev_incurred(self) -> list[float]:
        return self.incremental_dev(self.cumulative_dev_incurred)

    @property
    def incremental_dev_paid(self) -> list[float]:
        return self.incremental_dev(self.cumulative_dev_paid)

    @property
    def mean_payment_duration(self) -> float | None:
        if self.latest_paid > 0:
            return (
                sum(
                    m * p
                    for m, p in zip(
                        self.development_months, self.incremental_dev_paid, strict=False
                    )
                )
                / self.latest_paid
            )
        return None


@dataclass
class ClaimsMetaData:
    """Metadata for an insurance claim.

    Attributes:
        claim_id: Unique identifier for the claim.
        currency: ISO currency code.
        contract_limit: Maximum contract limit. Defaults to 0.0.
        contract_deductible: Contract deductible. Defaults to 0.0.
        claim_in_xs_of_deductible: Whether amounts are already net of deductible.
        claim_year_basis: Year type used for modelling.
        loss_date: Date of loss.
        policy_inception_date: Policy inception date.
        report_date: Date claim was reported.
        line_of_business: Optional LOB classification.
        status: Claim status. Defaults to "Open".
    """

    claim_id: str
    currency: str
    contract_limit: float = 0.0
    contract_deductible: float = 0.0
    claim_in_xs_of_deductible: bool = False
    claim_year_basis: ClaimYearType = field(default=ClaimYearType.ACCIDENT_YEAR)
    loss_date: date = field(default_factory=lambda: date(1900, 1, 1))
    policy_inception_date: date = field(default_factory=lambda: date(1900, 1, 1))
    report_date: date = field(default_factory=lambda: date(1900, 1, 1))
    line_of_business: str | None = None
    status: str | None = "Open"

    @property
    def modelling_year(self) -> int:
        """Year used for experience modelling, derived from claim_year_basis."""
        mapping = {
            ClaimYearType.ACCIDENT_YEAR: self.loss_date.year,
            ClaimYearType.UNDERWRITING_YEAR: self.policy_inception_date.year,
            ClaimYearType.REPORTED_YEAR: self.report_date.year,
        }
        if self.claim_year_basis in mapping:
            return mapping[self.claim_year_basis]
        raise ClaimsException(
            claim_id=self.claim_id,
            message="Required date missing from data",
        )


class Claim:
    """Represents an insurance claim with associated metadata and development history.

    This class provides access to the claim's metadata, uncapped and capped development histories,
    and a string representation for easy inspection. The uncapped and capped development histories
    are calculated based on the contract deductible and limit specified in the claim's metadata.

    Attributes:
        _claims_meta_data (ClaimsMetaData): Metadata associated with the claim, such as claim ID, deductible, and limit.
        _claim_development_history (ClaimDevelopmentHistory): The development history of the claim, including paid and incurred amounts over time.
        _uncapped_claim_development_history (ClaimDevelopmentHistory): Cached uncapped development history.
        _capped_claim_development_history (ClaimDevelopmentHistory): Cached capped development history.

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

    def __init__(
        self, claims_meta_data: ClaimsMetaData, claims_development_history: ClaimDevelopmentHistory
    ) -> None:
        self._claims_meta_data = claims_meta_data
        self._claim_development_history = claims_development_history
        self._uncapped_claim_development_history: ClaimDevelopmentHistory | None = None
        self._capped_claim_development_history: ClaimDevelopmentHistory | None = None

    @property
    def claims_meta_data(self) -> ClaimsMetaData:
        return self._claims_meta_data

    @property
    def uncapped_claim_development_history(self) -> ClaimDevelopmentHistory:
        if self._uncapped_claim_development_history is None:
            if self._claims_meta_data.claim_in_xs_of_deductible:
                uncapped_paid = self._claim_development_history.cumulative_dev_paid
                uncapped_incurred = self._claim_development_history.cumulative_dev_incurred
            else:
                uncapped_paid = [
                    max(paid - self._claims_meta_data.contract_deductible, 0.0)
                    for paid in self._claim_development_history.cumulative_dev_paid
                ]
                uncapped_incurred = [
                    max(incurred - self._claims_meta_data.contract_deductible, 0.0)
                    for incurred in self._claim_development_history.cumulative_dev_incurred
                ]
            self._uncapped_claim_development_history = ClaimDevelopmentHistory(
                self._claim_development_history.development_months, uncapped_paid, uncapped_incurred
            )
        return self._uncapped_claim_development_history

    @property
    def capped_claim_development_history(self) -> ClaimDevelopmentHistory:
        if self._capped_claim_development_history is None:
            capped_paid = [
                min(paid, self._claims_meta_data.contract_limit)
                for paid in self.uncapped_claim_development_history.cumulative_dev_paid
            ]
            capped_incurred = [
                min(incurred, self._claims_meta_data.contract_limit)
                for incurred in self.uncapped_claim_development_history.cumulative_dev_incurred
            ]
            self._capped_claim_development_history = ClaimDevelopmentHistory(
                self._claim_development_history.development_months, capped_paid, capped_incurred
            )
        return self._capped_claim_development_history

    def __repr__(self) -> str:
        return f"claim_id={self._claims_meta_data.claim_id},modelling_year={self._claims_meta_data.modelling_year},latest_incurred={self._claim_development_history.latest_incurred},latest_capped_incurred={self.capped_claim_development_history.latest_incurred}"


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
    def claims(self) -> list["Claim"]:
        return self._claims

    @claims.setter
    def claims(self, list_of_claim_classes: list["Claim"]) -> None:
        self._claims = list_of_claim_classes

    @property
    def modelling_years(self) -> list[int]:
        """
        Returns a list of modelling years for all claims.
        """
        years = {claim.claims_meta_data.modelling_year for claim in self.claims}
        return sorted(years)

    @property
    def development_periods(self) -> list[list[int]]:
        """
        Returns a sorted list of unique development period sequences across all claims.

        Each element in the returned list is a list of development months from a claim.
        """
        dev_periods = {
            tuple(claim.capped_claim_development_history.development_months)
            for claim in self.claims
        }
        return sorted([list(period) for period in dev_periods])

    @property
    def currencies(self) -> set[str]:
        """
        Returns a list of currencies for all claims.
        """
        return {claim.claims_meta_data.currency for claim in self.claims}

    def append(self, claim: "Claim") -> None:
        self._claims.append(claim)

    def __getitem__(self, key: int | slice) -> Union["Claim", "Claims"]:
        if isinstance(key, slice):
            cls = type(self)
            return cls(self._claims[key])
        index = operator.index(key)
        return self._claims[index]

    def __iter__(self) -> Iterator["Claim"]:
        return iter(self._claims)

    def __len__(self) -> int:
        return len(self._claims)
