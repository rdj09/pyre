import math
from datetime import date

import pytest

from src.pyre.enums import FrequencyDistribution, SeverityDistribution
from src.pyre.models.experience.frequency_severity import (
    FitResult,
    FrequencyFit,
    _fit_lognormal,
    _fit_negative_binomial,
    _fit_pareto,
    _fit_poisson,
)


def test_fit_lognormal_returns_mu_and_sigma():
    import random
    random.seed(42)
    data = [math.exp(random.gauss(0, 1)) for _ in range(500)]
    params = _fit_lognormal(data)
    assert "mu" in params
    assert "sigma" in params
    assert abs(params["mu"]) < 0.3
    assert abs(params["sigma"] - 1.0) < 0.3


def test_fit_pareto_returns_alpha_and_x_m():
    data = [1.0, 1.1, 1.3, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 10.0]
    params = _fit_pareto(data)
    assert "alpha" in params
    assert "x_m" in params
    assert params["x_m"] == pytest.approx(min(data))
    assert params["alpha"] > 0


def test_fit_lognormal_single_value_raises():
    with pytest.raises(ValueError, match="at least 2"):
        _fit_lognormal([100.0])


def test_fit_pareto_empty_raises():
    with pytest.raises(ValueError, match="at least 1"):
        _fit_pareto([])


def test_fit_result_has_aic():
    params = _fit_lognormal([100.0, 200.0, 300.0, 150.0, 250.0])
    result = FitResult(
        distribution=SeverityDistribution.LOGNORMAL,
        parameters=params,
        log_likelihood=-50.0,
        aic=2 * 2 - 2 * (-50.0),
    )
    assert result.aic == pytest.approx(104.0)


def test_fit_poisson_returns_lambda():
    counts = [3, 4, 3, 5, 4, 3, 4]
    params = _fit_poisson(counts)
    assert "lambda_" in params
    assert params["lambda_"] == pytest.approx(sum(counts) / len(counts))


def test_fit_negative_binomial_returns_r_and_p():
    # variance > mean required: mean=2.0, variance≈7.1
    counts = [0, 0, 1, 0, 5, 8, 2, 0, 1, 3]
    params = _fit_negative_binomial(counts)
    assert "r" in params
    assert "p" in params
    assert params["r"] > 0
    assert 0 < params["p"] < 1


def test_frequency_fit_poisson():
    from src.pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData
    from src.pyre.enums import ClaimYearType, ContractType, ExposureBasis
    from src.pyre.exposures.exposures import Exposure, ExposureMetaData, Exposures, ExposureValues
    from src.pyre.models.experience.experience_preparer import ExperienceModelData
    from src.pyre.treaty.contracts import (
        ClaimTriggerBasis,
        IndexationClauseType,
        RIContract,
        RIContractMetadata,
        RILayer,
    )

    meta = ClaimsMetaData(
        claim_id="C1", currency="GBP", contract_limit=1_000_000.0,
        contract_deductible=0.0, claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=date(2020, 6, 1),
    )
    dev_hist = ClaimDevelopmentHistory(
        development_months=[12],
        cumulative_dev_paid=[50_000.0],
        cumulative_dev_incurred=[80_000.0],
    )
    claims = Claims([Claim(meta, dev_hist)])
    exp_meta = ExposureMetaData(
        exposure_id="E1", exposure_name="2020",
        exposure_period_start=date(2020, 1, 1), exposure_period_end=date(2020, 12, 31),
        currency="GBP", exposure_type=ExposureBasis.EARNED,
    )
    exposures = Exposures([Exposure(exp_meta, ExposureValues(1_000_000.0, 0.0, 1_000_000.0))])
    layer = RILayer(
        layer_id=1, layer_name="test", layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=0.0, occurrence_limit=1_000_000.0,
        aggregate_attachment=0.0, aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"], subject_lob_exposure_amounts=[1_000_000.0],
        full_subject_premium=100_000.0, written_line=1.0, signed_line=1.0,
        number_of_reinstatements=1, reinstatement_cost={1: 1.0},
    )
    contract_meta = RIContractMetadata(
        contract_id="C1", contract_description="Test", cedent_name="Test",
        trigger_basis=ClaimTriggerBasis.LOD,
        indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0, inception_date=date(2021, 1, 1),
        expiration_date=date(2021, 12, 31), fx_rates={"GBP": 1.0},
    )
    contract = RIContract(contract_meta_data=contract_meta, layers=[layer])
    model_data = ExperienceModelData(
        claims=claims, exposures=exposures, ri_contract=contract,
        exposure_trend_factors={yr: 1.0 for yr in range(2010, 2022)},
        claim_trend_factors={yr: 1.0 for yr in range(2010, 2022)},
    )

    fitter = FrequencyFit(distributions=[FrequencyDistribution.POISSON], data=model_data)
    results = fitter.fit()
    assert "poisson" in results
    assert results["poisson"]["lambda_"] > 0
