from typing import Any, Dict, List
from ...Models.Experience.experience_preparer import ExperienceModelData
from ...enums import SeverityDistribution, FrequencyDistribution


class SeverityFit:
    def __init__(self, distributions: List[SeverityDistribution], data : ExperienceModelData, ibner_dev_pattern: Dict[int, float], ground_up:bool = True):
        self.data = data
        self.ground_up_model = ground_up
        self.ibner_dev_pattern = ibner_dev_pattern # could pass IBNERPatternExtractor().getIBNERPATTERN as outputs Dict[int,float] if needed
        self.distributions = distributions

    @property
    def _individual_projected_claims(self) -> Any | List[float]:
        if self.ground_up_model:
            # Return list of IBNER-projected incurred amounts for each claim
            return [claim.capped_claim_development_history.latest_incurred * self.ibner_dev_pattern[claim.claims_meta_data.modelling_year] for claim in self.data.trended_claims.claims]
        else:
            return NotImplementedError("non ground up fitting hasn't been implemented yet")


    def fit(self):
        """
        Fit the severity distribution to the data.
        This method should implement the logic to fit the specified severity distributions
        to the data provided in the ExperienceModelData instance.
        """
        self._individual_projected_claims
        pass


