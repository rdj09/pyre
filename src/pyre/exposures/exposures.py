import operator
from dataclasses import dataclass, field
from datetime import date

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
    line_of_business: str | None = None
    stacking_id: str | None = None
    exposure_type: ExposureBasis | None = field(default=ExposureBasis.EARNED)
    location: str | None = None
    peril: str | None = None
    occupancy: str | None = None

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
            return self._parallelogram_earned_pct(analysis_date)
        raw = (analysis_date - self._exposure_meta.exposure_period_start).days / self._exposure_meta.exposure_term_length_days
        return max(0.0, min(raw, 1.0))

    def _parallelogram_earned_pct(self, analysis_date: date) -> float:
        """Parallelogram method for aggregate exposures.

        Assumes policies are written uniformly throughout the exposure period,
        each with duration equal to exposure_term_length_days. The earning
        window extends from exposure_period_start to
        exposure_period_end + timedelta(days=term).
        """

        start = self._exposure_meta.exposure_period_start
        end = self._exposure_meta.exposure_period_end
        term = self._exposure_meta.exposure_term_length_days

        if term == 0:
            return 0.0

        period_days = (end - start).days
        total_earning_window = period_days + term

        if analysis_date <= start:
            return 0.0

        days_elapsed = (analysis_date - start).days

        if days_elapsed >= total_earning_window:
            return 1.0

        return days_elapsed / total_earning_window

    def earned_exposure_value(self, analysis_date: date) -> float:
        if self._exposure_meta.exposure_type == ExposureBasis.WRITTEN:
            return self._exposure_values.exposure_value
        else:
            return self._exposure_values.exposure_value * self._earned_pct(analysis_date)

    def __repr__(self) -> str:
        return (
            f"Exposure(id={self._exposure_meta.exposure_id!r}, "
            f"name={self._exposure_meta.exposure_name!r}, "
            f"value={self._exposure_values.exposure_value})"
        )

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

    def __init__(self, exposures: list[Exposure]) -> None:
        self._exposures = exposures

    @property
    def exposures(self) -> list[Exposure]:
        return self._exposures

    @exposures.setter
    def exposures(self, list_of_exposure_classes: list[Exposure]) -> None:
        self._exposures = list_of_exposure_classes

    @property
    def modelling_years(self) -> list[int]:
        years = {exposure.modelling_year for exposure in self.exposures}
        return sorted(years)

    @property
    def currencies(self):
        return {e.exposure_meta.currency for e in self._exposures}

    @property
    def exposure_ids(self):
        return {e.exposure_meta.exposure_id for e in self._exposures}

    def append(self, exposure: Exposure) -> None:
        self._exposures.append(exposure)

    def __repr__(self) -> str:
        ids = ", ".join(e.exposure_meta.exposure_id for e in self._exposures)
        return f"Exposures([{ids}])"

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
