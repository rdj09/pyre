"""Example 4 — Exposure rating using MBBEFD and mixed exponential curves.

Demonstrates:
- Building an exposure portfolio from individual risks
- Calculating exposure shares per treaty layer using the MBBEFD curve
- Comparing Swiss Re c-value presets (personal vs commercial vs industrial)
- Computing exposure rates and ILF-adjusted rates per layer

Run with:
    uv run python examples/04_exposure_rating.py
"""

from datetime import date

from pyre import (
    ContractType,
    Exposure,
    ExposureBasis,
    ExposureCurveType,
    ExposureMetaData,
    ExposureModel,
    Exposures,
    ExposureValues,
    IndexationClauseType,
    ClaimTriggerBasis,
    RIContract,
    RIContractMetadata,
    RILayer,
    SwissReCValues,
)

# ---------------------------------------------------------------------------
# Reinsurance contract: 5m xs 5m property XOL
# ---------------------------------------------------------------------------

ri_meta = RIContractMetadata(
    contract_id="EXP-2024-001",
    contract_description="Property Exposure Rating Example",
    cedent_name="Example Cedent",
    trigger_basis=ClaimTriggerBasis.LOD,
    indexation_clause=IndexationClauseType.FIC,
    indexation_margin=0.0,
    inception_date=date(2024, 1, 1),
    expiration_date=date(2024, 12, 31),
    fx_rates={"USD": 1.0},
)

layer_1 = RILayer(
    layer_id=1, layer_name="5m xs 5m", layer_type=ContractType.EXCESS_OF_LOSS,
    occurrence_attachment=5_000_000.0, occurrence_limit=5_000_000.0,
    aggregate_attachment=0.0, aggregate_limit=float("inf"),
    subject_lines_of_business=["Property"],
    subject_lob_exposure_amounts=[500_000_000.0],
    full_subject_premium=5_000_000.0,
    written_line=1.0, signed_line=1.0,
    number_of_reinstatements=1, reinstatement_cost={1: 1.0},
)

layer_2 = RILayer(
    layer_id=2, layer_name="10m xs 10m", layer_type=ContractType.EXCESS_OF_LOSS,
    occurrence_attachment=10_000_000.0, occurrence_limit=10_000_000.0,
    aggregate_attachment=0.0, aggregate_limit=float("inf"),
    subject_lines_of_business=["Property"],
    subject_lob_exposure_amounts=[500_000_000.0],
    full_subject_premium=5_000_000.0,
    written_line=1.0, signed_line=1.0,
    number_of_reinstatements=1, reinstatement_cost={1: 1.0},
)

ri_contract = RIContract(contract_meta_data=ri_meta, layers=[layer_1, layer_2])

# ---------------------------------------------------------------------------
# Exposure portfolio: 10 property risks with varying TIVs, attachments, limits
# ---------------------------------------------------------------------------

portfolio = [
    # (id, name, TIV, attachment, limit, start, end)
    ("RISK-001", "Warehouse A",      8_000_000,  0, 8_000_000,  date(2024, 1, 1), date(2024, 12, 31)),
    ("RISK-002", "Office Block B",  12_000_000,  0, 12_000_000, date(2024, 1, 1), date(2024, 12, 31)),
    ("RISK-003", "Factory C",       15_000_000,  500_000, 14_500_000, date(2024, 1, 1), date(2024, 12, 31)),
    ("RISK-004", "Retail Park D",   20_000_000,  0, 20_000_000, date(2024, 1, 1), date(2024, 12, 31)),
    ("RISK-005", "Hotel E",         25_000_000,  1_000_000, 24_000_000, date(2024, 1, 1), date(2024, 12, 31)),
    ("RISK-006", "Distribution F",   5_000_000,  0,  5_000_000, date(2024, 3, 1), date(2025, 2, 28)),
    ("RISK-007", "Cold Store G",     7_500_000,  0,  7_500_000, date(2024, 4, 1), date(2025, 3, 31)),
    ("RISK-008", "Shopping Centre H",30_000_000, 2_000_000, 28_000_000, date(2024, 1, 1), date(2024, 12, 31)),
    ("RISK-009", "Tower Block I",    18_000_000, 0, 18_000_000, date(2024, 6, 1), date(2025, 5, 31)),
    ("RISK-010", "Logistics Hub J",  22_000_000, 1_000_000, 21_000_000, date(2024, 1, 1), date(2024, 12, 31)),
]

exposure_list = []
for rid, rname, tiv, attach, limit, start, end in portfolio:
    em = ExposureMetaData(
        exposure_id=rid, exposure_name=rname,
        exposure_period_start=start, exposure_period_end=end,
        currency="USD", exposure_type=ExposureBasis.WRITTEN,
        line_of_business="Property",
    )
    ev = ExposureValues(exposure_value=float(tiv), attachment_point=float(attach), limit=float(limit))
    exposure_list.append(Exposure(exposure_meta=em, exposure_values=ev))

exposures = Exposures(exposure_list)

print("=" * 70)
print("EXPOSURE PORTFOLIO SUMMARY")
print("=" * 70)
print(f"  {'Risk ID':<12} {'Name':<22} {'TIV ($m)':>10} {'Limit ($m)':>12}")
print(f"  {'-'*12} {'-'*22} {'-'*10} {'-'*12}")
for rid, rname, tiv, _, limit, *_ in portfolio:
    print(f"  {rid:<12} {rname:<22} {tiv/1e6:>10.2f} {limit/1e6:>12.2f}")
total_tiv = sum(t for _, _, t, *_ in portfolio)
print(f"\n  Total TIV: ${total_tiv/1e6:.1f}m  |  Risks: {len(portfolio)}")

# ---------------------------------------------------------------------------
# Exposure rating with MBBEFD curve — compare Swiss Re c-value presets
# ---------------------------------------------------------------------------

analysis_date = date(2024, 7, 1)

print("\n" + "=" * 70)
print("EXPOSURE SHARES BY LAYER — MBBEFD CURVE")
print("  (proportion of each policy's exposure that attaches to each layer)")
print("=" * 70)

c_value_scenarios = [
    ("Personal Lines",          SwissReCValues.PERSONAL_LINES),
    ("Commercial (Medium)",     SwissReCValues.COMMERCIAL_LINES_MEDIUM),
    ("Industrial / Large Comm", SwissReCValues.INDUSTRIAL_LARGE_COMMERCIAL),
]

for label, c_preset in c_value_scenarios:
    curve_params = {"curve": c_preset}
    exp_model = ExposureModel(
        exposures=exposures,
        ri_contract=ri_contract,
        selected_curve=ExposureCurveType.MBBEFD,
        curve_parameters=curve_params,
    )
    rates = exp_model.calculate_exposure_rate(analysis_date)

    print(f"\n  Scenario: {label} (c = {c_preset.value})")
    print(f"  {'Layer':<15} {'Exposure Rate':>14}")
    print(f"  {'-'*15} {'-'*14}")
    for layer in ri_contract.layers:
        lid = layer.layer_id
        rate = rates.get(lid, 0.0)
        print(f"  {layer.layer_name:<15} {rate:>14.6f}")

# ---------------------------------------------------------------------------
# ILF-adjusted exposure rate (basic power ILF: ILF(L) = (L / base_limit)^0.5)
# ---------------------------------------------------------------------------

def power_ilf(limit: float, base_limit: float = 1_000_000.0, exponent: float = 0.5) -> float:
    """Basic power-law Increased Limit Factor."""
    return (limit / base_limit) ** exponent if limit > 0 else 0.0

print("\n" + "=" * 70)
print("ILF-ADJUSTED EXPOSURE RATE (power ILF, exponent=0.5, base=$1m)")
print("  MBBEFD Commercial (Medium), c = 3.0")
print("=" * 70)

curve_params_med = {"curve": SwissReCValues.COMMERCIAL_LINES_MEDIUM}
exp_model_med = ExposureModel(
    exposures=exposures,
    ri_contract=ri_contract,
    selected_curve=ExposureCurveType.MBBEFD,
    curve_parameters=curve_params_med,
)

plain_rates = exp_model_med.calculate_exposure_rate(analysis_date)
ilf_rates = exp_model_med.calculate_ilf_adjusted_rate(power_ilf, analysis_date)

print(f"\n  {'Layer':<15} {'Plain Rate':>14} {'ILF-Adj Rate':>14} {'ILF Uplift':>12}")
print(f"  {'-'*15} {'-'*14} {'-'*14} {'-'*12}")
for layer in ri_contract.layers:
    lid = layer.layer_id
    plain = plain_rates.get(lid, 0.0)
    ilf = ilf_rates.get(lid, 0.0)
    uplift = ilf / plain if plain > 0 else 0.0
    print(f"  {layer.layer_name:<15} {plain:>14.6f} {ilf:>14.6f} {uplift:>12.3f}x")

# ---------------------------------------------------------------------------
# Mixed exponential curve comparison (preset parameter set)
# ---------------------------------------------------------------------------

from pyre.models.exposure.exposure_curve_functions import MIXED_EXPO_CURVE_ONE  # noqa: E402

print("\n" + "=" * 70)
print("MIXED EXPONENTIAL CURVE — Preset Parameter Set")
print("=" * 70)

mixed_params = {
    "parameters_mus": MIXED_EXPO_CURVE_ONE["parameters_mus"],
    "parameter_weights": MIXED_EXPO_CURVE_ONE["parameter_weights"],
}
exp_model_mixed = ExposureModel(
    exposures=exposures,
    ri_contract=ri_contract,
    selected_curve=ExposureCurveType.MIXED_EXPONENTIAL,
    curve_parameters=mixed_params,
)
mixed_rates = exp_model_mixed.calculate_exposure_rate(analysis_date)

for layer in ri_contract.layers:
    lid = layer.layer_id
    print(f"  {layer.layer_name:<15}  Rate: {mixed_rates.get(lid, 0.0):.6f}")
