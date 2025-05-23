from dataclasses import dataclass
from typing import Dict, Optional
from pyre import claims
from pyre.Models.models import ModelData
from pyre.Models.trending import trend_claims
from pyre.claims.claims import Claims
from pyre.claims.triangles import IBNERPatternExtractor
from pyre.treaty.contracts import RIContract

@dataclass
class ExperienceModelData(ModelData):
    claims: Claims
    ri_contract: RIContract
    development_patter: Dict #TODO Consider development class
    ibner_pattern: Optional[IBNERPatternExtractor]
    #TODO refactor down reduce coupling on full classes
    
    @property
    def trended_claims(self):
        base_year = self.ri_contract.contract_meta_data.inception_date.year
        return trend_claims(self.claims, base_year=base_year, trend_factors={blah:blah})
    
    @property
    def subject_contract_claims(self)-> Claims:
        subject_loss_fns = self.ri_contract.loss_to_layer_function()

        for claim in self.trended_claims.claims:
            for layer, func in self.ri_contract.loss_to_layer_function():



        # TODO ricontract class should carry the details of loss to layer functions. 
        return claims(...)

    @property
    def aggregate_exposures(self):
        pass

    @property
    def aggregate_claims(self):
        pass