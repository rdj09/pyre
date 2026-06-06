"""Central enum definitions for the pyRE package.

All package-wide enumerations are defined here to provide a single
authoritative location for their values and to avoid circular imports.
"""

from enum import Enum, auto


class ClaimYearType(Enum):
    """Enumeration of claim year types used in insurance data analysis.

    Attributes:
        ACCIDENT_YEAR: Represents the year in which the insured event (accident) occurred.
        UNDERWRITING_YEAR: Represents the year in which the insurance policy was underwritten or issued.
        REPORTED_YEAR: Represents the year in which the claim was reported to the insurer.
    """
    ACCIDENT_YEAR = auto()
    UNDERWRITING_YEAR = auto()
    REPORTED_YEAR = auto()


class ExposureBasis(Enum):
    """Enumeration of exposure bases used in insurance calculations.

    Attributes:
        EARNED: Represents exposures that have been earned over a given period.
        WRITTEN: Represents exposures that have been written (i.e., policies issued) during a given period.
    """
    EARNED = auto()
    WRITTEN = auto()


class ClaimTriggerBasis(Enum):
    LOD = "Losses Occurrence"  # Accident Year
    RAD = "Risk Attaching"     # Policy Inception Year
    CMB = "Claims Made Basis"  # Reported Year


class IndexationClauseType(Enum):
    FULL_INDEXATION = "Full Indexation"
    FIC = "Franchise - FIC"
    SIC = "Severe Inflation (also London Market) - SIC"


class ContractType(Enum):
    QUOTA_SHARE = auto()
    EXCESS_OF_LOSS = auto()
    FRANCHISE_DEDUCTIBLE = auto()
    SURPLUS_SHARE = auto()
    AGGREGATE_STOP_LOSS = auto()


class SeverityDistribution(Enum):
    LOGNORMAL = auto()
    PARETO = auto()
    OTHER = auto()


class FrequencyDistribution(Enum):
    POISSON = auto()
    NEGATIVE_BINOMIAL = auto()
    OTHER = auto()
