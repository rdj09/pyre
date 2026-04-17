"""Tests for ExperienceModelData caching behaviour."""
from datetime import date
from functools import cached_property

from pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData, ClaimYearType
from pyre.enums import ClaimTriggerBasis, ContractType, IndexationClauseType
from pyre.exposures.exposures import (
    Exposure,
    ExposureBasis,
    ExposureMetaData,
    Exposures,
    ExposureValues,
)
from pyre.models.experience.experience_preparer import ExperienceModelData
from pyre.treaty.contracts import RIContract, RIContractMetadata, RILayer


def _make_model_data() -> ExperienceModelData:
    meta = ClaimsMetaData(
        claim_id="C1",
        currency="GBP",
        contract_limit=500_000.0,
        contract_deductible=0.0,
        claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=date(2020, 6, 1),
    )
    dev_hist = ClaimDevelopmentHistory(
        development_months=[12],
        cumulative_dev_paid=[40_000.0],
        cumulative_dev_incurred=[60_000.0],
    )
    claims = Claims([Claim(meta, dev_hist)])

    exp_meta = ExposureMetaData(
        exposure_id="E1",
        exposure_name="2020 Premium",
        exposure_period_start=date(2020, 1, 1),
        exposure_period_end=date(2020, 12, 31),
        currency="GBP",
        exposure_type=ExposureBasis.EARNED,
    )
    exp_vals = ExposureValues(exposure_value=500_000.0, attachment_point=0.0, limit=500_000.0)
    exposures = Exposures([Exposure(exp_meta, exp_vals)])

    layer = RILayer(
        layer_id=1,
        layer_name="500k xs 0",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=0.0,
        occurrence_limit=500_000.0,
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[500_000.0],
        full_subject_premium=50_000.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=1,
        reinstatement_cost={1: 1.0},
    )
    contract_meta = RIContractMetadata(
        contract_id="CTR001",
        contract_description="Test",
        cedent_name="Test Cedent",
        trigger_basis=ClaimTriggerBasis.LOD,
        indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0,
        inception_date=date(2021, 1, 1),
        expiration_date=date(2021, 12, 31),
        fx_rates={"GBP": 1.0},
    )
    contract = RIContract(contract_meta_data=contract_meta, layers=[layer])
    return ExperienceModelData(
        claims=claims,
        exposures=exposures,
        ri_contract=contract,
        exposure_trend_factors={yr: 1.0 for yr in range(2010, 2022)},
        claim_trend_factors={yr: 1.0 for yr in range(2010, 2022)},
    )


def test_trended_claims_is_cached_property():
    """trended_claims should be a functools.cached_property."""
    assert isinstance(
        ExperienceModelData.__dict__["trended_claims"], cached_property
    )


def test_trended_exposures_is_cached_property():
    assert isinstance(
        ExperienceModelData.__dict__["trended_exposures"], cached_property
    )


def test_subject_contract_claims_is_cached_property():
    assert isinstance(
        ExperienceModelData.__dict__["subject_contract_claims"], cached_property
    )


def test_aggregate_subject_contract_claims_is_cached_property():
    assert isinstance(
        ExperienceModelData.__dict__["aggregate_subject_contract_claims"], cached_property
    )


def test_aggregate_exposures_is_cached_property():
    assert isinstance(
        ExperienceModelData.__dict__["aggregate_exposures"], cached_property
    )


def test_cached_property_returns_same_object():
    """Calling trended_claims twice must return the identical object (cache hit)."""
    md = _make_model_data()
    first = md.trended_claims
    second = md.trended_claims
    assert first is second


def test_claims_setter_invalidates_cache():
    """Setting .claims must invalidate trended_claims so the next access recomputes."""
    md = _make_model_data()
    first = md.trended_claims  # populate cache

    # Build a new, different Claims object
    meta2 = ClaimsMetaData(
        claim_id="C2",
        currency="GBP",
        contract_limit=999_000.0,
        contract_deductible=0.0,
        claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=date(2020, 6, 1),
    )
    dev_hist2 = ClaimDevelopmentHistory(
        development_months=[12],
        cumulative_dev_paid=[99_000.0],
        cumulative_dev_incurred=[99_000.0],
    )
    md.claims = Claims([Claim(meta2, dev_hist2)])

    second = md.trended_claims
    assert first is not second  # cache was invalidated


def test_update_trend_factors_invalidates_cache():
    """update_trend_factors must clear all derived cached properties."""
    md = _make_model_data()
    _ = md.trended_claims  # populate cache
    assert "trended_claims" in md.__dict__

    md.update_trend_factors(claim_trend_factors={yr: 1.05 for yr in range(2010, 2022)})
    assert "trended_claims" not in md.__dict__
