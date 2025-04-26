from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import date
from enum import Enum

class ExposureType(Enum):
    """_summary_

    Args:
        Enum (_type_): _description_
    """
    EARNED = "earned"
    WRITTEN = "written"

@dataclass
class Exposure:
    """_summary_

    Raises:
        ValueError: _description_
        ValueError: _description_
        ValueError: _description_
        ValueError: _description_
        ValueError: _description_
        ValueError: _description_

    Returns:
        _type_: _description_
    """
    exposure_id: str
    insured_value: float
    attachment_point: float
    limit: float
    deductible: float
    policy_start: date
    policy_end: date
    exposure_type: ExposureType
    location: Optional[str] = None
    peril: Optional[str] = None
    occupancy: Optional[str] = None
    aggregate: bool = False

    def __post_init__(self):
        self.validate()

    def policy_term_days(self) -> int:
        """_summary_

        Returns:
            int: _description_
        """
        return (self.policy_end - self.policy_start).days

    def validate(self) -> None:
        """_summary_

        Raises:
            ValueError: _description_
            ValueError: _description_
            ValueError: _description_
            ValueError: _description_
            ValueError: _description_
            ValueError: _description_
        """
        if self.insured_value < 0:
            raise ValueError(f"[{self.exposure_id}] Insured value cannot be negative.")
        if self.attachment_point < 0:
            raise ValueError(f"[{self.exposure_id}] Attachment point cannot be negative.")
        if self.limit < 0:
            raise ValueError(f"[{self.exposure_id}] Limit cannot be negative.")
        if self.deductible < 0:
            raise ValueError(f"[{self.exposure_id}] Deductible cannot be negative.")
        if self.policy_end <= self.policy_start:
            raise ValueError(f"[{self.exposure_id}] Policy end date must be after start date.")
        if not isinstance(self.exposure_type, ExposureType):
            raise ValueError(f"[{self.exposure_id}] exposure_type must be an instance of ExposureType.")

@dataclass
class AggregateExposure:
    """_summary_

    Raises:
        ValueError: _description_
        ValueError: _description_

    Returns:
        _type_: _description_
    """
    exposures_by_year: Dict[int, List[Exposure]] = field(default_factory=dict)
    exposure_type: ExposureType = ExposureType.WRITTEN  # Default value

    def __post_init__(self):
        self.validate()

    def add_exposure(self, exposure: Exposure) -> None:
        """_summary_

        Args:
            exposure (Exposure): _description_
        """
        year = exposure.policy_start.year
        self.exposures_by_year.setdefault(year, []).append(exposure)

    def total_insured_value_by_year(self) -> Dict[int, float]:
        """_summary_

        Returns:
            Dict[int, float]: _description_
        """
        return {
            year: sum(e.insured_value for e in exposures)
            for year, exposures in self.exposures_by_year.items()
        }

    def total_limit_by_year(self) -> Dict[int, float]:
        """_summary_

        Returns:
            Dict[int, float]: _description_
        """
        return {
            year: sum(e.limit for e in exposures)
            for year, exposures in self.exposures_by_year.items()
        }

    def count_aggregate_exposures_by_year(self) -> Dict[int, int]:
        """_summary_

        Returns:
            Dict[int, int]: _description_
        """
        return {
            year: sum(1 for e in exposures if e.aggregate)
            for year, exposures in self.exposures_by_year.items()
        }

    def validate(self) -> None:
        """_summary_

        Raises:
            ValueError: _description_
            ValueError: _description_
        """
        if not self.exposures_by_year:
            raise ValueError("AggregateExposure must contain exposures.")
        if not isinstance(self.exposure_type, ExposureType):
            raise ValueError("exposure_type must be an instance of ExposureType.")
        for year, exposures in self.exposures_by_year.items():
            for exposure in exposures:
                exposure.validate()