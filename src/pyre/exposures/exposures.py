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
    def __init__(
        self,
        exposure_id: str,
        exposure_name: str,
        exposure_period_start: date,
        exposure_period_end: date,
        currency: str,
        aggregate: bool = False,
        line_of_business: Optional[str] = None,
        stacking_id: Optional[str] = None,
        exposure_type: Optional[ExposureBasis] = ExposureBasis.EARNED,
        location: Optional[str] = None,
        peril: Optional[str] = None,
        occupancy: Optional[str] = None
    ):
        """Initialize an ExposureMetaData instance.

        Args:
            exposure_id (str): Unique identifier for the exposure.
            exposure_name (str): Human-readable name for the exposure.
            exposure_period_start (date): Start date of the exposure period.
            exposure_period_end (date): End date of the exposure period.
            currency (str): Currency code associated with the exposure.
            aggregate (bool, optional): Indicates if the exposure is aggregated. Defaults to False.
            line_of_business (Optional[str], optional): Line of business. Defaults to None.
            stacking_id (Optional[str], optional): Identifier for stacking exposures. Defaults to None.
            exposure_type (Optional[ExposureBasis], optional): Type of exposure. Defaults to ExposureBasis.EARNED.
            location (Optional[str], optional): Location associated with the exposure. Defaults to None.
            peril (Optional[str], optional): Peril associated with the exposure. Defaults to None.
            occupancy (Optional[str], optional): Occupancy type for the exposure. Defaults to None.

        Raises:
            ValueError: If exposure_period_end is before exposure_period_start.
        """
        if exposure_period_end < exposure_period_start:
            raise ValueError("Exposure period end date cannot be before start date")

        self._exposure_id = exposure_id
        self._exposure_name = exposure_name
        self._exposure_period_start = exposure_period_start
        self._exposure_period_end = exposure_period_end
        self._currency = currency
        self._aggregate = aggregate
        self._line_of_business = line_of_business
        self._stacking_id = stacking_id
        self._exposure_type = exposure_type
        self._location = location
        self._peril = peril
        self._occupancy = occupancy

    @property
    def exposure_id(self) -> str:
        return self._exposure_id

    @exposure_id.setter
    def exposure_id(self, value: str) -> None:
        self._exposure_id = value

    @property
    def exposure_name(self) -> str:
        return self._exposure_name

    @exposure_name.setter
    def exposure_name(self, value: str) -> None:
        self._exposure_name = value

    @property
    def exposure_period_start(self) -> date:
        return self._exposure_period_start

    @exposure_period_start.setter
    def exposure_period_start(self, value: date) -> None:
        """Set the exposure period start date.

        Args:
            value (date): The new start date.

        Raises:
            ValueError: If the new start date is after the current end date.
        """
        if hasattr(self, '_exposure_period_end') and value > self._exposure_period_end:
            raise ValueError("Exposure period start date cannot be after end date")
        self._exposure_period_start = value

    @property
    def exposure_period_end(self) -> date:
        return self._exposure_period_end

    @exposure_period_end.setter
    def exposure_period_end(self, value: date) -> None:
        """Set the exposure period end date.

        Args:
            value (date): The new end date.

        Raises:
            ValueError: If the new end date is before the current start date.
        """
        if hasattr(self, '_exposure_period_start') and value < self._exposure_period_start:
            raise ValueError("Exposure period end date cannot be before start date")
        self._exposure_period_end = value

    @property
    def currency(self) -> str:
        return self._currency

    @currency.setter
    def currency(self, value: str) -> None:
        self._currency = value

    @property
    def aggregate(self) -> bool:
        return self._aggregate

    @aggregate.setter
    def aggregate(self, value: bool) -> None:
        self._aggregate = value

    @property
    def line_of_business(self) -> Optional[str]:
        return self._line_of_business

    @line_of_business.setter
    def line_of_business(self, value: Optional[str]) -> None:
        self._line_of_business = value

    @property
    def stacking_id(self) -> Optional[str]:
        return self._stacking_id

    @stacking_id.setter
    def stacking_id(self, value: Optional[str]) -> None:
        self._stacking_id = value

    @property
    def exposure_type(self) -> ExposureBasis:
        return self._exposure_type

    @exposure_type.setter
    def exposure_type(self, value: ExposureBasis) -> None:
        self._exposure_type = value

    @property
    def location(self) -> Optional[str]:
        return self._location

    @location.setter
    def location(self, value: Optional[str]) -> None:
        self._location = value

    @property
    def peril(self) -> Optional[str]:
        return self._peril

    @peril.setter
    def peril(self, value: Optional[str]) -> None:
        self._peril = value

    @property
    def occupancy(self) -> Optional[str]:
        return self._occupancy

    @occupancy.setter
    def occupancy(self, value: Optional[str]) -> None:
        self._occupancy = value
    @property
    def exposure_term_length_days(self) -> int:
        return (self.exposure_period_end - self.exposure_period_start).days

class ExposureValues:
    """Represents the key financial values associated with an insurance exposure.

    Attributes:
        exposure_value (float): The total value of the exposure, such as the insured amount.
        attachment_point (float): The threshold amount at which coverage begins to apply.
        limit (float): The maximum amount payable under the coverage.
    """
    def __init__(self, exposure_value: float, attachment_point: float, limit: float):
        """Initialize an ExposureValues instance.

        Args:
            exposure_value (float): The total value of the exposure.
            attachment_point (float): The threshold amount at which coverage begins to apply.
            limit (float): The maximum amount payable under the coverage.

        Raises:
            ValueError: If attachment_point or limit is negative.
        """
        if attachment_point < 0:
            raise ValueError("Attachment point cannot be negative")
        if limit < 0:
            raise ValueError("Limit cannot be negative")

        self._exposure_value = exposure_value
        self._attachment_point = attachment_point
        self._limit = limit

    @property
    def exposure_value(self) -> float:
        return self._exposure_value

    @exposure_value.setter
    def exposure_value(self, value: float) -> None:
        self._exposure_value = value

    @property
    def attachment_point(self) -> float:
        return self._attachment_point

    @attachment_point.setter
    def attachment_point(self, value: float) -> None:
        """Set the attachment point.

        Args:
            value (float): The new attachment point.

        Raises:
            ValueError: If the new attachment point is negative.
        """
        if value < 0:
            raise ValueError("Attachment point cannot be negative")
        self._attachment_point = value

    @property
    def limit(self) -> float:
        return self._limit

    @limit.setter
    def limit(self, value: float) -> None:
        """Set the limit.

        Args:
            value (float): The new limit.

        Raises:
            ValueError: If the new limit is negative.
        """
        if value < 0:
            raise ValueError("Limit cannot be negative")
        self._limit = value

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
        return min((analysis_date - self._exposure_meta.exposure_period_start).days / self._exposure_meta.exposure_term_length_days, 1.0)

    def earned_exposure_value(self, analysis_date: date) -> float:
        """Calculate the earned exposure value as of the given analysis date.

        Args:
            analysis_date (date): The date for which to calculate the earned exposure value.

        Returns:
            float: The earned exposure value. If the exposure type is EARNED, this is the full
                  exposure value. Otherwise, it's the exposure value multiplied by the earned percentage.
        """
        if self._exposure_meta.exposure_type == ExposureBasis.EARNED:
            return self._exposure_values.exposure_value
        else:
            return self._exposure_values.exposure_value * self._earned_pct(analysis_date)

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
    def exposures(self) -> List[Exposure]:
        """Returns the list of Exposure objects managed by this container."""
        return self._exposures

    @exposures.setter
    def exposures(self, list_of_exposure_classes: List[Exposure]) -> None:
        """Sets the list of Exposure objects managed by this container."""
        self._exposures = list_of_exposure_classes

    @property
    def modelling_years(self) -> List[int]: 
        """
        Returns a sorted list of unique modelling years for all exposures.

        Returns:
            List[int]: A sorted list of unique modelling years.
        """
        years = {exposure.modelling_year for exposure in self.exposures}
        return sorted(years)

    def append(self, exposure: Exposure) -> None:
        """Append an Exposure object to the collection.

        Args:
            exposure (Exposure): The Exposure object to append.
        """
        self._exposures.append(exposure)

    def __getitem__(self, key):
        """Get an Exposure object by index or a slice of Exposures.

        Args:
            key: An integer index or a slice object.

        Returns:
            Union[Exposure, 'Exposures']: An Exposure object if key is an integer,
                                         or a new Exposures instance if key is a slice.
        """
        if isinstance(key, slice):
            cls = type(self)
            return cls(self._exposures[key])
        index = operator.index(key)
        return self._exposures[index]

    def __iter__(self):
        """Return an iterator over the exposures.

        Returns:
            Iterator[Exposure]: An iterator over the Exposure objects.
        """
        return iter(self._exposures)

    def __len__(self) -> int:
        """Return the number of exposures in the collection.

        Returns:
            int: The number of Exposure objects.
        """
        return len(self._exposures)
