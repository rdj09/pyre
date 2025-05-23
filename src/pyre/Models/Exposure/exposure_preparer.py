from copier import dataclass
from pyre.Models.models import ModelData
from pyre.Models.trending import trend_exposures
from pyre.exposures.exposures import Exposures
from pyre.treaty.contracts import RIContract

@dataclass
class ExposureModelData(ModelData):
    exposures: Exposures
    ri_contract: RIContract
    
    @property
    def trended_exposurer(self):
        return trend_exposures(self.exposures, base_year=0, trend_factors={blah:blah})

    