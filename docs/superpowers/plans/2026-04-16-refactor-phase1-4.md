# pyRE Refactor — Phases 1–4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix six runtime bugs, eliminate Java-style boilerplate with dataclasses, rename packages to Python conventions, centralise all enums, define a public API surface, and add caching to expensive computed properties.

**Architecture:** Sequential phases — each phase leaves the test suite green before the next begins. Phase 3 (rename) is the riskiest step; it is isolated as a single git operation followed by an import-update pass. No backward compatibility shims — all old import paths are deleted.

**Tech Stack:** Python 3.10+, stdlib only (`dataclasses`, `functools.cached_property`), pytest, git mv for package rename.

**Spec:** `docs/superpowers/specs/2026-04-16-refactor-design.md`

---

## File Map

### Phase 1 — Files modified
| File | Change |
|---|---|
| `src/pyre/Models/trending.py` | Fix property call syntax on `modelling_year` and `exposure_values` |
| `src/pyre/claims/triangles.py` | Fix `from_claims()` iteration bug + IBNER formula |
| `src/pyre/treaty/contracts.py` | Fix `loss_to_layer_fn()` lambda/raise bugs |
| `src/pyre/Models/Exposure/exposure_rating_cost.py` | Fix share calculation indentation + missing import |
| `src/pyre/Models/Experience/burn_cost.py` | Fix silent exception swallowing |
| `tests/test_trending.py` | Add regression tests |
| `tests/test_triangles.py` | Add regression tests |
| `tests/test_treaty.py` | Add regression tests |
| `tests/test_burn_cost.py` | New file |

### Phase 2 — Files modified
| File | Change |
|---|---|
| `src/pyre/claims/claims.py` | `ClaimsMetaData`, `ClaimDevelopmentHistory` → `@dataclass` |
| `src/pyre/exposures/exposures.py` | `ExposureMetaData`, `ExposureValues` → `@dataclass` |
| `src/pyre/treaty/contracts.py` | `RILayer`, `RIContractMetadata` → `@dataclass` |

### Phase 3 — Files created/renamed/modified
| File | Change |
|---|---|
| `src/pyre/Models/` → `src/pyre/models/` | `git mv` (+ sub-renames below) |
| `src/pyre/models/Experience/` → `src/pyre/models/experience/` | `git mv` |
| `src/pyre/models/Exposure/` → `src/pyre/models/exposure/` | `git mv` |
| `src/pyre/models/AggregateFeatures/` → `src/pyre/models/aggregate/` | `git mv` |
| `src/pyre/enums.py` | New — all enumerations |
| `src/pyre/__init__.py` | New — public API |
| `src/pyre/py.typed` | New — PEP 561 marker |
| `src/pyre/treaty/contract_types.py` | Deleted (ContractType moves to enums.py) |
| All `src/pyre/**/*.py` | Update imports to new paths + enums.py |

### Phase 4 — Files modified
| File | Change |
|---|---|
| `src/pyre/models/experience/experience_preparer.py` | `cached_property` + cache invalidation |

---

## Phase 1: Bug Fixes

---

### Task 1: Fix `Trending.trend_exposures()` property call bug

**Files:**
- Modify: `src/pyre/Models/trending.py` lines 95–96
- Modify: `tests/test_trending.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_trending.py`:

```python
def test_trend_exposures_returns_trended_values():
    """Regression test: trend_exposures() was calling modelling_year() and
    exposure_values() as functions — both are properties. This test verifies
    the trended exposure value is 1000 * 1.05 = 1050.0."""
    from pyre.Models.trending import Trending
    from pyre.exposures.exposures import (
        Exposure, Exposures, ExposureMetaData, ExposureValues, ExposureBasis,
    )
    from datetime import date

    meta = ExposureMetaData(
        exposure_id="E1",
        exposure_name="Test Exposure",
        exposure_period_start=date(2020, 1, 1),
        exposure_period_end=date(2020, 12, 31),
        currency="GBP",
        exposure_type=ExposureBasis.EARNED,
    )
    values = ExposureValues(exposure_value=1000.0, attachment_point=0.0, limit=1_000_000.0)
    exposures = Exposures([Exposure(meta, values)])

    trending = Trending(
        exposure_trend_factors={2020: 1.05},
        claim_trend_factors={2020: 1.05},
        base_year=2021,
    )

    result = trending.trend_exposures(exposures)

    assert len(result) == 1
    assert result[0].exposure_values.exposure_value == pytest.approx(1050.0)
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_trending.py::test_trend_exposures_returns_trended_values -v
```

Expected: `FAILED` — `TypeError: 'int' object is not callable`

- [ ] **Step 3: Fix `trending.py`**

In `src/pyre/Models/trending.py`, lines 95–103:

```python
    def trend_exposures(self, exposures: Exposures) -> Exposures:
        trended_exposures = []

        for exposure in exposures:
            origin_year = exposure.modelling_year          # was: exposure.modelling_year()
            trend_factor = self.calculate_trend_factor(origin_year, for_claims=False)

            original_values = exposure.exposure_values     # was: exposure.exposure_values()
            trended_value = original_values.exposure_value * trend_factor

            new_values = ExposureValues(
                exposure_value=trended_value,
                attachment_point=original_values.attachment_point,
                limit=original_values.limit,
            )
            new_exposure = Exposure(
                exposure_meta=exposure.exposure_meta,
                exposure_values=new_values,
            )
            trended_exposures.append(new_exposure)

        return Exposures(trended_exposures)
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_trending.py::test_trend_exposures_returns_trended_values -v
```

Expected: `PASSED`

- [ ] **Step 5: Run full test suite to check no regressions**

```
pytest -v
```

Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add src/pyre/Models/trending.py tests/test_trending.py
git commit -m "fix: correct property call syntax in Trending.trend_exposures"
```

---

### Task 2: Fix `Triangle.from_claims()` iteration bugs

**Files:**
- Modify: `src/pyre/claims/triangles.py` lines 282–303
- Modify: `tests/test_triangles.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_triangles.py`:

```python
def test_triangle_from_claims_builds_correctly():
    """Regression: from_claims() called claim.modelling_year (doesn't exist)
    and iterated dev_history.items() on a List[float]."""
    from pyre.claims.triangles import Triangle
    from pyre.claims.claims import (
        Claim, ClaimDevelopmentHistory, ClaimsMetaData, Claims, ClaimYearType,
    )
    from datetime import date

    meta = ClaimsMetaData(
        claim_id="C1",
        currency="GBP",
        contract_limit=1_000_000.0,
        contract_deductible=0.0,
        claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=date(2020, 6, 1),
    )
    dev_hist = ClaimDevelopmentHistory(
        development_months=[12, 24, 36],
        cumulative_dev_paid=[100.0, 150.0, 175.0],
        cumulative_dev_incurred=[200.0, 220.0, 225.0],
    )
    claims = Claims([Claim(meta, dev_hist)])

    triangle = Triangle.from_claims(claims, value_type="incurred")

    assert triangle[2020, 12] == pytest.approx(200.0)
    assert triangle[2020, 24] == pytest.approx(220.0)
    assert triangle[2020, 36] == pytest.approx(225.0)


def test_triangle_from_claims_paid():
    from pyre.claims.triangles import Triangle
    from pyre.claims.claims import (
        Claim, ClaimDevelopmentHistory, ClaimsMetaData, Claims, ClaimYearType,
    )
    from datetime import date

    meta = ClaimsMetaData(
        claim_id="C1",
        currency="GBP",
        contract_limit=1_000_000.0,
        contract_deductible=0.0,
        claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
        loss_date=date(2020, 6, 1),
    )
    dev_hist = ClaimDevelopmentHistory(
        development_months=[12, 24],
        cumulative_dev_paid=[100.0, 150.0],
        cumulative_dev_incurred=[200.0, 220.0],
    )
    claims = Claims([Claim(meta, dev_hist)])

    triangle = Triangle.from_claims(claims, value_type="paid")

    assert triangle[2020, 12] == pytest.approx(100.0)
    assert triangle[2020, 24] == pytest.approx(150.0)
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_triangles.py::test_triangle_from_claims_builds_correctly tests/test_triangles.py::test_triangle_from_claims_paid -v
```

Expected: `FAILED` — `AttributeError: 'Claim' object has no attribute 'modelling_year'`

- [ ] **Step 3: Fix `Triangle.from_claims()` in `triangles.py`**

Replace the `from_claims` classmethod (lines 258–304):

```python
    @classmethod
    def from_claims(cls, claims: Claims, value_type: str = "incurred") -> "Triangle":
        """
        Construct a Triangle from a Claims object.

        Args:
            claims: Claims object containing claim data.
            value_type: "incurred" or "paid".

        Returns:
            A new Triangle object with aggregated claim values by origin year
            and development month.
        """
        if value_type not in ("incurred", "paid"):
            raise ValueError(f"value_type must be 'incurred' or 'paid', got '{value_type}'")

        origin_years = claims.modelling_years
        triangle: Dict[int, Dict[int, float]] = {year: {} for year in origin_years}

        for claim in claims:
            origin_year = claim.claims_meta_data.modelling_year
            dev_hist = claim.capped_claim_development_history

            if value_type == "incurred":
                values = dev_hist.cumulative_dev_incurred
            else:
                values = dev_hist.cumulative_dev_paid

            for dev_period, value in zip(dev_hist.development_months, values):
                if origin_year in triangle:
                    triangle[origin_year][dev_period] = (
                        triangle[origin_year].get(dev_period, 0.0) + value
                    )

        return cls(triangle=triangle)
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_triangles.py::test_triangle_from_claims_builds_correctly tests/test_triangles.py::test_triangle_from_claims_paid -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/claims/triangles.py tests/test_triangles.py
git commit -m "fix: correct iteration in Triangle.from_claims"
```

---

### Task 3: Fix `IBNERPatternExtractor._compute_N_and_D()`

**Files:**
- Modify: `src/pyre/claims/triangles.py` lines 460–483
- Modify: `tests/test_ibner_pattern_extractor.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ibner_pattern_extractor.py`:

```python
def test_ibner_n_and_d_are_not_both_zero():
    """Regression: N and D triangles both evaluated to zero for every cell
    because D = prev - current and N = current - prev + D = 0."""
    from pyre.claims.triangles import Triangle, IBNERPatternExtractor

    # Simple growing triangle: 2 origin years, 3 dev periods
    tri = Triangle(triangle={
        2020: {12: 100.0, 24: 160.0, 36: 200.0},
        2021: {12: 110.0, 24: 170.0},
    })
    extractor = IBNERPatternExtractor(tri)
    pattern = extractor.get_IBNER_pattern()

    # D at dev 12 should be None (no prior period)
    assert pattern[12] is None
    # D at dev 24 should be positive (IBNER development)
    assert pattern[24] is not None
    assert pattern[24] > 0
    # N at dev 24 should not be zero
    n_triangle = extractor.get_N_triangle()
    assert n_triangle[2020][24] != 0.0


def test_ibner_pattern_sums_to_total_development():
    """N + D at each period should equal total increment from prior period."""
    from pyre.claims.triangles import Triangle, IBNERPatternExtractor

    tri = Triangle(triangle={
        2020: {12: 100.0, 24: 160.0, 36: 190.0},
        2021: {12: 120.0, 24: 180.0},
    })
    extractor = IBNERPatternExtractor(tri)
    n = extractor.get_N_triangle()
    d = extractor.get_D_triangle()

    # For origin year 2020, dev 24:
    # total increment = 160 - 100 = 60
    # N[2020][24] + D[2020][24] should = 60
    total = n[2020][24] + d[2020][24]
    assert total == pytest.approx(160.0 - 100.0, rel=1e-6)
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_ibner_pattern_extractor.py::test_ibner_n_and_d_are_not_both_zero tests/test_ibner_pattern_extractor.py::test_ibner_pattern_sums_to_total_development -v
```

Expected: `FAILED`

- [ ] **Step 3: Fix `_compute_N_and_D()` in `triangles.py`**

Replace the `_compute_N_and_D` method:

```python
    def _compute_N_and_D(self) -> None:
        """
        Compute N (new IBNR emergence) and D (IBNER development) triangles.

        Per Schnieper (1991): at each development step d from d-1:
          - D[oy, d] = triangle[oy, d-1] * (f - 1)
            where f is the volume-weighted age-to-age factor for that step.
            This represents IBNER: development of already-reported claims.
          - N[oy, d] = (triangle[oy, d] - triangle[oy, d-1]) - D[oy, d]
            This represents new IBNR: emergence of previously unreported claims.

        Citation: Schnieper, R. (1991). Separating True IBNR and IBNER Claims.
        ASTIN Bulletin, 21(1), 111-127.
        https://www.casact.org/sites/default/files/database/astin_vol21no1_111.pdf
        """
        # Step 1: compute volume-weighted ATA factors across all origin years
        ata: Dict[int, float] = {}
        for i in range(len(self.dev_periods) - 1):
            d_curr = self.dev_periods[i]
            d_next = self.dev_periods[i + 1]
            pairs = [
                (oy, d_curr, d_next)
                for oy in self.origin_years
                if self.triangle[oy].get(d_curr) is not None
                and self.triangle[oy].get(d_next) is not None
            ]
            numerator = sum(self.triangle[oy][d_next] for oy, _, _ in pairs)
            denominator = sum(self.triangle[oy][d_curr] for oy, _, _ in pairs)
            ata[d_curr] = numerator / denominator if denominator > 0 else 1.0

        # Step 2: fill N and D triangles
        for oy in self.origin_years:
            for idx, d in enumerate(self.dev_periods):
                current = self.triangle[oy].get(d)
                if idx == 0:
                    # First development period: all emergence, no prior period to develop
                    self.N[oy][d] = current
                    self.D[oy][d] = None
                else:
                    prev_d = self.dev_periods[idx - 1]
                    prev = self.triangle[oy].get(prev_d)
                    if current is None or prev is None:
                        self.N[oy][d] = None
                        self.D[oy][d] = None
                    else:
                        f = ata.get(prev_d, 1.0)
                        ibner = prev * (f - 1.0)
                        self.D[oy][d] = ibner
                        self.N[oy][d] = (current - prev) - ibner
```

Add the `Dict` import if not already present at top of `triangles.py`:
```python
from typing import Dict, List, Optional, Union, Tuple, Any, Iterator
```
(Already present — no change needed.)

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_ibner_pattern_extractor.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/claims/triangles.py tests/test_ibner_pattern_extractor.py
git commit -m "fix: correct IBNER N and D formula per Schnieper (1991)"
```

---

### Task 4: Fix `RILayer.loss_to_layer_fn()`

**Files:**
- Modify: `src/pyre/treaty/contracts.py` lines 210–217
- Modify: `tests/test_treaty.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_treaty.py`:

```python
import pytest
from datetime import date
from pyre.treaty.contracts import RILayer, RIContractMetadata, ClaimTriggerBasis, IndexationClauseType
from pyre.treaty.contract_types import ContractType


def _make_xol_layer() -> RILayer:
    return RILayer(
        layer_id=1,
        layer_name="1m xs 1m",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=1_000_000.0,
        occurrence_limit=1_000_000.0,
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[10_000_000.0],
        full_subject_premium=500_000.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=1,
        reinstatement_cost={1: 1.0},
    )


def test_loss_to_layer_fn_xol_below_attachment():
    layer = _make_xol_layer()
    assert layer.loss_to_layer_fn(500_000.0) == pytest.approx(0.0)


def test_loss_to_layer_fn_xol_in_layer():
    layer = _make_xol_layer()
    assert layer.loss_to_layer_fn(1_500_000.0) == pytest.approx(500_000.0)


def test_loss_to_layer_fn_xol_above_limit():
    layer = _make_xol_layer()
    assert layer.loss_to_layer_fn(5_000_000.0) == pytest.approx(1_000_000.0)


def test_loss_to_layer_fn_quota_share_passes_through():
    layer = RILayer(
        layer_id=2,
        layer_name="QS",
        layer_type=ContractType.QUOTA_SHARE,
        occurrence_attachment=0.0,
        occurrence_limit=float("inf"),
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[1_000_000.0],
        full_subject_premium=100_000.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=0,
        reinstatement_cost={},
    )
    assert layer.loss_to_layer_fn(250_000.0) == pytest.approx(250_000.0)


def test_loss_to_layer_fn_surplus_share_raises():
    layer = RILayer(
        layer_id=3,
        layer_name="SS",
        layer_type=ContractType.SURPLUS_SHARE,
        occurrence_attachment=0.0,
        occurrence_limit=float("inf"),
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=[],
        subject_lob_exposure_amounts=[],
        full_subject_premium=0.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=0,
        reinstatement_cost={},
    )
    with pytest.raises(NotImplementedError):
        layer.loss_to_layer_fn(100_000.0)
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_treaty.py::test_loss_to_layer_fn_xol_below_attachment tests/test_treaty.py::test_loss_to_layer_fn_surplus_share_raises -v
```

Expected: `FAILED`

- [ ] **Step 3: Replace `loss_to_layer_fn` in `contracts.py`**

Replace lines 210–217:

```python
    def loss_to_layer_fn(self, gross_amount: float) -> float:
        """Apply this layer's terms to a gross loss amount.

        Args:
            gross_amount: Ground-up (or ceded-in) loss amount.

        Returns:
            The amount ceded to this layer.

        Raises:
            NotImplementedError: If layer_type is SURPLUS_SHARE.
        """
        if self.layer_type == ContractType.SURPLUS_SHARE:
            raise NotImplementedError("Surplus share loss function not yet implemented")
        if self.layer_type == ContractType.QUOTA_SHARE:
            return gross_amount
        func = layer_loss_calculation[self.layer_type]
        return func(gross_amount, self.occurrence_attachment, self.occurrence_limit)
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_treaty.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/treaty/contracts.py tests/test_treaty.py
git commit -m "fix: correct loss_to_layer_fn — raise NotImplementedError for surplus share, remove broken lambda"
```

---

### Task 5: Fix `BurnCostModel.calculate_burn_cost()` silent exception swallowing

**Files:**
- Modify: `src/pyre/Models/Experience/burn_cost.py` lines 426–429
- Create: `tests/test_burn_cost.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_burn_cost.py`:

```python
import pytest
from datetime import date
from pyre.Models.Experience.burn_cost import BurnCostModel, ProjectionMethods
from pyre.Models.Experience.experience_preparer import ExperienceModelData
from pyre.claims.claims import Claim, ClaimDevelopmentHistory, ClaimsMetaData, Claims, ClaimYearType
from pyre.exposures.exposures import Exposure, Exposures, ExposureMetaData, ExposureValues, ExposureBasis
from pyre.treaty.contracts import RILayer, RIContractMetadata, RIContract, ClaimTriggerBasis, IndexationClauseType
from pyre.treaty.contract_types import ContractType


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
    assert result[2020] == pytest.approx(80_000.0 / 1_000_000.0)


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
    import pyre.Models.Experience.burn_cost as bc_module

    model_data = _make_model_data()
    model = BurnCostModel(
        model_data=model_data,
        layer_id=1,
        projection_methods={2020: ProjectionMethods.CHAINLADDER},
        development_pattern={2020: 1.0},
    )

    # Force the projection function to raise
    def bad_fn(*args, **kwargs):
        raise RuntimeError("intentional failure")

    monkeypatch.setitem(
        bc_module.projection_methods_fn, ProjectionMethods.CHAINLADDER, bad_fn
    )

    with pytest.raises(ValueError, match="Projection failed"):
        model.calculate_burn_cost()
```

- [ ] **Step 2: Run tests to verify `test_burn_cost_raises_on_invalid_projection` fails**

```
pytest tests/test_burn_cost.py::test_burn_cost_raises_on_invalid_projection -v
```

Expected: `FAILED` — exception is swallowed, no `ValueError` raised.

- [ ] **Step 3: Fix the exception handler in `burn_cost.py`**

Replace lines 426–429:

```python
            except Exception as e:
                raise ValueError(
                    f"Projection failed for year {year}, layer {self._layer_id}: {e}"
                ) from e
```

- [ ] **Step 4: Run all burn cost tests**

```
pytest tests/test_burn_cost.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/Models/Experience/burn_cost.py tests/test_burn_cost.py
git commit -m "fix: propagate projection errors in BurnCostModel.calculate_burn_cost"
```

---

### Task 6: Fix `ExposureModel._calculate_single_exposure_share()` indentation bug

**Files:**
- Modify: `src/pyre/Models/Exposure/exposure_rating_cost.py`
- Create: `tests/test_exposure_model.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_exposure_model.py`:

```python
import pytest
from datetime import date
from pyre.Models.Exposure.exposure_rating_cost import ExposureModel
from pyre.Models.Exposure.exposure_curve_functions import ExposureCurveType, swissRe_c_values
from pyre.exposures.exposures import Exposure, Exposures, ExposureMetaData, ExposureValues, ExposureBasis
from pyre.treaty.contracts import RILayer, RIContractMetadata, RIContract, ClaimTriggerBasis, IndexationClauseType
from pyre.treaty.contract_types import ContractType


def _make_exposure_model() -> ExposureModel:
    exp_meta = ExposureMetaData(
        exposure_id="E1",
        exposure_name="Policy 1",
        exposure_period_start=date(2020, 1, 1),
        exposure_period_end=date(2020, 12, 31),
        currency="GBP",
        exposure_type=ExposureBasis.EARNED,
    )
    # Policy: 0 attachment, 5m limit. Treaty: 1m xs 1m.
    exp_vals = ExposureValues(
        exposure_value=1_000_000.0,
        attachment_point=0.0,
        limit=5_000_000.0,
    )
    exposures = Exposures([Exposure(exp_meta, exp_vals)])

    layer = RILayer(
        layer_id=1,
        layer_name="1m xs 1m",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=1_000_000.0,
        occurrence_limit=1_000_000.0,
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[5_000_000.0],
        full_subject_premium=100_000.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=1,
        reinstatement_cost={1: 1.0},
    )
    contract_meta = RIContractMetadata(
        contract_id="CTR001",
        contract_description="Test",
        cedent_name="Test Cedent",
        trigger_basis=ClaimTriggerBasis.LOD,
        indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0,
        inception_date=date(2021, 1, 1),
        expiration_date=date(2021, 12, 31),
        fx_rates={"GBP": 1.0},
    )
    contract = RIContract(contract_meta_data=contract_meta, layers=[layer])

    return ExposureModel(
        exposures=exposures,
        ri_contract=contract,
        selected_curve=ExposureCurveType.MBBEFD,
        curve_parameters={"curve": swissRe_c_values.COMMERCIAL_LINES_MEDIUM},
    )


def test_exposure_share_is_populated_for_all_layers():
    """Regression: _calculate_single_exposure_share() had shares assignment
    inside a misplaced else branch — shares were never populated for policies
    where treaty_layer_limit + treaty_layer_attachment >= policy_limit."""
    model = _make_exposure_model()
    exposures = model._exposures

    for exposure in exposures:
        shares = model._calculate_single_exposure_share(exposure)
        assert isinstance(shares, dict)
        assert len(shares) == 1  # one layer
        assert 1 in shares
        assert 0.0 <= shares[1] <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_exposure_model.py::test_exposure_share_is_populated_for_all_layers -v
```

Expected: `FAILED` — `shares` dict is empty `{}`

- [ ] **Step 3: Rewrite `_calculate_single_exposure_share` in `exposure_rating_cost.py`**

Replace the entire method with:

```python
    def _calculate_single_exposure_share(self, exposure) -> dict:
        """
        Calculate the share of risk ceded to each treaty layer for a single exposure.

        Args:
            exposure: An Exposure object.

        Returns:
            Dict mapping layer_id to share of risk (float between 0 and 1).
        """
        from typing import Any
        policy_attachment = exposure.exposure_values.attachment_point
        policy_limit = exposure.exposure_values.limit
        total_insured_value = policy_attachment + policy_limit

        shares_by_layer: dict = {}

        for layer in self._ri_contract.layers:
            treaty_attachment = layer.occurrence_attachment
            treaty_limit = layer.occurrence_limit

            treaty_bottom = min(policy_attachment + treaty_attachment, total_insured_value)

            if treaty_limit + treaty_attachment < policy_limit:
                treaty_top = policy_attachment + treaty_limit + treaty_attachment
            else:
                treaty_top = total_insured_value

            # Avoid division by zero
            if total_insured_value == 0:
                shares_by_layer[layer.layer_id] = 0.0
                continue

            curve_pos_policy_lower = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                policy_attachment / total_insured_value,
            )
            curve_pos_policy_upper = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                total_insured_value / total_insured_value,  # = 1.0
            )
            curve_pos_treaty_lower = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                treaty_bottom / total_insured_value,
            )
            curve_pos_treaty_upper = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                treaty_top / total_insured_value,
            )

            policy_span = curve_pos_policy_upper - curve_pos_policy_lower
            if policy_span == 0:
                shares_by_layer[layer.layer_id] = 0.0
            else:
                share = (curve_pos_treaty_upper - curve_pos_treaty_lower) / policy_span
                shares_by_layer[layer.layer_id] = share

        return shares_by_layer
```

Also add `from typing import Any` at the top of the file if not present.

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_exposure_model.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Run full suite**

```
pytest -v
```

Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add src/pyre/Models/Exposure/exposure_rating_cost.py tests/test_exposure_model.py
git commit -m "fix: restructure _calculate_single_exposure_share so shares are always populated"
```

---

## Phase 2: Dataclasses Conversion

---

### Task 7: Convert `ClaimsMetaData` and `ClaimDevelopmentHistory` to dataclasses

**Files:**
- Modify: `src/pyre/claims/claims.py`

- [ ] **Step 1: Verify existing claim tests pass before touching the file**

```
pytest tests/test_claims.py -v
```

Expected: all `PASSED` — baseline established.

- [ ] **Step 2: Replace `ClaimsMetaData` with dataclass version**

In `src/pyre/claims/claims.py`, replace the `ClaimsMetaData` class entirely:

```python
from dataclasses import dataclass, field
from datetime import date
import operator
from typing import Optional, List, Sequence, Set
from enum import Enum, auto

from ..exceptions.exceptions import ClaimsException


class ClaimYearType(Enum):
    ACCIDENT_YEAR = auto()
    UNDERWRITING_YEAR = auto()
    REPORTED_YEAR = auto()


@dataclass
class ClaimsMetaData:
    """Metadata for an insurance claim.

    Attributes:
        claim_id: Unique identifier for the claim.
        currency: ISO currency code.
        contract_limit: Maximum contract limit. Defaults to 0.0.
        contract_deductible: Contract deductible. Defaults to 0.0.
        claim_in_xs_of_deductible: Whether amounts are already net of deductible.
        claim_year_basis: Year type used for modelling.
        loss_date: Date of loss.
        policy_inception_date: Policy inception date.
        report_date: Date claim was reported.
        line_of_business: Optional LOB classification.
        status: Claim status. Defaults to "Open".
    """
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
    def modelling_year(self) -> int:
        """Year used for experience modelling, derived from claim_year_basis."""
        mapping = {
            ClaimYearType.ACCIDENT_YEAR: self.loss_date.year,
            ClaimYearType.UNDERWRITING_YEAR: self.policy_inception_date.year,
            ClaimYearType.REPORTED_YEAR: self.report_date.year,
        }
        if self.claim_year_basis in mapping:
            return mapping[self.claim_year_basis]
        raise ClaimsException(
            claim_id=self.claim_id,
            message="Required date missing from data",
        )
```

- [ ] **Step 3: Replace `ClaimDevelopmentHistory` with dataclass version**

```python
@dataclass
class ClaimDevelopmentHistory:
    """Development history of an insurance claim.

    Attributes:
        development_months: Development month at each data point.
        cumulative_dev_paid: Cumulative paid at each development month.
        cumulative_dev_incurred: Cumulative incurred at each development month.
    """
    development_months: List[int] = field(default_factory=list)
    cumulative_dev_paid: List[float] = field(default_factory=list)
    cumulative_dev_incurred: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._validate_list_lengths()

    def _validate_list_lengths(self) -> None:
        if not (
            len(self.development_months)
            == len(self.cumulative_dev_paid)
            == len(self.cumulative_dev_incurred)
        ):
            raise ValueError(
                "All development lists (months, paid, incurred) must have the same length."
            )

    @property
    def cumulative_reserved_amount(self) -> List[float]:
        return [i - p for i, p in zip(self.cumulative_dev_incurred, self.cumulative_dev_paid)]

    @property
    def latest_paid(self) -> float:
        return self.cumulative_dev_paid[-1] if self.cumulative_dev_paid else 0.0

    @property
    def latest_incurred(self) -> float:
        return self.cumulative_dev_incurred[-1] if self.cumulative_dev_incurred else 0.0

    @property
    def latest_reserved_amount(self) -> float:
        return (
            self.cumulative_dev_incurred[-1] - self.cumulative_dev_paid[-1]
            if self.cumulative_dev_paid
            else 0.0
        )

    @property
    def latest_development_month(self) -> int:
        return self.development_months[-1] if self.development_months else 0

    @staticmethod
    def incremental_dev(cumulative_dev: Sequence[float]) -> List[float]:
        if not cumulative_dev:
            return []
        result = [cumulative_dev[0]]
        result.extend(cumulative_dev[i] - cumulative_dev[i - 1] for i in range(1, len(cumulative_dev)))
        return result

    @property
    def incremental_dev_incurred(self) -> List[float]:
        return self.incremental_dev(self.cumulative_dev_incurred)

    @property
    def incremental_dev_paid(self) -> List[float]:
        return self.incremental_dev(self.cumulative_dev_paid)

    @property
    def mean_payment_duration(self) -> Optional[float]:
        if self.latest_paid > 0:
            return sum(
                m * p for m, p in zip(self.development_months, self.incremental_dev_paid)
            ) / self.latest_paid
        return None
```

Keep `Claim` and `Claims` classes unchanged.

- [ ] **Step 4: Run the full test suite**

```
pytest -v
```

Expected: all `PASSED` — the public interface (attribute access) is identical.

- [ ] **Step 5: Commit**

```bash
git add src/pyre/claims/claims.py
git commit -m "refactor: convert ClaimsMetaData and ClaimDevelopmentHistory to dataclasses"
```

---

### Task 8: Convert `ExposureMetaData` and `ExposureValues` to dataclasses

**Files:**
- Modify: `src/pyre/exposures/exposures.py`

- [ ] **Step 1: Verify baseline**

```
pytest tests/test_exposures.py -v
```

Expected: all `PASSED`

- [ ] **Step 2: Replace `ExposureMetaData` with dataclass version**

```python
from dataclasses import dataclass, field
from datetime import date, timedelta
import operator
from typing import List, Optional
from enum import Enum, auto


class ExposureBasis(Enum):
    EARNED = auto()
    WRITTEN = auto()


@dataclass
class ExposureMetaData:
    """Metadata for an insurance exposure.

    Attributes:
        exposure_id: Unique identifier.
        exposure_name: Human-readable name.
        exposure_period_start: Start of exposure period.
        exposure_period_end: End of exposure period.
        currency: ISO currency code.
        aggregate: Whether this is an aggregate exposure. Defaults to False.
        line_of_business: LOB classification.
        stacking_id: Identifier for stacking exposures.
        exposure_type: Earned or written basis.
        location: Geographic location.
        peril: Associated peril.
        occupancy: Occupancy class.
    """
    exposure_id: str
    exposure_name: str
    exposure_period_start: date
    exposure_period_end: date
    currency: str
    aggregate: bool = False
    line_of_business: Optional[str] = None
    stacking_id: Optional[str] = None
    exposure_type: Optional[ExposureBasis] = field(default=ExposureBasis.EARNED)
    location: Optional[str] = None
    peril: Optional[str] = None
    occupancy: Optional[str] = None

    def __post_init__(self) -> None:
        if self.exposure_period_end < self.exposure_period_start:
            raise ValueError("Exposure period end date cannot be before start date")

    @property
    def exposure_term_length_days(self) -> int:
        return (self.exposure_period_end - self.exposure_period_start).days
```

- [ ] **Step 3: Replace `ExposureValues` with dataclass version**

```python
@dataclass
class ExposureValues:
    """Key financial values for an insurance exposure.

    Attributes:
        exposure_value: Total insured amount or premium.
        attachment_point: Threshold at which coverage begins.
        limit: Maximum amount payable.
    """
    exposure_value: float
    attachment_point: float
    limit: float

    def __post_init__(self) -> None:
        if self.attachment_point < 0:
            raise ValueError("Attachment point cannot be negative")
        if self.limit < 0:
            raise ValueError("Limit cannot be negative")
```

Keep `Exposure` and `Exposures` unchanged.

- [ ] **Step 4: Run the full test suite**

```
pytest -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/exposures/exposures.py
git commit -m "refactor: convert ExposureMetaData and ExposureValues to dataclasses"
```

---

### Task 9: Convert `RILayer` and `RIContractMetadata` to dataclasses

**Files:**
- Modify: `src/pyre/treaty/contracts.py`

- [ ] **Step 1: Verify baseline**

```
pytest tests/test_treaty.py -v
```

Expected: all `PASSED`

- [ ] **Step 2: Replace `RILayer` with dataclass version**

```python
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Sequence

from ..treaty.layer_loss_functions import layer_loss_calculation
from ..claims.claims import ClaimYearType
from ..exceptions.exceptions import ContractException
from ..treaty.contract_types import ContractType


class ClaimTriggerBasis(Enum):
    LOD = "Losses Occurrence"   # Accident Year
    RAD = "Risk Attaching"      # Policy Inception Year
    CMB = "Claims Made Basis"   # Reported Year


class IndexationClauseType(Enum):
    FULL_INDEXATION = "Full Indexation"
    FIC = "Franchise - FIC"
    SIC = "Severe Inflation (also London Market) - SIC"


_TRIGGER_TO_CLAIM_YEAR: Dict[ClaimTriggerBasis, ClaimYearType] = {
    ClaimTriggerBasis.RAD: ClaimYearType.UNDERWRITING_YEAR,
    ClaimTriggerBasis.CMB: ClaimYearType.REPORTED_YEAR,
    ClaimTriggerBasis.LOD: ClaimYearType.ACCIDENT_YEAR,
}


@dataclass
class RILayer:
    """A single reinsurance layer with its terms and conditions."""
    layer_id: int
    layer_name: str
    layer_type: ContractType
    occurrence_attachment: float
    occurrence_limit: float
    aggregate_attachment: float
    aggregate_limit: float
    subject_lines_of_business: List[str]
    subject_lob_exposure_amounts: List[float]
    full_subject_premium: float
    written_line: float
    signed_line: float
    number_of_reinstatements: int
    reinstatement_cost: Dict[int, float]
    cession: float = 1.0
    inures_to_benefit_of: List[Any] = field(default_factory=list)
    interlocking_classes: List[Any] = field(default_factory=list)

    @property
    def written_line_premium(self) -> float:
        return self.cession * self.written_line * self.full_subject_premium

    @property
    def signed_line_premium(self) -> float:
        return self.cession * self.signed_line * self.full_subject_premium

    def loss_to_layer_fn(self, gross_amount: float) -> float:
        """Apply this layer's terms to a gross loss amount."""
        if self.layer_type == ContractType.SURPLUS_SHARE:
            raise NotImplementedError("Surplus share loss function not yet implemented")
        if self.layer_type == ContractType.QUOTA_SHARE:
            return gross_amount
        func = layer_loss_calculation[self.layer_type]
        return func(gross_amount, self.occurrence_attachment, self.occurrence_limit)
```

- [ ] **Step 3: Replace `RIContractMetadata` with dataclass version**

```python
@dataclass
class RIContractMetadata:
    """Contract-level metadata for a reinsurance agreement."""
    contract_id: str
    contract_description: str
    cedent_name: str
    trigger_basis: ClaimTriggerBasis
    indexation_clause: IndexationClauseType
    indexation_margin: float
    inception_date: date
    expiration_date: date
    fx_rates: Dict[str, float]

    @property
    def claim_year_basis(self) -> ClaimYearType:
        if self.trigger_basis in _TRIGGER_TO_CLAIM_YEAR:
            return _TRIGGER_TO_CLAIM_YEAR[self.trigger_basis]
        raise ContractException(
            contract_id=self.contract_id,
            message="Trigger basis not found in claim year mapping",
        )
```

Keep `RIContract` unchanged. Remove the module-level `claim_year_basis` dict (replaced by `_TRIGGER_TO_CLAIM_YEAR`).

- [ ] **Step 4: Run the full test suite**

```
pytest -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/treaty/contracts.py
git commit -m "refactor: convert RILayer and RIContractMetadata to dataclasses"
```

---

## Phase 3: Module Restructure, Enums, Public API

---

### Task 10: Rename package directories

**Files:**
- `src/pyre/Models/` → `src/pyre/models/`
- `src/pyre/models/Experience/` → `src/pyre/models/experience/`
- `src/pyre/models/Exposure/` → `src/pyre/models/exposure/`
- `src/pyre/models/AggregateFeatures/` → `src/pyre/models/aggregate/`

- [ ] **Step 1: Run the rename using git mv**

```bash
cd src/pyre
git mv Models models
git mv models/Experience models/experience
git mv models/Exposure models/exposure
git mv models/AggregateFeatures models/aggregate
```

- [ ] **Step 2: Update all internal relative imports that reference the old paths**

Search for all files that import from the old paths:

```bash
grep -r "Models\." src/pyre --include="*.py" -l
grep -r "from.*Models" src/pyre --include="*.py" -l
grep -r "from.*Experience" src/pyre --include="*.py" -l
grep -r "from.*Exposure" src/pyre --include="*.py" -l
grep -r "from.*AggregateFeatures" src/pyre --include="*.py" -l
```

For each file found, update imports. The pattern changes are:

| Old import | New import |
|---|---|
| `from ...Models.Experience.` | `from ...models.experience.` |
| `from ...Models.Exposure.` | `from ...models.exposure.` |
| `from ...Models.AggregateFeatures.` | `from ...models.aggregate.` |
| `from ...Models.trending` | `from ...models.trending` |
| `from ..Models.Experience.` | `from ..models.experience.` |
| `from ..Models.trending` | `from ..models.trending` |

Apply to every affected file. Also update any test imports:
```bash
grep -r "Models\." tests/ --include="*.py" -l
```

Update `tests/test_burn_cost.py` and any other test files that import from old paths.

- [ ] **Step 3: Run the full test suite**

```
pytest -v
```

Expected: all `PASSED`

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: rename Models/ to models/ and subpackages to lowercase"
```

---

### Task 11: Create `enums.py` and migrate all enumerations

**Files:**
- Create: `src/pyre/enums.py`
- Modify: `src/pyre/claims/claims.py` (remove `ClaimYearType`)
- Modify: `src/pyre/exposures/exposures.py` (remove `ExposureBasis`)
- Modify: `src/pyre/treaty/contracts.py` (remove `ClaimTriggerBasis`, `IndexationClauseType`; import from enums)
- Modify: `src/pyre/treaty/contract_types.py` (delete — `ContractType` moves to enums)
- Modify: `src/pyre/treaty/layer_loss_functions.py` (import from enums)
- Modify: `src/pyre/models/experience/burn_cost.py` (remove `ProjectionMethods`)
- Modify: `src/pyre/models/experience/frequency_severity.py` (remove `SeverityDistribution`, `FrequencyDistribution`)
- Modify: `src/pyre/claims/triangles.py` (remove `CurveType`)
- Modify: `src/pyre/models/exposure/exposure_curve_functions.py` (remove `ExposureCurveType`)

- [ ] **Step 1: Create `src/pyre/enums.py`**

```python
"""Central enumeration definitions for pyRE.

All cross-cutting enumerations are defined here to avoid circular imports
and provide a single import location for users of the library.
"""

from enum import Enum, auto


class ClaimYearType(Enum):
    """Basis for determining which year a claim belongs to."""
    ACCIDENT_YEAR = auto()
    UNDERWRITING_YEAR = auto()
    REPORTED_YEAR = auto()


class ClaimTriggerBasis(Enum):
    """Defines how claims attach to a reinsurance contract."""
    LOD = "Losses Occurrence"   # Accident Year
    RAD = "Risk Attaching"      # Policy Inception Year
    CMB = "Claims Made Basis"   # Reported Year

    def to_claim_year_type(self) -> ClaimYearType:
        """Map trigger basis to the corresponding ClaimYearType."""
        return {
            ClaimTriggerBasis.LOD: ClaimYearType.ACCIDENT_YEAR,
            ClaimTriggerBasis.RAD: ClaimYearType.UNDERWRITING_YEAR,
            ClaimTriggerBasis.CMB: ClaimYearType.REPORTED_YEAR,
        }[self]


class ExposureBasis(Enum):
    """Whether exposure figures are earned or written."""
    EARNED = auto()
    WRITTEN = auto()


class ContractType(Enum):
    """Reinsurance contract structure type."""
    QUOTA_SHARE = auto()
    EXCESS_OF_LOSS = auto()
    SURPLUS_SHARE = auto()
    FRANCHISE_DEDUCTIBLE = auto()
    AGGREGATE_STOP_LOSS = auto()


class IndexationClauseType(Enum):
    """Indexation clause type for a reinsurance contract."""
    FULL_INDEXATION = "Full Indexation"
    FIC = "Franchise - FIC"
    SIC = "Severe Inflation (also London Market) - SIC"


class ProjectionMethods(Enum):
    """Available ultimate loss projection methods."""
    CHAINLADDER = auto()
    BF = auto()
    SIMPLE_CAPE_COD = auto()
    GENERALISED_CAPE_COD = auto()


class SeverityDistribution(Enum):
    """Severity distribution families for fitting."""
    LOGNORMAL = auto()
    PARETO = auto()
    OTHER = auto()


class FrequencyDistribution(Enum):
    """Frequency distribution families for fitting."""
    POISSON = auto()
    NEGATIVE_BINOMIAL = auto()
    OTHER = auto()


class ExposureCurveType(Enum):
    """Exposure curve type for exposure rating."""
    RIEBESELL = auto()
    MIXED_EXPONENTIAL = auto()
    MBBEFD = auto()


class CurveType(Enum):
    """Development curve type for triangle fitting."""
    EXPONENTIAL = auto()
    POWER = auto()
    WEIBULL = auto()
    INVERSE_POWER = auto()
    OTHER = auto()
```

- [ ] **Step 2: Update `claims/claims.py`**

Remove the `ClaimYearType` class definition. Replace with import:

```python
from ..enums import ClaimYearType
```

- [ ] **Step 3: Update `exposures/exposures.py`**

Remove `ExposureBasis` class definition. Replace with:

```python
from ..enums import ExposureBasis
```

- [ ] **Step 4: Update `treaty/contracts.py`**

Remove `ClaimTriggerBasis` and `IndexationClauseType` definitions. Remove `_TRIGGER_TO_CLAIM_YEAR` dict. Replace with:

```python
from ..enums import ClaimYearType, ClaimTriggerBasis, IndexationClauseType, ContractType
```

Update `claim_year_basis` property to use the new method:

```python
    @property
    def claim_year_basis(self) -> ClaimYearType:
        return self.trigger_basis.to_claim_year_type()
```

- [ ] **Step 5: Update `treaty/layer_loss_functions.py`**

Replace `from ..treaty.contract_types import ContractType` with:

```python
from ..enums import ContractType
```

- [ ] **Step 6: Delete `treaty/contract_types.py`**

```bash
git rm src/pyre/treaty/contract_types.py
```

- [ ] **Step 7: Update `models/experience/burn_cost.py`**

Remove `ProjectionMethods` definition. Replace with:

```python
from ...enums import ProjectionMethods
```

- [ ] **Step 8: Update `models/experience/frequency_severity.py`**

Remove `SeverityDistribution` and `FrequencyDistribution`. Replace with:

```python
from ...enums import SeverityDistribution, FrequencyDistribution
```

- [ ] **Step 9: Update `claims/triangles.py`**

Remove `CurveType`. Replace with:

```python
from ..enums import CurveType
```

- [ ] **Step 10: Update `models/exposure/exposure_curve_functions.py`**

Remove `ExposureCurveType`. Replace with:

```python
from ...enums import ExposureCurveType
```

- [ ] **Step 11: Run full test suite**

```
pytest -v
```

Expected: all `PASSED`

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "refactor: centralise all enumerations in pyre/enums.py"
```

---

### Task 12: Create public `__init__.py` and `py.typed` marker

**Files:**
- Modify: `src/pyre/__init__.py`
- Create: `src/pyre/py.typed`

- [ ] **Step 1: Create `src/pyre/py.typed`**

```bash
touch src/pyre/py.typed
```

This empty file tells type checkers (mypy, pyright) that pyRE ships type information (PEP 561).

- [ ] **Step 2: Write `src/pyre/__init__.py`**

```python
"""pyRE — Python Reinsurance Pricing Library.

Import the most commonly used classes directly from this package:

    from pyre import Claim, Claims, RIContract, BurnCostModel, ExperienceModelData

See the full API documentation at https://rdj09.github.io/pyre/
"""

from pyre.__about__ import __version__

# Core data structures
from pyre.claims.claims import Claim, Claims, ClaimDevelopmentHistory, ClaimsMetaData
from pyre.exposures.exposures import Exposure, Exposures, ExposureMetaData, ExposureValues
from pyre.treaty.contracts import RILayer, RIContractMetadata, RIContract

# Models
from pyre.models.trending import Trending
from pyre.models.experience.experience_preparer import ExperienceModelData
from pyre.models.experience.burn_cost import BurnCostModel
from pyre.models.exposure.exposure_rating_cost import ExposureModel
from pyre.models.aggregate.selections import Selections, CredibilityWeight
from pyre.models.aggregate.aggregate_features import AggregateFeatures
from pyre.models.aggregate.simulation_engine import Simulation, SimulationResults

# Enumerations
from pyre.enums import (
    ClaimYearType,
    ClaimTriggerBasis,
    ExposureBasis,
    ContractType,
    IndexationClauseType,
    ProjectionMethods,
    SeverityDistribution,
    FrequencyDistribution,
    ExposureCurveType,
    CurveType,
)

# Rate monitoring utilities
from pyre.rate_monitoring.rate_adequacy import rate_adequacy, rate_adequacy_change
from pyre.rate_monitoring.rate_change import rate_change_simple, rate_change_adjusted

__all__ = [
    "__version__",
    # Claims
    "Claim", "Claims", "ClaimDevelopmentHistory", "ClaimsMetaData",
    # Exposures
    "Exposure", "Exposures", "ExposureMetaData", "ExposureValues",
    # Treaty
    "RILayer", "RIContractMetadata", "RIContract",
    # Models
    "Trending", "ExperienceModelData", "BurnCostModel",
    "ExposureModel", "Selections", "CredibilityWeight",
    "AggregateFeatures", "Simulation", "SimulationResults",
    # Enums
    "ClaimYearType", "ClaimTriggerBasis", "ExposureBasis",
    "ContractType", "IndexationClauseType", "ProjectionMethods",
    "SeverityDistribution", "FrequencyDistribution", "ExposureCurveType", "CurveType",
    # Rate monitoring
    "rate_adequacy", "rate_adequacy_change",
    "rate_change_simple", "rate_change_adjusted",
]
```

- [ ] **Step 3: Write a smoke test**

Add `tests/test_public_api.py`:

```python
def test_top_level_imports_work():
    """Verify all symbols listed in __all__ are importable from pyre directly."""
    import pyre

    for name in pyre.__all__:
        assert hasattr(pyre, name), f"pyre.{name} not found"


def test_version_is_string():
    import pyre
    assert isinstance(pyre.__version__, str)
    assert len(pyre.__version__) > 0
```

- [ ] **Step 4: Run test**

```
pytest tests/test_public_api.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Run full test suite**

```
pytest -v
```

Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add src/pyre/__init__.py src/pyre/py.typed tests/test_public_api.py
git commit -m "feat: add public API surface via __init__.py and PEP 561 py.typed marker"
```

---

## Phase 4: Caching

---

### Task 13: Add `cached_property` to `ExperienceModelData`

**Files:**
- Modify: `src/pyre/models/experience/experience_preparer.py`

- [ ] **Step 1: Write a performance regression test**

Add to `tests/test_models.py`:

```python
def test_experience_model_data_cached_properties_compute_once(mocker):
    """cached_property should mean trend_claims is only called once even if
    accessed multiple times."""
    # We use the call count on Trending.trend_claims as a proxy.
    import pytest
    pytest.importorskip("pytest_mock")

    from pyre.models.experience.experience_preparer import ExperienceModelData
    # ... build model_data same as test_burn_cost.py _make_model_data() ...
```

Note: if `pytest-mock` is not installed, skip this test and rely on functional tests instead. The functional test below is sufficient.

- [ ] **Step 2: Write a functional test that accesses computed properties twice**

Add to `tests/test_models.py`:

```python
def test_trended_claims_accessible():
    """Smoke test: trended_claims returns a Claims object."""
    from datetime import date
    from pyre.models.experience.experience_preparer import ExperienceModelData
    from pyre.claims.claims import Claim, ClaimDevelopmentHistory, ClaimsMetaData, Claims, ClaimYearType
    from pyre.exposures.exposures import Exposure, Exposures, ExposureMetaData, ExposureValues, ExposureBasis
    from pyre.treaty.contracts import RILayer, RIContractMetadata, RIContract, ClaimTriggerBasis, IndexationClauseType
    from pyre.enums import ContractType
    from pyre.claims.claims import Claims

    meta = ClaimsMetaData(
        claim_id="C1", currency="GBP",
        contract_limit=1_000_000.0, contract_deductible=0.0,
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
        exposure_id="E1", exposure_name="2020",
        exposure_period_start=date(2020, 1, 1),
        exposure_period_end=date(2020, 12, 31),
        currency="GBP", exposure_type=ExposureBasis.EARNED,
    )
    exposures = Exposures([Exposure(exp_meta, ExposureValues(1_000_000.0, 0.0, 1_000_000.0))])

    layer = RILayer(
        layer_id=1, layer_name="test", layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=0.0, occurrence_limit=1_000_000.0,
        aggregate_attachment=0.0, aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[1_000_000.0],
        full_subject_premium=100_000.0, written_line=1.0, signed_line=1.0,
        number_of_reinstatements=1, reinstatement_cost={1: 1.0},
    )
    contract_meta = RIContractMetadata(
        contract_id="C1", contract_description="Test", cedent_name="Test",
        trigger_basis=ClaimTriggerBasis.LOD,
        indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0,
        inception_date=date(2021, 1, 1), expiration_date=date(2021, 12, 31),
        fx_rates={"GBP": 1.0},
    )
    contract = RIContract(contract_meta_data=contract_meta, layers=[layer])
    trend_factors = {yr: 1.0 for yr in range(2010, 2022)}
    model_data = ExperienceModelData(
        claims=claims, exposures=exposures, ri_contract=contract,
        exposure_trend_factors=trend_factors, claim_trend_factors=trend_factors,
    )

    # Access twice — should not raise
    result1 = model_data.trended_claims
    result2 = model_data.trended_claims
    assert result1 is result2  # same object — cached
    assert len(result1) == 1
```

- [ ] **Step 3: Run test to verify `result1 is result2` fails (currently recomputes)**

```
pytest tests/test_models.py::test_trended_claims_accessible -v
```

Expected: `FAILED` — `result1 is result2` is False (two different objects computed each time).

- [ ] **Step 4: Apply `cached_property` to `ExperienceModelData`**

In `src/pyre/models/experience/experience_preparer.py`:

```python
from functools import cached_property
from typing import Dict, List, Any, Optional
from ...models.trending import Trending
from ...claims.claims import Claim, ClaimDevelopmentHistory, Claims
from ...exposures.exposures import Exposure, Exposures
from ...treaty.contracts import RIContract


class ExperienceModelData:
    """Holds claims, exposures, and a reinsurance contract for experience pricing.

    Trend factors and contract details are set at construction. Computed
    aggregations are cached after first access; call update_trend_factors()
    to clear the cache when inputs change.
    """

    def __init__(
        self,
        claims: Claims,
        exposures: Exposures,
        ri_contract: RIContract,
        exposure_trend_factors: Optional[Dict[int, float]] = None,
        claim_trend_factors: Optional[Dict[int, float]] = None,
    ) -> None:
        self._claims = claims
        self._exposures = exposures
        self._ri_contract = ri_contract

        base_year = ri_contract.contract_meta_data.inception_date.year
        default_factors = {yr: 1.0 for yr in range(base_year - 10, base_year + 1)}

        self._trending = Trending(
            exposure_trend_factors=exposure_trend_factors or default_factors,
            claim_trend_factors=claim_trend_factors or default_factors,
            base_year=base_year,
        )

    # --- simple passthrough properties (not cached — cheap) ---

    @property
    def claims(self) -> Claims:
        return self._claims

    @claims.setter
    def claims(self, value: Claims) -> None:
        self._claims = value
        self._clear_cache()

    @property
    def exposures(self) -> Exposures:
        return self._exposures

    @exposures.setter
    def exposures(self, value: Exposures) -> None:
        self._exposures = value
        self._clear_cache()

    @property
    def ri_contract(self) -> RIContract:
        return self._ri_contract

    @ri_contract.setter
    def ri_contract(self, value: RIContract) -> None:
        self._ri_contract = value
        self._clear_cache()

    @property
    def trending(self) -> Trending:
        return self._trending

    # --- cache management ---

    _CACHED_KEYS = (
        "trended_claims",
        "trended_exposures",
        "subject_contract_claims",
        "aggregate_subject_contract_claims",
        "aggregate_exposures",
    )

    def _clear_cache(self) -> None:
        for key in self._CACHED_KEYS:
            self.__dict__.pop(key, None)

    def update_trend_factors(
        self,
        exposure_trend_factors: Optional[Dict[int, float]] = None,
        claim_trend_factors: Optional[Dict[int, float]] = None,
        base_year: Optional[int] = None,
    ) -> None:
        """Update trending assumptions and clear all cached aggregations."""
        self._trending = Trending(
            exposure_trend_factors=exposure_trend_factors or self._trending.exposure_trend_factors,
            claim_trend_factors=claim_trend_factors or self._trending.claim_trend_factors,
            base_year=base_year or self._trending.base_year,
        )
        self._clear_cache()

    # --- cached aggregations ---

    @cached_property
    def trended_claims(self) -> Claims:
        """Claims trended to the contract inception year."""
        return self._trending.trend_claims(self._claims)

    @cached_property
    def trended_exposures(self) -> Exposures:
        """Exposures trended to the contract inception year."""
        return self._trending.trend_exposures(self._exposures)

    @cached_property
    def subject_contract_claims(self) -> Dict[int, Claims]:
        """Ceded claims per layer after applying loss_to_layer_fn."""
        ceded: Dict[int, Claims] = {}
        for layer in self._ri_contract.layers:
            layer_claims = []
            for claim in self.trended_claims.claims:
                new_hist = ClaimDevelopmentHistory(
                    development_months=claim.capped_claim_development_history.development_months,
                    cumulative_dev_paid=[
                        layer.loss_to_layer_fn(p)
                        for p in claim.capped_claim_development_history.cumulative_dev_paid
                    ],
                    cumulative_dev_incurred=[
                        layer.loss_to_layer_fn(i)
                        for i in claim.capped_claim_development_history.cumulative_dev_incurred
                    ],
                )
                layer_claims.append(Claim(
                    claims_meta_data=claim.claims_meta_data,
                    claims_development_history=new_hist,
                ))
            ceded[layer.layer_id] = Claims(layer_claims)
        return ceded

    @cached_property
    def aggregate_subject_contract_claims(self) -> Dict[int, Dict[int, Dict[str, Any]]]:
        """Aggregate ceded claims by layer and modelling year."""
        result: Dict[int, Dict[int, Dict[str, Any]]] = {}
        for layer_id, claims_obj in self.subject_contract_claims.items():
            year_agg: Dict[int, Dict[str, Any]] = {}
            for claim in claims_obj.claims:
                year = claim.claims_meta_data.modelling_year
                status = getattr(claim.claims_meta_data, "status", "Unknown")
                if year not in year_agg:
                    year_agg[year] = {
                        "latest_paid": 0.0,
                        "latest_incurred": 0.0,
                        "claim_counts": {},
                        "total_count": 0,
                    }
                year_agg[year]["latest_paid"] += claim.capped_claim_development_history.latest_paid
                year_agg[year]["latest_incurred"] += claim.capped_claim_development_history.latest_incurred
                year_agg[year]["claim_counts"][status] = (
                    year_agg[year]["claim_counts"].get(status, 0) + 1
                )
                year_agg[year]["total_count"] += 1
            result[layer_id] = year_agg
        return result

    @cached_property
    def aggregate_exposures(self) -> Dict[int, Dict[str, float]]:
        """Aggregate trended exposures by modelling year."""
        analysis_date = self._ri_contract.contract_meta_data.inception_date
        by_year: Dict[int, Dict[str, float]] = {}
        for exposure in self.trended_exposures:
            year = exposure.modelling_year
            if year not in by_year:
                by_year[year] = {"written": 0.0, "earned": 0.0}
            by_year[year]["written"] += exposure.written_exposure_value(analysis_date)
            by_year[year]["earned"] += exposure.earned_exposure_value(analysis_date)
        return by_year
```

- [ ] **Step 5: Run tests**

```
pytest tests/test_models.py::test_trended_claims_accessible -v
```

Expected: `PASSED` — `result1 is result2` is True.

- [ ] **Step 6: Run full test suite**

```
pytest -v
```

Expected: all `PASSED`

- [ ] **Step 7: Commit**

```bash
git add src/pyre/models/experience/experience_preparer.py tests/test_models.py
git commit -m "perf: cache expensive computed properties on ExperienceModelData"
```

---

## End of Plan A

**All phases 1–4 complete.** Verify the full suite one final time:

```
pytest -v --tb=short
```

Expected: all tests pass with no warnings about deprecated imports.

Proceed to **Plan B** (`docs/superpowers/plans/2026-04-16-refactor-phase5.md`) for feature completions.
