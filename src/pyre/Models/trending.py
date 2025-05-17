from typing import Protocol
from pyre.claims.claims_aggregator import ClaimAggregator
from pyre.exposures.exposures import ExposuresAggregator

class Trender(Protocol):
    def get_trend_factor(self, year: int) -> float:
        ...
    def trended_values(self, values: list[float], years: list[int]) -> list[float]:
        ...
    
class ExposureTrender(Trender):
    def __init__(self, exposures: ExposuresAggregator) -> None:
        self._exposures = exposures
        
    @property
    def exposures(self) -> ExposuresAggregator:
        return self._exposures
    
    @exposures.setter
    def exposures(self, values: ExposuresAggregator):
        self._exposures = values
    
    @property
    def trended_exposures(self) -> ExposuresAggregator:
        #TODO apply trend factors to data
        return ExposuresAggregator(self._exposures)


class ClaimTrender(Trender):
    def __init__(self, claims: ClaimAggregator) -> None:
        self._claims = claims

    @property
    def claims(self) -> ClaimAggregator:
        return self._claims
    
    @claims.setter
    def claims(self, values: ClaimAggregator):
        self._claims = values 
        
    @property
    def trended_claims(self) -> ClaimAggregator:
        #TODO #apply trend factors to the data
        return ClaimAggregator(self._claims)


#source citation: 
# Deters, I. (2017). The Mathematics of On-Leveling. 
# https://www.casact.org/sites/default/files/database/forum_17spforum_03-deters.pdf
