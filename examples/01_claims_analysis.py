"""Example 1 — Claims analysis, development triangles, and IBNER extraction.

Demonstrates:
- Building a Claims collection from individual Claim objects
- Constructing a development Triangle from claims data
- Fitting a development curve to age-to-age factors
- Extracting IBNER development patterns

Run with:
    uv run python examples/01_claims_analysis.py
"""

from datetime import date

from pyre import (
    Claim,
    ClaimDevelopmentHistory,
    Claims,
    ClaimsMetaData,
    ClaimYearType,
    CurveType,
    IBNERPatternExtractor,
    Triangle,
)

# ---------------------------------------------------------------------------
# Build a realistic claims dataset (5 accident years, 3 claims per year)
# ---------------------------------------------------------------------------

raw_claims = [
    # (claim_id, loss_date, report_date, dev_months, cumul_paid, cumul_incurred)
    ("CL2019-01", date(2019, 3, 15), date(2019, 4, 1),
     [12, 24, 36, 48, 60], [0, 8_000, 20_000, 35_000, 42_000], [60_000, 55_000, 48_000, 44_000, 42_000]),
    ("CL2019-02", date(2019, 7, 20), date(2019, 8, 5),
     [12, 24, 36, 48, 60], [5_000, 18_000, 30_000, 38_000, 40_000], [80_000, 70_000, 55_000, 42_000, 40_000]),
    ("CL2019-03", date(2019, 11, 10), date(2019, 12, 1),
     [12, 24, 36, 48, 60], [0, 2_000, 10_000, 22_000, 28_000], [40_000, 35_000, 30_000, 28_500, 28_000]),

    ("CL2020-01", date(2020, 2, 5), date(2020, 3, 1),
     [12, 24, 36, 48], [0, 15_000, 40_000, 65_000], [100_000, 85_000, 72_000, 67_000]),
    ("CL2020-02", date(2020, 6, 15), date(2020, 7, 1),
     [12, 24, 36, 48], [2_000, 20_000, 50_000, 75_000], [120_000, 100_000, 82_000, 77_000]),
    ("CL2020-03", date(2020, 9, 25), date(2020, 10, 10),
     [12, 24, 36, 48], [0, 5_000, 18_000, 30_000], [50_000, 42_000, 35_000, 31_000]),

    ("CL2021-01", date(2021, 1, 20), date(2021, 2, 15),
     [12, 24, 36], [0, 12_000, 35_000], [90_000, 75_000, 62_000]),
    ("CL2021-02", date(2021, 5, 10), date(2021, 6, 1),
     [12, 24, 36], [0, 8_000, 25_000], [70_000, 58_000, 48_000]),
    ("CL2021-03", date(2021, 10, 5), date(2021, 11, 1),
     [12, 24, 36], [3_000, 22_000, 45_000], [110_000, 90_000, 75_000]),

    ("CL2022-01", date(2022, 3, 10), date(2022, 4, 1),
     [12, 24], [0, 10_000], [80_000, 65_000]),
    ("CL2022-02", date(2022, 8, 18), date(2022, 9, 5),
     [12, 24], [0, 5_000], [55_000, 45_000]),
    ("CL2022-03", date(2022, 11, 22), date(2022, 12, 10),
     [12, 24], [1_000, 15_000], [95_000, 78_000]),

    ("CL2023-01", date(2023, 2, 14), date(2023, 3, 1),
     [12], [0], [70_000]),
    ("CL2023-02", date(2023, 7, 7), date(2023, 8, 1),
     [12], [0], [50_000]),
    ("CL2023-03", date(2023, 12, 1), date(2024, 1, 5),
     [12], [2_000], [85_000]),
]

claims_list = []
for cid, loss_dt, report_dt, months, paid, incurred in raw_claims:
    meta = ClaimsMetaData(
        claim_id=cid,
        currency="USD",
        contract_limit=500_000.0,
        contract_deductible=0.0,
        claim_in_xs_of_deductible=False,
        claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=loss_dt,
        report_date=report_dt,
        line_of_business="Property",
    )
    dev_hist = ClaimDevelopmentHistory(
        development_months=months,
        cumulative_dev_paid=paid,
        cumulative_dev_incurred=incurred,
    )
    claims_list.append(Claim(claims_meta_data=meta, claims_development_history=dev_hist))

claims = Claims(claims_list)

print("=" * 60)
print("CLAIMS SUMMARY")
print("=" * 60)
print(f"Total claims:          {len(claims.claims)}")
print(f"Accident years:        {sorted(set(c.claims_meta_data.modelling_year for c in claims.claims))}")
print(f"Total latest incurred: ${sum(c.capped_claim_development_history.latest_incurred for c in claims.claims):,.0f}")
print(f"Total latest paid:     ${sum(c.capped_claim_development_history.latest_paid for c in claims.claims):,.0f}")

# ---------------------------------------------------------------------------
# Build development triangle
# ---------------------------------------------------------------------------

triangle = Triangle.from_claims(claims, value_type="incurred")

print("\n" + "=" * 60)
print("INCURRED DEVELOPMENT TRIANGLE (cumulative, $000s)")
print("=" * 60)
header = "Year  | " + " | ".join(f"{m:>6}" for m in triangle.dev_periods)
print(header)
print("-" * len(header))
for oy in sorted(triangle.origin_years):
    row = triangle.triangle.get(oy, {})
    vals = " | ".join(
        f"{row[m]:>6,.0f}" if m in row else " " * 6
        for m in triangle.dev_periods
    )
    print(f"{oy}  | {vals}")

# ---------------------------------------------------------------------------
# Age-to-age factors (volume-weighted average across all years)
# ---------------------------------------------------------------------------

avg_factors = triangle.get_average_age_to_age_factors(method="volume")
print("\n" + "=" * 60)
print("AGE-TO-AGE DEVELOPMENT FACTORS (volume-weighted average)")
print("=" * 60)
dev_sorted = sorted(avg_factors.keys())
for i, from_m in enumerate(dev_sorted):
    to_m = triangle.dev_periods[triangle.dev_periods.index(from_m) + 1]
    print(f"  {from_m:>3} -> {to_m:<3}  {avg_factors[from_m]:.4f}")

# ---------------------------------------------------------------------------
# Fit an exponential development curve to the paid triangle
# Development curves are fitted to paid data (monotonically increasing)
# ---------------------------------------------------------------------------

paid_triangle = Triangle.from_claims(claims, value_type="paid")

selected_pattern = paid_triangle.get_selected_development_pattern(
    curve_type=CurveType.EXPONENTIAL,
    tail_factor=1.05,
)
print("\n" + "=" * 60)
print("SELECTED DEVELOPMENT PATTERN (paid, cumulative-to-ultimate)")
print("  Curve: Exponential  |  Tail: 1.05x")
print("=" * 60)
for month, factor in sorted(selected_pattern.items()):
    print(f"  Month {month:>3}:  {factor:.4f}x to ultimate")

# ---------------------------------------------------------------------------
# IBNER pattern extraction (where enough data exists)
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("IBNER PATTERN EXTRACTION")
print("=" * 60)
try:
    extractor = IBNERPatternExtractor(triangle)
    ibner = extractor.get_IBNER_pattern()
    for oy, pattern in sorted(ibner.items()):
        print(f"  {oy}: {pattern}")
except Exception as exc:
    print(f"  IBNER requires a complete square triangle — {exc}")
