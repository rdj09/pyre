from datetime import date
from enum import Enum
from typing import List, Dict, Sequence
from dataclasses import dataclass, field

from pyre.claims.claims import ClaimYearType
from pyre.exceptions.exceptions import ContractException #TODO need to move this to a common ENUM module so no dependency on claims module


def xol_calculation(gross_amount: float, attachment: float, limit: float):
    return max(min(gross_amount - attachment,limit),0)

def qs_calculation(gross_amount:float, cession:float):
    return max(gross_amount * cession,0)

def franchise_calculation(    gross_amount: float, attachment: float, limit: float):
    if gross_amount > attachment:
        return min(gross_amount,limit)
    else: 
        return 0.0

def surplus_share_calculation(gross_amount: float, sum_insured:float, attachment:float):
    if sum_insured <= attachment:
        return 0.0  # No ceded amount if the sum insured is within the retention
    surplus = sum_insured - attachment
    share = surplus / sum_insured
    return share * gross_amount

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
    def signed_line_premium(self) -> float:
        return self.cession * self.signed_line * self.full_subject_premium

@dataclass
class RIContractMetadata:
    contract_id: str
    contract_description: str
    cedent_name: str 
    contract_type: ContractType
    trigger_basis: ClaimTriggerBasis
    indexation_clause: IndexationClauseType
    indexation_margin: float
    inception_date: date
    expiration_date: date
    fx_rates: Dict # {"GBP":1.0, "USD":1.25}

    _claim_year_basis ={
        ClaimTriggerBasis.RAD:ClaimYearType.UNDERWRITING_YEAR,
        ClaimTriggerBasis.CMB:ClaimYearType.REPORTED_YEAR,
        ClaimTriggerBasis.LOD:ClaimYearType.ACCIDENT_YEAR
        } # not sure this needs to be in the function as a generic mapping. Might be best placed outside as mapping to enums together.

    @property
    def claim_year_basis(self) -> ContractException | ClaimYearType:
        if self.trigger_basis in self._claim_year_basis:
            return self._claim_year_basis[self.trigger_basis]
        else:
            raise ContractException(
                contract_id= self.contract_id, 
                message="Trigger basis missing in data"
                )

class RIContract:

    def __init__(self, contract_meta_data: RIContractMetadata, layers:Sequence[RILayer]) -> None:
        self._contract_meta_data = contract_meta_data
        self._contract_layers = {layer.layer_id: layer for layer in layers}
    
    @property
    def contract_meta_data(self):
        return self._contract_meta_data

    # def _xol_calculation(gross_amount: float, attachment: float, limit: float):
    #     return max(min(gross_amount - attachment,limit),0)

    # def _qs_calculation(gross_amount:float, cession:float):
    #     return max(gross_amount * cession,0)

    # def _franchise_calculation(    gross_amount: float, attachment: float, limit: float):
    #     if gross_amount > attachment:
    #         return min(gross_amount,limit)
    #     else: 
    #         return 0.0

    # def _surplus_share_calculation(gross_amount: float, sum_insured:float, attachment:float):
    #     if sum_insured <= attachment:
    #         return 0.0  # No ceded amount if the sum insured is within the retention
    #     surplus = sum_insured - attachment
    #     share = surplus / sum_insured
    #     return share * gross_amount

    # _layer_loss_calculation = {
    #     ContractType.QUOTA_SHARE: qs_calculation,
    #     ContractType.FRANCHISE_DEDUCTIBLE: franchise_calculation,
    #     ContractType.EXCESS_OF_LOSS: xol_calculation,
    #     ContractType.AGGREGATE_STOP_LOSS: xol_calculation,
    #     ContractType.SURPLUS_SHARE: surplus_share_calculation
    # }


    # def loss_to_layer_function(self):
    #     """
    #     Returns a list of tuples: (RILayer, layer_function) for each layer in the contract.
    #     """
    #     layer_func_list = []
    #     for layer in self._contract_layers.values():
    #         func = self._layer_loss_calculation.get(layer.layer_type)
    #         layer_func_list.append((layer, func))
    #     return layer_func_list



    



# class QuotaShareContract:
#     def __init__(self, share):
#         self.share = share

#     def ceded_amount(self, loss):
#         return self.share * loss

# class ExcessOfLossContract:
#     def __init__(self, retention, limit):
#         self.retention = retention
#         self.limit = limit

#     def ceded_amount(self, loss):
#         if loss <= self.retention:
#             return 0
#         return min(loss - self.retention, self.limit)

# class SurplusShareContract:
#     def __init__(self, retention):
#         self.retention = retention

#     def ceded_amount(self, sum_insured, loss):
#         if sum_insured <= self.retention:
#             return 0
#         surplus = sum_insured - self.retention
#         share = surplus / sum_insured
#         return share * loss

# class AggregateStopLossContract:
#     def __init__(self, attachment_point, limit):
#         self.attachment_point = attachment_point
#         self.limit = limit

#     def ceded_amount(self, total_losses):
#         if total_losses <= self.attachment_point:
#             return 0
#         return min(total_losses - self.attachment_point, self.limit)