from dataclasses import dataclass
from typing import Optional
from pyre.Models.models import ModelData
from pyre.Models.trending import trend_claims
from pyre.claims.claims import Claims
from pyre.claims.triangles import IBNERPatternExtractor
from pyre.treaty.contracts import RIContract

@dataclass
class ExperienceModelData(ModelData):
    claims: Claims
    ri_contract: RIContract
    ibner_pattern: Optional[IBNERPatternExtractor]
    #TODO refactor down reduce coupling on full classes
    
    @property
    def trended_claims(self):
        base_year = self.ri_contract.contract_meta_data.inception_date.year
        return trend_claims(self.claims, base_year=base_year, trend_factors={blah:blah})
    
    @property
    def subject_contract_claims(self):
        return None

    @property
    def data_for_model(self):
        #counts, totals, averages
        return None
