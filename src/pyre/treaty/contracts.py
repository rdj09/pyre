from datetime import date
from enum import Enum
from typing import Any, Dict, Sequence
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


class RILayer:
    def __init__(
        self,
        layer_id: int,
        layer_name: str,
        layer_type: ContractType,
        occurrence_attachment: float,
        occurrence_limit: float,
        aggregate_attachment: float,
        aggregate_limit: float,
        subject_lines_of_business: list,
        subject_lob_exposure_amounts: list,
        full_subject_premium: float,
        written_line: float,
        signed_line: float,
        number_of_reinstatements: int,
        reinstatement_cost: dict,
        cession: float = 1.0,
        inures_to_benefit_of: list = None,
        interlocking_classes: list = None
    ):
        self._layer_id = layer_id
        self._layer_name = layer_name
        self._layer_type = layer_type
        self._occurrence_attachment = occurrence_attachment
        self._occurrence_limit = occurrence_limit
        self._aggregate_attachment = aggregate_attachment
        self._aggregate_limit = aggregate_limit
        self._subject_lines_of_business = subject_lines_of_business
        self._subject_lob_exposure_amounts = subject_lob_exposure_amounts
        self._full_subject_premium = full_subject_premium
        self._written_line = written_line
        self._signed_line = signed_line
        self._number_of_reinstatements = number_of_reinstatements
        self._reinstatement_cost = reinstatement_cost
        self._cession = cession
        self._inures_to_benefit_of = inures_to_benefit_of if inures_to_benefit_of is not None else []
        self._interlocking_classes = interlocking_classes if interlocking_classes is not None else []
    

    @property
    def layer_id(self):
        return self._layer_id

    @layer_id.setter
    def layer_id(self, value):
        self._layer_id = value

    @property
    def layer_name(self):
        return self._layer_name

    @layer_name.setter
    def layer_name(self, value):
        self._layer_name = value

    @property
    def layer_type(self):
        return self._layer_type

    @layer_type.setter
    def layer_type(self, value):
        self._layer_type = value

    @property
    def occurrence_attachment(self):
        return self._occurrence_attachment

    @occurrence_attachment.setter
    def occurrence_attachment(self, value):
        self._occurrence_attachment = value

    @property
    def occurrence_limit(self):
        return self._occurrence_limit

    @occurrence_limit.setter
    def occurrence_limit(self, value):
        self._occurrence_limit = value

    @property
    def aggregate_attachment(self):
        return self._aggregate_attachment

    @aggregate_attachment.setter
    def aggregate_attachment(self, value):
        self._aggregate_attachment = value

    @property
    def aggregate_limit(self):
        return self._aggregate_limit

    @aggregate_limit.setter
    def aggregate_limit(self, value):
        self._aggregate_limit = value

    @property
    def subject_lines_of_business(self):
        return self._subject_lines_of_business

    @subject_lines_of_business.setter
    def subject_lines_of_business(self, value):
        self._subject_lines_of_business = value

    @property
    def subject_lob_exposure_amounts(self):
        return self._subject_lob_exposure_amounts

    @subject_lob_exposure_amounts.setter
    def subject_lob_exposure_amounts(self, value):
        self._subject_lob_exposure_amounts = value

    @property
    def full_subject_premium(self):
        return self._full_subject_premium

    @full_subject_premium.setter
    def full_subject_premium(self, value):
        self._full_subject_premium = value

    @property
    def written_line(self):
        return self._written_line

    @written_line.setter
    def written_line(self, value):
        self._written_line = value

    @property
    def signed_line(self):
        return self._signed_line

    @signed_line.setter
    def signed_line(self, value):
        self._signed_line = value

    @property
    def number_of_reinstatements(self):
        return self._number_of_reinstatements

    @number_of_reinstatements.setter
    def number_of_reinstatements(self, value):
        self._number_of_reinstatements = value

    @property
    def reinstatement_cost(self):
        return self._reinstatement_cost

    @reinstatement_cost.setter
    def reinstatement_cost(self, value):
        self._reinstatement_cost = value

    @property
    def cession(self):
        return self._cession

    @cession.setter
    def cession(self, value):
        self._cession = value

    @property
    def inures_to_benefit_of(self):
        return self._inures_to_benefit_of

    @inures_to_benefit_of.setter
    def inures_to_benefit_of(self, value):
        self._inures_to_benefit_of = value

    @property
    def interlocking_classes(self):
        return self._interlocking_classes

    @interlocking_classes.setter
    def interlocking_classes(self, value):
        self._interlocking_classes = value

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

class RIContractMetadata:
    def __init__(
        self,
        contract_id: str,
        contract_description: str,
        cedent_name: str,
        trigger_basis: ClaimTriggerBasis,
        indexation_clause: IndexationClauseType,
        indexation_margin: float,
        inception_date: date,
        expiration_date: date,
        fx_rates: Dict # {"GBP":1.0, "USD":1.25}
    ):
        self._contract_id = contract_id
        self._contract_description = contract_description
        self._cedent_name = cedent_name
        self._trigger_basis = trigger_basis
        self._indexation_clause = indexation_clause
        self._indexation_margin = indexation_margin
        self._inception_date = inception_date
        self._expiration_date = expiration_date
        self._fx_rates = fx_rates

    @property
    def contract_id(self):
        return self._contract_id

    @contract_id.setter
    def contract_id(self, value):
        self._contract_id = value

    @property
    def contract_description(self):
        return self._contract_description

    @contract_description.setter
    def contract_description(self, value):
        self._contract_description = value

    @property
    def cedent_name(self):
        return self._cedent_name

    @cedent_name.setter
    def cedent_name(self, value):
        self._cedent_name = value

    @property
    def trigger_basis(self):
        return self._trigger_basis

    @trigger_basis.setter
    def trigger_basis(self, value):
        self._trigger_basis = value

    @property
    def indexation_clause(self):
        return self._indexation_clause

    @indexation_clause.setter
    def indexation_clause(self, value):
        self._indexation_clause = value

    @property
    def indexation_margin(self):
        return self._indexation_margin

    @indexation_margin.setter
    def indexation_margin(self, value):
        self._indexation_margin = value

    @property
    def inception_date(self):
        return self._inception_date

    @inception_date.setter
    def inception_date(self, value):
        self._inception_date = value

    @property
    def expiration_date(self):
        return self._expiration_date

    @expiration_date.setter
    def expiration_date(self, value):
        self._expiration_date = value

    @property
    def fx_rates(self): # {"GBP":1.0, "USD":1.25}
        return self._fx_rates

    @fx_rates.setter
    def fx_rates(self, value): # {"GBP":1.0, "USD":1.25}
        self._fx_rates = value

    @property
    def claim_year_basis(self) -> ContractException | ClaimYearType:
        if self.trigger_basis in claim_year_basis:
            return claim_year_basis[self.trigger_basis]
        else:
            raise ContractException(
                contract_id= self.contract_id, 
                message="Trigger basis missing in data"
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

