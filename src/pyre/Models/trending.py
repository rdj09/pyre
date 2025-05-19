from typing import Protocol
from pyre.claims.claims import Claims
from pyre.exposures.exposures import Exposures

class Trender(Protocol):
    def get_trend_factor(self, year: int) -> float:
        ...
    def trended_values(self, values: list[float], years: list[int]) -> list[float]:
        ...
    
class ExposureTrender(Trender):
    def __init__(self, exposures) -> None:
        self._exposures = exposures
        
    @property
    def exposures(self):
        return self._exposures
    
    @exposures.setter
    def exposures(self, values):
        self._exposures = values
    
    @property
    def trended_exposures(self):
        #TODO apply trend factors to data
        pass


class ClaimTrender(Trender):
    def __init__(self, claims:Claims) -> None:
        self._claims = claims

    @property
    def claims(self):
        return self._claims
    
    @claims.setter
    def claims(self, values):
        self._claims = values 
        
    def trended_claims(self):
        #TODO #apply trend factors to the data

        return Claims(...) 


#source citation: 
# Deters, I. (2017). The Mathematics of On-Leveling. 
# https://www.casact.org/sites/default/files/database/forum_17spforum_03-deters.pdf
