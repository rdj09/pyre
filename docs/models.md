# Models Module

The Models module provides actuarial and statistical modeling tools for
reinsurance pricing: experience rating, exposure rating, trending, and
aggregate loss features.

!!! note "Maturity varies by submodule"
    `experience_preparer.py` (`ExperienceModelData`) and `trending.py` are
    the stable, tested entry points — they back the
    [treaty pricing workbench](workbench.md) and have unit test coverage.
    `SeverityFit`/`FrequencyFit` (distribution fitting) and
    `AggregateFeatures`/`Simulation` (the Monte Carlo DFA engine) now have
    real, tested implementations — see [Severity and frequency
    fitting](#severity-and-frequency-fitting) and [Aggregate
    Features](#aggregate-features) below. `Selections`' credibility
    formulas are implemented and tested; the one piece still outstanding is
    wiring experience/exposure *blending* through `AggregateFeatures.run()`
    (it accepts `exposure_data`/`selections` constructor arguments for
    interface completeness but does not yet use them — see that class's
    docstring). This page says so explicitly wherever a real limitation
    remains, rather than showing a fabricated "working" example.

## Submodules

| Submodule | Files | Purpose |
|---|---|---|
| `Experience/` | `experience_preparer.py`, `trending.py` (one level up), `burn_cost.py`, `frequency_severity.py`, `pareto_rating.py`, `resampling.py`, `curve_fitting.py` | Combine claims + exposures + contract into ceded-loss results; burn-cost and frequency/severity rating |
| `Exposure/` | `exposure_curve_functions.py`, `exposure_curve_fitting.py`, `exposure_ILF_functions.py`, `exposure_ILF_fitting.py`, `exposure_rating_cost.py` | Exposure (increased limit factor / exposure curve) rating |
| `AggregateFeatures/` | `aggregate_features.py`, `selections.py`, `simulation_engine.py` | Aggregate loss distribution modelling (Monte Carlo DFA simulation) and credibility-weighted selections |

## Experience Rating

### `ExperienceModelData` — the central entry point

`ExperienceModelData` ties `Claims` + `Exposures` + `RIContract` together,
applies [trending](#trending), applies each layer's loss-to-layer function
(see [Treaty: layer loss-to-layer formulas](treaty.md#layer-loss-to-layer-formulas)),
and aggregates the result by layer and modelling year. This is the same
calculation the [treaty pricing workbench](workbench.md) runs.

```python
from datetime import date

from pyre import (
    Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData,
    Exposure, ExposureMetaData, Exposures, ExposureValues,
    RIContract, RIContractMetadata, RILayer,
    ExperienceModelData,
)
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType

# One claim that exhausts a 200k xs 100k XOL layer in its second valuation
claim = Claim(
    ClaimsMetaData(claim_id="CL001", currency="USD", contract_limit=2_000_000,
                    loss_date=date(2023, 5, 15)),
    ClaimDevelopmentHistory(
        development_months=[12, 24],
        cumulative_dev_paid=[50_000, 350_000],
        cumulative_dev_incurred=[120_000, 350_000],
    ),
)
claims = Claims([claim])

exposure = Exposure(
    ExposureMetaData(exposure_id="EXP2023", exposure_name="2023 Premium",
                        exposure_period_start=date(2023, 1, 1),
                        exposure_period_end=date(2023, 12, 31), currency="USD"),
    ExposureValues(exposure_value=1_200_000, attachment_point=0, limit=0),
)
exposures = Exposures([exposure])

metadata = RIContractMetadata(
    contract_id="C-0001", contract_description="Demo XOL", cedent_name="Acme Re",
    trigger_basis=ClaimTriggerBasis.LOD, indexation_clause=IndexationClauseType.FULL_INDEXATION,
    indexation_margin=0.0, inception_date=date(2023, 1, 1), expiration_date=date(2023, 12, 31),
    fx_rates={"USD": 1.0},
)
layer = RILayer(
    layer_id=1, layer_name="XOL Layer", layer_type=ContractType.EXCESS_OF_LOSS,
    occurrence_attachment=100_000, occurrence_limit=200_000,
    aggregate_attachment=0, aggregate_limit=0, subject_lines_of_business=["Property"],
    subject_lob_exposure_amounts=[1_200_000], full_subject_premium=0,
    written_line=1.0, signed_line=1.0, number_of_reinstatements=0, reinstatement_cost={},
)
contract = RIContract(metadata, [layer])

data = ExperienceModelData(claims, exposures, contract)
# defaults: trend factors of 1.0 for every year, base_year = contract inception year

print(data.aggregate_subject_contract_claims[1][2023])
# {'latest_paid': 200000.0, 'latest_incurred': 200000.0,
#  'claim_counts': {'Open': 1}, 'total_count': 1}
print(data.aggregate_exposures[2023])
# {'written': 1200000.0, 'earned': 1200000.0}

loss_ratio = data.aggregate_subject_contract_claims[1][2023]["latest_incurred"] / \
    data.aggregate_exposures[2023]["earned"]
print(f"Loss ratio: {loss_ratio:.1%}")  # 16.7%
```

This mirrors `tests/test_app_service.py::TestRunPricing`, which asserts
these exact figures end-to-end.

!!! note "SURPLUS_SHARE layers"
    `loss_to_layer_fn` supports `SURPLUS_SHARE` layers — it raises
    `ValueError` (not `NotImplementedError`) if `RILayer.sum_insured` is not
    set, since the per-risk cession percentage cannot be computed without it.
    See [Treaty: layer loss-to-layer formulas](treaty.md#layer-loss-to-layer-formulas)
    for the formula, and the worked example below.

#### Worked example: SURPLUS_SHARE cession

Clark (1996/2014), *Basics of Reinsurance Pricing*, uses a risk with
sum insured 1,000,000, a retained line of 100,000, and a surplus treaty
limit of 400,000 to illustrate the cession percentage:

```python
from pyre.treaty.contracts import RILayer
from pyre.treaty.contract_types import ContractType

surplus_layer = RILayer(
    layer_id=1, layer_name="Surplus Treaty", layer_type=ContractType.SURPLUS_SHARE,
    occurrence_attachment=100_000,  # retained_line
    occurrence_limit=400_000,       # surplus_limit
    aggregate_attachment=0, aggregate_limit=0,
    subject_lines_of_business=["Property"], subject_lob_exposure_amounts=[1_000_000],
    full_subject_premium=0, written_line=1.0, signed_line=1.0,
    number_of_reinstatements=0, reinstatement_cost={},
    sum_insured=1_000_000,
)

cession_pct = surplus_layer.loss_to_layer_fn(1.0) / 1.0  # treat gross_amount=1.0 as a rate
print(f"Cession: {cession_pct:.0%}")  # Cession: 40%

# A ground-up loss of 250,000 on this risk:
print(surplus_layer.loss_to_layer_fn(250_000))  # 100000.0 (= 40% of 250,000)
```

`surplus_over_retention = max(sum_insured - retained_line, 0) = 900,000`;
`ceded_portion = min(surplus_over_retention, surplus_limit) = 400,000`;
`cession = ceded_portion / sum_insured = 40%` — matching Clark's own
worked numbers. See `pyre.treaty.layer_loss_functions.surplus_share_calculation`
for the implementation.

### Trending

`Trending` moves claims/exposures from their origin year to a common base
year using pre-computed cumulative trend indices.

Each dict value is a **cumulative index relative to `base_year`**, not a
standalone annual rate — `trend_factors[base_year]` is `1.0`, and
`calculate_trend_factor` is a direct lookup into these indices (it does not
itself compound annual rates). The caller is responsible for supplying the
correct cumulative index for every year it looks up, including years before
`base_year` (e.g. with 5% p.a. compounding and `base_year=2022`, year 2020's
entry is `1 / 1.05**2`).

```python
from pyre.models.trending import Trending

trending = Trending(
    exposure_trend_factors={2021: 1.02, 2022: 1.03},
    claim_trend_factors={2021: 1.04, 2022: 1.05},
    base_year=2023,
)
trended_exposures = trending.trend_exposures(exposures)
trended_claims = trending.trend_claims(claims)
factor = trending.calculate_trend_factor(2022, for_claims=False)  # 1.03
```

Citation for the underlying method: Deters, I. (2017),
*The Mathematics of On-Leveling* —
[casact.org](https://www.casact.org/sites/default/files/database/forum_17spforum_03-deters.pdf).

### Burn cost

`BurnCostModel` wraps an `ExperienceModelData` instance and a specific layer
to produce a burn cost (ceded loss / exposure) per modelling year:

```python
from pyre.models.Experience.burn_cost import BurnCostModel

model = BurnCostModel(model_data=data, layer_id=1)
print(model.calculate_burn_cost())  # {2023: 0.16666...}
```

Projection method selection (`ProjectionMethods`), year weighting, a priori
loss ratios, and development patterns are constructor arguments — see the
API reference below for the full parameter set. The standalone functions
`chainladder_method`, `bf_method` (Bornhuetter–Ferguson), `cape_cod_method`,
and `generalised_cape_cod_method` in the same module implement those
projection methods individually.

### Severity and frequency fitting

`SeverityFit` and `FrequencyFit` (in `frequency_severity.py`) fit parametric
distributions and return a `FitResult` (`distribution`, `parameters`,
`log_likelihood`, `aic`) per requested distribution:

```python
from pyre.enums import SeverityDistribution, FrequencyDistribution
from pyre.models.Experience.frequency_severity import SeverityFit, FrequencyFit

severity_results = SeverityFit(
    distributions=[SeverityDistribution.LOGNORMAL, SeverityDistribution.PARETO],
    data=data,  # an ExperienceModelData instance
    ibner_dev_pattern={2023: 1.0},
).fit()
best_severity = min(severity_results, key=lambda r: r.aic)

frequency_results = FrequencyFit(
    distributions=[FrequencyDistribution.POISSON, FrequencyDistribution.NEGATIVE_BINOMIAL],
    claim_counts=[3, 5, 2, 7],
).fit()
```

`SeverityFit.fit()` supports `LOGNORMAL` (method of moments) and `PARETO`
(single-parameter, maximum likelihood); `FrequencyFit.fit()` supports
`POISSON` (maximum likelihood) and `NEGATIVE_BINOMIAL` (method of moments,
requires overdispersed data — raises `ValueError` otherwise). Both raise
`NotImplementedError` for any other enum member (e.g.
`SeverityDistribution.OTHER`). See Klugman, Panjer & Willmot, *Loss Models:
From Data to Decisions*, 4th ed., Ch. 13 "Parameter Estimation", for the
estimation methods (already cited in the module's docstrings).

`SeverityFit`'s `ibner_dev_pattern` argument is designed to be populated
from `IBNERPatternExtractor.get_IBNER_pattern()`
(`pyre.claims.triangles` — see [Claims](claims.md#working-with-claims-triangles)).
Its N-triangle/D-triangle terminology follows the underlying method in
Schnieper, R. (1991), *Separating True IBNR and IBNER Claims*, ASTIN
Bulletin, 21(1), pp. 111-127 —
[casact.org](https://www.casact.org/sites/default/files/database/astin_vol21no1_111.pdf).
`IBNERPatternExtractor` approximates that method using only the
aggregated cumulative triangle rather than claim-level detail — see its
class docstring for the exact divergence, checked against Schnieper's own
worked numerical example in the paper.

## Exposure Rating

### Exposure curves

`exposure_curve_functions.py` implements three curve families used to
distribute loss cost across a layer relative to total sum insured:

```python
from pyre.models.Exposure.exposure_curve_functions import (
    mbbefd_curve, mixed_exponential_curve, riebesell_curve, swissRe_c_values,
)

# MBBEFD (Bernegger exposure curve), using a published Swiss Re c-value
g_value = mbbefd_curve(swissRe_c_values.COMMERCIAL_LINES_MEDIUM, curve_position=0.5)

# Riebesell power-curve approximation (z = ILF base for doubling the limit)
riebesell_value = riebesell_curve(attachment=0, limit=1_000_000, z_value=0.1, base_limit=1_000_000)
```

Citations (in source): Bernegger, S. (1997), *The Swiss Re Exposure
Curves and the MBBEFD Distribution Class* —
[casact.org](https://www.casact.org/sites/default/files/2021-03/8_Bernegger.pdf);
mixed-exponential fitting — [casact.org](https://www.casact.org/sites/default/files/database/proceed_proceed99_99578.pdf).
`ExposureCurveFitter` (`exposure_curve_fitting.py`) fits these curves to
empirical data but requires `scipy`, which is **not** installed by default
(see `test_exposure_curve_fitting.py`, always skipped/ignored in this repo's
test runs).

### Increased Limit Factors (ILFs)

```python
from pyre.models.Exposure.exposure_ILF_functions import pareto_ilf, power_ilf

# Pareto-distribution ILF moving from a 1M to a 5M limit
ilf = pareto_ilf(limit_1=1_000_000, limit_2=5_000_000, alpha=2.0, x_m=1.0)

# Simple power-curve ILF
ilf_power = power_ilf(limit=5_000_000, basic_limit=1_000_000, power_parameter=0.3)
```

`ILFFitter` (`exposure_ILF_fitting.py`) fits power-curve or Pareto ILF
parameters to observed `(limit, ILF)` pairs — its Pareto fit also requires
`scipy`.

### `ExposureModel`

`ExposureModel.calculate_exposure_curve(curve_type, parameters, position)`
is a thin dispatcher over the three curve functions above, driven by an
`ExposureCurveType` enum:

```python
from pyre.models.Exposure.exposure_rating_cost import ExposureModel
from pyre.models.Exposure.exposure_curve_functions import ExposureCurveType, swissRe_c_values

exposure_model = ExposureModel(
    exposures=exposures, ri_contract=contract,
    selected_curve=ExposureCurveType.MBBEFD,
    curve_parameters={"curve": swissRe_c_values.COMMERCIAL_LINES_MEDIUM},
)
value = exposure_model.calculate_exposure_curve(
    ExposureCurveType.MBBEFD, exposure_model._curve_parameters, position=0.5
)
```

`ExposureModel._calculate_single_exposure_share` (the per-risk,
stacking-aware share-of-layer calculation cited from
[casact.org](https://www.casact.org/sites/default/files/presentation/reinsure_2009_handouts_cs1-rosin.pdf))
now calls curves through the uniform `calculate_curve(curve_type, parameters,
position)` adapter (`exposure_curve_functions.calculate_curve`), so the
curve-call signature mismatch that previously broke `RIEBESELL`/
`MIXED_EXPONENTIAL` is fixed — all three `ExposureCurveType` members work.
`ExposureModel.calculate_ilf_adjusted_rate` additionally supports scaling a
base-limit rate to a target limit via an optional `ilf_function`, as a
separate, additive adjustment layered on top of the curve-based share.

Known remaining limitations: `_calculate_single_exposure_share` only
considers each layer's `occurrence_attachment`/`occurrence_limit` (aggregate
layer limits are not reflected in the per-risk share), and it divides by
`total_insured_value`, which raises `ZeroDivisionError` for a policy with
`attachment_point + limit == 0`. It remains `_`-prefixed/internal and is
not documented as a stable public API here.

## Aggregate Features

`AggregateFeatures` (`aggregate_features.py`) orchestrates a frequency/severity
fit from experience data into a Monte Carlo `Simulation` and returns its
`SimulationResults`:

```python
from pyre.models.AggregateFeatures.aggregate_features import AggregateFeatures, ModellingAssumptions

assumptions = ModellingAssumptions(
    cost_of_capital=0.10, required_rate_of_return=0.12,
)
features = AggregateFeatures(
    experience_data=data,  # an ExperienceModelData instance
    exposure_data=exposure_model,  # an ExposureModel instance
    selections=selections,  # a Selections instance
    assumptions=assumptions,
)
results = features.run(n_simulations=10_000)
```

`Simulation` (`simulation_engine.py`) is a fully implemented Monte Carlo
DFA engine: it samples claim counts and severities from the fitted
`FrequencyFit`/`SeverityFit` distributions (`POISSON`/`NEGATIVE_BINOMIAL`
and `LOGNORMAL`/`PARETO` respectively — the same ones `SeverityFit`/
`FrequencyFit` support, see
[above](#severity-and-frequency-fitting)), applies each layer's
`loss_to_layer_fn`, and computes `loss_cost`, `required_capital` (VaR or
TVaR, per `ModellingAssumptions.use_tvar`), `investment_return`,
`cashflows`, `profit_commission`, `retrocession_benefits`/
`retrocession_cost`, and `required_premium_layer`/
`required_premium_programme`. `AggregateFeatures.run()` currently only
drives experience-side fitting through `Simulation` — it accepts
`exposure_data`/`selections` constructor arguments for interface
completeness but does not yet blend them in via `Selections`' credibility
weighting (that blended run is separate, out-of-scope work — see the
class's own docstring).

`Selections` and its `CredibilityWeight` helper (`selections.py`)
implement standard credibility formulas (limited fluctuation, Bühlmann,
Bühlmann–Straub, greatest-accuracy, and Bayesian credibility) for blending
experience and exposure rating indications — see the class docstrings and
API reference below for exact signatures.

## API Reference

::: pyre.models.Experience.experience_preparer

::: pyre.models.Experience.burn_cost

::: pyre.models.Experience.curve_fitting

::: pyre.models.Experience.frequency_severity

::: pyre.models.Experience.pareto_rating

::: pyre.models.Experience.resampling

::: pyre.models.Exposure.exposure_curve_functions

::: pyre.models.Exposure.exposure_curve_fitting

::: pyre.models.Exposure.exposure_ILF_functions

::: pyre.models.Exposure.exposure_ILF_fitting

::: pyre.models.Exposure.exposure_rating_cost

::: pyre.models.AggregateFeatures.aggregate_features

::: pyre.models.AggregateFeatures.selections

::: pyre.models.AggregateFeatures.simulation_engine

::: pyre.models.trending
