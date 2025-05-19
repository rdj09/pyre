from typing import Protocol
from pyre.claims.claims import ClaimDevelopmentHistory
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
    def __init__(self, claims: ClaimDevelopmentHistory) -> None:
        self._claims = claims

    @property
    def claims(self) -> ClaimDevelopmentHistory:
        return self._claims
    
    @claims.setter
    def claims(self, values: ClaimDevelopmentHistory):
        self._claims = values 
        
    @property
    def trended_claims(self) -> ClaimDevelopmentHistory:
        #TODO #apply trend factors to the data
        return ClaimDevelopmentHistory(self._claims)


#source citation: 
# Deters, I. (2017). The Mathematics of On-Leveling. 
# https://www.casact.org/sites/default/files/database/forum_17spforum_03-deters.pdf
