from typing import Dict
from pyre.Models.trending import trend_claims, trend_exposures
from pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims
from pyre.exposures.exposures import Exposures
from pyre.treaty.contracts import RIContract


class ExperienceModelData():
    """
    ExperienceModelData is a data class that holds the claims and exposures data for a reinsurance contract.    
    It provides methods to trend claims and exposures, apply reinsurance contract layers, and aggregate results by modelling year and layer.
    """
    def __init__(self, claims:Claims, exposures:Exposures, ri_contract:RIContract):
        self._claims = claims
        self._exposures = exposures
        self._ri_contract = ri_contract

    @property
    def claims(self):
        return self._claims

    @claims.setter
    def claims(self, value:Claims):
        self._claims = value

    @property
    def exposures(self):
        return self._exposures

    @exposures.setter
    def exposures(self, value:Exposures):
        self._exposures = value

    @property
    def ri_contract(self):
        return self._ri_contract

    @ri_contract.setter
    def ri_contract(self, value:RIContract):
        self._ri_contract = value
    
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
    
    @property
    def aggregate_subject_contract_claims(self) -> Dict[int, Dict[int, Dict[str, float]]]:
        """
        Aggregates the output of subject_contract_claims by modelling year and layer, and also returns claim counts by layer, modelling year, claim status, and total count.

        Returns:
            Dict[layer_id, Dict[modelling_year, Dict[str, Any]]]:
                {
                    layer_id: {
                        modelling_year: {
                            "latest_paid": float,
                            "latest_incurred": float,
                            "claim_counts": {
                                status: count,
                                ...
                            },
                            "total_count": int
                        }, ...
                    }, ...
                }
        """
        subject_claims_by_year = {}
        for layer_id, claims_list in self.subject_contract_claims.items():
            year_agg = {}
            for claim in claims_list:
                year = claim.claims_meta_data.modelling_year
                status = getattr(claim.claims_meta_data, "status", "Unknown")
                latest_paid = claim.capped_claim_development_history.latest_paid
                latest_incurred = claim.capped_claim_development_history.latest_incurred
                if year not in year_agg:
                    year_agg[year] = {
                        "latest_paid": 0.0,
                        "latest_incurred": 0.0,
                        "claim_counts": {},
                        "total_count": 0
                    }
                year_agg[year]["latest_paid"] += latest_paid
                year_agg[year]["latest_incurred"] += latest_incurred
                if status not in year_agg[year]["claim_counts"]:
                    year_agg[year]["claim_counts"][status] = 0
                year_agg[year]["claim_counts"][status] += 1
                year_agg[year]["total_count"] += 1
            subject_claims_by_year[layer_id] = year_agg
        return subject_claims_by_year
    
    @property
    def aggregate_exposures(self) -> Dict[int, Dict[str, float]]:
        """
        Returns a dictionary mapping modelling year to the sum of trended written and earned exposure values for that year,
        using the properties and methods of the Exposure class.

        Returns:
            Dict[int, Dict[str, float]]:
                {
                    modelling_year: {
                        "written": total_written,
                        "earned": total_earned
                    }, ...
                }
        """
        exposures_by_year = {}
        for exposure in self.trended_exposures:
            # Use Exposure class properties
            year = getattr(exposure, "modelling_year", None)
            written_val = getattr(exposure, "written_exposure_value", None)
            earned_val = getattr(exposure, "earned_exposure_value", None)

            if year is not None:
                if year not in exposures_by_year:
                    exposures_by_year[year] = {"written": 0.0, "earned": 0.0}
                exposures_by_year[year]["written"] += written_val
                exposures_by_year[year]["earned"] += earned_val
        return exposures_by_year