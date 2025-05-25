from dataclasses import dataclass
from typing import Dict
from pyre.Models.trending import trend_claims, trend_exposures
from pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims
from pyre.exposures.exposures import Exposures
from pyre.treaty.contracts import RIContract


@dataclass
class ExperienceModelData():
    claims: Claims
    exposures : Exposures 
    ri_contract: RIContract
    
    @property
    def trended_claims(self):
        base_year = self.ri_contract.contract_meta_data.inception_date.year
        return trend_claims(self.claims, base_year=base_year, trend_factors={blah:blah}) #TODO Trend factors Dict[int, float]
    
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
    def trended_exposures(self):
        base_year = self.ri_contract.contract_meta_data.inception_date.year
        return trend_exposures(self.exposures, base_year=base_year, trend_factors={blah:blah}) #TODO trend factors Dict[int, float]
