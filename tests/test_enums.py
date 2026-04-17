from pyre.enums import (
    ClaimTriggerBasis,
    ClaimYearType,
    ContractType,
    ExposureBasis,
    FrequencyDistribution,
    SeverityDistribution,
)


def test_claim_trigger_basis_lod_maps_to_accident_year():
    result = ClaimTriggerBasis.LOD.to_claim_year_type()
    assert result == ClaimYearType.ACCIDENT_YEAR


def test_claim_trigger_basis_rad_maps_to_underwriting_year():
    result = ClaimTriggerBasis.RAD.to_claim_year_type()
    assert result == ClaimYearType.UNDERWRITING_YEAR


def test_claim_trigger_basis_cmb_maps_to_reported_year():
    result = ClaimTriggerBasis.CMB.to_claim_year_type()
    assert result == ClaimYearType.REPORTED_YEAR


def test_all_claim_year_types_are_covered():
    covered = {b.to_claim_year_type() for b in ClaimTriggerBasis}
    assert covered == set(ClaimYearType)


def test_contract_type_members():
    assert ContractType.QUOTA_SHARE in ContractType
    assert ContractType.EXCESS_OF_LOSS in ContractType
    assert ContractType.SURPLUS_SHARE in ContractType


def test_exposure_basis_values():
    assert ExposureBasis.EARNED.value is not None
    assert ExposureBasis.WRITTEN.value is not None


def test_severity_distribution_members():
    assert SeverityDistribution.LOGNORMAL in SeverityDistribution
    assert SeverityDistribution.PARETO in SeverityDistribution


def test_frequency_distribution_members():
    assert FrequencyDistribution.POISSON in FrequencyDistribution
    assert FrequencyDistribution.NEGATIVE_BINOMIAL in FrequencyDistribution
