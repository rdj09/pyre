"""Smoke tests for the public API surface exposed via pyre.__init__."""
import pyre


def test_version_is_accessible():
    assert hasattr(pyre, "__version__")
    assert isinstance(pyre.__version__, str)


def test_enum_types_accessible():
    from pyre import (
        ClaimTriggerBasis,
        ClaimYearType,
        ContractType,
        ExposureBasis,
        IndexationClauseType,
        ProjectionMethods,
    )
    assert ClaimYearType.ACCIDENT_YEAR is not None
    assert ClaimTriggerBasis.LOD is not None
    assert ExposureBasis.EARNED is not None
    assert ContractType.EXCESS_OF_LOSS is not None
    assert IndexationClauseType.FULL_INDEXATION is not None
    assert ProjectionMethods.CHAINLADDER is not None


def test_core_classes_accessible():
    from pyre import (
        BurnCostModel,
        Claim,
        ClaimDevelopmentHistory,
        Claims,
        ClaimsMetaData,
        ExperienceModelData,
        Exposure,
        ExposureMetaData,
        ExposureModel,
        Exposures,
        ExposureValues,
        RIContract,
        RIContractMetadata,
        RILayer,
        Trending,
    )
    assert all(cls is not None for cls in [
        Claim, Claims, ClaimDevelopmentHistory, ClaimsMetaData,
        Exposure, Exposures, ExposureMetaData, ExposureValues,
        RILayer, RIContractMetadata, RIContract,
        Trending, ExperienceModelData, BurnCostModel, ExposureModel,
    ])


def test_rate_monitoring_functions_accessible():
    from pyre import rate_adequacy, rate_adequacy_change, rate_change_adjusted, rate_change_simple
    assert callable(rate_adequacy)
    assert callable(rate_adequacy_change)
    assert callable(rate_change_simple)
    assert callable(rate_change_adjusted)


def test_all_exports_present():
    """Every name in __all__ must resolve on the pyre namespace."""
    import pyre
    for name in pyre.__all__:
        assert hasattr(pyre, name), f"pyre.{name} missing from namespace"
