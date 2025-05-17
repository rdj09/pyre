from typing import Dict
from pyre.Models.models import ModelData
from pyre.Models.trending import ExposureTrender
from pyre.exposures.exposures import ExposuresAggregator
from pyre.treaty.contracts import RIContract

class ExposureModelData(ModelData):
    def __init__(self, exposures: ExposuresAggregator, exposure_trender: ExposureTrender, ri_contract: RIContract) -> None:
        self._exposures = exposures
        self._exposure_trended_values = exposure_trender.trended_values
        self._ri_contract = ri_contract # don't need full class only key items
        self.model_data : Dict 
        