from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..enums import ClaimTriggerBasis, ClaimYearType, ContractType, IndexationClauseType
from ..exceptions.exceptions import ContractException
from ..treaty.layer_loss_functions import layer_loss_calculation


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
    subject_lines_of_business: list[str]
    subject_lob_exposure_amounts: list[float]
    full_subject_premium: float
    written_line: float
    signed_line: float
    number_of_reinstatements: int
    reinstatement_cost: dict[int, float]
    cession: float = 1.0
    inures_to_benefit_of: list[Any] = field(default_factory=list)
    interlocking_classes: list[Any] = field(default_factory=list)

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
        return float(func(gross_amount, self.occurrence_attachment, self.occurrence_limit))


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
    fx_rates: dict[str, float]

    @property
    def claim_year_basis(self) -> ClaimYearType:
        try:
            return self.trigger_basis.to_claim_year_type()
        except KeyError:
            raise ContractException(
                contract_id=self.contract_id,
                message="Trigger basis not found in claim year mapping",
            ) from None


class RIContract:
    def __init__(self, contract_meta_data: RIContractMetadata, layers: Sequence[RILayer]):
        self._contract_meta_data = contract_meta_data
        self._layers = list(layers)

    @property
    def contract_meta_data(self) -> RIContractMetadata:
        return self._contract_meta_data

    @contract_meta_data.setter
    def contract_meta_data(self, value: RIContractMetadata) -> None:
        self._contract_meta_data = value

    @property
    def layers(self) -> list[RILayer]:
        return self._layers

    @layers.setter
    def layers(self, value: Sequence[RILayer]) -> None:
        self._layers = list(value)

    @property
    def layer_ids(self) -> list[int]:
        return [layer.layer_id for layer in self._layers]
