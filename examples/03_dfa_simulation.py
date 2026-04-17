"""Example 3 — Full DFA pricing simulation.

Demonstrates:
- Fitting frequency (Poisson) and severity (Lognormal) distributions
- Running a Monte Carlo simulation with 50,000 trials
- Computing loss cost, TVaR capital, and required premium per layer
- Sensitivity analysis: varying cost of capital and expense loading
- Saving results to JSON

Run with:
    uv run python examples/03_dfa_simulation.py
"""

import json
from datetime import date

from pyre import (
    AggregateFeatures,
    BurnCostModel,
    Claim,
    ClaimDevelopmentHistory,
    Claims,
    ClaimsMetaData,
    ClaimTriggerBasis,
    ClaimYearType,
    ContractType,
    Exposure,
    ExposureBasis,
    ExperienceModelData,
    ExposureMetaData,
    Exposures,
    ExposureValues,
    FrequencyDistribution,
    IndexationClauseType,
    ModellingAssumptions,
    ProjectionMethods,
    RIContract,
    RIContractMetadata,
    RILayer,
    Selections,
    SeverityDistribution,
    Simulation,
)
from pyre.models.experience.frequency_severity import FrequencyFit, SeverityFit

# ---------------------------------------------------------------------------
# Contract structure: two XOL layers
# ---------------------------------------------------------------------------

ri_meta = RIContractMetadata(
    contract_id="DFA-2024-001",
    contract_description="Casualty XOL DFA Example",
    cedent_name="Example Cedent",
    trigger_basis=ClaimTriggerBasis.LOD,
    indexation_clause=IndexationClauseType.FIC,
    indexation_margin=0.0,
    inception_date=date(2024, 1, 1),
    expiration_date=date(2024, 12, 31),
    fx_rates={"USD": 1.0},
)

layer_1 = RILayer(
    layer_id=1, layer_name="5 xs 5", layer_type=ContractType.EXCESS_OF_LOSS,
    occurrence_attachment=5_000.0, occurrence_limit=5_000.0,
    aggregate_attachment=0.0, aggregate_limit=float("inf"),
    subject_lines_of_business=["Casualty"],
    subject_lob_exposure_amounts=[100_000_000.0],
    full_subject_premium=25_000.0,   # market premium ~2x simulated loss cost
    written_line=1.0, signed_line=1.0,
    number_of_reinstatements=2, reinstatement_cost={1: 1.0, 2: 1.0},
)

layer_2 = RILayer(
    layer_id=2, layer_name="10 xs 10", layer_type=ContractType.EXCESS_OF_LOSS,
    occurrence_attachment=10_000.0, occurrence_limit=10_000.0,
    aggregate_attachment=0.0, aggregate_limit=float("inf"),
    subject_lines_of_business=["Casualty"],
    subject_lob_exposure_amounts=[100_000_000.0],
    full_subject_premium=12_000.0,   # market premium ~5x simulated loss cost
    written_line=1.0, signed_line=1.0,
    number_of_reinstatements=1, reinstatement_cost={1: 1.0},
)

ri_contract = RIContract(contract_meta_data=ri_meta, layers=[layer_1, layer_2])

# ---------------------------------------------------------------------------
# Historical claims — 5 years of ground-up losses ($000s)
# ---------------------------------------------------------------------------

raw = [
    ("CL19-01", date(2019, 3, 1), [12, 24, 36, 48, 60], [200, 800, 2_500, 5_500, 6_200], [8_000, 7_200, 7_000, 6_500, 6_200]),
    ("CL19-02", date(2019, 8, 1), [12, 24, 36, 48, 60], [0, 500, 2_000, 4_800, 5_400], [9_000, 7_500, 6_500, 5_600, 5_400]),
    ("CL19-03", date(2019, 11, 1), [12, 24, 36, 48, 60], [100, 700, 1_800, 3_800, 4_200], [7_500, 6_000, 5_200, 4_400, 4_200]),
    ("CL20-01", date(2020, 2, 1), [12, 24, 36, 48], [300, 1_200, 3_500, 7_000], [11_000, 9_500, 8_500, 7_200]),
    ("CL20-02", date(2020, 6, 1), [12, 24, 36, 48], [0, 400, 1_900, 4_500], [8_500, 7_200, 6_000, 4_700]),
    ("CL20-03", date(2020, 9, 1), [12, 24, 36, 48], [500, 2_000, 5_500, 9_000], [14_000, 12_000, 11_000, 9_200]),
    ("CL21-01", date(2021, 1, 1), [12, 24, 36], [0, 600, 2_200], [9_000, 7_800, 6_800]),
    ("CL21-02", date(2021, 5, 1), [12, 24, 36], [400, 1_500, 4_000], [12_000, 10_200, 8_800]),
    ("CL21-03", date(2021, 9, 1), [12, 24, 36], [0, 300, 1_500], [6_500, 5_500, 4_800]),
    ("CL22-01", date(2022, 2, 1), [12, 24], [0, 800], [10_000, 8_500]),
    ("CL22-02", date(2022, 7, 1), [12, 24], [600, 2_500], [13_500, 11_000]),
    ("CL23-01", date(2023, 3, 1), [12], [0], [9_500]),
    ("CL23-02", date(2023, 8, 1), [12], [500], [14_500]),
    ("CL23-03", date(2023, 11, 1), [12], [0], [7_000]),
]

claims_list = []
for cid, loss_dt, months, paid, incurred in raw:
    yr = loss_dt.year
    m = ClaimsMetaData(
        claim_id=cid, currency="USD",
        contract_limit=20_000.0, contract_deductible=0.0,
        claim_in_xs_of_deductible=False,
        claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=loss_dt,
        report_date=date(loss_dt.year, loss_dt.month, 1),
        line_of_business="Casualty",
    )
    d = ClaimDevelopmentHistory(
        development_months=months, cumulative_dev_paid=paid, cumulative_dev_incurred=incurred
    )
    claims_list.append(Claim(claims_meta_data=m, claims_development_history=d))

claims = Claims(claims_list)

# ---------------------------------------------------------------------------
# Exposures
# ---------------------------------------------------------------------------

exposure_list = []
for yr in range(2019, 2024):
    premium = 900_000.0 + (yr - 2019) * 25_000.0
    em = ExposureMetaData(
        exposure_id=f"EXP-{yr}", exposure_name=f"Casualty Portfolio {yr}",
        exposure_period_start=date(yr, 1, 1), exposure_period_end=date(yr, 12, 31),
        currency="USD", exposure_type=ExposureBasis.WRITTEN,
        line_of_business="Casualty",
    )
    ev = ExposureValues(exposure_value=premium, attachment_point=0.0, limit=20_000.0)
    exposure_list.append(Exposure(exposure_meta=em, exposure_values=ev))

exposures = Exposures(exposure_list)

# ---------------------------------------------------------------------------
# ExperienceModelData with 4% claims trend, 2% exposure trend
# ---------------------------------------------------------------------------

claim_trend = {yr: 1.04 for yr in range(2014, 2025)}
exposure_trend = {yr: 1.02 for yr in range(2014, 2025)}

model_data = ExperienceModelData(
    claims=claims, exposures=exposures, ri_contract=ri_contract,
    exposure_trend_factors=exposure_trend, claim_trend_factors=claim_trend,
)

# ---------------------------------------------------------------------------
# Fit frequency and severity distributions
# ---------------------------------------------------------------------------

freq_fit = FrequencyFit(
    distributions=[FrequencyDistribution.POISSON],
    data=model_data,
)

sev_fit = SeverityFit(
    distributions=[SeverityDistribution.LOGNORMAL],
    data=model_data,
    ibner_dev_pattern={yr: 1.10 for yr in range(2019, 2024)},
)

print("=" * 65)
print("FITTED DISTRIBUTIONS")
print("=" * 65)
freq_params = freq_fit.fit()
sev_params = sev_fit.fit()
print(f"  Frequency — Poisson:   lambda = {freq_params['poisson']['lambda_']:.3f} claims/year")
ln = sev_params["lognormal"]
print(f"  Severity  — Lognormal: mu = {ln['mu']:.4f}, sigma = {ln['sigma']:.4f}")
import math
mean_sev = math.exp(ln["mu"] + 0.5 * ln["sigma"] ** 2)
print(f"  Implied mean severity: ${mean_sev:,.0f}")

# ---------------------------------------------------------------------------
# Base case simulation: CoC = 8%, TVaR 99.5%, 50k trials
# ---------------------------------------------------------------------------

assumptions = ModellingAssumptions(
    cost_of_capital=0.08,
    required_rate_of_return=0.12,
    capital_confidence_level=0.995,
    use_tvar=True,
    investment_yield=0.04,
    acquisition_cost_ratio=0.05,
    brokerage_cost_ratio=0.025,
)

print("\n" + "=" * 65)
print("BASE CASE SIMULATION (50,000 trials, TVaR 99.5%, CoC 8%)")
print("=" * 65)

sim = Simulation(
    frequency_fit=freq_fit,
    severity_fit=sev_fit,
    ri_contract=ri_contract,
    assumptions=assumptions,
    n_simulations=50_000,
    random_seed=42,
)
sim.run()

results = sim.output()

print(f"\n  {'Layer':<20} {'Loss Cost':>12} {'Req. Capital':>14} {'Req. Premium':>14}")
print(f"  {'-'*20} {'-'*12} {'-'*14} {'-'*14}")
for layer in ri_contract.layers:
    lid = layer.layer_id
    lc = results.loss_cost_by_layer[lid]
    rc = results.required_capital_by_layer[lid]
    rp = results.required_premium_by_layer[lid]
    print(f"  {layer.layer_name:<20} {lc:>12,.0f} {rc:>14,.0f} {rp:>14,.0f}")
print(f"  {'TOTAL PROGRAMME':<20} {'':>12} {'':>14} {results.required_premium_programme:>14,.0f}")

# ---------------------------------------------------------------------------
# Sensitivity: cost of capital
# ---------------------------------------------------------------------------

print("\n" + "=" * 65)
print("SENSITIVITY — COST OF CAPITAL (Layer 1: 5 xs 5)")
print("=" * 65)
print(f"  {'CoC':>6} {'Loss Cost':>12} {'Req. Capital':>14} {'Req. Premium':>14}")
print(f"  {'-'*6} {'-'*12} {'-'*14} {'-'*14}")

for coc in [0.04, 0.06, 0.08, 0.10, 0.12]:
    sens_assumptions = ModellingAssumptions(
        cost_of_capital=coc,
        required_rate_of_return=0.12,
        capital_confidence_level=0.995,
        use_tvar=True,
        investment_yield=0.04,
        acquisition_cost_ratio=0.05,
        brokerage_cost_ratio=0.025,
    )
    sens_sim = Simulation(
        frequency_fit=freq_fit, severity_fit=sev_fit,
        ri_contract=ri_contract, assumptions=sens_assumptions,
        n_simulations=20_000, random_seed=42,
    )
    sens_sim.run()
    sr = sens_sim.output()
    lc1 = sr.loss_cost_by_layer[1]
    rc1 = sr.required_capital_by_layer[1]
    rp1 = sr.required_premium_by_layer[1]
    print(f"  {coc:>5.0%} {lc1:>12,.0f} {rc1:>14,.0f} {rp1:>14,.0f}")

# ---------------------------------------------------------------------------
# Save base case results to JSON
# ---------------------------------------------------------------------------

output_path = "examples/dfa_results.json"
sim.save(output_path)
print(f"\nBase case results saved to: {output_path}")

with open(output_path) as f:
    saved = json.load(f)
print(f"  Required premium programme: ${saved['required_premium_programme']:,.0f}")
