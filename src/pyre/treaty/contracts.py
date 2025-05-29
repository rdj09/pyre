from datetime import date
from enum import Enum
from typing import Any, List, Dict, Sequence
from dataclasses import dataclass, field
from pyre.treaty.layer_loss_functions import layer_loss_calculation
from pyre.claims.claims import ClaimYearType
from pyre.exceptions.exceptions import ContractException #TODO need to move this to a common ENUM module so no dependency on claims module

class ContractType(Enum):
    QUOTA_SHARE = "Quota Share"
    EXCESS_OF_LOSS = "Excess of Loss"
    FRANCHISE_DEDUCTIBLE = "Franchise Deductible"
    SURPLUS_SHARE = "Surplus Share"
    AGGREGATE_STOP_LOSS = "Aggregate Stop Loss"

class ClaimTriggerBasis(Enum):
    LOD = "Losses Occurrence" #Accident Year
    RAD = "Risk Attaching" # Policy Inception Year
    CMB = "Claims Made Basis" # Reported Year

class IndexationClauseType(Enum):
    FULL_INDEXATION = "Full Indexation"
    FIC = "Franchise - FIC"
    SIC = "Severe Inflation (also London Market) - SIC"

claim_year_basis ={
    ClaimTriggerBasis.RAD:ClaimYearType.UNDERWRITING_YEAR,
    ClaimTriggerBasis.CMB:ClaimYearType.REPORTED_YEAR,
    ClaimTriggerBasis.LOD:ClaimYearType.ACCIDENT_YEAR
    } # not sure this needs to be in the function as a generic mapping. Might be best placed outside as mapping to enums together.


@dataclass
class RILayer:
    layer_id: int
    layer_name: str 
    layer_type: ContractType
    occurrence_attachment:float
    occurrence_limit:float
    aggregate_attachment: float
    aggregate_limit: float 
    subject_lines_of_business: List
    subject_lob_exposure_amounts: List
    full_subject_premium: float
    written_line: float
    signed_line: float
    number_of_reinstatements: int # unlimited 999 default need to build in logic elsewhere
    reinstatement_cost: Dict # {1:100%,2:125%,3:125%} unlimited = 0% cost
    cession: float = 1.0 # us for order and QS
    inures_to_benefit_of: List = field(default_factory = list) # list of layers that layer inures to
    interlocking_classes: List = field(default_factory= list) # subject classes for which interlcoking clause applies

    @property
    def written_line_premium(self) -> float:
        return self.cession * self.written_line * self.full_subject_premium
    
    @property
    def signed_line_premium(self) -> float | Any:
        return self.cession * self.signed_line * self.full_subject_premium
    
    def loss_to_layer_fn(self, gross_amount:float):
        func = layer_loss_calculation[self.layer_type]
        if self.layer_type == ContractType.QUOTA_SHARE:
            return gross_amount  # TODO analysis typically easier to do at 100% - inuring and profitability at share consider elsewhere !!!!!!
        if self.layer_type == ContractType.SURPLUS_SHARE:
            return NotImplementedError("Yet to be implemented")
        else:
            return lambda gross_amount : func(gross_amount, self.occurrence_attachment, self.occurrence_limit)

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
    fx_rates: Dict # {"GBP":1.0, "USD":1.25}

    @property
    def claim_year_basis(self) -> ContractException | ClaimYearType:
        if self.trigger_basis in claim_year_basis:
            return claim_year_basis[self.trigger_basis]
        else:
            raise ContractException(
                contract_id= self.contract_id, 
                message="Trigger basis missing in data"
                )

@dataclass
class RIContract:
    contract_meta_data: RIContractMetadata 
    layers: Sequence[RILayer]

    @property
    def layer_ids(self) -> List:
        return [layer.layer_id for layer in self.layers]

