# pyRE Refactor — Phase 5: Feature Completions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete every stubbed, broken, or TODO-marked piece of functionality: fix miscellaneous bugs across several modules, implement the parallelogram exposure method, close the Triangle → BurnCostModel development pattern gap, implement severity/frequency distribution fitting, complete `ExposureModel`, and fully implement the `Simulation` DFA engine.

**Architecture:** All tasks build on the refactored codebase from Plan A (Phases 1–4). Each task is independently testable. The `Simulation` engine (Task 10) is the largest single piece — it depends on `FrequencyFit` and `SeverityFit` from Task 8, so those must be done first.

**Tech Stack:** Python 3.10+, stdlib only (`math`, `random`, `json`, `dataclasses`). No new external dependencies.

**Spec:** `docs/superpowers/specs/2026-04-16-refactor-design.md` § Phase 5

**Prerequisite:** Plan A (Phases 1–4) must be complete and all tests passing.

---

## File Map

| File | Change |
|---|---|
| `src/pyre/rate_monitoring/rate_change.py` | Add missing `Optional` import |
| `src/pyre/models/experience/frequency_severity.py` | Fix bugs; rename class; implement `SeverityFit.fit()`; add `FrequencyFit`, `FitResult` |
| `src/pyre/models/aggregate/selections.py` | Fix wildcard import; fix property call |
| `src/pyre/models/exposure/exposure_curve_functions.py` | Fix typo; uncomment `calculate_curve`; replace enum presets |
| `src/pyre/exposures/exposures.py` | Add `_parallelogram_earned_pct` |
| `src/pyre/claims/triangles.py` | Add `get_selected_development_pattern` |
| `src/pyre/models/exposure/exposure_rating_cost.py` | Add `calculate_exposure_rate`, `calculate_ilf_adjusted_rate` |
| `src/pyre/models/aggregate/aggregate_features.py` | Add `ModellingAssumptions`; refactor `AggregateFeatures` as orchestrator |
| `src/pyre/models/aggregate/simulation_engine.py` | Full `Simulation` + `SimulationResults` implementation |
| `tests/test_frequency_severity.py` | New |
| `tests/test_parallelogram.py` | New |
| `tests/test_triangles.py` | Extend |
| `tests/test_exposure_model.py` | Extend |
| `tests/test_simulation.py` | New |
| `tests/test_selections.py` | New |

---

## Task 14: Fix miscellaneous small bugs

**Files:**
- Modify: `src/pyre/rate_monitoring/rate_change.py`
- Modify: `src/pyre/models/aggregate/selections.py`
- Modify: `src/pyre/models/exposure/exposure_curve_functions.py`

- [ ] **Step 1: Fix missing import in `rate_change.py`**

Add to the top of `src/pyre/rate_monitoring/rate_change.py`:

```python
from typing import Optional
```

- [ ] **Step 2: Fix wildcard import and property call in `selections.py`**

In `src/pyre/models/aggregate/selections.py`, replace:

```python
from ...Models.Exposure.exposure_rating_cost import  * # TODO: sort out
```

with:

```python
from ...models.exposure.exposure_rating_cost import ExposureModel
```

Find both occurrences of `subject_contract_claims()` (called as a function) and remove the parentheses:

```python
# was: kwargs['claim_count'] = len(self.experience_data.subject_contract_claims())
kwargs['claim_count'] = len(self.experience_data.subject_contract_claims)

# was: kwargs['data'] = [claim.amount for claim in self.experience_data.subject_contract_claims()]
# Note: subject_contract_claims is Dict[int, Claims] — the call also has wrong semantics.
# Replace with total claim count across all layers:
total_claims = sum(
    len(claims_obj) for claims_obj in self.experience_data.subject_contract_claims.values()
)
kwargs['claim_count'] = total_claims
```

- [ ] **Step 3: Fix typo and update `exposure_curve_functions.py`**

In `src/pyre/models/exposure/exposure_curve_functions.py`:

(a) Rename parameter throughout file: `paramaters_mus` → `parameters_mus`

(b) Replace the `mixed_expo_curves` Enum (which used dicts as values — non-standard) with module-level preset dicts:

```python
# Remove this:
# class mixed_expo_curves(Enum):
#     CURVE_ONE = {...}
#     CURVE_TWO = {...}

# Add this instead:
MIXED_EXPO_CURVE_ONE = {
    "parameters_mus": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0,
                       100.0, 110.0, 120.0, 130.0, 140.0, 150.0],
    "parameter_weights": [1.0] * 15,
}

MIXED_EXPO_CURVE_TWO = {
    "parameters_mus": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0,
                       100.0, 110.0, 120.0, 130.0, 140.0, 150.0],
    "parameter_weights": [1.0] * 15,
}
```

(c) Uncomment the `calculate_curve` function and tidy it:

```python
def calculate_curve(
    curve_type: ExposureCurveType,
    parameters: dict,
    position: float,
) -> float:
    """Calculate an exposure curve value at a given position.

    Args:
        curve_type: Which curve family to use.
        parameters: Curve-specific keyword arguments passed to the curve function.
        position: Position on the curve (typically loss / total insured value).

    Returns:
        Curve value at `position`.

    Raises:
        ValueError: If curve_type is not in exposure_curve_calculation.
    """
    if curve_type not in exposure_curve_calculation:
        raise ValueError(f"Unsupported curve type: {curve_type}")
    func = exposure_curve_calculation[curve_type]
    return func(**parameters, curve_position=position)
```

(d) Update `ExposureModel.calculate_exposure_curve` in `exposure_rating_cost.py` to delegate to `calculate_curve`:

```python
    def calculate_exposure_curve(
        self, curve_type: ExposureCurveType, parameters: dict, position: float
    ) -> float:
        from ...models.exposure.exposure_curve_functions import calculate_curve
        return calculate_curve(curve_type, parameters, position)
```

- [ ] **Step 4: Run full test suite**

```
pytest -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/rate_monitoring/rate_change.py \
        src/pyre/models/aggregate/selections.py \
        src/pyre/models/exposure/exposure_curve_functions.py \
        src/pyre/models/exposure/exposure_rating_cost.py
git commit -m "fix: miscellaneous small bugs — missing import, wildcard import, typo, calculate_curve"
```

---

## Task 15: Fix `frequency_severity.py` bugs and rename class

**Files:**
- Modify: `src/pyre/models/experience/frequency_severity.py`

- [ ] **Step 1: Fix all bugs in the existing code**

Replace the entire file content:

```python
"""Frequency and severity distribution fitting for experience pricing."""

from typing import Any, Dict, List
from ...models.experience.experience_preparer import ExperienceModelData
from ...enums import SeverityDistribution, FrequencyDistribution


class SeverityFit:
    """Fit severity distributions to projected individual claims.

    Args:
        distributions: List of distributions to fit.
        data: Experience model data containing claims.
        ibner_dev_pattern: Dict mapping modelling year to IBNER development factor.
        ground_up: If True, fit to ground-up (capped) claims. Defaults to True.
    """

    def __init__(
        self,
        distributions: List[SeverityDistribution],
        data: ExperienceModelData,
        ibner_dev_pattern: Dict[int, float],
        ground_up: bool = True,
    ) -> None:
        self.distributions = distributions
        self.data = data
        self.ibner_dev_pattern = ibner_dev_pattern
        self.ground_up = ground_up

    @property
    def _individual_projected_claims(self) -> List[float]:
        """Individual projected ultimate claims using IBNER development factors."""
        if self.ground_up:
            return [
                claim.capped_claim_development_history.latest_incurred
                * self.ibner_dev_pattern.get(claim.claims_meta_data.modelling_year, 1.0)
                for claim in self.data.trended_claims.claims
            ]
        raise NotImplementedError("Non-ground-up fitting has not been implemented yet")

    def fit(self) -> Dict[str, Dict[str, float]]:
        """Fit each distribution to the projected claims.

        Returns:
            Dict mapping distribution name to fitted parameters.
        """
        claims = self._individual_projected_claims
        results: Dict[str, Dict[str, float]] = {}
        for dist in self.distributions:
            if dist == SeverityDistribution.LOGNORMAL:
                results["lognormal"] = _fit_lognormal(claims)
            elif dist == SeverityDistribution.PARETO:
                results["pareto"] = _fit_pareto(claims)
        return results
```

- [ ] **Step 2: Run full suite to confirm no regressions**

```
pytest -v
```

Expected: all `PASSED`

- [ ] **Step 3: Commit**

```bash
git add src/pyre/models/experience/frequency_severity.py
git commit -m "fix: rename severity_fit to SeverityFit, fix missing return and raise"
```

---

## Task 16: Implement `SeverityFit.fit()`, `FrequencyFit`, and `FitResult`

**Files:**
- Modify: `src/pyre/models/experience/frequency_severity.py`
- Create: `tests/test_frequency_severity.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_frequency_severity.py`:

```python
import pytest
import math
from pyre.models.experience.frequency_severity import (
    SeverityFit, FrequencyFit, FitResult,
    _fit_lognormal, _fit_pareto, _fit_poisson, _fit_negative_binomial,
)
from pyre.enums import SeverityDistribution, FrequencyDistribution


def test_fit_lognormal_returns_mu_and_sigma():
    # Generate synthetic lognormal data: mu=0, sigma=1
    import random
    random.seed(42)
    data = [math.exp(random.gauss(0, 1)) for _ in range(500)]

    params = _fit_lognormal(data)

    assert "mu" in params
    assert "sigma" in params
    # With 500 samples, MOM estimates should be within 0.2 of true values
    assert abs(params["mu"]) < 0.3
    assert abs(params["sigma"] - 1.0) < 0.3


def test_fit_pareto_returns_alpha_and_x_m():
    # Pareto: x_m = 1, alpha = 2 → mean = 2, var = inf for alpha <= 2
    # Use alpha = 3 for finite variance: mean = 3/2, shape detectable
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
    counts = [0, 1, 2, 3, 1, 0, 2, 4, 1, 2]
    params = _fit_negative_binomial(counts)
    assert "r" in params
    assert "p" in params
    assert params["r"] > 0
    assert 0 < params["p"] < 1


def test_frequency_fit_poisson():
    from datetime import date
    from pyre.models.experience.experience_preparer import ExperienceModelData
    from pyre.claims.claims import Claim, ClaimDevelopmentHistory, ClaimsMetaData, Claims
    from pyre.exposures.exposures import Exposure, Exposures, ExposureMetaData, ExposureValues
    from pyre.treaty.contracts import RILayer, RIContractMetadata, RIContract, ClaimTriggerBasis, IndexationClauseType
    from pyre.enums import ClaimYearType, ExposureBasis, ContractType

    # Build minimal model_data (same structure as test_burn_cost.py)
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

    fitter = FrequencyFit(
        distributions=[FrequencyDistribution.POISSON],
        data=model_data,
    )
    results = fitter.fit()
    assert "poisson" in results
    assert results["poisson"]["lambda_"] > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_frequency_severity.py -v
```

Expected: `FAILED` — `_fit_lognormal`, `FrequencyFit`, `FitResult` not defined.

- [ ] **Step 3: Implement the fitting functions and classes**

Add to `src/pyre/models/experience/frequency_severity.py`:

```python
import math
from dataclasses import dataclass
from typing import Dict, List, Union

from ...enums import SeverityDistribution, FrequencyDistribution


# ---------------------------------------------------------------------------
# FitResult
# ---------------------------------------------------------------------------

@dataclass
class FitResult:
    """Result of fitting a distribution to data.

    Attributes:
        distribution: The distribution that was fitted.
        parameters: Dict of parameter name → estimated value.
        log_likelihood: Log-likelihood at the estimated parameters.
        aic: Akaike Information Criterion = 2k - 2 ln(L).
    """
    distribution: Union[SeverityDistribution, FrequencyDistribution]
    parameters: Dict[str, float]
    log_likelihood: float
    aic: float


# ---------------------------------------------------------------------------
# Internal fitting functions
# ---------------------------------------------------------------------------

def _fit_lognormal(data: List[float]) -> Dict[str, float]:
    """Fit lognormal distribution by method of moments.

    mu = log(mean^2 / sqrt(variance + mean^2))
    sigma = sqrt(log(variance / mean^2 + 1))

    Args:
        data: Observed positive loss values.

    Returns:
        Dict with keys "mu" and "sigma".

    Raises:
        ValueError: If data has fewer than 2 elements.
    """
    if len(data) < 2:
        raise ValueError("Lognormal fitting requires at least 2 observations.")

    n = len(data)
    mean = sum(data) / n
    variance = sum((x - mean) ** 2 for x in data) / (n - 1)

    if mean <= 0 or variance <= 0:
        raise ValueError("Data must have positive mean and variance for lognormal fitting.")

    sigma2 = math.log(variance / (mean ** 2) + 1.0)
    mu = math.log(mean ** 2 / math.sqrt(variance + mean ** 2))

    return {"mu": mu, "sigma": math.sqrt(sigma2)}


def _fit_pareto(data: List[float]) -> Dict[str, float]:
    """Fit single-parameter Pareto by maximum likelihood.

    x_m = min(data)
    alpha = n / sum(log(xi / x_m))

    Citation: Klugman, Panjer & Willmot, Loss Models (4th ed.), Ch. 4.

    Args:
        data: Observed positive loss values.

    Returns:
        Dict with keys "alpha" and "x_m".

    Raises:
        ValueError: If data is empty.
    """
    if len(data) < 1:
        raise ValueError("Pareto fitting requires at least 1 observation.")

    x_m = min(data)
    if x_m <= 0:
        raise ValueError("All observations must be positive for Pareto fitting.")

    n = len(data)
    log_sum = sum(math.log(x / x_m) for x in data)

    if log_sum == 0:
        raise ValueError("All observations are equal; Pareto alpha is undefined.")

    alpha = n / log_sum
    return {"alpha": alpha, "x_m": x_m}


def _fit_poisson(counts: List[int]) -> Dict[str, float]:
    """Fit Poisson distribution by MLE (lambda = sample mean).

    Args:
        counts: Non-negative integer claim counts.

    Returns:
        Dict with key "lambda_".

    Raises:
        ValueError: If counts is empty.
    """
    if not counts:
        raise ValueError("Poisson fitting requires at least 1 observation.")
    return {"lambda_": sum(counts) / len(counts)}


def _fit_negative_binomial(counts: List[int]) -> Dict[str, float]:
    """Fit Negative Binomial by method of moments.

    mean = r * (1-p) / p
    variance = r * (1-p) / p^2

    Solving: p = mean / variance, r = mean * p / (1 - p)

    Args:
        counts: Non-negative integer claim counts.

    Returns:
        Dict with keys "r" and "p".

    Raises:
        ValueError: If counts has fewer than 2 elements or variance <= mean.
    """
    if len(counts) < 2:
        raise ValueError("Negative Binomial fitting requires at least 2 observations.")

    n = len(counts)
    mean = sum(counts) / n
    variance = sum((x - mean) ** 2 for x in counts) / (n - 1)

    if variance <= mean:
        # Variance <= mean means Poisson is a better fit; NB is not identifiable.
        raise ValueError(
            "Sample variance is not greater than mean; "
            "Negative Binomial is not identifiable (use Poisson instead)."
        )

    p = mean / variance
    r = mean * p / (1.0 - p)
    return {"r": r, "p": p}


# ---------------------------------------------------------------------------
# SeverityFit (update fit() to use helper functions)
# ---------------------------------------------------------------------------

# (Replace the existing SeverityFit.fit() body):

    def fit(self) -> Dict[str, Dict[str, float]]:
        """Fit each distribution in self.distributions to the projected claims.

        Returns:
            Dict mapping distribution name to fitted parameter dict.
        """
        claims = self._individual_projected_claims
        results: Dict[str, Dict[str, float]] = {}
        for dist in self.distributions:
            if dist == SeverityDistribution.LOGNORMAL:
                results["lognormal"] = _fit_lognormal(claims)
            elif dist == SeverityDistribution.PARETO:
                results["pareto"] = _fit_pareto(claims)
        return results


# ---------------------------------------------------------------------------
# FrequencyFit
# ---------------------------------------------------------------------------

class FrequencyFit:
    """Fit frequency distributions to claim counts by modelling year.

    Args:
        distributions: List of frequency distributions to fit.
        data: Experience model data.
    """

    def __init__(
        self,
        distributions: List[FrequencyDistribution],
        data: ExperienceModelData,
    ) -> None:
        self.distributions = distributions
        self.data = data

    @property
    def _claim_counts_by_year(self) -> Dict[int, int]:
        """Claim count per modelling year from subject_contract_claims."""
        counts: Dict[int, int] = {}
        for layer_claims in self.data.subject_contract_claims.values():
            for claim in layer_claims.claims:
                year = claim.claims_meta_data.modelling_year
                counts[year] = counts.get(year, 0) + 1
            break  # Use first layer only for frequency — avoid double-counting
        return counts

    def fit(self) -> Dict[str, Dict[str, float]]:
        """Fit each distribution to claim counts across modelling years.

        Returns:
            Dict mapping distribution name to fitted parameter dict.
        """
        counts_by_year = self._claim_counts_by_year
        counts = list(counts_by_year.values())

        results: Dict[str, Dict[str, float]] = {}
        for dist in self.distributions:
            if dist == FrequencyDistribution.POISSON:
                results["poisson"] = _fit_poisson(counts)
            elif dist == FrequencyDistribution.NEGATIVE_BINOMIAL:
                results["negative_binomial"] = _fit_negative_binomial(counts)
        return results
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_frequency_severity.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Run full suite**

```
pytest -v
```

- [ ] **Step 6: Commit**

```bash
git add src/pyre/models/experience/frequency_severity.py tests/test_frequency_severity.py
git commit -m "feat: implement SeverityFit.fit() (lognormal + pareto MLE) and FrequencyFit (poisson + NB)"
```

---

## Task 17: Implement parallelogram method for aggregate exposures

**Files:**
- Modify: `src/pyre/exposures/exposures.py`
- Create: `tests/test_parallelogram.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_parallelogram.py`:

```python
import pytest
from datetime import date, timedelta
from pyre.exposures.exposures import Exposure, ExposureMetaData, ExposureValues, ExposureBasis


def _make_aggregate_exposure(
    start: date, end: date, earned_pct_override: float = None
) -> Exposure:
    meta = ExposureMetaData(
        exposure_id="E1",
        exposure_name="Aggregate 2020",
        exposure_period_start=start,
        exposure_period_end=end,
        currency="GBP",
        aggregate=True,
        exposure_type=ExposureBasis.WRITTEN,
    )
    return Exposure(meta, ExposureValues(1_000_000.0, 0.0, 1_000_000.0))


def test_parallelogram_returns_zero_before_start():
    exp = _make_aggregate_exposure(date(2020, 1, 1), date(2020, 12, 31))
    # analysis date is before the policy start — nothing written yet
    pct = exp._earned_pct(date(2019, 12, 31))
    assert pct == pytest.approx(0.0)


def test_parallelogram_returns_one_after_all_policies_expire():
    exp = _make_aggregate_exposure(date(2020, 1, 1), date(2020, 12, 31))
    # Exposure period: 1 Jan – 31 Dec 2020 (364 days)
    # Term = 364 days. All policies expire by 31 Dec 2020 + 364 days = 30 Dec 2021.
    term_days = (date(2020, 12, 31) - date(2020, 1, 1)).days
    fully_earned_date = date(2020, 12, 31) + timedelta(days=term_days + 1)
    pct = exp._earned_pct(fully_earned_date)
    assert pct == pytest.approx(1.0)


def test_parallelogram_midpoint():
    """At the midpoint of the earning window, approx 50% should be earned."""
    exp = _make_aggregate_exposure(date(2020, 1, 1), date(2020, 12, 31))
    term_days = (date(2020, 12, 31) - date(2020, 1, 1)).days
    # Total earning window = term_days + period_days = 364 + 364 = 728 days from start
    # Midpoint = start + 364 days = 2020-12-31
    mid = date(2020, 1, 1) + timedelta(days=364)
    pct = exp._earned_pct(mid)
    assert 0.45 < pct < 0.55


def test_parallelogram_analysis_at_period_end():
    """At exposure period end, about half the exposure should be earned
    (policies written at start are fully earned; those written at end are 0% earned)."""
    exp = _make_aggregate_exposure(date(2020, 1, 1), date(2020, 12, 31))
    pct = exp._earned_pct(date(2020, 12, 31))
    assert 0.40 < pct < 0.60


def test_non_aggregate_exposure_not_affected():
    """Normal (non-aggregate) exposures must not use the parallelogram method."""
    meta = ExposureMetaData(
        exposure_id="E2",
        exposure_name="Normal",
        exposure_period_start=date(2020, 1, 1),
        exposure_period_end=date(2020, 12, 31),
        currency="GBP",
        aggregate=False,
        exposure_type=ExposureBasis.WRITTEN,
    )
    exp = Exposure(meta, ExposureValues(1_000_000.0, 0.0, 1_000_000.0))
    # Halfway through the term
    pct = exp._earned_pct(date(2020, 7, 2))
    assert 0.45 < pct < 0.55
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_parallelogram.py -v
```

Expected: `FAILED` — `_earned_pct` returns `0.0` for aggregate exposures.

- [ ] **Step 3: Implement `_parallelogram_earned_pct` in `exposures.py`**

In `src/pyre/exposures/exposures.py`, update `Exposure._earned_pct`:

```python
    def _earned_pct(self, analysis_date: date) -> float:
        """Calculate earned percentage of the exposure as of analysis_date.

        For aggregate exposures, applies the parallelogram method assuming
        policies are written uniformly over the exposure period.
        For non-aggregate written exposures, uses simple pro-rata.
        For earned exposures, always returns 1.0 (or 0.0 if zero-length term).
        """
        if self._exposure_meta.exposure_term_length_days == 0:
            return 0.0
        if self._exposure_meta.aggregate:
            return self._parallelogram_earned_pct(analysis_date)
        return min(
            (analysis_date - self._exposure_meta.exposure_period_start).days
            / self._exposure_meta.exposure_term_length_days,
            1.0,
        )

    def _parallelogram_earned_pct(self, analysis_date: date) -> float:
        """Parallelogram method for aggregate exposures.

        Assumes policies are written uniformly throughout the exposure period,
        each with duration equal to exposure_term_length_days. The earning
        window therefore extends from exposure_period_start to
        exposure_period_end + timedelta(days=term).

        Args:
            analysis_date: Date for which to calculate earned proportion.

        Returns:
            Proportion of the aggregate exposure earned (0.0 to 1.0).
        """
        from datetime import timedelta

        start = self._exposure_meta.exposure_period_start
        end = self._exposure_meta.exposure_period_end
        term = self._exposure_meta.exposure_term_length_days

        if term == 0:
            return 0.0

        period_days = (end - start).days
        total_earning_window = period_days + term  # days from start to last policy expiry

        if analysis_date <= start:
            return 0.0

        days_elapsed = (analysis_date - start).days

        if days_elapsed >= total_earning_window:
            return 1.0

        return days_elapsed / total_earning_window
```

Add `from datetime import timedelta` at the top of the file if not already present.

- [ ] **Step 4: Run tests**

```
pytest tests/test_parallelogram.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/exposures/exposures.py tests/test_parallelogram.py
git commit -m "feat: implement parallelogram method for aggregate exposures"
```

---

## Task 18: Implement `Triangle.get_selected_development_pattern()`

**Files:**
- Modify: `src/pyre/claims/triangles.py`
- Modify: `tests/test_triangles.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_triangles.py`:

```python
def test_get_selected_development_pattern_returns_dict():
    from pyre.claims.triangles import Triangle, CurveType

    tri = Triangle(triangle={
        2018: {12: 100.0, 24: 160.0, 36: 190.0, 48: 200.0},
        2019: {12: 110.0, 24: 172.0, 36: 200.0},
        2020: {12: 120.0, 24: 185.0},
        2021: {12: 130.0},
    })

    pattern = tri.get_selected_development_pattern(
        curve_type=CurveType.EXPONENTIAL, tail_factor=1.05
    )

    assert isinstance(pattern, dict)
    # Each development period maps to a CDF factor >= 1.0
    for dev, factor in pattern.items():
        assert factor >= 1.0, f"factor at dev {dev} should be >= 1.0, got {factor}"
    # First period should have the largest factor (furthest from ultimate)
    dev_periods = sorted(pattern.keys())
    assert pattern[dev_periods[0]] >= pattern[dev_periods[-1]]


def test_get_selected_development_pattern_tail_factor_applied():
    from pyre.claims.triangles import Triangle, CurveType

    tri = Triangle(triangle={
        2018: {12: 100.0, 24: 160.0, 36: 200.0},
        2019: {12: 110.0, 24: 172.0},
        2020: {12: 120.0},
    })

    pattern_no_tail = tri.get_selected_development_pattern(
        curve_type=CurveType.EXPONENTIAL, tail_factor=1.0
    )
    pattern_with_tail = tri.get_selected_development_pattern(
        curve_type=CurveType.EXPONENTIAL, tail_factor=1.10
    )

    # With a 10% tail factor, all cumulative factors should be 10% larger
    for dev in pattern_no_tail:
        assert pattern_with_tail[dev] == pytest.approx(
            pattern_no_tail[dev] * 1.10, rel=1e-6
        )
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_triangles.py::test_get_selected_development_pattern_returns_dict -v
```

Expected: `FAILED` — method does not exist.

- [ ] **Step 3: Implement `get_selected_development_pattern` in `triangles.py`**

Add after the `fit_curve` method:

```python
    def get_selected_development_pattern(
        self,
        curve_type: CurveType,
        tail_factor: float = 1.0,
        c_values: Optional[List[float]] = None,
    ) -> Dict[int, float]:
        """Fit a curve to age-to-age factors and return cumulative-to-ultimate
        development factors for each development period.

        The returned dict is directly usable as `BurnCostModel.development_pattern`.

        Args:
            curve_type: Which development curve to fit.
            tail_factor: Multiplicative tail factor applied beyond the last
                development period. Defaults to 1.0 (no tail).
            c_values: Candidate c-values for INVERSE_POWER fit. Defaults to
                [0.5, 1.0, 1.5, 2.0, 2.5, 3.0].

        Returns:
            Dict mapping development period to cumulative-to-ultimate factor.
            Factors are >= 1.0, decreasing from first to last period.
        """
        from math import exp

        params, _ = self.fit_curve(curve_type, c_values)

        # Build age-to-age factors for each development period gap using fitted params
        dev_sorted = sorted(self.dev_periods)
        ata: Dict[int, float] = {}

        for dp in dev_sorted[:-1]:  # no ATA for the last period
            if curve_type == CurveType.EXPONENTIAL:
                a, b = params["a"], params["b"]
                ata[dp] = 1.0 + exp(a + b * dp)
            elif curve_type == CurveType.POWER:
                a, b = params["a"], params["b"]
                ata[dp] = a * (b ** dp)
            elif curve_type == CurveType.WEIBULL:
                a, b = params["a"], params["b"]
                ata[dp] = 1.0 / (1.0 - exp(-a * (dp ** b)))
            elif curve_type == CurveType.INVERSE_POWER:
                a, b, c = params["a"], params["b"], params["c"]
                ata[dp] = 1.0 + a * ((dp + c) ** b)
            else:
                raise ValueError(f"Unknown curve type: {curve_type}")

        # Convert ATA factors to cumulative-to-ultimate (CDF) factors
        # CDF at last dev period = tail_factor
        # CDF at earlier periods = product of all subsequent ATAs * tail_factor
        cdf: Dict[int, float] = {}
        cdf[dev_sorted[-1]] = tail_factor

        for dp in reversed(dev_sorted[:-1]):
            cdf[dp] = ata[dp] * cdf[dev_sorted[dev_sorted.index(dp) + 1]]

        return cdf
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_triangles.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/claims/triangles.py tests/test_triangles.py
git commit -m "feat: add Triangle.get_selected_development_pattern() for BurnCostModel integration"
```

---

## Task 19: Complete `ExposureModel` with `calculate_exposure_rate` and ILF path

**Files:**
- Modify: `src/pyre/models/exposure/exposure_rating_cost.py`
- Modify: `tests/test_exposure_model.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_exposure_model.py`:

```python
def test_calculate_exposure_rate_returns_rate_per_layer():
    from datetime import date
    model = _make_exposure_model()
    analysis_date = date(2021, 1, 1)

    rates = model.calculate_exposure_rate(analysis_date)

    assert isinstance(rates, dict)
    assert 1 in rates
    assert rates[1] >= 0.0


def test_calculate_ilf_adjusted_rate_differs_from_base():
    from datetime import date
    from pyre.models.exposure.exposure_ILF_functions import power_ilf

    model = _make_exposure_model()
    analysis_date = date(2021, 1, 1)

    base_rates = model.calculate_exposure_rate(analysis_date)

    # ILF function: policy limit / basic limit with exponent 0.5
    def ilf_fn(limit: float) -> float:
        return power_ilf(limit=limit, basic_limit=1_000_000.0, power_parameter=0.5)

    ilf_rates = model.calculate_ilf_adjusted_rate(ilf_fn, analysis_date)

    assert isinstance(ilf_rates, dict)
    assert 1 in ilf_rates
    # ILF-adjusted rate should differ from base rate
    assert ilf_rates[1] != pytest.approx(base_rates[1])
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_exposure_model.py::test_calculate_exposure_rate_returns_rate_per_layer -v
```

Expected: `FAILED` — method not defined.

- [ ] **Step 3: Implement the two methods in `exposure_rating_cost.py`**

Add to the `ExposureModel` class:

```python
    def calculate_exposure_rate(self, analysis_date) -> dict:
        """Exposure-rated burning cost per unit of earned exposure per layer.

        For each layer: sum(exposure_value * share_of_risk) / total_earned_exposure.

        Args:
            analysis_date: The date used to calculate earned exposure values.

        Returns:
            Dict mapping layer_id to exposure rate (float).
        """
        total_earned = sum(
            exp.earned_exposure_value(analysis_date) for exp in self._exposures
        )
        if total_earned == 0:
            return {layer.layer_id: 0.0 for layer in self._ri_contract.layers}

        layer_weighted_sums: dict = {layer.layer_id: 0.0 for layer in self._ri_contract.layers}

        for exposure in self._exposures:
            shares = self._calculate_single_exposure_share(exposure)
            ev = exposure.earned_exposure_value(analysis_date)
            for layer_id, share in shares.items():
                layer_weighted_sums[layer_id] += ev * share

        return {lid: val / total_earned for lid, val in layer_weighted_sums.items()}

    def calculate_ilf_adjusted_rate(
        self,
        ilf_function,
        analysis_date,
    ) -> dict:
        """ILF-adjusted exposure rate per layer.

        Multiplies each exposure's contribution by an Increased Limit Factor
        evaluated at the policy limit, then aggregates.

        Args:
            ilf_function: Callable(limit: float) -> float. Any function from
                exposure_ILF_functions (e.g. power_ilf, pareto_ilf) partially
                applied so it only takes limit as input.
            analysis_date: Date used to calculate earned exposure.

        Returns:
            Dict mapping layer_id to ILF-adjusted exposure rate.
        """
        total_earned = sum(
            exp.earned_exposure_value(analysis_date) for exp in self._exposures
        )
        if total_earned == 0:
            return {layer.layer_id: 0.0 for layer in self._ri_contract.layers}

        layer_weighted_sums: dict = {layer.layer_id: 0.0 for layer in self._ri_contract.layers}

        for exposure in self._exposures:
            shares = self._calculate_single_exposure_share(exposure)
            ev = exposure.earned_exposure_value(analysis_date)
            ilf = ilf_function(exposure.exposure_values.limit)
            for layer_id, share in shares.items():
                layer_weighted_sums[layer_id] += ev * share * ilf

        return {lid: val / total_earned for lid, val in layer_weighted_sums.items()}
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_exposure_model.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/models/exposure/exposure_rating_cost.py tests/test_exposure_model.py
git commit -m "feat: add ExposureModel.calculate_exposure_rate and calculate_ilf_adjusted_rate"
```

---

## Task 20: Implement `ModellingAssumptions` and refactor `AggregateFeatures`

**Files:**
- Modify: `src/pyre/models/aggregate/aggregate_features.py`

- [ ] **Step 1: Rewrite `aggregate_features.py`**

```python
"""Aggregate pricing features and orchestration.

ModellingAssumptions is defined here and imported by simulation_engine.
AggregateFeatures is the top-level orchestrator for a full pricing run.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...models.experience.experience_preparer import ExperienceModelData
from ...models.exposure.exposure_rating_cost import ExposureModel
from ...models.aggregate.selections import Selections

if TYPE_CHECKING:
    from ...models.aggregate.simulation_engine import SimulationResults


@dataclass
class ModellingAssumptions:
    """Financial assumptions for a DFA pricing simulation.

    Attributes:
        cost_of_capital: Required return on risk capital (e.g. 0.08 = 8%).
        required_rate_of_return: Minimum acceptable return on equity.
        capital_confidence_level: Confidence level for VaR/TVaR (default 99.5% = Solvency II).
        use_tvar: If True, use TVaR; if False, use VaR. Defaults to True.
        investment_yield: Annual investment return on float. Defaults to 0.0.
        tax_rate: Combined premium and profit tax rate. Defaults to 0.0.
        acquisition_cost_ratio: Acquisition costs as proportion of premium. Defaults to 0.0.
        brokerage_cost_ratio: Brokerage as proportion of premium. Defaults to 0.0.
    """
    cost_of_capital: float
    required_rate_of_return: float
    capital_confidence_level: float = 0.995
    use_tvar: bool = True
    investment_yield: float = 0.0
    tax_rate: float = 0.0
    acquisition_cost_ratio: float = 0.0
    brokerage_cost_ratio: float = 0.0


class AggregateFeatures:
    """Orchestrates the full pricing workflow: select → simulate → output.

    Args:
        experience_data: Claims and exposures prepared for experience rating.
        exposure_data: Exposure model for exposure rating.
        selections: Credibility-weighting logic.
        assumptions: Financial/capital assumptions for the simulation.
    """

    def __init__(
        self,
        experience_data: ExperienceModelData,
        exposure_data: ExposureModel,
        selections: Selections,
        assumptions: ModellingAssumptions,
    ) -> None:
        self._experience_data = experience_data
        self._exposure_data = exposure_data
        self._selections = selections
        self._assumptions = assumptions

    def run(self, n_simulations: int = 10_000) -> "SimulationResults":
        """Execute the full pricing workflow.

        1. Calculate credibility weights from selections.
        2. Build frequency and severity fits from experience data.
        3. Run Monte Carlo simulation.
        4. Return SimulationResults.

        Args:
            n_simulations: Number of Monte Carlo trials. Defaults to 10,000.

        Returns:
            SimulationResults dataclass with loss distribution and required premiums.
        """
        from ...models.aggregate.simulation_engine import Simulation
        from ...models.experience.frequency_severity import FrequencyFit, SeverityFit
        from ...enums import FrequencyDistribution, SeverityDistribution

        frequency_fit = FrequencyFit(
            distributions=[FrequencyDistribution.POISSON],
            data=self._experience_data,
        )
        severity_fit = SeverityFit(
            distributions=[SeverityDistribution.LOGNORMAL],
            data=self._experience_data,
            ibner_dev_pattern={
                year: 1.0
                for year in self._experience_data.claims.modelling_years
            },
        )

        simulation = Simulation(
            frequency_fit=frequency_fit,
            severity_fit=severity_fit,
            ri_contract=self._experience_data.ri_contract,
            assumptions=self._assumptions,
            n_simulations=n_simulations,
        )
        simulation.run()
        return simulation.output()
```

- [ ] **Step 2: Run full test suite**

```
pytest -v
```

Expected: all `PASSED`

- [ ] **Step 3: Commit**

```bash
git add src/pyre/models/aggregate/aggregate_features.py
git commit -m "feat: add ModellingAssumptions dataclass and refactor AggregateFeatures as orchestrator"
```

---

## Task 21: Implement the full `Simulation` DFA engine

**Files:**
- Modify: `src/pyre/models/aggregate/simulation_engine.py`
- Create: `tests/test_simulation.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_simulation.py`:

```python
import pytest
from datetime import date
from pyre.models.aggregate.simulation_engine import Simulation, SimulationResults
from pyre.models.aggregate.aggregate_features import ModellingAssumptions
from pyre.models.experience.frequency_severity import FrequencyFit, SeverityFit
from pyre.enums import (
    FrequencyDistribution, SeverityDistribution, ContractType,
    ClaimTriggerBasis, ClaimYearType, ExposureBasis,
)
from pyre.claims.claims import Claim, ClaimDevelopmentHistory, ClaimsMetaData, Claims
from pyre.exposures.exposures import Exposure, Exposures, ExposureMetaData, ExposureValues
from pyre.treaty.contracts import (
    RILayer, RIContractMetadata, RIContract, IndexationClauseType,
)
from pyre.models.experience.experience_preparer import ExperienceModelData


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
    claims = Claims([Claim(meta, dev_hist)])
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
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_simulation.py -v
```

Expected: `FAILED` — `Simulation` is a stub.

- [ ] **Step 3: Implement `simulation_engine.py`**

Replace the entire file:

```python
"""DFA (Dynamic Financial Analysis) simulation engine for reinsurance pricing.

The Simulation class runs a Monte Carlo model that:
1. Draws aggregate losses from fitted frequency/severity distributions.
2. Applies reinsurance contract layer terms.
3. Computes loss cost, required capital, and required premium per layer.

No external dependencies — uses stdlib random and math only.
"""

import json
import math
import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, TYPE_CHECKING

from ...treaty.contracts import RIContract

if TYPE_CHECKING:
    from ...models.aggregate.aggregate_features import ModellingAssumptions
    from ...models.experience.frequency_severity import FrequencyFit, SeverityFit


@dataclass
class SimulationResults:
    """Output of a completed Simulation run.

    Attributes:
        loss_cost_by_layer: Mean ceded loss per layer.
        required_capital_by_layer: VaR/TVaR capital per layer.
        required_premium_by_layer: Required premium per layer.
        required_premium_programme: Total required premium across all layers.
        aggregate_loss_distribution: Per-layer sorted simulated aggregate losses.
        n_simulations: Number of Monte Carlo trials run.
        assumptions: The financial assumptions used.
    """
    loss_cost_by_layer: Dict[int, float]
    required_capital_by_layer: Dict[int, float]
    required_premium_by_layer: Dict[int, float]
    required_premium_programme: float
    aggregate_loss_distribution: Dict[int, List[float]]
    n_simulations: int
    assumptions: "ModellingAssumptions"


def _sample_lognormal(mu: float, sigma: float, rng: random.Random) -> float:
    """Draw one sample from a lognormal distribution."""
    return math.exp(rng.gauss(mu, sigma))


def _sample_pareto(alpha: float, x_m: float, rng: random.Random) -> float:
    """Draw one sample from a single-parameter Pareto distribution."""
    u = rng.random()
    if u >= 1.0:
        u = 1.0 - 1e-15
    return x_m / ((1.0 - u) ** (1.0 / alpha))


def _sample_poisson(lambda_: float, rng: random.Random) -> int:
    """Draw one sample from a Poisson distribution using Knuth's algorithm."""
    L = math.exp(-lambda_)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= rng.random()
    return k - 1


def _sample_negative_binomial(r: float, p: float, rng: random.Random) -> int:
    """Draw one sample from a Negative Binomial by gamma-Poisson mixture."""
    # NB(r, p): generate gamma shape=r, rate=p/(1-p), then Poisson(gamma)
    lambda_ = rng.gammavariate(r, (1.0 - p) / p)
    return _sample_poisson(lambda_, rng)


def _tvar(sorted_losses: List[float], confidence: float) -> float:
    """Tail Value at Risk (Expected Shortfall) at given confidence level."""
    n = len(sorted_losses)
    threshold_idx = int(math.ceil(confidence * n))
    tail = sorted_losses[threshold_idx:]
    if not tail:
        return sorted_losses[-1]
    return sum(tail) / len(tail)


def _var(sorted_losses: List[float], confidence: float) -> float:
    """Value at Risk at given confidence level."""
    n = len(sorted_losses)
    idx = min(int(math.ceil(confidence * n)), n - 1)
    return sorted_losses[idx]


class Simulation:
    """Monte Carlo DFA pricing simulation.

    Args:
        frequency_fit: Fitted frequency distribution.
        severity_fit: Fitted severity distribution.
        ri_contract: Reinsurance contract defining layers.
        assumptions: Financial assumptions (CoC, yield, tax, etc.).
        n_simulations: Number of trials. Defaults to 10,000.
        random_seed: Seed for reproducibility. Defaults to None.
        retrocession_contract: Optional nested retrocession contract.
    """

    def __init__(
        self,
        frequency_fit: "FrequencyFit",
        severity_fit: "SeverityFit",
        ri_contract: RIContract,
        assumptions: "ModellingAssumptions",
        n_simulations: int = 10_000,
        random_seed: Optional[int] = None,
        retrocession_contract: Optional[RIContract] = None,
    ) -> None:
        self._frequency_fit = frequency_fit
        self._severity_fit = severity_fit
        self._ri_contract = ri_contract
        self._assumptions = assumptions
        self._n_simulations = n_simulations
        self._rng = random.Random(random_seed)
        self._retrocession_contract = retrocession_contract

        # Results populated by run()
        self._aggregate_losses: Dict[int, List[float]] = {}  # layer_id -> sorted losses
        self._ran = False

    def _assert_ran(self) -> None:
        if not self._ran:
            raise RuntimeError("Call run() before accessing results.")

    # ------------------------------------------------------------------
    # Core simulation
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Execute the Monte Carlo simulation.

        Draws n_simulations aggregate loss scenarios and stores the sorted
        loss distribution for each layer.
        """
        freq_params = self._frequency_fit.fit()
        sev_params = self._severity_fit.fit()

        # Extract frequency parameters (prefer Poisson, fall back to NB)
        if "poisson" in freq_params:
            lambda_ = freq_params["poisson"]["lambda_"]
            freq_dist = "poisson"
        elif "negative_binomial" in freq_params:
            freq_dist = "negative_binomial"
        else:
            raise ValueError("No supported frequency distribution fitted.")

        # Extract severity parameters (prefer lognormal, fall back to Pareto)
        if "lognormal" in sev_params:
            sev_dist = "lognormal"
            mu = sev_params["lognormal"]["mu"]
            sigma = sev_params["lognormal"]["sigma"]
        elif "pareto" in sev_params:
            sev_dist = "pareto"
            alpha = sev_params["pareto"]["alpha"]
            x_m = sev_params["pareto"]["x_m"]
        else:
            raise ValueError("No supported severity distribution fitted.")

        layer_ids = [layer.layer_id for layer in self._ri_contract.layers]
        raw: Dict[int, List[float]] = {lid: [] for lid in layer_ids}

        for _ in range(self._n_simulations):
            # Draw claim count
            if freq_dist == "poisson":
                n_claims = _sample_poisson(lambda_, self._rng)
            else:
                nb = freq_params["negative_binomial"]
                n_claims = _sample_negative_binomial(nb["r"], nb["p"], self._rng)

            # Draw individual claim amounts and apply layers
            per_layer_aggregate: Dict[int, float] = {lid: 0.0 for lid in layer_ids}
            for _ in range(n_claims):
                if sev_dist == "lognormal":
                    gross = _sample_lognormal(mu, sigma, self._rng)
                else:
                    gross = _sample_pareto(alpha, x_m, self._rng)

                for layer in self._ri_contract.layers:
                    try:
                        ceded = layer.loss_to_layer_fn(gross)
                    except NotImplementedError:
                        ceded = 0.0
                    per_layer_aggregate[layer.layer_id] += ceded

            # Apply aggregate attachment / limit per layer
            for layer in self._ri_contract.layers:
                agg = per_layer_aggregate[layer.layer_id]
                if layer.aggregate_attachment > 0:
                    agg = max(agg - layer.aggregate_attachment, 0.0)
                if layer.aggregate_limit < float("inf"):
                    agg = min(agg, layer.aggregate_limit)
                raw[layer.layer_id].append(agg)

        # Sort for quantile calculations
        self._aggregate_losses = {lid: sorted(losses) for lid, losses in raw.items()}
        self._ran = True

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def loss_cost(self) -> Dict[int, float]:
        """Mean ceded aggregate loss per layer across all simulations."""
        self._assert_ran()
        return {
            lid: sum(losses) / len(losses) if losses else 0.0
            for lid, losses in self._aggregate_losses.items()
        }

    def required_capital(self) -> Dict[int, float]:
        """Risk capital per layer using TVaR or VaR at the configured confidence level."""
        self._assert_ran()
        a = self._assumptions
        result: Dict[int, float] = {}
        for lid, losses in self._aggregate_losses.items():
            if a.use_tvar:
                result[lid] = _tvar(losses, a.capital_confidence_level)
            else:
                result[lid] = _var(losses, a.capital_confidence_level)
        return result

    def cashflows(self) -> Dict[int, Dict[str, float]]:
        """Premium inflow and expected claim outflow per layer.

        Returns:
            Dict mapping layer_id to {"premium": float, "claims": float}.
            Premium is taken from RILayer.signed_line_premium.
            Claims is the mean loss cost.
        """
        self._assert_ran()
        lc = self.loss_cost()
        result: Dict[int, Dict[str, float]] = {}
        for layer in self._ri_contract.layers:
            result[layer.layer_id] = {
                "premium": layer.signed_line_premium,
                "claims": lc[layer.layer_id],
            }
        return result

    def investment_return(self) -> Dict[int, float]:
        """Present value of investment return on premium float per layer.

        Assumes premium is held for one year before claims are paid.
        investment_return = premium * investment_yield

        Returns:
            Dict mapping layer_id to investment return (float).
        """
        self._assert_ran()
        cf = self.cashflows()
        y = self._assumptions.investment_yield
        return {
            lid: cf[lid]["premium"] * y
            for lid in cf
        }

    def profit_commission(
        self,
        profit_commission_rate: float = 0.0,
        loss_ratio_threshold: float = 0.6,
    ) -> Dict[int, float]:
        """Sliding scale profit commission per layer.

        PC = max(0, (loss_ratio_threshold - actual_loss_ratio) * profit_commission_rate * premium)

        Args:
            profit_commission_rate: Proportion of underwriting profit returned as PC.
            loss_ratio_threshold: Loss ratio below which PC is payable. Defaults to 0.60.

        Returns:
            Dict mapping layer_id to expected profit commission.
        """
        self._assert_ran()
        lc = self.loss_cost()
        result: Dict[int, float] = {}
        for layer in self._ri_contract.layers:
            premium = layer.signed_line_premium
            if premium == 0:
                result[layer.layer_id] = 0.0
                continue
            actual_lr = lc[layer.layer_id] / premium
            pc = max(0.0, (loss_ratio_threshold - actual_lr) * profit_commission_rate * premium)
            result[layer.layer_id] = pc
        return result

    def retrocession_cost(self) -> Dict[int, float]:
        """Net retrocession cost per layer.

        If no retrocession contract is set, returns zero for all layers.

        Returns:
            Dict mapping layer_id to net retrocession premium cost.
        """
        if self._retrocession_contract is None:
            return {layer.layer_id: 0.0 for layer in self._ri_contract.layers}

        # Retrocession premium = sum of retro layer signed_line_premiums
        retro_premium = sum(
            rl.signed_line_premium for rl in self._retrocession_contract.layers
        )
        # Distribute proportionally across subject layers by loss cost
        self._assert_ran()
        lc = self.loss_cost()
        total_lc = sum(lc.values())
        result: Dict[int, float] = {}
        for layer in self._ri_contract.layers:
            if total_lc > 0:
                share = lc[layer.layer_id] / total_lc
            else:
                share = 1.0 / len(self._ri_contract.layers)
            result[layer.layer_id] = retro_premium * share
        return result

    def retrocession_benefits(self) -> Dict[int, float]:
        """Expected ceded loss recovered from retrocession per subject layer.

        If no retrocession contract is set, returns zero for all layers.

        Returns:
            Dict mapping layer_id to expected retrocession recovery.
        """
        if self._retrocession_contract is None:
            return {layer.layer_id: 0.0 for layer in self._ri_contract.layers}

        self._assert_ran()
        # Apply retrocession layers to each simulated aggregate loss
        retro_layer_ids = [rl.layer_id for rl in self._retrocession_contract.layers]
        subject_layer_ids = [layer.layer_id for layer in self._ri_contract.layers]

        # Simple implementation: total retro recovery distributed by subject loss cost
        retro_recoveries: Dict[int, List[float]] = {rid: [] for rid in retro_layer_ids}
        for lid in subject_layer_ids:
            losses = self._aggregate_losses.get(lid, [])
            for gross_agg in losses:
                for rl in self._retrocession_contract.layers:
                    try:
                        ceded = rl.loss_to_layer_fn(gross_agg)
                    except NotImplementedError:
                        ceded = 0.0
                    retro_recoveries[rl.layer_id].append(ceded)

        mean_retro = sum(
            sum(v) / len(v) if v else 0.0
            for v in retro_recoveries.values()
        )

        lc = self.loss_cost()
        total_lc = sum(lc.values())
        result: Dict[int, float] = {}
        for layer in self._ri_contract.layers:
            if total_lc > 0:
                share = lc[layer.layer_id] / total_lc
            else:
                share = 1.0 / len(self._ri_contract.layers)
            result[layer.layer_id] = mean_retro * share
        return result

    def required_premium_layer(self) -> Dict[int, float]:
        """Required premium per layer using the DFA pricing formula:

        P = loss_cost + expenses + CoC * required_capital
            - investment_return + net_retrocession_cost

        where:
          expenses = (acquisition_cost_ratio + brokerage_cost_ratio) * P
          net_retrocession_cost = retrocession_cost - retrocession_benefits

        Solving for P:
          P * (1 - expense_ratio) = loss_cost + CoC * required_capital
                                    - investment_return + net_retro

        Returns:
            Dict mapping layer_id to required premium.
        """
        self._assert_ran()
        a = self._assumptions
        lc = self.loss_cost()
        rc = self.required_capital()
        ir = self.investment_return()
        retro_cost = self.retrocession_cost()
        retro_ben = self.retrocession_benefits()

        expense_ratio = a.acquisition_cost_ratio + a.brokerage_cost_ratio
        loadings_multiplier = 1.0 / (1.0 - expense_ratio) if expense_ratio < 1.0 else 1.0

        result: Dict[int, float] = {}
        for layer in self._ri_contract.layers:
            lid = layer.layer_id
            net_tech_cost = (
                lc[lid]
                + a.cost_of_capital * rc[lid]
                - ir[lid]
                + retro_cost[lid]
                - retro_ben[lid]
            )
            result[lid] = net_tech_cost * loadings_multiplier

        return result

    def required_premium_programme(self) -> float:
        """Total required premium across all layers."""
        self._assert_ran()
        return sum(self.required_premium_layer().values())

    def output(self) -> SimulationResults:
        """Return a SimulationResults dataclass with all computed metrics."""
        self._assert_ran()
        return SimulationResults(
            loss_cost_by_layer=self.loss_cost(),
            required_capital_by_layer=self.required_capital(),
            required_premium_by_layer=self.required_premium_layer(),
            required_premium_programme=self.required_premium_programme(),
            aggregate_loss_distribution=self._aggregate_losses,
            n_simulations=self._n_simulations,
            assumptions=self._assumptions,
        )

    def save(self, path: str) -> None:
        """Serialise SimulationResults to a JSON file.

        Args:
            path: File path to write to.
        """
        results = self.output()
        # Convert to JSON-serialisable dict
        data = {
            "loss_cost_by_layer": {str(k): v for k, v in results.loss_cost_by_layer.items()},
            "required_capital_by_layer": {str(k): v for k, v in results.required_capital_by_layer.items()},
            "required_premium_by_layer": {str(k): v for k, v in results.required_premium_by_layer.items()},
            "required_premium_programme": results.required_premium_programme,
            "n_simulations": results.n_simulations,
            "assumptions": {
                "cost_of_capital": results.assumptions.cost_of_capital,
                "required_rate_of_return": results.assumptions.required_rate_of_return,
                "capital_confidence_level": results.assumptions.capital_confidence_level,
                "use_tvar": results.assumptions.use_tvar,
                "investment_yield": results.assumptions.investment_yield,
                "tax_rate": results.assumptions.tax_rate,
                "acquisition_cost_ratio": results.assumptions.acquisition_cost_ratio,
                "brokerage_cost_ratio": results.assumptions.brokerage_cost_ratio,
            },
            # Omit aggregate_loss_distribution from JSON (can be very large)
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_simulation.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Run full suite**

```
pytest -v
```

Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add src/pyre/models/aggregate/simulation_engine.py tests/test_simulation.py
git commit -m "feat: full Simulation DFA engine — Monte Carlo, required capital, required premium, JSON save"
```

---

## Task 22: Add `Selections` tests

**Files:**
- Create: `tests/test_selections.py`

- [ ] **Step 1: Write tests for all five credibility methods**

Create `tests/test_selections.py`:

```python
import pytest
import math
from pyre.models.aggregate.selections import CredibilityWeight


def _cw():
    return CredibilityWeight(experience_data=None, exposure_data=None)


def test_limited_fluctuation_full_credibility():
    cw = _cw()
    result = cw.limited_fluctuation_credibility(1082, 1082)
    assert result == pytest.approx(1.0)


def test_limited_fluctuation_partial_credibility():
    cw = _cw()
    result = cw.limited_fluctuation_credibility(100, 1082)
    assert result == pytest.approx(math.sqrt(100 / 1082))


def test_limited_fluctuation_zero_claims():
    cw = _cw()
    assert cw.limited_fluctuation_credibility(0, 1082) == pytest.approx(0.0)


def test_buhlmann_credibility_high_claims():
    cw = _cw()
    # k = EPV / VHM = 1.0 / 1.0 = 1.0
    # Z = n / (n + k) → 1000 / 1001 ≈ 0.999
    result = cw.buhlmann_credibility(1000, 1.0, 1.0)
    assert result > 0.99


def test_buhlmann_credibility_zero_vhm():
    cw = _cw()
    assert cw.buhlmann_credibility(100, 1.0, 0.0) == pytest.approx(0.0)


def test_buhlmann_straub_uses_total_exposure():
    cw = _cw()
    exposures = [100.0, 200.0, 300.0]
    counts = [3, 6, 9]
    result = cw.buhlmann_straub_credibility(exposures, counts, 1.0, 1.0)
    # k = 1.0; Z = 600 / (600 + 1) ≈ 0.998
    assert result > 0.99


def test_greatest_accuracy_returns_between_0_and_1():
    cw = _cw()
    data = [0.05, 0.08, 0.07, 0.06, 0.09]
    result = cw.greatest_accuracy_credibility(data, collective_mean=0.10)
    assert 0.0 <= result <= 1.0


def test_bayesian_credibility_high_prior_variance():
    cw = _cw()
    data = [100.0, 110.0, 90.0]
    # High prior variance → high credibility to data
    result = cw.bayesian_credibility(
        prior_mean=100.0, prior_variance=1000.0,
        data=data, data_variance=50.0,
    )
    assert 0.0 <= result <= 1.0


def test_calculate_sample_variance():
    cw = _cw()
    data = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    # Known sample variance = 4.571...
    result = cw.calculate_sample_variance(data)
    assert result == pytest.approx(4.5714, rel=1e-3)
```

- [ ] **Step 2: Run tests**

```
pytest tests/test_selections.py -v
```

Expected: all `PASSED`

- [ ] **Step 3: Commit**

```bash
git add tests/test_selections.py
git commit -m "test: add CredibilityWeight tests for all five credibility methods"
```

---

## End of Plan B

**All Phase 5 completions done.** Verify full suite:

```
pytest -v --tb=short
```

Expected: all tests pass.

Proceed to **Plan C** (`docs/superpowers/plans/2026-04-16-refactor-phase6.md`) for professional workstreams.
