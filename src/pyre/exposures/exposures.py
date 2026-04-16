from dataclasses import dataclass, field
from datetime import date
import operator
from typing import List, Optional

from ..enums import ExposureBasis


@dataclass
class ExposureMetaData:
    """Metadata for an insurance exposure.

    Attributes:
        exposure_id: Unique identifier.
        exposure_name: Human-readable name.
        exposure_period_start: Start of exposure period.
        exposure_period_end: End of exposure period.
        currency: ISO currency code.
        aggregate: Whether this is an aggregate exposure. Defaults to False.
        line_of_business: LOB classification.
        stacking_id: Identifier for stacking exposures.
        exposure_type: Earned or written basis.
        location: Geographic location.
        peril: Associated peril.
        occupancy: Occupancy class.
    """
    exposure_id: str
    exposure_name: str
    exposure_period_start: date
    exposure_period_end: date
    currency: str
    aggregate: bool = False
    line_of_business: Optional[str] = None
    stacking_id: Optional[str] = None
    exposure_type: Optional[ExposureBasis] = field(default=ExposureBasis.EARNED)
    location: Optional[str] = None
    peril: Optional[str] = None
    occupancy: Optional[str] = None

    def __post_init__(self) -> None:
        if self.exposure_period_end < self.exposure_period_start:
            raise ValueError("Exposure period end date cannot be before start date")

    @property
    def exposure_term_length_days(self) -> int:
        return (self.exposure_period_end - self.exposure_period_start).days


@dataclass
class ExposureValues:
    """Key financial values for an insurance exposure.

    Attributes:
        exposure_value: Total insured amount or premium.
        attachment_point: Threshold at which coverage begins.
        limit: Maximum amount payable.
    """
    exposure_value: float
    attachment_point: float
    limit: float

    def __post_init__(self) -> None:
        if self.attachment_point < 0:
            raise ValueError("Attachment point cannot be negative")
        if self.limit < 0:
            raise ValueError("Limit cannot be negative")


class Exposure:
    """Represents an insurance exposure with associated metadata and values.

    This class encapsulates the metadata and values for a single exposure, providing
    methods to calculate earned exposure based on an analysis date.

    Attributes:
        _exposure_meta (ExposureMetaData): Metadata describing the exposure period and characteristics.
        _exposure_values (ExposureValues): Values associated with the exposure.

    Properties:
        exposure_meta (ExposureMetaData): The metadata associated with this exposure.
        exposure_values (ExposureValues): The values associated with this exposure.
        modelling_year (int): The calendar year in which the exposure period starts.

    Methods:
        earned_exposure_value(analysis_date: date) -> float:
            Calculates the earned portion of the exposure value as of the given analysis date.
        written_exposure_value(analysis_date: date) -> float:
            Calculates the written exposure value as of the given analysis date.
    """

    def __init__(self, exposure_meta: ExposureMetaData, exposure_values: ExposureValues) -> None:
        self._exposure_meta = exposure_meta
        self._exposure_values = exposure_values

    @property
    def exposure_meta(self) -> ExposureMetaData:
        return self._exposure_meta

    @property
    def exposure_values(self) -> ExposureValues:
        return self._exposure_values

    @property
    def modelling_year(self) -> int:
        return self._exposure_meta.exposure_period_start.year

    def _earned_pct(self, analysis_date: date) -> float:
        if self._exposure_meta.exposure_term_length_days == 0:
            return 0.0
        if self._exposure_meta.aggregate:
            return 0.0
        return min((analysis_date - self._exposure_meta.exposure_period_start).days / self._exposure_meta.exposure_term_length_days, 1.0)

    def earned_exposure_value(self, analysis_date: date) -> float:
        if self._exposure_meta.exposure_type == ExposureBasis.EARNED:
            return self._exposure_values.exposure_value
        else:
            return self._exposure_values.exposure_value * self._earned_pct(analysis_date)

    def written_exposure_value(self, analysis_date: date) -> float:
        if self._exposure_meta.exposure_type == ExposureBasis.EARNED:
            earned_pct = self._earned_pct(analysis_date)
            if earned_pct > 0:
                return self._exposure_values.exposure_value / earned_pct
            return self._exposure_values.exposure_value
        else:
            return self._exposure_values.exposure_value


class Exposures:
    """A container class for managing a collection of Exposure objects."""

    def __init__(self, exposures: List[Exposure]) -> None:
        self._exposures = exposures

    @property
    def exposures(self) -> List[Exposure]:
        return self._exposures

    @exposures.setter
    def exposures(self, list_of_exposure_classes: List[Exposure]) -> None:
        self._exposures = list_of_exposure_classes

    @property
    def modelling_years(self) -> List[int]:
        years = {exposure.modelling_year for exposure in self.exposures}
        return sorted(years)

    def append(self, exposure: Exposure) -> None:
        self._exposures.append(exposure)

    def __getitem__(self, key):
        if isinstance(key, slice):
            cls = type(self)
            return cls(self._exposures[key])
        index = operator.index(key)
        return self._exposures[index]

    def __iter__(self):
        return iter(self._exposures)

    def __len__(self) -> int:
        return len(self._exposures)
