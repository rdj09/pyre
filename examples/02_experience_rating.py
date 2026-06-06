"""Example 2 — Experience rating with burn cost projection.

Demonstrates:
- Building ExperienceModelData from claims, exposures, and an RI contract
- Applying claim trend and exposure trend factors
- Burning cost calculation using multiple projection methods (Chain Ladder, BF, Cape Cod)
- Comparing weighted average burn costs across layers

Run with:
    uv run python examples/02_experience_rating.py
"""

from datetime import date

from pyre import (
    BurnCostModel,
    Claim,
    ClaimDevelopmentHistory,
    Claims,
    ClaimsMetaData,
    ClaimTriggerBasis,
    ClaimYearType,
    ContractType,
    ExperienceModelData,
    Exposure,
    ExposureBasis,
    ExposureMetaData,
    Exposures,
    ExposureValues,
    IndexationClauseType,
    ProjectionMethods,
    RIContract,
    RIContractMetadata,
    RILayer,
)

# ---------------------------------------------------------------------------
# Reinsurance contract: 3 xs 2 and 5 xs 5 (£000s)
# ---------------------------------------------------------------------------

meta = RIContractMetadata(
    contract_id="XOL-2024-001",
    contract_description="Property XOL Programme 2024",
    cedent_name="ACME Insurance Ltd",
    trigger_basis=ClaimTriggerBasis.LOD,
    indexation_clause=IndexationClauseType.FIC,
    indexation_margin=0.0,
    inception_date=date(2024, 1, 1),
    expiration_date=date(2024, 12, 31),
    fx_rates={"GBP": 1.0},
)

layer_1 = RILayer(
    layer_id=1,
    layer_name="Layer 1: 3 xs 2",
    layer_type=ContractType.EXCESS_OF_LOSS,
    occurrence_attachment=2_000.0,
    occurrence_limit=3_000.0,
    aggregate_attachment=0.0,
    aggregate_limit=float("inf"),
    subject_lines_of_business=["Property"],
    subject_lob_exposure_amounts=[50_000_000.0],
    full_subject_premium=500_000.0,
    written_line=1.0,
    signed_line=1.0,
    number_of_reinstatements=1,
    reinstatement_cost={1: 1.0},
)

layer_2 = RILayer(
    layer_id=2,
    layer_name="Layer 2: 5 xs 5",
    layer_type=ContractType.EXCESS_OF_LOSS,
    occurrence_attachment=5_000.0,
    occurrence_limit=5_000.0,
    aggregate_attachment=0.0,
    aggregate_limit=float("inf"),
    subject_lines_of_business=["Property"],
    subject_lob_exposure_amounts=[50_000_000.0],
    full_subject_premium=500_000.0,
    written_line=1.0,
    signed_line=1.0,
    number_of_reinstatements=1,
    reinstatement_cost={1: 1.0},
)

ri_contract = RIContract(contract_meta_data=meta, layers=[layer_1, layer_2])

# ---------------------------------------------------------------------------
# Historical claims (5 accident years, £000s)
# ---------------------------------------------------------------------------

claims_data = [
    # (id, loss_date, report_date, dev_months, cum_paid, cum_incurred)
    ("CL19-01", date(2019, 4, 1), date(2019, 5, 1),
     [12, 24, 36, 48, 60], [0, 500, 1_500, 3_000, 3_500], [5_000, 4_500, 4_000, 3_600, 3_500]),
    ("CL19-02", date(2019, 9, 1), date(2019, 10, 1),
     [12, 24, 36, 48, 60], [200, 1_000, 2_500, 4_000, 4_500], [8_000, 7_000, 6_000, 4_800, 4_500]),
    ("CL20-01", date(2020, 3, 1), date(2020, 4, 1),
     [12, 24, 36, 48], [0, 800, 2_200, 3_800], [6_500, 5_800, 5_000, 4_000]),
    ("CL20-02", date(2020, 8, 1), date(2020, 9, 1),
     [12, 24, 36, 48], [500, 1_800, 3_500, 5_200], [10_000, 8_500, 7_000, 5_400]),
    ("CL21-01", date(2021, 2, 1), date(2021, 3, 1),
     [12, 24, 36], [0, 600, 2_000], [7_000, 6_000, 5_200]),
    ("CL21-02", date(2021, 7, 1), date(2021, 8, 1),
     [12, 24, 36], [300, 1_200, 3_000], [9_000, 7_800, 6_500]),
    ("CL22-01", date(2022, 1, 1), date(2022, 2, 1),
     [12, 24], [0, 700], [7_500, 6_200]),
    ("CL22-02", date(2022, 6, 1), date(2022, 7, 1),
     [12, 24], [400, 1_500], [11_000, 9_000]),
    ("CL23-01", date(2023, 3, 1), date(2023, 4, 1),
     [12], [0], [8_000]),
    ("CL23-02", date(2023, 9, 1), date(2023, 10, 1),
     [12], [600], [12_000]),
]

claims_list = []
for cid, loss_dt, rep_dt, months, paid, incurred in claims_data:
    m = ClaimsMetaData(
        claim_id=cid, currency="GBP",
        contract_limit=10_000.0, contract_deductible=0.0,
        claim_in_xs_of_deductible=False,
        claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=loss_dt, report_date=rep_dt,
        line_of_business="Property",
    )
    d = ClaimDevelopmentHistory(
        development_months=months, cumulative_dev_paid=paid, cumulative_dev_incurred=incurred
    )
    claims_list.append(Claim(claims_meta_data=m, claims_development_history=d))

claims = Claims(claims_list)

# ---------------------------------------------------------------------------
# Historical exposures (5 years of written premium, £000s)
# ---------------------------------------------------------------------------

exposure_list = []
for yr in range(2019, 2024):
    exp_val = 45_000.0 + (yr - 2019) * 2_000.0  # growing book
    em = ExposureMetaData(
        exposure_id=f"EXP-{yr}",
        exposure_name=f"Property Portfolio {yr}",
        exposure_period_start=date(yr, 1, 1),
        exposure_period_end=date(yr, 12, 31),
        currency="GBP",
        exposure_type=ExposureBasis.WRITTEN,
        line_of_business="Property",
    )
    ev = ExposureValues(exposure_value=exp_val, attachment_point=0.0, limit=10_000.0)
    exposure_list.append(Exposure(exposure_meta=em, exposure_values=ev))

exposures = Exposures(exposure_list)

# ---------------------------------------------------------------------------
# Trend factors: 5% p.a. claims inflation, 3% p.a. exposure growth
# ---------------------------------------------------------------------------

claim_trend = {yr: 1.05 for yr in range(2014, 2025)}
exposure_trend = {yr: 1.03 for yr in range(2014, 2025)}

model_data = ExperienceModelData(
    claims=claims,
    exposures=exposures,
    ri_contract=ri_contract,
    exposure_trend_factors=exposure_trend,
    claim_trend_factors=claim_trend,
)

# ---------------------------------------------------------------------------
# Inspect aggregate data
# ---------------------------------------------------------------------------

print("=" * 65)
print("EXPERIENCE MODEL — AGGREGATE CLAIMS BY LAYER & YEAR (trended)")
print("=" * 65)
agg = model_data.aggregate_subject_contract_claims
for lid in sorted(agg):
    print(f"\n  Layer {lid}:")
    print(f"  {'Year':<6} {'Latest Incurred':>16} {'Claim Count':>12}")
    print(f"  {'-'*6} {'-'*16} {'-'*12}")
    for yr, stats in sorted(agg[lid].items()):
        print(f"  {yr:<6} {stats['latest_incurred']:>16,.1f} {stats['total_count']:>12}")

print("\n" + "=" * 65)
print("AGGREGATE TRENDED EXPOSURES BY YEAR")
print("=" * 65)
print(f"  {'Year':<6} {'Earned':>14} {'Written':>14}")
print(f"  {'-'*6} {'-'*14} {'-'*14}")
for yr, vals in sorted(model_data.aggregate_exposures.items()):
    print(f"  {yr:<6} {vals['earned']:>14,.1f} {vals['written']:>14,.1f}")

# ---------------------------------------------------------------------------
# Burn cost models: one per layer, using different projection methods
# ---------------------------------------------------------------------------

print("\n" + "=" * 65)
print("BURN COST ANALYSIS")
print("=" * 65)

modelling_years = list(range(2019, 2024))

for lid in [1, 2]:
    print(f"\n  Layer {lid}:")

    # Chain Ladder (development to ultimate)
    dev_pattern = {yr: 1.15 - (yr - 2019) * 0.03 for yr in modelling_years}  # illustrative
    bc_cl = BurnCostModel(
        model_data=model_data,
        layer_id=lid,
        projection_methods={yr: ProjectionMethods.CHAINLADDER for yr in modelling_years},
        development_pattern=dev_pattern,
    )
    bc_cl_results = bc_cl.calculate_burn_cost()

    # Bornhuetter-Ferguson (a priori = 80% loss ratio)
    a_priori = {yr: 0.80 for yr in modelling_years}
    bc_bf = BurnCostModel(
        model_data=model_data,
        layer_id=lid,
        projection_methods={yr: ProjectionMethods.BF for yr in modelling_years},
        development_pattern=dev_pattern,
        a_priori_assumption=a_priori,
    )
    bc_bf_results = bc_bf.calculate_burn_cost()

    # Cape Cod
    bc_cc = BurnCostModel(
        model_data=model_data,
        layer_id=lid,
        projection_methods={yr: ProjectionMethods.SIMPLE_CAPE_COD for yr in modelling_years},
        development_pattern=dev_pattern,
    )
    bc_cc_results = bc_cc.calculate_burn_cost()

    print(f"  {'Year':<6} {'Chain Ladder':>14} {'B-F':>14} {'Cape Cod':>14}")
    print(f"  {'-'*6} {'-'*14} {'-'*14} {'-'*14}")
    for yr in modelling_years:
        cl_v = bc_cl_results.get(yr, 0.0)
        bf_v = bc_bf_results.get(yr, 0.0)
        cc_v = bc_cc_results.get(yr, 0.0)
        print(f"  {yr:<6} {cl_v:>14.4f} {bf_v:>14.4f} {cc_v:>14.4f}")

    # Simple weighted average (equal weights)
    if bc_cl_results:
        avg = sum(bc_cl_results.values()) / len(bc_cl_results)
        print(f"\n  Weighted avg burn cost (CL, equal weights): {avg:.4f}")
        print(f"  Implied rate on line:                       {avg * 100:.2f}%")
