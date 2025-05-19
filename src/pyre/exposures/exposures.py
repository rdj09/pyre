from dataclasses import dataclass 
from typing import List, Optional
from datetime import date
from enum import Enum, auto

class ExposureBasis(Enum):
    EARNED = auto()
    WRITTEN = auto()

@dataclass
class ExposureMetaData():
    exposure_id: str
    exposure_name: str
    exposure_period_start: date
    exposure_period_end: date
    currency: str
    aggregate: bool = False
    line_of_business: Optional[str] = None
    stacking_id: Optional[str] = None
    exposure_type: Optional[ExposureBasis] = ExposureBasis.EARNED
    location: Optional[str] = None
    peril: Optional[str] = None
    occupancy: Optional[str] = None
    
    @property
    def exposure_term_length_days(self) -> int:
        return (self.exposure_period_end - self.exposure_period_start).days
    
@dataclass
class ExposureValues:
    exposure_value: float
    attachment_point: float
    limit: float

class Exposure:
    def __init__(self, exposure_meta: ExposureMetaData, exposure_values: ExposureValues) -> None:
        self._exposure_meta = exposure_meta
        self._exposure_values = exposure_values

    @property
    def modelling_year(self) -> int:
        return self._exposure_meta.exposure_period_start.year
    
    def _earned_pct(self, analysis_date: date) -> float:
        if self._exposure_meta.exposure_term_length_days == 0:
            return 0.0
        if self._exposure_meta.aggregate == True:
            return 0.0 #TODO parallelogram method when handling aggreagte exposures
        return min((analysis_date - self._exposure_meta.exposure_period_start).days / self._exposure_meta.exposure_term_length_days, 1.0)
    
    def earned_exposure_value(self, analysis_date: date) -> float:
        return self._exposure_values.exposure_value * self._earned_pct(analysis_date)


@dataclass
class Exposures:
    exposures : List[Exposure]