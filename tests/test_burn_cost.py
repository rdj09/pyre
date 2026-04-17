from datetime import date

import pytest

from pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData, ClaimYearType
from pyre.enums import ContractType
from pyre.exposures.exposures import (
    Exposure,
    ExposureBasis,
    ExposureMetaData,
    Exposures,
    ExposureValues,
)
from pyre.models.experience.burn_cost import BurnCostModel, ProjectionMethods
from pyre.models.experience.experience_preparer import ExperienceModelData
from pyre.treaty.contracts import (
    ClaimTriggerBasis,
    IndexationClauseType,
    RIContract,
    RIContractMetadata,
    RILayer,
)


def _make_model_data() -> ExperienceModelData:
    meta = ClaimsMetaData(
        claim_id="C1",
        currency="GBP",
        contract_limit=1_000_000.0,
        contract_deductible=0.0,
        claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=date(2020, 6, 1),
    )
    dev_hist = ClaimDevelopmentHistory(
        development_months=[12],
        cumulative_dev_paid=[50_000.0],
        cumulative_dev_incurred=[80_000.0],
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
    exp_vals = ExposureValues(exposure_value=1_000_000.0, attachment_point=0.0, limit=1_000_000.0)
    exposures = Exposures([Exposure(exp_meta, exp_vals)])

    layer = RILayer(
        layer_id=1,
        layer_name="1m xs 0",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=0.0,
        occurrence_limit=1_000_000.0,
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[1_000_000.0],
        full_subject_premium=100_000.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=1,
        reinstatement_cost={1: 1.0},
    )
    contract_meta = RIContractMetadata(
        contract_id="CTR001",
        contract_description="Test contract",
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


def test_burn_cost_chainladder_returns_dict():
    model_data = _make_model_data()
    model = BurnCostModel(
        model_data=model_data,
        layer_id=1,
        projection_methods={2020: ProjectionMethods.CHAINLADDER},
        development_pattern={2020: 1.0},
    )
    result = model.calculate_burn_cost()
    assert isinstance(result, dict)
    assert 2020 in result


def test_burn_cost_bf_returns_dict():
    model_data = _make_model_data()
    model = BurnCostModel(
        model_data=model_data,
        layer_id=1,
        projection_methods={2020: ProjectionMethods.BF},
        development_pattern={2020: 1.0},
        a_priori_assumption={2020: 0.10},
    )
    result = model.calculate_burn_cost()
    assert isinstance(result, dict)
    assert 2020 in result


def test_burn_cost_raises_on_invalid_projection(monkeypatch):
    """Regression: calculate_burn_cost used to silently swallow exceptions
    and substitute chain-ladder results. Now it must propagate."""
    import pyre.models.experience.burn_cost as bc_module

    model_data = _make_model_data()
    model = BurnCostModel(
        model_data=model_data,
        layer_id=1,
        projection_methods={2020: ProjectionMethods.CHAINLADDER},
        development_pattern={2020: 1.0},
    )

    def bad_fn(*args, **kwargs):
        raise RuntimeError("intentional failure")

    monkeypatch.setitem(
        bc_module.projection_methods_fn, ProjectionMethods.CHAINLADDER, bad_fn
    )

    with pytest.raises(ValueError, match="Projection failed"):
        model.calculate_burn_cost()
