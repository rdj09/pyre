# pyRE Refactoring & Completion Design

**Date:** 2026-04-16  
**Status:** Approved  
**Scope:** Fix-and-restructure — bugs, structure, TODO completions, production readiness  
**Backward compatibility:** None required — clean breaks throughout

---

## Overview

pyRE is a Python reinsurance pricing library (v0.0.1). This design covers a full refactor across six sequential phases:

1. **Phase 1** — Bug fixes (ship immediately, no API changes)
2. **Phase 2** — Dataclasses conversion (eliminate boilerplate)
3. **Phase 3** — Module restructure, enums, public API
4. **Phase 4** — Caching (performance)
5. **Phase 5** — TODO completions and functional gaps
6. **Phase 6** — Professional workstreams (CI/CD, testing, docs, packaging)

---

## Target Module Structure

End-state after all phases:

```
src/pyre/
├── __init__.py                    # public API surface
├── __about__.py                   # version
├── py.typed                       # PEP 561 marker
├── enums.py                       # all cross-cutting enumerations
├── exceptions/
│   └── exceptions.py
├── claims/
│   ├── __init__.py
│   ├── claims.py                  # ClaimDevelopmentHistory, ClaimsMetaData, Claim, Claims
│   └── triangles.py               # Triangle, IBNERPatternExtractor, CurveType
├── exposures/
│   ├── __init__.py
│   └── exposures.py               # ExposureMetaData, ExposureValues, Exposure, Exposures
├── treaty/
│   ├── __init__.py
│   ├── contracts.py               # RILayer, RIContractMetadata, RIContract
│   ├── contract_types.py
│   └── layer_loss_functions.py
├── models/                        # renamed from Models/
│   ├── __init__.py
│   ├── trending.py                # Trending (stays in models/)
│   ├── experience/                # renamed from Experience/
│   │   ├── __init__.py
│   │   ├── experience_preparer.py
│   │   ├── burn_cost.py
│   │   ├── frequency_severity.py
│   │   ├── pareto_rating.py
│   │   ├── resampling.py
│   │   └── curve_fitting.py
│   ├── exposure/                  # renamed from Exposure/
│   │   ├── __init__.py
│   │   ├── exposure_rating_cost.py
│   │   ├── exposure_curve_fitting.py
│   │   ├── exposure_curve_functions.py
│   │   ├── exposure_ILF_fitting.py
│   │   └── exposure_ILF_functions.py
│   └── aggregate/                 # renamed from AggregateFeatures/
│       ├── __init__.py
│       ├── aggregate_features.py
│       ├── selections.py
│       └── simulation_engine.py
└── rate_monitoring/
    ├── __init__.py
    ├── rate_adequacy.py
    └── rate_change.py
```

---

## Phase 1 — Bug Fixes

No structural changes. Six targeted fixes. Fix 3 changes the observable behaviour of `loss_to_layer_fn` (from returning a broken lambda to returning a correct float) — this is intentional; the previous return value was never usable.

### Fix 1 — `Trending.trend_exposures()` (`models/trending.py`)

`exposure.modelling_year()` and `exposure.exposure_values()` called as functions but are properties. Raises `TypeError` at runtime.

```python
# broken
origin_year = exposure.modelling_year()
original_values = exposure.exposure_values()

# fixed
origin_year = exposure.modelling_year
original_values = exposure.exposure_values
```

### Fix 2 — `Triangle.from_claims()` (`claims/triangles.py`)

(a) `claim.modelling_year` does not exist — path is `claim.claims_meta_data.modelling_year`.  
(b) `for dev_period, value in dev_history.items()` — `dev_history` is `List[float]`, not a dict. Must zip development months with values.

```python
# broken
origin_year = claim.modelling_year
for dev_period, value in dev_history.items():

# fixed
origin_year = claim.claims_meta_data.modelling_year
dev_months = claim.capped_claim_development_history.development_months
for dev_period, value in zip(dev_months, dev_history):
```

### Fix 3 — `RILayer.loss_to_layer_fn()` (`treaty/contracts.py`)

(a) Surplus share returns the exception object instead of raising it.  
(b) Quota share returns a raw float instead of a float result.  
(c) Final `lambda` shadows its outer `gross_amount` parameter.

```python
# fixed
def loss_to_layer_fn(self, gross_amount: float) -> float:
    if self.layer_type == ContractType.SURPLUS_SHARE:
        raise NotImplementedError("Surplus share not yet implemented")
    if self.layer_type == ContractType.QUOTA_SHARE:
        return gross_amount
    func = layer_loss_calculation[self.layer_type]
    return func(gross_amount, self.occurrence_attachment, self.occurrence_limit)
```

### Fix 4 — `ExposureModel._calculate_single_exposure_share()` (`models/exposure/exposure_rating_cost.py`)

Curve calculation block and `shares_by_layer` assignment are inside a misplaced `else` branch — shares are silently never populated for most layers. Restructure so both branches of the `if/else` compute and store a share. Add missing `Any` import.

### Fix 5 — `BurnCostModel.calculate_burn_cost()` (`models/experience/burn_cost.py`)

Bare `except Exception` swallows all errors and silently substitutes chain-ladder results. Replace with explicit re-raise:

```python
# fixed
except Exception as e:
    raise ValueError(
        f"Projection failed for year {year}, layer {self._layer_id}: {e}"
    ) from e
```

### Fix 6 — `IBNERPatternExtractor._compute_N_and_D()` (`claims/triangles.py`)

`N[oy][d] = current - prev + D[oy][d]` where `D[oy][d] = prev - current` evaluates to zero for every cell. Fix formula to match Schnieper (1991) IBNER methodology as cited in the source comment.

---

## Phase 2 — Dataclasses Conversion

Replace Java-style `_foo` + `@property` + no-op setter pattern with `@dataclass`. Validation moves to `__post_init__`. Computed properties and properties with real logic stay as `@property`.

### Classes converted

| Class | File | Notes |
|---|---|---|
| `ClaimsMetaData` | `claims/claims.py` | `modelling_year` stays as `@property` |
| `ClaimDevelopmentHistory` | `claims/claims.py` | `__post_init__` runs `_validate_list_lengths`; all computed properties stay |
| `ExposureMetaData` | `exposures/exposures.py` | Period validation in `__post_init__` |
| `ExposureValues` | `exposures/exposures.py` | Non-negative validation in `__post_init__` |
| `RILayer` | `treaty/contracts.py` | `written_line_premium`, `signed_line_premium`, `loss_to_layer_fn` stay |
| `RIContractMetadata` | `treaty/contracts.py` | `claim_year_basis` stays as `@property` |

### Classes not converted

`Claim`, `Claims`, `Exposure`, `Exposures`, `RIContract`, `BurnCostModel`, `ExperienceModelData`, `Trending` — collection/composite/stateful classes where `@dataclass` adds no value.

### Example

```python
# BEFORE: 60 lines
class ClaimsMetaData:
    def __init__(self, claim_id: str, ...):
        self._claim_id = claim_id
        ...
    @property
    def claim_id(self): return self._claim_id
    @claim_id.setter
    def claim_id(self, value): self._claim_id = value
    # ... x 10 more

# AFTER: 20 lines
@dataclass
class ClaimsMetaData:
    claim_id: str
    currency: str
    contract_limit: float = 0.0
    contract_deductible: float = 0.0
    claim_in_xs_of_deductible: bool = False
    claim_year_basis: ClaimYearType = field(default=ClaimYearType.ACCIDENT_YEAR)
    loss_date: date = field(default_factory=lambda: date(1900, 1, 1))
    policy_inception_date: date = field(default_factory=lambda: date(1900, 1, 1))
    report_date: date = field(default_factory=lambda: date(1900, 1, 1))
    line_of_business: Optional[str] = None
    status: Optional[str] = "Open"

    @property
    def modelling_year(self) -> int: ...
```

---

## Phase 3 — Module Restructure, Enums, Public API

### 3a — Package rename

`Models/` → `models/`, `Experience/` → `experience/`, `Exposure/` → `exposure/`, `AggregateFeatures/` → `aggregate/`. All internal imports updated in-place. No re-exports.

### 3b — `pyre/enums.py`

Single source of truth for all cross-cutting enumerations. All enum definitions move here; original locations are deleted.

```python
# src/pyre/enums.py
class ClaimYearType(Enum): ...           # was claims/claims.py
class ClaimTriggerBasis(Enum): ...       # was treaty/contracts.py
class ExposureBasis(Enum): ...           # was exposures/exposures.py
class ContractType(Enum): ...            # was treaty/contract_types.py
class IndexationClauseType(Enum): ...    # was treaty/contracts.py
class ProjectionMethods(Enum): ...       # was models/experience/burn_cost.py
class SeverityDistribution(Enum): ...    # was models/experience/frequency_severity.py
class FrequencyDistribution(Enum): ...   # was models/experience/frequency_severity.py
class ExposureCurveType(Enum): ...       # was models/exposure/exposure_curve_functions.py
class CurveType(Enum): ...               # was claims/triangles.py
```

The `claim_year_basis` module-level mapping dict in `contracts.py` is removed. Replaced with a method on `ClaimTriggerBasis`:

```python
class ClaimTriggerBasis(Enum):
    LOD = "Losses Occurrence"
    RAD = "Risk Attaching"
    CMB = "Claims Made Basis"

    def to_claim_year_type(self) -> ClaimYearType:
        return {
            self.LOD: ClaimYearType.ACCIDENT_YEAR,
            self.RAD: ClaimYearType.UNDERWRITING_YEAR,
            self.CMB: ClaimYearType.REPORTED_YEAR,
        }[self]
```

### 3c — `pyre/__init__.py` public API

```python
from pyre.claims.claims import Claim, Claims, ClaimDevelopmentHistory, ClaimsMetaData
from pyre.exposures.exposures import Exposure, Exposures, ExposureMetaData, ExposureValues
from pyre.treaty.contracts import RILayer, RIContractMetadata, RIContract
from pyre.models.trending import Trending
from pyre.models.experience.burn_cost import BurnCostModel
from pyre.models.experience.experience_preparer import ExperienceModelData
from pyre.models.exposure.exposure_rating_cost import ExposureModel
from pyre.models.aggregate.selections import Selections, CredibilityWeight
from pyre.models.aggregate.aggregate_features import AggregateFeatures
from pyre.models.aggregate.simulation_engine import Simulation, SimulationResults
from pyre.enums import (
    ClaimYearType, ClaimTriggerBasis, ExposureBasis,
    ContractType, ProjectionMethods, ExposureCurveType,
    SeverityDistribution, FrequencyDistribution, CurveType,
    IndexationClauseType,
)
from pyre.__about__ import __version__
```

### 3d — `py.typed` marker

Add empty `src/pyre/py.typed` (PEP 561) so downstream type checkers recognise pyre as fully typed.

---

## Phase 4 — Caching

`ExperienceModelData` computed properties recompute expensive O(n × layers) loops on every access. Convert to `functools.cached_property`.

```python
from functools import cached_property

class ExperienceModelData:
    @cached_property
    def trended_claims(self) -> Claims: ...

    @cached_property
    def trended_exposures(self) -> Exposures: ...

    @cached_property
    def subject_contract_claims(self) -> Dict[int, Claims]: ...

    @cached_property
    def aggregate_subject_contract_claims(self) -> Dict[int, Dict[int, Dict[str, Any]]]: ...

    @cached_property
    def aggregate_exposures(self) -> Dict[int, Dict[str, float]]: ...
```

`update_trend_factors()` clears the cache explicitly:

```python
def update_trend_factors(self, ...) -> None:
    # update self._trending ...
    for key in ("trended_claims", "trended_exposures", "subject_contract_claims",
                "aggregate_subject_contract_claims", "aggregate_exposures"):
        self.__dict__.pop(key, None)
```

---

## Phase 5 — TODO Completions & Functional Gaps

### 5a — Miscellaneous bugs and typos

| Location | Issue | Fix |
|---|---|---|
| `rate_change.py` | Missing `Optional` import | Add `from typing import Optional` |
| `frequency_severity.py` | `_inidividual_projected_claims` missing `return` on ground-up branch | Add `return` |
| `frequency_severity.py` | Returns `NotImplementedError(...)` instead of raising | `raise NotImplementedError(...)` |
| `frequency_severity.py` | `class severity_fit` snake_case name | Rename to `SeverityFit` |
| `frequency_severity.py` | `fit()` is empty stub | Implement (see 5d) |
| `selections.py` | `from ...exposure_rating_cost import *` wildcard | Replace with explicit names |
| `selections.py` | `subject_contract_claims()` called as function | Remove `()` — it's a property |
| `exposure_curve_functions.py` | `paramaters_mus` typo | Rename to `parameters_mus` throughout |
| `exposure_curve_functions.py` | Commented-out `calculate_curve` function | Uncomment and wire into `ExposureModel` |
| `exposure_curve_functions.py` | `mixed_expo_curves` Enum uses dicts as values — unused | Replace with module-level preset dicts |
| `simulation_engine.py` | `profit_commsission` typo | Rename to `profit_commission` |
| `simulation_engine.py` | `retrocession_beneits` typo | Rename to `retrocession_benefits` |
| `simulation_engine.py` | All methods missing `self` parameter | Add `self` to all instance methods |

### 5b — Parallelogram method for aggregate exposures

`Exposure._earned_pct()` returns `0.0` for aggregate exposures. Implement the parallelogram method:

```python
def _parallelogram_earned_pct(self, analysis_date: date) -> float:
    """
    Parallelogram method: assumes policies written uniformly over the
    exposure period, each with term length equal to exposure_term_length_days.
    Returns the proportion of the aggregate exposure earned by analysis_date.
    """
    start = self._exposure_meta.exposure_period_start
    end = self._exposure_meta.exposure_period_end
    term = self._exposure_meta.exposure_term_length_days
    if term == 0:
        return 0.0
    if analysis_date <= start:
        return 0.0
    if analysis_date >= end + timedelta(days=term):
        return 1.0
    days_into_earning = (analysis_date - start).days
    total_earning_days = term + (end - start).days
    return min(days_into_earning / total_earning_days, 1.0)
```

### 5c — `Triangle.get_selected_development_pattern()`

Closes the loop between `Triangle.fit_curve()` and `BurnCostModel.development_pattern`. Add:

```python
def get_selected_development_pattern(
    self,
    curve_type: CurveType,
    tail_factor: float = 1.0,
    c_values: Optional[List[float]] = None
) -> Dict[int, float]:
    """
    Fits a curve to age-to-age factors and returns cumulative-to-ultimate
    development factors for each development period.

    Returns:
        Dict mapping development period to cumulative-to-ultimate factor.
        Suitable for direct use as BurnCostModel.development_pattern.
    """
```

### 5d — `SeverityFit.fit()` and `FrequencyFit`

Implement `SeverityFit.fit()` for `LOGNORMAL` and `PARETO` using method of moments (stdlib `math` only, no external dependencies):

- **Lognormal**: `mu = log(mean² / sqrt(variance + mean²))`, `sigma = sqrt(log(variance/mean² + 1))`
- **Pareto**: MLE estimator `alpha = n / sum(log(xi / x_m))` where `x_m` is the minimum observed loss. Cite: Klugman, Panjer & Willmot, *Loss Models* (4th ed.), Chapter 4.

Add new `FrequencyFit` class (parallel structure to `SeverityFit`) fitting claim counts per year to:
- **Poisson**: `lambda = mean(counts)`
- **Negative Binomial**: method of moments using mean and variance of counts

Both classes return a `FitResult` dataclass:

```python
@dataclass
class FitResult:
    distribution: SeverityDistribution | FrequencyDistribution
    parameters: Dict[str, float]
    log_likelihood: float
    aic: float
```

### 5e — `ExposureModel` completion

After Phase 1 fix to `_calculate_single_exposure_share()`, add:

```python
def calculate_exposure_rate(self, analysis_date: date) -> Dict[int, float]:
    """
    Returns the exposure-rated burning cost per unit of earned exposure
    for each layer: sum(exposure_value * share_of_risk) / total_exposure.
    """

def calculate_ilf_adjusted_rate(
    self,
    ilf_function: Callable[[float], float],
    analysis_date: date,
) -> Dict[int, float]:
    """
    ILF-adjusted exposure rate. Accepts any callable ILF function
    (e.g. pareto_ilf or power_ilf from exposure_ILF_functions) to
    adjust for the portfolio limit profile.
    """
```

### 5f — `Simulation` and `AggregateFeatures` — full implementation

The `Simulation` class is a complete DFA (Dynamic Financial Analysis) pricing engine.

**`ModellingAssumptions` lives in `models/aggregate/aggregate_features.py`** (imported by both `Simulation` and `AggregateFeatures`):

```python
@dataclass
class ModellingAssumptions:
    cost_of_capital: float
    required_rate_of_return: float
    capital_confidence_level: float = 0.995   # VaR/TVaR confidence (Solvency II default)
    use_tvar: bool = True                      # TVaR vs VaR for required capital
    investment_yield: float = 0.0
    tax_rate: float = 0.0
    acquisition_cost_ratio: float = 0.0
    brokerage_cost_ratio: float = 0.0
```

**`Simulation` constructor** (lives in `models/aggregate/simulation_engine.py`):

```python
class Simulation:
    def __init__(
        self,
        frequency_fit: FrequencyFit,
        severity_fit: SeverityFit,
        ri_contract: RIContract,
        assumptions: ModellingAssumptions,
        n_simulations: int = 10_000,
        random_seed: Optional[int] = None,
        retrocession_contract: Optional[RIContract] = None,
    ) -> None: ...
```

**Methods to implement:**

| Method | Description |
|---|---|
| `run()` | Monte Carlo: draw N frequency samples; for each draw severity samples; apply `loss_to_layer_fn` per layer; store per-simulation aggregate ceded loss |
| `loss_cost()` | Mean ceded loss per layer across simulations |
| `required_capital()` | TVaR or VaR at `assumptions.capital_confidence_level` of simulated aggregate loss distribution per layer |
| `cashflows()` | Premium inflow and claim outflow timed by `ClaimDevelopmentHistory.mean_payment_duration` |
| `investment_return()` | Apply `assumptions.investment_yield` to cashflow timing to get present value benefit |
| `profit_commission()` | Sliding scale PC calculation against simulated ceded loss ratio |
| `retrocession_cost()` / `retrocession_benefits()` | Apply a nested `RIContract` as retrocession structure |
| `required_premium_layer()` | `loss_cost + expenses + CoC * required_capital - investment_return + net_retrocession_cost` |
| `required_premium_programme()` | Sum `required_premium_layer()` across all layers |
| `output()` | Returns `SimulationResults` dataclass |
| `save(path)` | Serialise `SimulationResults` to JSON |

**`SimulationResults` dataclass:**

```python
@dataclass
class SimulationResults:
    loss_cost_by_layer: Dict[int, float]
    required_capital_by_layer: Dict[int, float]
    required_premium_by_layer: Dict[int, float]
    required_premium_programme: float
    aggregate_loss_distribution: Dict[int, List[float]]  # layer_id -> sorted sim losses
    n_simulations: int
    assumptions: ModellingAssumptions
```

**`AggregateFeatures` refactored as orchestrator:**

```python
class AggregateFeatures:
    def __init__(
        self,
        experience_data: ExperienceModelData,
        exposure_data: ExposureModel,
        selections: Selections,
        assumptions: ModellingAssumptions,
    ) -> None: ...

    def run(self, n_simulations: int = 10_000) -> SimulationResults:
        """Full pricing workflow: credibility-weight → simulate → output."""
```

---

## Phase 6 — Professional Development Workstreams

### 6a — Linting & Formatting

Add `ruff` to `pyproject.toml` for linting and formatting:

```toml
[tool.hatch.envs.default]
dependencies = ["ruff", "pytest", "pytest-cov"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.ruff.format]
quote-style = "double"
```

### 6b — Type checking (strict)

```toml
[tool.mypy]
strict = true
python_version = "3.10"
```

All type errors resulting from `strict = true` are fixed as part of Phase 6. `src/pyre/py.typed` added (PEP 561).

### 6c — Test coverage

```toml
[tool.hatch.envs.default.scripts]
test = "pytest --cov=pyre --cov-report=term-missing --cov-fail-under=80"
```

New test modules:

| Test file | Covers |
|---|---|
| `tests/test_trending.py` | Extend with `trend_exposures` and `trend_claims` regression tests for Phase 1 fixes |
| `tests/test_triangles.py` | Extend with `from_claims()` regression test and `get_selected_development_pattern()` |
| `tests/test_burn_cost.py` | All four projection methods, exception propagation |
| `tests/test_exposure_model.py` | `_calculate_single_exposure_share()`, `calculate_exposure_rate()`, `calculate_ilf_adjusted_rate()` |
| `tests/test_simulation.py` | `run()`, `loss_cost()`, `required_capital()`, `required_premium_layer()`, `required_premium_programme()` |
| `tests/test_frequency_severity.py` | `SeverityFit.fit()`, `FrequencyFit.fit()`, `FitResult` fields |
| `tests/test_selections.py` | All five credibility methods in `CredibilityWeight`, `Selections.make_selection()` |
| `tests/test_parallelogram.py` | `Exposure._parallelogram_earned_pct()` edge cases |
| `tests/test_enums.py` | `ClaimTriggerBasis.to_claim_year_type()`, all enum values |

### 6d — CI/CD (GitHub Actions)

Three workflows:

```
.github/workflows/
├── ci.yml          # on push/PR: ruff, mypy, pytest --cov
├── release.yml     # on tag v*: build + publish to PyPI via Trusted Publisher
└── docs.yml        # on push to main: mkdocs gh-deploy
```

`ci.yml` steps:
1. `ruff check .`
2. `ruff format --check .`
3. `mypy src/pyre`
4. `pytest --cov=pyre --cov-fail-under=80`

`release.yml` uses PyPI OIDC Trusted Publisher — no stored API tokens.

### 6e — Pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: ["types-all"]
```

### 6f — Documentation

- `docs/index.md` — add end-to-end quickstart showing full pricing workflow
- `docs/models.md` — document `BurnCostModel`, `ExposureModel`, `Selections`, `Simulation`
- `docs/simulation.md` — new page covering DFA pricing model and `ModellingAssumptions`
- All new public classes/methods use Google-style docstrings
- Add `mkdocs-gen-files` + `mkdocs-literate-nav` to auto-generate API reference

### 6g — Versioning & Changelog

- `v0.1.0` — after Phase 1+2 (bug fixes + dataclasses)
- `v0.2.0` — after Phase 3+4 (restructure + caching)
- `v0.3.0` — after Phase 5 (TODO completions)
- `v1.0.0` — after Phase 6 (full professional workstreams, ≥80% test coverage)
- Add `CHANGELOG.md` (Keep a Changelog format)
- Add `CONTRIBUTING.md` (dev setup, branch naming, PR expectations)
- Add `SECURITY.md` (responsible disclosure contact)

---

## Summary of All Changes by File

| File | Phase | Change type |
|---|---|---|
| `models/trending.py` | 1 | Bug fix: property call syntax |
| `claims/triangles.py` | 1, 5 | Bug fix: `from_claims()`, IBNER formula; new: `get_selected_development_pattern()` |
| `treaty/contracts.py` | 1, 2, 3 | Bug fix: `loss_to_layer_fn`; dataclass: `RILayer`, `RIContractMetadata`; enum move |
| `models/experience/burn_cost.py` | 1, 3 | Bug fix: exception swallowing; rename |
| `models/exposure/exposure_rating_cost.py` | 1, 5 | Bug fix: share calculation indentation; new: `calculate_exposure_rate`, `calculate_ilf_adjusted_rate` |
| `claims/claims.py` | 2, 3 | Dataclass: `ClaimsMetaData`, `ClaimDevelopmentHistory`; enum move |
| `exposures/exposures.py` | 2, 3, 5 | Dataclass: `ExposureMetaData`, `ExposureValues`; enum move; parallelogram method |
| `enums.py` | 3 | New file: all enumerations |
| `__init__.py` | 3 | New: public API surface |
| `py.typed` | 3 | New: PEP 561 marker |
| `models/experience/experience_preparer.py` | 4 | `cached_property` on all computed properties |
| `rate_monitoring/rate_change.py` | 5 | Bug fix: missing import |
| `models/experience/frequency_severity.py` | 5 | Bug fix + implement `SeverityFit.fit()`; new `FrequencyFit`, `FitResult` |
| `models/aggregate/selections.py` | 5 | Bug fix: wildcard import, property call |
| `models/exposure/exposure_curve_functions.py` | 5 | Fix typo, uncomment `calculate_curve`, replace enum preset pattern |
| `models/aggregate/simulation_engine.py` | 5 | Full implementation: `Simulation`, `SimulationResults` |
| `models/aggregate/aggregate_features.py` | 5 | Refactor: `AggregateFeatures` as orchestrator |
| `pyproject.toml` | 6 | Add ruff, pytest-cov, mypy strict, version bumps |
| `.pre-commit-config.yaml` | 6 | New |
| `.github/workflows/ci.yml` | 6 | New |
| `.github/workflows/release.yml` | 6 | New |
| `.github/workflows/docs.yml` | 6 | New |
| `CHANGELOG.md` | 6 | New |
| `CONTRIBUTING.md` | 6 | New |
| `SECURITY.md` | 6 | New |
| `docs/index.md` | 6 | Quickstart example |
| `docs/simulation.md` | 6 | New |
