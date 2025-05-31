from pyre.Models.trending import trend_exposures
from pyre.exposures.exposures import Exposures
from pyre.treaty.contracts import RIContract

class ExposureModelData:
    def __init__(self, exposures: Exposures, ri_contract: RIContract):
        self._exposures = exposures
        self._ri_contract = ri_contract

    @property
    def exposures(self):
        return self._exposures

    @exposures.setter
    def exposures(self, value):
        self._exposures = value

    @property
    def ri_contract(self):
        return self._ri_contract

    @ri_contract.setter
    def ri_contract(self, value):
        self._ri_contract = value

    @property
    def trended_exposurer(self):
        # You may want to use the actual base_year and trend_factors logic here
        return trend_exposures(self._exposures, base_year=0, trend_factors={blah: blah})