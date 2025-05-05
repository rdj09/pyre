from datetime import date
from enum import Enum
from typing import List, Dict, Sequence
from dataclasses import dataclass

from pyre.claims.claims import ClaimYearType #TODO need to move this to a common ENUM module so no dependency on claims module

class ContractType(Enum):
    QUOTA_SHARE = "Quota Share"
    EXCESS_OF_LOSS = "Excess of Loss"
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

    @property
    def written_line_premium(self) -> float:
        return self.cession * self.written_line * self.full_subject_premium
    
    @property
    def signed_line_premium(self) -> float:
        return self.cession * self.signed_line * self.full_subject_premium

@dataclass
class RIContractMetadata:
    contract_id: int
    contract_description: str
    cedent_name: str 
    contract_type: ContractType
    trigger_basis: ClaimTriggerBasis
    indexation_clause: IndexationClauseType
    indexation_margin: float
    inception_date: date
    expiration_date: date
    fx_rates: Dict # {"GBP":1.0, "USD":1.25}
    
    @property
    def claim_year_basis(self) -> ClaimYearType:
        if self.trigger_basis == ClaimTriggerBasis.RAD:
            return ClaimYearType.UNDERWRITING_YEAR
        elif self.trigger_basis == ClaimTriggerBasis.CMB:
            return ClaimYearType.REPORTED_YEAR
        else:
            return ClaimYearType.ACCIDENT_YEAR # default is accident year basis.


class RIContract:
    def __init__(self, contract_meta_data: RIContractMetadata, layers:Sequence[RILayer]) -> None:
        self._contract_meta_data = contract_meta_data
        self._contract_layers = {layer.layer_id: layer for layer in layers}

    



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