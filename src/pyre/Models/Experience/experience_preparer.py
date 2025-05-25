from dataclasses import dataclass
from typing import Dict, Optional
from pyre.Models.trending import trend_claims, trend_exposures
from pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims
from pyre.exposures.exposures import Exposures
from pyre.treaty.contracts import RIContract

@dataclass
class ExperienceModelData():
    claims: Claims
    expousres : Exposures 
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
        return trend_exposures(self.expousres, base_year=base_year, trend_factors={blah:blah}) #TODO trend factors Dict[int, float]

    @property
    def aggregate_exposures(self) -> Dict[int, float]:
        """
        Returns a dictionary mapping modelling year to the sum of trended exposure values for that year.
        """
        exposures_by_year = {}
        for exposure in self.trended_exposures:
            year = getattr(exposure, "modelling_year", None)
            value = getattr(exposure, "value", None)
            if year is not None and value is not None:
                exposures_by_year.setdefault(year, 0.0)
                exposures_by_year[year] += value
        return exposures_by_year

    @property
    def aggregate_subject_contract_claims(self) -> Dict[int, Dict[int, Dict[str, float]]]:
        """Aggregates the output of subject_contract_claims by modelling year and layer.

        Returns:
            Dict[layer_id, Dict[modelling_year, Dict[str, float]]]:
                {
                    layer_id: {
                        modelling_year: {
                            "latest_paid": float,
                            "latest_incurred": float
                        }, ...
                    }, ...
                }
        """
        subjct_claims_by_layer_by_year = {}
        for layer_id, claims_list in self.subject_contract_claims.items():
            years = {}
            # claims_list is a list of Claim objects (see Claims class)
            for claim in claims_list:
                year = claim.claims_meta_data.modelling_year
                latest_paid = claim.capped_claim_development_history.latest_paid
                latest_incurred = claim.capped_claim_development_history.latest_incurred
                if year not in years:
                    years[year] = {"latest_paid": 0.0, "latest_incurred": 0.0}
                years[year]["latest_paid"] += latest_paid
                years[year]["latest_incurred"] += latest_incurred
            subjct_claims_by_layer_by_year[layer_id] = years
        return subjct_claims_by_layer_by_year