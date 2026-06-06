from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Sequence
from ..treaty.layer_loss_functions import layer_loss_calculation
from ..enums import ClaimYearType, ClaimTriggerBasis, IndexationClauseType, ContractType
from ..exceptions.exceptions import ContractException

claim_year_basis = {
    ClaimTriggerBasis.RAD: ClaimYearType.UNDERWRITING_YEAR,
    ClaimTriggerBasis.CMB: ClaimYearType.REPORTED_YEAR,
    ClaimTriggerBasis.LOD: ClaimYearType.ACCIDENT_YEAR,
}  # not sure this needs to be in the function as a generic mapping. Might be best placed outside as mapping to enums together.


@dataclass
class RILayer:
    layer_id: int
    layer_name: str
    layer_type: ContractType
    occurrence_attachment: float
    occurrence_limit: float
    aggregate_attachment: float
    aggregate_limit: float
    subject_lines_of_business: list
    subject_lob_exposure_amounts: list
    full_subject_premium: float
    written_line: float
    signed_line: float
    number_of_reinstatements: int
    reinstatement_cost: dict
    cession: float = 1.0
    inures_to_benefit_of: list = field(default_factory=list)
    interlocking_classes: list = field(default_factory=list)

    @property
    def written_line_premium(self) -> float:
        return self.cession * self.written_line * self.full_subject_premium

    @property
    def signed_line_premium(self) -> float | Any:
        return self.cession * self.signed_line * self.full_subject_premium

    def loss_to_layer_fn(self, gross_amount: float):
        func = layer_loss_calculation[self.layer_type]
        if self.layer_type == ContractType.QUOTA_SHARE:
            return gross_amount  # TODO analysis typically easier to do at 100% - inuring and profitability at share consider elsewhere !!!!!!
        if self.layer_type == ContractType.SURPLUS_SHARE:
            return NotImplementedError("Yet to be implemented")
        else:
            return lambda gross_amount: func(
                gross_amount, self.occurrence_attachment, self.occurrence_limit
            )


@dataclass
class RIContractMetadata:
    contract_id: str
    contract_description: str
    cedent_name: str
    trigger_basis: ClaimTriggerBasis
    indexation_clause: IndexationClauseType
    indexation_margin: float
    inception_date: date
    expiration_date: date
    fx_rates: Dict  # {"GBP":1.0, "USD":1.25}

    @property
    def claim_year_basis(self) -> ContractException | ClaimYearType:
        if self.trigger_basis in claim_year_basis:
            return claim_year_basis[self.trigger_basis]
        else:
            raise ContractException(
                contract_id=self.contract_id, message="Trigger basis missing in data"
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
