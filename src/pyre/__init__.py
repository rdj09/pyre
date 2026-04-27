"""pyRE — Python Reinsurance Pricing Library."""

from pyre.__about__ import __version__
from pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData
from pyre.claims.triangles import IBNERPatternExtractor, Triangle
from pyre.enums import (
    ClaimTriggerBasis,
    ClaimYearType,
    ContractType,
    CurveType,
    ExposureBasis,
    ExposureCurveType,
    FrequencyDistribution,
    IndexationClauseType,
    ProjectionMethods,
    SeverityDistribution,
)
from pyre.exceptions.exceptions import (
    ClaimsException,
    ContractException,
    ExposureException,
    GeneralException,
)
from pyre.exposures.exposures import Exposure, ExposureMetaData, Exposures, ExposureValues
from pyre.models.aggregate.aggregate_features import AggregateFeatures, ModellingAssumptions
from pyre.models.aggregate.selections import CredibilityConfig, CredibilityWeight, Selections
from pyre.models.aggregate.simulation_engine import Simulation, SimulationResults
from pyre.models.experience.burn_cost import BurnCostModel
from pyre.models.experience.experience_preparer import ExperienceModelData
from pyre.models.experience.frequency_severity import FitResult, FrequencyFit, SeverityFit
from pyre.models.experience.resampling import Resampling
from pyre.models.exposure.exposure_curve_functions import SwissReCValues, swissRe_c_values
from pyre.models.exposure.exposure_rating_cost import ExposureModel
from pyre.models.trending import Trending
from pyre.rate_monitoring.rate_adequacy import rate_adequacy, rate_adequacy_change
from pyre.rate_monitoring.rate_change import rate_change_adjusted, rate_change_simple
from pyre.treaty.contracts import RIContract, RIContractMetadata, RILayer
from pyre.treaty.layer_loss_functions import (
    franchise_calculation,
    layer_loss_calculation,
    qs_calculation,
    quota_share_calculation,
    surplus_share_calculation,
    xol_calculation,
)

__all__ = [
    "__version__",
    # Enums
    "ClaimYearType",
    "ClaimTriggerBasis",
    "ExposureBasis",
    "ContractType",
    "IndexationClauseType",
    "ProjectionMethods",
    "SeverityDistribution",
    "FrequencyDistribution",
    "ExposureCurveType",
    "CurveType",
    # Claims
    "Claim",
    "Claims",
    "ClaimDevelopmentHistory",
    "ClaimsMetaData",
    "Triangle",
    "IBNERPatternExtractor",
    # Exposures
    "Exposure",
    "Exposures",
    "ExposureMetaData",
    "ExposureValues",
    # Exceptions
    "GeneralException",
    "ExposureException",
    "ClaimsException",
    "ContractException",
    # Treaty
    "RILayer",
    "RIContractMetadata",
    "RIContract",
    "xol_calculation",
    "qs_calculation",
    "quota_share_calculation",
    "surplus_share_calculation",
    "franchise_calculation",
    "layer_loss_calculation",
    # Models
    "Trending",
    "ExperienceModelData",
    "BurnCostModel",
    "FrequencyFit",
    "SeverityFit",
    "FitResult",
    "Resampling",
    "ExposureModel",
    "SwissReCValues",
    "swissRe_c_values",
    "Selections",
    "CredibilityWeight",
    "CredibilityConfig",
    "AggregateFeatures",
    "ModellingAssumptions",
    "Simulation",
    "SimulationResults",
    # Rate monitoring
    "rate_adequacy",
    "rate_adequacy_change",
    "rate_change_simple",
    "rate_change_adjusted",
]
