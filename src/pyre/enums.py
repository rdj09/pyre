"""Central enumeration definitions for pyRE.

All cross-cutting enumerations are defined here to avoid circular imports
and provide a single import location for users of the library.
"""

from enum import Enum, auto


class ClaimYearType(Enum):
    """Basis for determining which year a claim belongs to."""

    ACCIDENT_YEAR = auto()
    UNDERWRITING_YEAR = auto()
    REPORTED_YEAR = auto()


class ClaimTriggerBasis(Enum):
    """Defines how claims attach to a reinsurance contract."""

    LOD = "Losses Occurrence"  # Accident Year
    RAD = "Risk Attaching"  # Policy Inception Year
    CMB = "Claims Made Basis"  # Reported Year

    def to_claim_year_type(self) -> "ClaimYearType":
        """Map trigger basis to the corresponding ClaimYearType."""
        return {
            ClaimTriggerBasis.LOD: ClaimYearType.ACCIDENT_YEAR,
            ClaimTriggerBasis.RAD: ClaimYearType.UNDERWRITING_YEAR,
            ClaimTriggerBasis.CMB: ClaimYearType.REPORTED_YEAR,
        }[self]


class ExposureBasis(Enum):
    """Whether exposure figures are earned or written."""

    EARNED = auto()
    WRITTEN = auto()


class ContractType(Enum):
    """Reinsurance contract structure type."""

    QUOTA_SHARE = auto()
    EXCESS_OF_LOSS = auto()
    SURPLUS_SHARE = auto()
    FRANCHISE_DEDUCTIBLE = auto()
    AGGREGATE_STOP_LOSS = auto()


class IndexationClauseType(Enum):
    """Indexation clause type for a reinsurance contract."""

    FULL_INDEXATION = "Full Indexation"
    FIC = "Franchise - FIC"
    SIC = "Severe Inflation (also London Market) - SIC"


class ProjectionMethods(Enum):
    """Available ultimate loss projection methods."""

    CHAINLADDER = auto()
    BF = auto()
    SIMPLE_CAPE_COD = auto()
    GENERALISED_CAPE_COD = auto()


class SeverityDistribution(Enum):
    """Severity distribution families for fitting."""

    LOGNORMAL = auto()
    PARETO = auto()
    OTHER = auto()


class FrequencyDistribution(Enum):
    """Frequency distribution families for fitting."""

    POISSON = auto()
    NEGATIVE_BINOMIAL = auto()
    OTHER = auto()


class ExposureCurveType(Enum):
    """Exposure curve type for exposure rating."""

    RIEBESELL = auto()
    MIXED_EXPONENTIAL = auto()
    MBBEFD = auto()


class CurveType(Enum):
    """Development curve type for triangle fitting."""

    EXPONENTIAL = auto()
    POWER = auto()
    WEIBULL = auto()
    INVERSE_POWER = auto()
    OTHER = auto()
