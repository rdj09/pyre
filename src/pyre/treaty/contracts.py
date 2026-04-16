from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Sequence

from ..treaty.layer_loss_functions import layer_loss_calculation
from ..claims.claims import ClaimYearType
from ..exceptions.exceptions import ContractException
from ..treaty.contract_types import ContractType


class ClaimTriggerBasis(Enum):
    LOD = "Losses Occurrence"   # Accident Year
    RAD = "Risk Attaching"      # Policy Inception Year
    CMB = "Claims Made Basis"   # Reported Year


class IndexationClauseType(Enum):
    FULL_INDEXATION = "Full Indexation"
    FIC = "Franchise - FIC"
    SIC = "Severe Inflation (also London Market) - SIC"


_TRIGGER_TO_CLAIM_YEAR: Dict[ClaimTriggerBasis, ClaimYearType] = {
    ClaimTriggerBasis.RAD: ClaimYearType.UNDERWRITING_YEAR,
    ClaimTriggerBasis.CMB: ClaimYearType.REPORTED_YEAR,
    ClaimTriggerBasis.LOD: ClaimYearType.ACCIDENT_YEAR,
}


@dataclass
class RILayer:
    """A single reinsurance layer with its terms and conditions."""
    layer_id: int
    layer_name: str
    layer_type: ContractType
    occurrence_attachment: float
    occurrence_limit: float
    aggregate_attachment: float
    aggregate_limit: float
    subject_lines_of_business: List[str]
    subject_lob_exposure_amounts: List[float]
    full_subject_premium: float
    written_line: float
    signed_line: float
    number_of_reinstatements: int
    reinstatement_cost: Dict[int, float]
    cession: float = 1.0
    inures_to_benefit_of: List[Any] = field(default_factory=list)
    interlocking_classes: List[Any] = field(default_factory=list)

    @property
    def written_line_premium(self) -> float:
        return self.cession * self.written_line * self.full_subject_premium

    @property
    def signed_line_premium(self) -> float:
        return self.cession * self.signed_line * self.full_subject_premium

    def loss_to_layer_fn(self, gross_amount: float) -> float:
        """Apply this layer's terms to a gross loss amount.

        Args:
            gross_amount: Ground-up (or ceded-in) loss amount.

        Returns:
            The amount ceded to this layer.

        Raises:
            NotImplementedError: If layer_type is SURPLUS_SHARE.
        """
        if self.layer_type == ContractType.SURPLUS_SHARE:
            raise NotImplementedError("Surplus share loss function not yet implemented")
        if self.layer_type == ContractType.QUOTA_SHARE:
            return gross_amount
        func = layer_loss_calculation[self.layer_type]
        return func(gross_amount, self.occurrence_attachment, self.occurrence_limit)


@dataclass
class RIContractMetadata:
    """Contract-level metadata for a reinsurance agreement."""
    contract_id: str
    contract_description: str
    cedent_name: str
    trigger_basis: ClaimTriggerBasis
    indexation_clause: IndexationClauseType
    indexation_margin: float
    inception_date: date
    expiration_date: date
    fx_rates: Dict[str, float]

    @property
    def claim_year_basis(self) -> ClaimYearType:
        if self.trigger_basis in _TRIGGER_TO_CLAIM_YEAR:
            return _TRIGGER_TO_CLAIM_YEAR[self.trigger_basis]
        raise ContractException(
            contract_id=self.contract_id,
            message="Trigger basis not found in claim year mapping",
        )


class RIContract:
    def __init__(self, contract_meta_data: RIContractMetadata, layers: Sequence[RILayer]):
        self._contract_meta_data = contract_meta_data
        self._layers = list(layers)

    @property
    def contract_meta_data(self):
        return self._contract_meta_data

    @contract_meta_data.setter
    def contract_meta_data(self, value):
        self._contract_meta_data = value

    @property
    def layers(self):
        return self._layers

    @layers.setter
    def layers(self, value):
        self._layers = list(value)

    @property
    def layer_ids(self) -> list:
        return [layer.layer_id for layer in self._layers]
