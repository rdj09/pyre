from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date

from ..enums import ExposureBasis
from .._container import ItemContainer


@dataclass
class ExposureMetaData:
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
    exposure_type: Optional[ExposureBasis] = field(default=ExposureBasis.EARNED)
    location: Optional[str] = None
    peril: Optional[str] = None
    occupancy: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate date ordering after initialisation.

        Raises:
            ValueError: If exposure_period_end is before exposure_period_start.
        """
        if self.exposure_period_end < self.exposure_period_start:
            raise ValueError("Exposure period end date cannot be before start date")

    def __setattr__(self, name: str, value: object) -> None:
        """Set an attribute, enforcing date-ordering invariant for period fields.

        Raises:
            ValueError: If setting either date field would make start > end.
        """
        object.__setattr__(self, name, value)
        if name in ("exposure_period_start", "exposure_period_end"):
            if (
                hasattr(self, "exposure_period_start")
                and hasattr(self, "exposure_period_end")
                and self.exposure_period_start > self.exposure_period_end
            ):
                raise ValueError("Exposure period start date cannot be after end date")

    @property
    def exposure_term_length_days(self) -> int:
        """Number of days in the exposure period."""
        return (self.exposure_period_end - self.exposure_period_start).days


@dataclass
class ExposureValues:
    """Represents the key financial values associated with an insurance exposure.

    Attributes:
        exposure_value (float): The total value of the exposure, such as the insured amount.
        attachment_point (float): The threshold amount at which coverage begins to apply.
        limit (float): The maximum amount payable under the coverage.
    """

    exposure_value: float
    attachment_point: float
    limit: float

    def __post_init__(self) -> None:
        """Validate that attachment_point and limit are non-negative.

        Raises:
            ValueError: If attachment_point or limit is negative.
        """
        if self.attachment_point < 0:
            raise ValueError("Attachment point cannot be negative")
        if self.limit < 0:
            raise ValueError("Limit cannot be negative")

    def __setattr__(self, name: str, value: object) -> None:
        """Set an attribute, enforcing non-negative invariant for attachment_point and limit.

        Raises:
            ValueError: If attachment_point or limit is set to a negative value.
        """
        if name in ("attachment_point", "limit") and isinstance(value, (int, float)) and value < 0:
            raise ValueError(f"{name} cannot be negative")
        object.__setattr__(self, name, value)


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
        """Initialize an Exposure instance.

        Args:
            exposure_meta (ExposureMetaData): Metadata describing the exposure period and characteristics.
            exposure_values (ExposureValues): Values associated with the exposure.
        """
        self._exposure_meta = exposure_meta
        self._exposure_values = exposure_values

    @property
    def exposure_meta(self) -> ExposureMetaData:
        """Get the metadata associated with this exposure.

        Returns:
            ExposureMetaData: The metadata object.
        """
        return self._exposure_meta

    @property
    def exposure_values(self) -> ExposureValues:
        """Get the values associated with this exposure.

        Returns:
            ExposureValues: The values object.
        """
        return self._exposure_values

    @property
    def modelling_year(self) -> int:
        """Get the modelling year for this exposure.

        Returns:
            int: The calendar year in which the exposure period starts.
        """
        return self._exposure_meta.exposure_period_start.year

    def _earned_pct(self, analysis_date: date) -> float:
        """Calculate the earned percentage of the exposure as of the given analysis date.

        Args:
            analysis_date (date): The date for which to calculate the earned percentage.

        Returns:
            float: The earned percentage (0.0 to 1.0). Returns 0.0 if the exposure term length is 0
                  or if the exposure is aggregate.
        """
        if self._exposure_meta.exposure_term_length_days == 0:
            return 0.0
        if self._exposure_meta.aggregate:  # No need for == True
            return 0.0  # TODO: Implement parallelogram method when handling aggregate exposures
        return max(
            min(
                (analysis_date - self._exposure_meta.exposure_period_start).days
                / self._exposure_meta.exposure_term_length_days,
                1.0,
            ),
            0.0,
        )

    def earned_exposure_value(self, analysis_date: date) -> float:
        """Calculate the earned exposure value as of the given analysis date.

        Args:
            analysis_date (date): The date for which to calculate the earned exposure value.

        Returns:
            float: The exposure value prorated by the elapsed fraction of the exposure
                  period as of analysis_date (0.0 before the period starts, the full
                  value once it ends). This applies regardless of exposure_type --
                  what fraction has earned by a given date doesn't depend on how the
                  stored exposure_value was itself measured.
        """
        return self._exposure_values.exposure_value * self._earned_pct(analysis_date)

    def __repr__(self) -> str:
        return (
            f"Exposure(id={self._exposure_meta.exposure_id!r}, "
            f"name={self._exposure_meta.exposure_name!r})"
        )

    def written_exposure_value(self, analysis_date: date) -> float:
        """Calculate the written exposure value as of the given analysis date.

        Args:
            analysis_date (date): The date for which to calculate the written exposure value.

        Returns:
            float: The written exposure value. If the exposure type is EARNED, this is calculated
                  by dividing the exposure value by the earned percentage. If the earned percentage
                  is zero, returns the exposure value directly to avoid division by zero.
        """
        if self._exposure_meta.exposure_type == ExposureBasis.EARNED:
            earned_pct = self._earned_pct(analysis_date)
            if earned_pct > 0:
                return self._exposure_values.exposure_value / earned_pct
            return self._exposure_values.exposure_value  # Avoid division by zero
        else:
            return self._exposure_values.exposure_value


class Exposures(ItemContainer["Exposure"]):
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

    def __init__(self, exposures: List["Exposure"]) -> None:
        super().__init__()
        self._items = exposures

    @property
    def exposures(self) -> List["Exposure"]:
        """Returns the list of Exposure objects managed by this container."""
        return self._items

    @exposures.setter
    def exposures(self, list_of_exposure_classes: List["Exposure"]) -> None:
        """Sets the list of Exposure objects managed by this container."""
        self._items = list_of_exposure_classes

    @property
    def modelling_years(self) -> List[int]:
        """
        Returns a sorted list of unique modelling years for all exposures.

        Returns:
            List[int]: A sorted list of unique modelling years.
        """
        years = {exposure.modelling_year for exposure in self.exposures}
        return sorted(years)

    @property
    def currencies(self) -> set:
        """Returns the set of unique currencies across all exposures."""
        return {exposure._exposure_meta.currency for exposure in self._items}

    @property
    def exposure_ids(self) -> List[str]:
        """Returns the list of exposure IDs."""
        return [exposure._exposure_meta.exposure_id for exposure in self._items]
