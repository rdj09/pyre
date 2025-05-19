from copier import dataclass
from pyre.Models.models import ModelData
from pyre.Models.trending import trend_claims
from pyre.claims.claims import Claims
from pyre.treaty.contracts import RIContract

@dataclass
class ExperienceModelData(ModelData):
    claims: Claims
    ri_contract: RIContract
    
    @property
    def trended_claims(self):
        return trend_claims(self.claims, base_year=0, trend_factors={blah:blah})
    
    @property
    def contract_terms_claims(self):
        #apply ri contract terms to trended claims
        #self.ri_contract.loss_to_layer_function
        return None

    @property
    def aggreagte_data_for_model(self):
        #counts, totals, averages
        return None
    