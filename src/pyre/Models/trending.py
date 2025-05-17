from typing import Protocol

class Trender(Protocol):
    def get_trend_factor(self, year: int) -> float:
        ...
    def trended_values(self, values: list[float], years: list[int]) -> list[float]:
        ...
    
class ExposureTrender(Trender):
    def __init__(self) -> None:
        pass


class ClaimTrender(Trender):
    def __init__(self) -> None:
        pass

#source citation: 
# Deters, I. (2017). The Mathematics of On-Leveling. 
# https://www.casact.org/sites/default/files/database/forum_17spforum_03-deters.pdf
