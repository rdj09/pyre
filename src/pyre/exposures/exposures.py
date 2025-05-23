from dataclasses import dataclass 
import operator
from typing import List, Optional
from datetime import date
from enum import Enum, auto

class ExposureBasis(Enum):
    """Enumeration of exposure bases used in insurance calculations.
    
    Attributes:
        EARNED: Represents exposures that have been earned over a given period.
        WRITTEN: Represents exposures that have been written (i.e., policies issued) during a given period.
    """

    EARNED = auto()
    WRITTEN = auto()

@dataclass
class ExposureMetaData():
    """Represents metadata for an insurance exposure, including identification, period, and classification details.
    
    Attributes:
        exposure_id (str): Unique identifier for the exposure.
        exposure_name (str): Human-readable name for the exposure.
        exposure_period_start (date): Start date of the exposure period.
        exposure_period_end (date): End date of the exposure period.
        currency (str): Currency code associated with the exposure.
        aggregate (bool): Indicates if the exposure is aggregated. Defaults to False.
        line_of_business (Optional[str]): Line of business associated with the exposure.
        stacking_id (Optional[str]): Identifier for stacking exposures.
        exposure_type (Optional[ExposureBasis]): Type or basis of the exposure. Defaults to ExposureBasis.EARNED.
        location (Optional[str]): Location associated with the exposure.
        peril (Optional[str]): Peril associated with the exposure.
        occupancy (Optional[str]): Occupancy type for the exposure.
    
    Properties:
        exposure_term_length_days (int): Number of days in the exposure period.
    """

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
class ExposureValues: #TODO consider fleshing out identifiers etc (differing class/coverage values BI/PD ...)
    """Represents the key financial values associated with an insurance exposure.
    
    Attributes:
        exposure_value (float): The total value of the exposure, such as the insured amount.
        attachment_point (float): The threshold amount at which coverage begins to apply.
        limit (float): The maximum amount payable under the coverage.
    """

    exposure_value: float
    attachment_point: float
    limit: float

class Exposure:
    """Represents an insurance exposure with associated metadata and values.
    
    This class encapsulates the metadata and values for a single exposure, providing
    methods to calculate earned exposure based on an analysis date.
    
    Attributes:
        _exposure_meta (ExposureMetaData): Metadata describing the exposure period and characteristics.
        _exposure_values (ExposureValues): Values associated with the exposure.
    
    Properties:
        modelling_year (int): The calendar year in which the exposure period starts.
    
    Methods:
        earned_exposure_value(analysis_date: date) -> float:
            Calculates the earned portion of the exposure value as of the given analysis date.
    """

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

class Exposures:
    """A container class for managing a collection of Exposure objects.
    
    This class provides list-like behavior for storing and manipulating multiple
    Exposure instances. It supports indexing, slicing, iteration, and appending
    new exposures.
    
    Attributes:
        exposures (List[Exposure]): The list of Exposure objects managed by this container.
    
    Args:
        exposures (List[Exposure]): A list of Exposure objects to initialize the container.
    
    Methods:
        append(exposure: Exposure): Appends an Exposure object to the collection.
        __getitem__(key): Returns an Exposure or a new Exposures instance for slices.
        __iter__(): Returns an iterator over the exposures.
        __len__(): Returns the number of exposures in the collection.
    """

    def __init__(self, exposures: List[Exposure])->None:
        self._exposures = exposures

    @property
    def exposures(self):
        return self._exposures
    
    @exposures.setter
    def exposures(self, list_of_exposure_classes:list[Exposure]):
        self._exposures = list_of_exposure_classes

    def append(self, exposure:Exposure):
        self._exposures.append(exposure)
    
    def __getitem__(self, key):
        if isinstance(key,slice):
            cls = type(self)
            return cls(self._exposures[key])
        index = operator.index(key)
        return self._exposures[index]

    def __iter__(self):
        return iter(self._exposures)
    
    def __len__(self):
        return len(self._exposures)

