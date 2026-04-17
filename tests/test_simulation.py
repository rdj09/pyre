from datetime import date

import pytest

from pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData
from pyre.enums import (
    ClaimTriggerBasis,
    ClaimYearType,
    ContractType,
    ExposureBasis,
    FrequencyDistribution,
    SeverityDistribution,
)
from pyre.exposures.exposures import Exposure, ExposureMetaData, Exposures, ExposureValues
from pyre.models.aggregate.aggregate_features import ModellingAssumptions
from pyre.models.aggregate.simulation_engine import Simulation, SimulationResults
from pyre.models.experience.experience_preparer import ExperienceModelData
from pyre.models.experience.frequency_severity import FrequencyFit, SeverityFit
from pyre.treaty.contracts import (
    IndexationClauseType,
    RIContract,
    RIContractMetadata,
    RILayer,
)


def _make_experience_data() -> ExperienceModelData:
    meta = ClaimsMetaData(
        claim_id="C1", currency="GBP", contract_limit=1_000_000.0,
        contract_deductible=0.0, claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=date(2020, 6, 1),
    )
    dev_hist = ClaimDevelopmentHistory(
        development_months=[12],
        cumulative_dev_paid=[500_000.0],
        cumulative_dev_incurred=[800_000.0],
    )
    meta2 = ClaimsMetaData(
        claim_id="C2", currency="GBP", contract_limit=1_000_000.0,
        contract_deductible=0.0, claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=date(2020, 9, 1),
    )
    dev_hist2 = ClaimDevelopmentHistory(
        development_months=[12],
        cumulative_dev_paid=[300_000.0],
        cumulative_dev_incurred=[400_000.0],
    )
    claims = Claims([Claim(meta, dev_hist), Claim(meta2, dev_hist2)])
    exp_meta = ExposureMetaData(
        exposure_id="E1", exposure_name="2020",
        exposure_period_start=date(2020, 1, 1), exposure_period_end=date(2020, 12, 31),
        currency="GBP", exposure_type=ExposureBasis.EARNED,
    )
    exposures = Exposures([Exposure(exp_meta, ExposureValues(1_000_000.0, 0.0, 1_000_000.0))])
    layer = RILayer(
        layer_id=1, layer_name="1m xs 0", layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=0.0, occurrence_limit=1_000_000.0,
        aggregate_attachment=0.0, aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"], subject_lob_exposure_amounts=[1_000_000.0],
        full_subject_premium=100_000.0, written_line=1.0, signed_line=1.0,
        number_of_reinstatements=1, reinstatement_cost={1: 1.0},
    )
    contract_meta = RIContractMetadata(
        contract_id="C1", contract_description="Test", cedent_name="Cedent",
        trigger_basis=ClaimTriggerBasis.LOD, indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0, inception_date=date(2021, 1, 1), expiration_date=date(2021, 12, 31),
        fx_rates={"GBP": 1.0},
    )
    contract = RIContract(contract_meta_data=contract_meta, layers=[layer])
    return ExperienceModelData(
        claims=claims, exposures=exposures, ri_contract=contract,
        exposure_trend_factors={yr: 1.0 for yr in range(2010, 2022)},
        claim_trend_factors={yr: 1.0 for yr in range(2010, 2022)},
    )


def _make_simulation(n: int = 1_000) -> Simulation:
    data = _make_experience_data()
    freq_fit = FrequencyFit(
        distributions=[FrequencyDistribution.POISSON], data=data,
    )
    sev_fit = SeverityFit(
        distributions=[SeverityDistribution.LOGNORMAL], data=data,
        ibner_dev_pattern={2020: 1.0},
    )
    assumptions = ModellingAssumptions(
        cost_of_capital=0.08,
        required_rate_of_return=0.10,
        capital_confidence_level=0.995,
        use_tvar=True,
    )
    return Simulation(
        frequency_fit=freq_fit,
        severity_fit=sev_fit,
        ri_contract=data.ri_contract,
        assumptions=assumptions,
        n_simulations=n,
        random_seed=42,
    )


def test_simulation_run_produces_results():
    sim = _make_simulation()
    sim.run()
    results = sim.output()
    assert isinstance(results, SimulationResults)


def test_simulation_loss_cost_is_positive():
    sim = _make_simulation()
    sim.run()
    lc = sim.loss_cost()
    assert isinstance(lc, dict)
    assert 1 in lc
    assert lc[1] >= 0.0


def test_simulation_required_capital_is_positive():
    sim = _make_simulation()
    sim.run()
    rc = sim.required_capital()
    assert isinstance(rc, dict)
    assert 1 in rc
    assert rc[1] >= 0.0


def test_simulation_required_premium_layer_is_positive():
    sim = _make_simulation()
    sim.run()
    rp = sim.required_premium_layer()
    assert isinstance(rp, dict)
    assert 1 in rp
    assert rp[1] > 0.0


def test_simulation_required_premium_programme_equals_sum_of_layers():
    sim = _make_simulation()
    sim.run()
    layer_premiums = sim.required_premium_layer()
    programme_premium = sim.required_premium_programme()
    assert programme_premium == pytest.approx(sum(layer_premiums.values()))


def test_simulation_results_serialise_to_json(tmp_path):
    sim = _make_simulation()
    sim.run()
    out_path = tmp_path / "results.json"
    sim.save(str(out_path))
    assert out_path.exists()
    import json
    with open(out_path) as f:
        data = json.load(f)
    assert "required_premium_programme" in data
    assert "n_simulations" in data


def test_simulation_deterministic_with_seed():
    sim1 = _make_simulation(n=500)
    sim2 = _make_simulation(n=500)
    sim1.run()
    sim2.run()
    lc1 = sim1.loss_cost()
    lc2 = sim2.loss_cost()
    assert lc1[1] == pytest.approx(lc2[1])
