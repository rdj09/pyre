
from typing import Dict
from pyre.Models.models import ModelData
from pyre.Models.trending import ClaimTrender, ExposureTrender
from pyre.treaty.contracts import RIContract

class ExperienceModelData(ModelData):
    def __init__(self, claim_trender: ClaimTrender, exposure_trender: ExposureTrender, ri_contract: RIContract) -> None:
        self._claim_trender = claim_trender
        self._exposure_trender = exposure_trender
        self._ri_contract = ri_contract # don't need full class only key items

    # def apply_treaty_terms(self) -> Any:
    #     for claim in self._claims.claims:
    #         for layer in self._ri_contract._contract_layers.values():
    #             untrended_loss_to_layer = max(min(claim._capped_claim_development_history.latest_incurred - layer.occurrence_attachment, layer.occurrence_limit),0)
    #             trended_loss_to_layer = max(min())
    #     pass

    @property
    def model_data(self) -> Dict:
        return {}
        

    @property
    def data_summary(self) -> Dict:
        #do something
        #TODO combine untrended and trended data 
        return {}