from dataclasses import dataclass
from typing import Dict, List, Optional
from pyre.Models.models import ModelData
from pyre.Models.trending import trend_claims
from pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims
from pyre.claims.triangles import IBNERPatternExtractor
from pyre.treaty.contracts import RIContract

@dataclass
class ExperienceModelData(ModelData):
    claims: Claims
    ri_contract: RIContract
    development_patter: Optional[Dict] #TODO Consider development class
    ibner_pattern: Optional[IBNERPatternExtractor] #TODO refactor down reduce coupling on full classes
    
    @property
    def trended_claims(self):
        base_year = self.ri_contract.contract_meta_data.inception_date.year
        return trend_claims(self.claims, base_year=base_year, trend_factors={blah:blah})
    
    @property
    def subject_contract_claims(self)-> Dict[int, Claims]:
        """Returns a new Claims object where each claim's cumulative_dev_paid and cumulative_dev_incurred
        have had the RI contract's loss_to_layer_fn applied for each layer.

        Args:
            trended_claims (Claims): Claims object with trended values.
            ri_contract (RIContract): Reinsurance contract with layers, each having a loss_to_layer_fn.

        Returns:
            Claims: New Claims object with ceded (contract-applied) values.
        """
        ceded_claims = dict()
        for layer in self.ri_contract.layers:
            layer_ceded_claims = []
            for claim in self.trended_claims.claims:
                new_dev_hist = ClaimDevelopmentHistory(
                    development_months=claim.capped_claim_development_history.development_months,
                    cumulative_dev_paid=[layer.loss_to_layer_fn(paid) for paid in claim.capped_claim_development_history.cumulative_dev_paid],
                    cumulative_dev_incurred=[layer.loss_to_layer_fn(incurred) for incurred in claim.capped_claim_development_history.cumulative_dev_incurred]
                )
                new_claim = Claim(
                    claims_meta_data=claim.claims_meta_data,
                    claims_development_history=new_dev_hist,
                )
                layer_ceded_claims.append(new_claim)
            
            ceded_claims[layer.layer_id] = layer_ceded_claims

        return ceded_claims # returns dictioanry of claims and layer id that can be used to create aggregate numbers

    @property
    def aggregate_exposures(self):

        pass

    @property
    def aggregate_claims(self):
        #TODO iterate of each key in dictionary (layer id) and aggreagte up the latest capped values from claims by year
        #self.subject_contract_claims
        #aggregate total, and claim count by year
        # consider status of claim also.
        pass