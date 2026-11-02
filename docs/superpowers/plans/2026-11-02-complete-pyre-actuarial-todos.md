# Complete Remaining pyRE Actuarial TODOs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish every incomplete/placeholder implementation in `src/pyre/`
(literal TODOs, stub `pass` bodies, `raise NotImplementedError`, and one
stale-but-documented "known bug"), each cross-checked against a real,
independently-verifiable actuarial source, each with full unit + end-to-end
test coverage.

**Architecture:** No new subsystems — this fills gaps in the existing
`src/pyre/` module map (`treaty/`, `claims/`, `exposures/`, `models/Experience/`,
`models/Exposure/`, `models/AggregateFeatures/`) and the `app/` Panel workbench's
contract-config page, following each module's existing patterns exactly
(dataclasses, `ItemContainer`, the `layer_loss_calculation`/`exposure_curve_calculation`
dispatch-dict style).

**Tech Stack:** Pure Python 3.10+ stdlib for everything except Phase 4/6's
curve-fitting integration, which needs a new optional `curve-fitting` extra
(numpy/scipy/pandas/matplotlib) — mirrors the existing `panel`/`excel` extras.

**Spec:** No separate spec doc; this plan's own Context/Citation-verification
sections (below) serve that role — derived from a direct codebase audit plus
independently fetched/searched primary sources (not the unexecuted older
draft at `docs/superpowers/specs/2026-04-16-refactor-design.md`, which this
plan supersedes and corrects).

## Global Constraints

- Every new/fixed actuarial formula cites a real source (CAS/ASTIN/a named
  textbook) with a corrected or verified citation — never invent one. Where a
  source's exact worked numbers can't be independently confirmed, say so in
  the test docstring and fall back to a self-derived regression test rather
  than fabricating "textbook" numbers.
- Follow existing test conventions exactly: `unittest.TestCase` subclasses,
  `test_<behavior>` names, `setUp()`/builder-function fixtures, `assertAlmostEqual`
  for floats, `assertRaises` + `.identifier`/`.message` checks for custom exceptions.
- `pytest -q --ignore=tests/test_exposure_curve_fitting.py` must stay green
  (162-test baseline) after every task.
- Dataclass field ordering: required fields before optional; new optional
  fields go last to avoid breaking existing positional/keyword call sites.
- No new runtime dependency for the core `src/pyre` package except through
  a new, clearly optional extra (curve-fitting) — mirrors `panel`/`excel`.
- `CLAUDE.md`/`docs/*.md` updates always use the plan's execution-time real
  `pytest` output for test counts, never a guessed number.

## Review Focus

- SURPLUS_SHARE math must reproduce Clark's own worked example exactly,
  including the surplus-limit cap the existing `surplus_share_calculation`
  currently lacks (a real correctness bug found during planning, not just an
  unreachable stub) — a reviewer should re-check all 6 rows of the table, not
  just that `loss_to_layer_fn` no longer raises.
- `selections.py`'s fix must correctly flatten `Dict[int, Claims]` (nested by
  layer) rather than assuming a flat list — the original bug reports used
  `subject_contract_claims()` as if it were callable/flat.
- The Simulation engine's `required_capital()` must use the *ceded* (post-layer)
  loss distribution per layer, not the gross loss distribution — easy to get
  backwards when wiring Monte Carlo draws through `loss_to_layer_fn`.
- `ModellingAssumptions.capital_confidence_level=0.995` must be documented as
  a Solvency-II-style convention, explicitly NOT attributed to Butsic/DFA
  Handbook (neither source mandates that number) — a reviewer should flag a
  false citation here as a Critical finding, not a Minor one.
- The `curve-fitting` optional extra must not leak into the core package's
  default import path — `import pyre` and `import pyre.models.Exposure` must
  both succeed with scipy absent; only touching `ExposureCurveFitter`/`ILFFitter`
  should require it (lazy `__getattr__`, not an eager import).

---

## Citation verification (completed during planning — reference, not a task)

| Source | Used for | Verification |
|---|---|---|
| Clark, D.R. (1996/2014), *Basics of Reinsurance Pricing*, CAS Study Note | Task 5 (SURPLUS_SHARE), Task 20 (investment income/profit commission) | Fetched PDF directly; p.3 has the full worked surplus-share example used as Task 5's golden value. Existing citation URL in the repo is dead (404); working URL: `https://www.casact.org/sites/default/files/old/studynotes_clark_2014.pdf`. |
| Schnieper, R. (1991), *Separating True IBNR and IBNER Claims*, ASTIN Bulletin 21(1), pp.111-127 | Task 8 (IBNER citation write-up) | Fetched PDF; N/D-triangle terminology matches the existing `IBNERPatternExtractor` implementation exactly. |
| Klugman, Panjer & Willmot, *Loss Models*, 4th ed., Ch.13 ("Frequentist Estimation"), §13.2 | Tasks 9-10 (SeverityFit/FrequencyFit) | Real textbook, confirmed via search. Corrects the unexecuted old draft's wrong citation ("Ch.4", which is distribution definitions, not estimation). |
| Werner, G. & Modlin, C., *Basic Ratemaking*, 5th ed. (CAS) | Task 17 (parallelogram method) | Confirmed real CAS exam text with an explicit parallelogram-method chapter. |
| Mahler, H.C. & Dean, C.G., "Credibility," Ch.8, *Foundations of Casualty Actuarial Science*, 4th ed. (CAS) | Task 12 (`selections.py`) | Confirmed real; existing `CredibilityWeight` formulas already match this chapter's standard content. |
| Efron, B. & Tibshirani, R.J. (1993), *An Introduction to the Bootstrap*, Ch.2 | Task 11 (`resampling.py`) | Standard, bibliographically confirmed reference for resample-with-replacement. |
| CAS Dynamic Financial Analysis Research Handbook (1999) / CAS DFA Handbook, Forum Winter 1996 | Tasks 19-20 (Simulation engine framework) | Real, found at casact.org. |
| Butsic, R.P. (1999), "Capital Allocation for Property-Liability Insurers: A Catastrophe Reinsurance Application," CAS Forum | Task 19 (risk-adjusted capital) | Real, reinsurance-specific. |
| Bernegger (1997), Palmer (CAS Study Note), Rosin (2009 CAS presentation), Hrevuš & Marek (2019) | Already correctly cited in `exposure_curve_functions.py`/`exposure_ILF_fitting.py`/`exposure_rating_cost.py` | Spot-checked; no changes needed beyond what Tasks 13-16 touch for other (non-citation) reasons. |

---

### Task 1: Fix `frequency_severity.py` return/raise bug

**Files:**
- Modify: `src/pyre/models/Experience/frequency_severity.py:19`
- Test: `tests/test_frequency_severity.py` (new file — also used by Tasks 9-10)

**Interfaces:**
- Produces: `tests/test_frequency_severity.py` as the shared home for all
  `SeverityFit`/`FrequencyFit` tests (Tasks 9-10 extend this same file).

- [ ] **Step 1: Write the failing test**

```python
import unittest
from pyre.models.Experience.frequency_severity import SeverityFit

class TestSeverityFitNonGroundUp(unittest.TestCase):
    def test_non_ground_up_fit_raises_not_implemented_error(self):
        fit = SeverityFit(distributions=[], data=None, ibner_dev_pattern={}, ground_up=False)
        with self.assertRaises(NotImplementedError):
            fit._individual_projected_claims
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_frequency_severity.py -v`
Expected: FAIL — no exception raised (the current code `return`s the exception
object instead of raising it, so the property access completes normally and
`assertRaises` fails with "NotImplementedError not raised").

- [ ] **Step 3: Fix the bug**

In `frequency_severity.py:19`, change `return NotImplementedError(...)` to
`raise NotImplementedError(...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_frequency_severity.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pyre/models/Experience/frequency_severity.py tests/test_frequency_severity.py
git commit -m "fix: raise (not return) NotImplementedError in SeverityFit non-ground-up path"
```

---

### Task 2: Fix `resampling.py` property-binding bug

**Files:**
- Modify: `src/pyre/models/Experience/resampling.py:31`
- Test: `tests/test_resampling.py` (new file — also used by Task 11)

**Interfaces:**
- Consumes: `ExperienceModelData.trended_claims` (existing property, returns `Claims`).

- [ ] **Step 1: Write the failing test**

```python
import unittest
from unittest.mock import MagicMock
from pyre.models.Experience.resampling import resampling
from pyre.claims.claims import Claims

class TestResamplingInit(unittest.TestCase):
    def test_init_uses_claims_argument_trended_claims(self):
        fake_claims = Claims([])
        mock_data = MagicMock()
        mock_data.trended_claims = fake_claims
        r = resampling(mock_data)
        self.assertIs(r._claims, fake_claims)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_resampling.py -v`
Expected: FAIL — `r._claims` is the unbound `property` object from the class
(`ExperienceModelData.trended_claims`), not `fake_claims`.

- [ ] **Step 3: Fix the bug**

In `resampling.py:31`, change `self._claims = ExperienceModelData.trended_claims`
to `self._claims = claims.trended_claims` (use the `claims` constructor
argument, not the class itself).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_resampling.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pyre/models/Experience/resampling.py tests/test_resampling.py
git commit -m "fix: resampling binds the instance's trended_claims, not the unbound property"
```

---

### Task 3: Fix `simulation_engine.py` signatures and typos (mechanical only)

**Files:**
- Modify: `src/pyre/models/AggregateFeatures/simulation_engine.py`

**Interfaces:**
- Produces: method names `profit_commission`, `retrocession_benefits` (renamed
  from the typo'd originals) — Task 20 implements these bodies for real; this
  task only fixes the signatures so later tasks don't inherit the typos.

- [ ] **Step 1: Add `self` as the first parameter** to every method currently
  missing it: `profit_commsission`, `cashflows`, `loss_cost`, `required_capital`,
  `investment_return`, `tax_rate`, `retrocession_cost`, `retrocession_beneits`,
  `required_premium_layer`, `required_premium_programme`. Verify `__init__`,
  `run`, `output`, `save` already have it (they do).

- [ ] **Step 2: Rename typos** — `profit_commsission` → `profit_commission`,
  `retrocession_beneits` → `retrocession_benefits`.

- [ ] **Step 3: Run the full suite to confirm no regressions**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: 162 passed (nothing currently calls these stub methods, so this is
a no-op for behavior — pure signature cleanup).

- [ ] **Step 4: Commit**

```bash
git add src/pyre/models/AggregateFeatures/simulation_engine.py
git commit -m "fix: add missing self parameter and fix method-name typos in Simulation stub"
```

---

### Task 4: Correct the stale Trending "known limitation" claim + bidirectional test

**Files:**
- Modify: `src/pyre/models/trending.py` (docstring only), `docs/models.md`
- Test: `tests/test_trending.py` (extend)

**Interfaces:**
- Consumes: `Trending.calculate_trend_factor(origin_year, for_claims)` (existing,
  unchanged logic — this task only adds coverage and corrects documentation).

- [ ] **Step 1: Write the failing test**

```python
def test_calculate_trend_factor_for_origin_year_before_base_year(self):
    """Golden value: 5% p.a. compounding, base_year=2022. Deters (2017),
    'The Mathematics of On-Leveling,' CAS E-Forum, establishes that a
    consistent on-leveling formula must be symmetric about the base year --
    this pins that symmetry for a year *before* base_year, which no existing
    test exercises (all prior fixtures only trend origin_year > base_year)."""
    trending = Trending(
        exposure_trend_factors={2020: 1 / 1.05**2, 2022: 1.0},
        claim_trend_factors={2020: 1 / 1.05**2, 2022: 1.0},
        base_year=2022,
    )
    factor = trending.calculate_trend_factor(2020, for_claims=False)
    self.assertAlmostEqual(factor, 0.9070294784580498, places=6)
    original_value = 100_000.0
    trended = original_value / factor
    self.assertAlmostEqual(trended, 100_000 * 1.05**2, places=2)
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `pytest tests/test_trending.py -v`
Expected: PASS immediately — `calculate_trend_factor` is a direct dict lookup
with no directional logic, so it already works correctly for `origin_year <
base_year` as long as the caller supplies that year's factor. This step's
purpose is to *prove* the docs' "9 failures" claim is false, not to fix a bug.

- [ ] **Step 3: Correct the documentation**

In `trending.py`'s `Trending` class docstring, clarify that
`trend_factors`/`exposure_trend_factors`/`claim_trend_factors` dict values are
cumulative indices relative to `base_year` (not standalone compounding annual
rates) — state this explicitly since "annual trend factor" in the current
docstring is misleading. In `docs/models.md`, remove or rewrite the "Known
limitation" warning block about `origin_year > base_year` — it is stale (all
10 `test_trending.py` tests pass today; verified by running the suite
directly during planning).

- [ ] **Step 4: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: 163 passed (162 + this task's 1 new test).

- [ ] **Step 5: Commit**

```bash
git add src/pyre/models/trending.py docs/models.md tests/test_trending.py
git commit -m "docs: correct stale Trending direction-bug claim; add origin_year<base_year coverage"
```

---

### Task 5: SURPLUS_SHARE backend support

**Files:**
- Modify: `src/pyre/treaty/contracts.py:16-52`, `src/pyre/treaty/layer_loss_functions.py:19-24`
- Test: `tests/test_treaty.py` (extend — check existing class names first)
- Modify (docs): `docs/treaty.md`, `CLAUDE.md`

**Interfaces:**
- Produces: `RILayer.sum_insured: Optional[float] = None` (new field, last
  position); `surplus_share_calculation(gross_amount, sum_insured,
  retained_line, surplus_limit) -> float` (changed signature, 4 params not 3).
- Consumes: nothing new — reuses `RILayer.occurrence_attachment` as
  `retained_line` and `RILayer.occurrence_limit` as `surplus_limit` when
  calling from `loss_to_layer_fn`.

- [ ] **Step 1: Write the failing golden-value test**

```python
class TestSurplusShareCalculation(unittest.TestCase):
    def test_matches_clark_worked_example(self):
        """Golden value from Clark, D.R. (1996/2014), Basics of Reinsurance
        Pricing, CAS Study Note, p.3:
        Retained line $100,000; 1st Surplus 4 lines ($400,000).
        sum_insured -> expected cession %:
          50,000 -> 0%; 100,000 -> 0%; 250,000 -> 60%; 500,000 -> 80%;
          1,000,000 -> 40%; 10,000,000 -> 4%
        """
        cases = [
            (50_000, 0.0), (100_000, 0.0), (250_000, 0.60),
            (500_000, 0.80), (1_000_000, 0.40), (10_000_000, 0.04),
        ]
        for sum_insured, expected_pct in cases:
            with self.subTest(sum_insured=sum_insured):
                result = surplus_share_calculation(
                    gross_amount=1.0, sum_insured=sum_insured,
                    retained_line=100_000, surplus_limit=400_000,
                )
                self.assertAlmostEqual(result, expected_pct, places=4)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_treaty.py -k SurplusShareCalculation -v`
Expected: FAIL — current `surplus_share_calculation(gross_amount, sum_insured,
attachment)` has no surplus-limit cap, so rows for sum_insured=1,000,000 and
10,000,000 compute 90%/99% instead of the correct 40%/4% (and the function's
current 3-arg signature doesn't even match this test's call).

- [ ] **Step 3: Fix `surplus_share_calculation`** in `layer_loss_functions.py`:

```python
def surplus_share_calculation(gross_amount, sum_insured, retained_line, surplus_limit):
    if sum_insured <= 0:
        return 0.0
    surplus_over_retention = max(sum_insured - retained_line, 0.0)
    ceded_portion = min(surplus_over_retention, surplus_limit)
    return (ceded_portion / sum_insured) * gross_amount
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_treaty.py -k SurplusShareCalculation -v`
Expected: PASS, all 6 subtests.

- [ ] **Step 5: Add `sum_insured` field and wire `loss_to_layer_fn`**

In `contracts.py`, add `sum_insured: Optional[float] = None` as the last field
on `RILayer` (after `interlocking_classes`). In `loss_to_layer_fn`, replace the
`NotImplementedError` branch:

```python
if self.layer_type == ContractType.SURPLUS_SHARE:
    if self.sum_insured is None:
        raise ValueError(
            f"SURPLUS_SHARE layer {self.layer_id} requires sum_insured to be set"
        )
    return surplus_share_calculation(
        gross_amount, self.sum_insured, self.occurrence_attachment, self.occurrence_limit
    )
```

Also turn the `# TODO analysis typically easier...` comment on the
`QUOTA_SHARE` branch (line 46) into a one-line docstring note on
`loss_to_layer_fn` that cession/inuring is deliberately the caller's
responsibility, not computed here.

- [ ] **Step 6: Write failing tests for `loss_to_layer_fn`**

```python
def test_loss_to_layer_fn_surplus_share_without_sum_insured_raises(self):
    layer = _build_layer(layer_type=ContractType.SURPLUS_SHARE, sum_insured=None)
    with self.assertRaises(ValueError):
        layer.loss_to_layer_fn(50_000)

def test_loss_to_layer_fn_surplus_share_applies_cession_to_gross_loss(self):
    # Clark risk 5: sum_insured=1,000,000, retained_line=100,000,
    # surplus_limit=400,000 -> 40% cession.
    layer = _build_layer(
        layer_type=ContractType.SURPLUS_SHARE, sum_insured=1_000_000,
        occurrence_attachment=100_000, occurrence_limit=400_000,
    )
    self.assertAlmostEqual(layer.loss_to_layer_fn(50_000), 20_000, places=2)
```

(Use this file's existing `_build_layer` helper if present; add the
`layer_type`/`sum_insured` kwargs to it if it doesn't already accept them.)

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_treaty.py -v`
Expected: PASS, all tests.

- [ ] **Step 8: Update docs**

`docs/treaty.md`: update the SURPLUS_SHARE table row with the real formula
and fix the dead Clark citation URL to
`https://www.casact.org/sites/default/files/old/studynotes_clark_2014.pdf`.
`CLAUDE.md`: update the "SURPLUS_SHARE layers are intentionally excluded"
sentence in the Panel-workbench section to say the backend now supports it
(Task 6 re-enables the UI).

- [ ] **Step 9: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: previous count + this task's new tests, 0 failed.

- [ ] **Step 10: Commit**

```bash
git add src/pyre/treaty/contracts.py src/pyre/treaty/layer_loss_functions.py tests/test_treaty.py docs/treaty.md CLAUDE.md
git commit -m "feat: implement SURPLUS_SHARE loss-to-layer calculation (Clark CAS Study Note)"
```

---

### Task 6: SURPLUS_SHARE Panel UI re-enablement

**Files:**
- Modify: `app/pages/contract_config.py:15-23, 122-151, 187-191`
- Modify: `app/service.py:197-219, 222-229`
- Test: `tests/test_app_service.py` (extend `TestBuildContractAndLayer`)

**Interfaces:**
- Consumes: `RILayer.sum_insured` from Task 5.
- Produces: `build_layer(form)` now reads an optional `form["sum_insured"]`.

- [ ] **Step 1: Write the failing test**

```python
def test_build_layer_passes_through_sum_insured_for_surplus_share(self):
    form = {
        "layer_id": 1, "layer_name": "Surplus 1", "layer_type": "SURPLUS_SHARE",
        "occurrence_attachment": 100_000, "occurrence_limit": 400_000,
        "full_subject_premium": 0.0, "written_line": 1.0, "signed_line": 1.0,
        "sum_insured": 1_000_000,
    }
    layer = build_layer(form)
    self.assertEqual(layer.sum_insured, 1_000_000)

def test_build_layer_sum_insured_defaults_to_none(self):
    form = {"layer_id": 1, "layer_name": "XOL 1", "layer_type": "EXCESS_OF_LOSS",
            "occurrence_attachment": 0.0, "occurrence_limit": 100_000}
    layer = build_layer(form)
    self.assertIsNone(layer.sum_insured)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_app_service.py -k sum_insured -v`
Expected: FAIL — `build_layer` doesn't pass `sum_insured` to `RILayer` at all yet.

- [ ] **Step 3: Update `build_layer`**

In `app/service.py:203-219`, add:
```python
sum_insured=float(form["sum_insured"]) if form.get("sum_insured") else None,
```
as a new kwarg to the `RILayer(...)` call.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_app_service.py -k sum_insured -v`
Expected: PASS.

- [ ] **Step 5: Update the Panel UI**

In `app/pages/contract_config.py`:
- Add `ContractType.SURPLUS_SHARE` to `SELECTABLE_LAYER_TYPES` (line 18-23).
- Add a `sum_insured = pn.widgets.FloatInput(name="Sum insured (SURPLUS_SHARE only)", value=0.0)`
  widget near `occurrence_attachment`/`occurrence_limit` (around line 127-131).
- In `_on_add_layer`'s `form` dict (line 137-146), add `"sum_insured":
  sum_insured.value or None,`.
- Remove the "Surplus share is not yet available" sentence from the Markdown
  note at lines 187-191.
- In `app/service.py`, remove the stale SURPLUS_SHARE `NotImplementedError`
  docstring note on `run_pricing` (lines 226-229).

- [ ] **Step 6: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: previous count + 2 new tests, 0 failed.

- [ ] **Step 7: Manual verification**

Run `hatch run panel:serve`, add a SURPLUS_SHARE layer with a sum_insured
value via the UI, run pricing, confirm no crash. (Not automatable via
`tests/test_app_service.py`, which tests `app/service.py` functions directly,
not the live Panel widgets — do this manually before this task's review.)

- [ ] **Step 8: Commit**

```bash
git add app/pages/contract_config.py app/service.py tests/test_app_service.py
git commit -m "feat: re-enable SURPLUS_SHARE layer type in the Panel contract-config UI"
```

---

### Task 7: Triangle → BurnCostModel development-pattern method

**Files:**
- Modify: `src/pyre/claims/triangles.py` (add method after `fit_curve`, ~line 453)
- Test: `tests/test_triangles.py` (extend)

**Interfaces:**
- Consumes: `Triangle.fit_curve(curve_type, c_values) -> (params, metrics)` (existing).
- Produces: `Triangle.get_selected_development_pattern(curve_type, tail_factor=1.0, c_values=None) -> Dict[int, float]`,
  consumable by `BurnCostModel(..., development_pattern=...)` (confirm this
  constructor parameter name — singular — before wiring).

- [ ] **Step 1: Write the failing test**

```python
def test_get_selected_development_pattern_returns_cumulative_factors(self):
    triangle = Triangle(...)  # build from a synthetic fixture with known
                               # exponential decay in age-to-age factors,
                               # matching this file's existing fixture style
    pattern = triangle.get_selected_development_pattern(CurveType.EXPONENTIAL)
    dev_periods = sorted(pattern.keys())
    # Cumulative-to-ultimate factors decrease monotonically toward 1.0
    for earlier, later in zip(dev_periods, dev_periods[1:]):
        self.assertGreaterEqual(pattern[earlier], pattern[later])
    self.assertAlmostEqual(pattern[dev_periods[-1]], 1.0, places=2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_triangles.py -k development_pattern -v`
Expected: FAIL — `AttributeError: no method get_selected_development_pattern`.

- [ ] **Step 3: Implement the method**

Reuse `fit_curve`'s own `expected = [...]` formulas (don't re-derive) for each
`CurveType` to reconstruct fitted incremental age-to-age factors from `params`,
then take the cumulative product from each dev period forward to the final
period, multiplied by `tail_factor`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_triangles.py -k development_pattern -v`
Expected: PASS.

- [ ] **Step 5: Write an integration test with `BurnCostModel`**

```python
def test_development_pattern_feeds_burn_cost_model_without_error(self):
    pattern = triangle.get_selected_development_pattern(CurveType.EXPONENTIAL)
    model = BurnCostModel(model_data, layer_id, development_pattern=pattern)
    # just assert it constructs/runs without raising
```

- [ ] **Step 6: Run test, then full suite**

Run: `pytest tests/test_triangles.py -v` then
`pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: both green.

- [ ] **Step 7: Commit**

```bash
git add src/pyre/claims/triangles.py tests/test_triangles.py
git commit -m "feat: add Triangle.get_selected_development_pattern for BurnCostModel"
```

---

### Task 8: IBNER (Schnieper) citation write-up

**Files:**
- Modify: `src/pyre/claims/triangles.py:458` (docstring only)
- Modify (docs): `docs/models.md`
- Test: `tests/test_ibner_pattern_extractor.py` (check existing content first; extend if missing coverage)

**Interfaces:**
- Consumes: `IBNERPatternExtractor` (existing, unchanged — this task is
  citation/documentation plus a possible golden-value test, not a code fix).

- [ ] **Step 1: Check existing test coverage**

Read `tests/test_ibner_pattern_extractor.py` in full. If it already has a case
matching Schnieper's own worked 3-accident-year example (ASTIN Bulletin 21(1)
p.113: `E₁=20, E₂=25, E₃=32`; X-triangle rows `3,5,6.5 / 2.5,5 / 5.5`), skip to
Step 4. Otherwise continue to Step 2.

- [ ] **Step 2: Write the failing golden-value test**

```python
def test_matches_schnieper_worked_example(self):
    """Golden value from Schnieper, R. (1991), 'Separating True IBNR and
    IBNER Claims,' ASTIN Bulletin 21(1), p.113."""
    # build a triangle fixture matching Schnieper's E_i claim counts and
    # X-triangle values, run IBNERPatternExtractor, assert the computed
    # N/D triangle values match his table exactly.
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_ibner_pattern_extractor.py -v`
Expected: PASS without any production-code change (the existing implementation
already matches Schnieper's method — this test is new coverage, not a bug fix).
If it does NOT pass, that is itself a finding — stop and investigate via
superpowers:systematic-debugging rather than adjusting the test to match
whatever the code happens to produce.

- [ ] **Step 4: Replace the bare TODO comment with a proper citation**

In `triangles.py:458`, replace `# TODO IBNER methodology citation...` with a
formal docstring on `IBNERPatternExtractor` (author, year, title, journal,
volume/issue/pages, URL).

- [ ] **Step 5: Update docs**

Add a short paragraph to `docs/models.md` describing the N/D-triangle method
with the same citation, matching the style of the existing Bernegger/Rosin
citations there.

- [ ] **Step 6: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: previous count (+1 if Step 2 added a new test), 0 failed.

- [ ] **Step 7: Commit**

```bash
git add src/pyre/claims/triangles.py docs/models.md tests/test_ibner_pattern_extractor.py
git commit -m "docs: formalize Schnieper (1991) citation for IBNERPatternExtractor"
```

---

### Task 9: `SeverityFit.fit()` implementation

**Files:**
- Modify: `src/pyre/models/Experience/frequency_severity.py`
- Test: `tests/test_frequency_severity.py` (extend, from Task 1)

**Interfaces:**
- Produces: `FitResult` dataclass (`distribution: SeverityDistribution`,
  `parameters: Dict[str, float]`, `log_likelihood: float`, `aic: float`);
  `SeverityFit.fit() -> List[FitResult]` (one per distribution in
  `self.distributions`).
- Consumes: `self._individual_projected_claims` (existing property, fixed in Task 1).

- [ ] **Step 1: Write failing regression tests**

```python
def test_fit_lognormal_recovers_known_parameters(self):
    # Generate synthetic data from a known lognormal (mu=8.0, sigma=0.5),
    # build a SeverityFit with mocked _individual_projected_claims returning
    # that data, assert fit()'s LOGNORMAL FitResult.parameters converge
    # within a documented tolerance.

def test_fit_pareto_recovers_known_parameters(self):
    # Same pattern for Pareto (alpha=2.5, x_m known).
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_frequency_severity.py -k fit_ -v`
Expected: FAIL — `fit()` currently returns `None`.

- [ ] **Step 3: Implement `fit()`**

Method of moments for `SeverityDistribution.LOGNORMAL`:
`mu = log(mean**2 / sqrt(variance + mean**2))`,
`sigma = sqrt(log(variance / mean**2 + 1))`.
MLE for `SeverityDistribution.PARETO`:
`x_m = min(data)`, `alpha = n / sum(log(xi / x_m) for xi in data)`.
Return a `FitResult` per requested distribution. Cite Klugman, Panjer &
Willmot, *Loss Models*, 4th ed., Ch.13 §13.2 in the method's docstring.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_frequency_severity.py -k fit_ -v`
Expected: PASS within documented tolerance.

- [ ] **Step 5: Attempt a textbook golden-value test**

Before finalizing, check whether *Loss Models*' own worked MLE example data
(not just its quoted output) can be independently sourced. If the exact input
claim values can be confirmed (not just a remembered/quoted result), add
`test_fit_pareto_matches_loss_models_worked_example` as a golden-value test
citing the exact chapter/example. If the input data cannot be independently
verified, skip this step and document in the test module's docstring that no
textbook golden value was available — do not fabricate input numbers to
produce a remembered output.

- [ ] **Step 6: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: previous count + new tests, 0 failed.

- [ ] **Step 7: Commit**

```bash
git add src/pyre/models/Experience/frequency_severity.py tests/test_frequency_severity.py
git commit -m "feat: implement SeverityFit.fit() for lognormal (MoM) and Pareto (MLE)"
```

---

### Task 10: `FrequencyFit` class (new — prerequisite for Task 19)

**Files:**
- Modify: `src/pyre/models/Experience/frequency_severity.py`
- Test: `tests/test_frequency_severity.py` (extend)

**Interfaces:**
- Produces: `FrequencyFit` class, same `FitResult`-returning pattern as
  `SeverityFit`, for `FrequencyDistribution.POISSON` and `.NEGATIVE_BINOMIAL`.
  Required by Task 19's `Simulation.__init__` for claim-count sampling.

- [ ] **Step 1: Write failing regression tests**

```python
def test_fit_poisson_recovers_known_lambda(self):
    # synthetic Poisson(lambda=3.5) count data -> fitted lambda within tolerance

def test_fit_negative_binomial_recovers_known_parameters(self):
    # synthetic NegBin data via method-of-moments from mean/variance
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_frequency_severity.py -k Frequency -v`
Expected: FAIL — `FrequencyFit` doesn't exist yet.

- [ ] **Step 3: Implement `FrequencyFit`**

```python
class FrequencyFit:
    def __init__(self, distributions: List[FrequencyDistribution], claim_counts: List[int]):
        ...
    def fit(self) -> List[FitResult]:
        ...  # Poisson: lambda = mean(counts).
             # NegBinomial: method of moments from mean/variance of counts.
```
Cite the same Klugman/Panjer/Willmot Ch.13 chapter.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_frequency_severity.py -k Frequency -v`
Expected: PASS. No textbook golden value exists for this closed-form MoM
estimator — document that in the test module's docstring; these are
regression-only by design, not an oversight.

- [ ] **Step 5: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`

- [ ] **Step 6: Commit**

```bash
git add src/pyre/models/Experience/frequency_severity.py tests/test_frequency_severity.py
git commit -m "feat: add FrequencyFit (Poisson, Negative Binomial) for claim-count fitting"
```

---

### Task 11: `resampling.py` full `resample(n)` implementation

**Files:**
- Modify: `src/pyre/models/Experience/resampling.py`
- Test: `tests/test_resampling.py` (extend, from Task 2)

**Interfaces:**
- Produces: `resampling.resample(n: int = 1, random_seed: Optional[int] = None) -> List[Claim]`.
- Consumes: `self._claims.claims` (the underlying `List[Claim]`, fixed access in Task 2).

- [ ] **Step 1: Write failing tests**

```python
def test_resample_n_returns_n_claims(self):
    r = resampling(mock_data_with_3_claims)
    result = r.resample(n=5, random_seed=42)
    self.assertEqual(len(result), 5)
    for claim in result:
        self.assertIsInstance(claim, Claim)

def test_resample_is_deterministic_with_seed(self):
    r = resampling(mock_data_with_3_claims)
    first = r.resample(n=10, random_seed=7)
    second = r.resample(n=10, random_seed=7)
    self.assertEqual([id(c) for c in first], [id(c) for c in second])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_resampling.py -k resample_n -v`
Expected: FAIL — `resample()` currently takes no `n`/`random_seed` params and returns `None`.

- [ ] **Step 3: Implement `resample(n, random_seed)`**

```python
def resample(self, n: int = 1, random_seed: Optional[int] = None) -> List[Claim]:
    rng = random.Random(random_seed) if random_seed is not None else random
    return rng.choices(self._claims.claims, k=n)
```
Cite Efron & Tibshirani (1993), Ch.2 in the docstring. Explicitly note in the
docstring that "different return periods" (the file's prior TODO) remains
deferred as under-specified — not part of this task.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_resampling.py -v`
Expected: PASS. No golden value possible for randomized output — document why
in the test module's docstring (seeded-RNG determinism substitutes for it).

- [ ] **Step 5: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`

- [ ] **Step 6: Commit**

```bash
git add src/pyre/models/Experience/resampling.py tests/test_resampling.py
git commit -m "feat: implement resampling.resample(n) via seeded bootstrap (Efron & Tibshirani)"
```

---

### Task 12: Fix `selections.py` integration bugs

**Files:**
- Modify: `src/pyre/models/AggregateFeatures/selections.py` (docstring + `calculate_experience_weight`)
- Test: `tests/test_selections.py` (check existing filename first; create if absent)

**Interfaces:**
- Consumes: `ExperienceModelData.subject_contract_claims` (existing `@property`,
  returns `Dict[int, Claims]` keyed by layer_id — confirmed at
  `experience_preparer.py:158`); `Claim.capped_claim_development_history.latest_incurred`
  (existing property).

- [ ] **Step 1: Write failing tests isolating the two buggy branches**

```python
def test_greatest_accuracy_branch_does_not_raise_with_real_experience_data(self):
    selections = Selections(experience_data=real_fixture, exposure_data=mock_exposure_model)
    weight = selections.calculate_experience_weight(method="greatest_accuracy", collective_mean=1.0)
    self.assertGreaterEqual(weight, 0.0)
    self.assertLessEqual(weight, 1.0)

def test_bayesian_branch_does_not_raise_with_real_experience_data(self):
    selections = Selections(experience_data=real_fixture, exposure_data=mock_exposure_model)
    weight = selections.calculate_experience_weight(method="bayesian", prior_mean=1.0, prior_variance=0.1)
    self.assertGreaterEqual(weight, 0.0)
    self.assertLessEqual(weight, 1.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_selections.py -k branch_does_not_raise -v`
Expected: FAIL — `TypeError: 'dict' object is not callable` (line ~358/421/434
calling `subject_contract_claims()`) or `AttributeError: 'Claim' object has no
attribute 'amount'`.

- [ ] **Step 3: Fix `calculate_experience_weight`**

Replace `self.experience_data.subject_contract_claims()` (no parens — it's a
property) with correct claim-count logic:
`sum(len(c) for c in self.experience_data.subject_contract_claims.values())`.
Replace `claim.amount for claim in self.experience_data.subject_contract_claims()`
with a correctly nested comprehension:
```python
[
    claim.capped_claim_development_history.latest_incurred
    for claims_obj in self.experience_data.subject_contract_claims.values()
    for claim in claims_obj.claims
]
```
in both the `greatest_accuracy` and `bayesian` branches. Add a class docstring
to `CredibilityWeight` citing Mahler & Dean, Ch.8.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_selections.py -v`
Expected: PASS.

- [ ] **Step 5: Add a golden-value test for the credibility standard**

```python
def test_full_credibility_standard_matches_cas_exam_5_standard(self):
    """1,082 claims is the well-known Poisson full-credibility standard for
    +/-5% at 95% confidence (Mahler & Dean, Ch.8, Foundations of Casualty
    Actuarial Science, 4th ed., CAS)."""
    cw = CredibilityWeight(experience_data=mock, exposure_data=mock)
    self.assertEqual(cw.limited_fluctuation_credibility.__defaults__[0], 1082)
```
(Adjust to however the default is actually introspectable/asserted — the
point is pinning the 1082 default to the cited standard.)

- [ ] **Step 6: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`

- [ ] **Step 7: Commit**

```bash
git add src/pyre/models/AggregateFeatures/selections.py tests/test_selections.py
git commit -m "fix: correct subject_contract_claims property access and claim-amount reference in Selections"
```

---

### Task 13: Uniform exposure-curve-call adapter

**Files:**
- Modify: `src/pyre/models/Exposure/exposure_curve_functions.py:102-184`
- Modify: `src/pyre/models/Exposure/exposure_rating_cost.py:40-115`
- Test: `tests/test_exposure_rating_cost.py` (extend)

**Interfaces:**
- Produces: `calculate_curve(curve_type: ExposureCurveType, parameters: Dict, position: float) -> float`
  (revived from the dead commented-out code at `exposure_curve_functions.py:169-184`,
  fixed to dispatch correctly per curve type).
- Consumes: `riebesell_curve`, `mixed_exponential_curve`, `mbbefd_curve` (existing, unchanged internals).

- [ ] **Step 1: Write failing tests**

```python
def test_calculate_exposure_curve_works_for_all_curve_types_without_typeerror(self):
    for curve_type, params in [
        (ExposureCurveType.MBBEFD, {"curve": swissRe_c_values.COMMERCIAL_LINES_MEDIUM}),
        (ExposureCurveType.RIEBESELL, {"attachment": 100_000, "limit": 400_000, "z_value": 0.1, "base_limit": 1_000_000}),
        (ExposureCurveType.MIXED_EXPONENTIAL, {"paramaters_mus": [...], "parameter_weights": [...]}),
    ]:
        with self.subTest(curve_type=curve_type):
            model = ExposureModel(exposures=mock, ri_contract=mock, selected_curve=curve_type, curve_parameters=params)
            result = model.calculate_exposure_curve(curve_type, params, position=0.5)
            self.assertIsInstance(result, float)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_exposure_rating_cost.py -k all_curve_types -v`
Expected: FAIL — `TypeError` for RIEBESELL (no `curve_position` param) and
MIXED_EXPONENTIAL (`curve_position_value`, not `curve_position`).

- [ ] **Step 3: Implement the adapter**

In `exposure_curve_functions.py`, replace the dead comment at lines 169-184
with a real `calculate_curve` function that wraps each curve type into a
uniform `(parameters, curve_position) -> float` call — map RIEBESELL's
`curve_position` onto its `attachment`/`limit` inputs appropriately, map
MIXED_EXPONENTIAL's `curve_position_value` parameter name correctly. Update
`ExposureModel.calculate_exposure_curve` (`exposure_rating_cost.py:54-58`) to
call this adapter instead of `func(**parameters, curve_position=position)`
directly. Fix the `paramaters_mus` → `parameters_mus` typo in
`mixed_exponential_curve`'s signature and all call sites while here.

- [ ] **Step 4: Run test to verify it passes, plus a numeric-parity check**

```python
def test_adapter_matches_calling_underlying_function_directly(self):
    # same inputs through the adapter and through mbbefd_curve() directly
    # must produce the same value -- proves the adapter doesn't change behavior
```

Run: `pytest tests/test_exposure_rating_cost.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`

- [ ] **Step 6: Commit**

```bash
git add src/pyre/models/Exposure/exposure_curve_functions.py src/pyre/models/Exposure/exposure_rating_cost.py tests/test_exposure_rating_cost.py
git commit -m "fix: uniform curve-call adapter so ExposureModel works for all ExposureCurveType members"
```

---

### Task 14: ILF integration into `ExposureModel`

**Files:**
- Modify: `src/pyre/models/Exposure/exposure_rating_cost.py`
- Test: `tests/test_exposure_rating_cost.py` (extend)

**Interfaces:**
- Consumes: `pareto_ilf`, `power_ilf` from `exposure_ILF_functions.py` (existing, already cited to Palmer).
- Produces: `ExposureModel.__init__(..., ilf_function: Optional[Callable[[float], float]] = None)`;
  `ExposureModel.calculate_ilf_adjusted_rate(base_limit, target_limit) -> float`.

- [ ] **Step 1: Write failing test**

```python
def test_ilf_adjusted_rate_differs_from_unadjusted_for_higher_limit(self):
    from functools import partial
    from pyre.models.Exposure.exposure_ILF_functions import pareto_ilf
    model = ExposureModel(
        exposures=mock, ri_contract=mock, selected_curve=ExposureCurveType.MBBEFD,
        curve_parameters={...}, ilf_function=partial(pareto_ilf, alpha=1.5),
    )
    rate_at_base = model.calculate_ilf_adjusted_rate(base_limit=100_000, target_limit=100_000)
    rate_at_higher = model.calculate_ilf_adjusted_rate(base_limit=100_000, target_limit=500_000)
    self.assertGreater(rate_at_higher, rate_at_base)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_exposure_rating_cost.py -k ilf_adjusted -v`
Expected: FAIL — `TypeError: unexpected keyword argument 'ilf_function'`.

- [ ] **Step 3: Implement the ILF constructor param and method**

Add `ilf_function: Optional[Callable[[float], float]] = None` to
`ExposureModel.__init__`. Add `calculate_ilf_adjusted_rate(base_limit,
target_limit)` that applies `self._ilf_function(target_limit) /
self._ilf_function(base_limit)` when `ilf_function` is set (raise a clear
`ValueError` if called without one). This closes the TODO at
`exposure_rating_cost.py:40` — purely additive, no change to existing
curve-only behavior.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_exposure_rating_cost.py -k ilf_adjusted -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`

- [ ] **Step 6: Commit**

```bash
git add src/pyre/models/Exposure/exposure_rating_cost.py tests/test_exposure_rating_cost.py
git commit -m "feat: add ILF-adjusted rate option to ExposureModel (Palmer CAS Study Note)"
```

---

### Task 15: `curve-fitting` optional extra + docs

**Files:**
- Modify: `pyproject.toml`
- Modify: `CLAUDE.md`

**Interfaces:**
- Produces: `[project.optional-dependencies].curve-fitting` and
  `[tool.hatch.envs.curve-fitting]` in `pyproject.toml`, matching the existing
  `excel` extra's pattern exactly (`pyproject.toml:32-34, 119-122`).

- [ ] **Step 1: Add the extra**

```toml
[project.optional-dependencies]
curve-fitting = [
  "numpy>=1.24",
  "scipy>=1.10",
  "pandas>=2.0",
  "matplotlib>=3.7",
]
```
and
```toml
[tool.hatch.envs.curve-fitting]
dependencies = [
  "numpy>=1.24",
  "scipy>=1.10",
  "pandas>=2.0",
  "matplotlib>=3.7",
]
```

- [ ] **Step 2: Verify installability**

Run: `pip install -e ".[curve-fitting]"`
Expected: installs cleanly (no conflicting pins with the `panel`/`excel` extras).

- [ ] **Step 3: Update `CLAUDE.md`**

Add `pip install -e ".[curve-fitting]"` to the Commands section, matching the
style of the existing `panel`/`excel` lines.

- [ ] **Step 4: Run the full suite (without the new extra)**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: unchanged — this task has no code-behavior effect yet (Task 16 is
what actually uses the extra).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml CLAUDE.md
git commit -m "build: add optional curve-fitting extra (numpy/scipy/pandas/matplotlib)"
```

---

### Task 16: Wire `ExposureCurveFitter`/`ILFFitter` into `ExposureModel`; fix `test_exposure_curve_fitting.py`

**Files:**
- Modify: `src/pyre/models/Exposure/exposure_rating_cost.py`
- Modify: `tests/test_exposure_curve_fitting.py` (fix collection, add real tests)

**Interfaces:**
- Consumes: `ExposureCurveFitter.fit_all_curves()` (existing, returns best-fit
  curve type + params + R²); Task 15's `curve-fitting` extra.
- Produces: `ExposureModel.from_fitted_curve(fitter: ExposureCurveFitter, exposures, ri_contract) -> ExposureModel` classmethod.

- [ ] **Step 1: Check and fix the test file's collection error**

Read `tests/test_io_excel.py`'s skip-without-extra pattern (likely
`pytest.importorskip` or a module-level `try/except ImportError`). Apply the
exact same pattern to the top of `tests/test_exposure_curve_fitting.py` so it
skips gracefully without `scipy` instead of erroring at collection.

Run: `pytest tests/test_exposure_curve_fitting.py -v`
Expected (without the extra installed): all tests skip, 0 errors.
Expected (with `pip install -e ".[curve-fitting]"`): tests actually run.

- [ ] **Step 2: Write failing test for the new integration method**

```python
@pytest.mark.skipif(not _scipy_available(), reason="requires curve-fitting extra")
def test_from_fitted_curve_builds_usable_exposure_model():
    fitter = ExposureCurveFitter()
    fitter.fit_all_curves(observed_positions, observed_values)  # existing API
    model = ExposureModel.from_fitted_curve(fitter, exposures=mock, ri_contract=mock)
    shares = model.calculate_all_shares()
    assert all(0.0 <= v <= 1.0 for layer_shares in shares.values() for v in layer_shares.values())
```

- [ ] **Step 3: Run test to verify it fails (with the extra installed)**

Run: `pip install -e ".[curve-fitting]" && pytest tests/test_exposure_curve_fitting.py -k from_fitted_curve -v`
Expected: FAIL — `AttributeError: no classmethod from_fitted_curve`.

- [ ] **Step 4: Implement `ExposureModel.from_fitted_curve`**

Translate `fit_all_curves()`'s best-fit output (curve type + params) into
`ExposureModel`'s existing `selected_curve`/`curve_parameters` constructor args.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_exposure_curve_fitting.py -v`
Expected: PASS (with the extra installed).

- [ ] **Step 6: Run the full suite both ways**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py` (always)
Run: `pytest tests/test_exposure_curve_fitting.py -v` (with and without the
extra installed, to confirm the skip-vs-run split works both ways).

- [ ] **Step 7: Commit**

```bash
git add src/pyre/models/Exposure/exposure_rating_cost.py tests/test_exposure_curve_fitting.py
git commit -m "feat: wire ExposureCurveFitter into ExposureModel; skip curve-fitting tests gracefully without scipy"
```

---

### Task 17: Parallelogram method for aggregate exposures

**Files:**
- Modify: `src/pyre/exposures/exposures.py:169-190`
- Test: `tests/test_exposures.py` (extend)

**Interfaces:**
- Modifies: `Exposure._earned_pct(analysis_date)` — the `aggregate=True`
  branch only; non-aggregate behavior (lines 183-190) is unchanged.

- [ ] **Step 1: Write the failing golden-value test**

```python
def test_earned_pct_aggregate_symmetric_case_matches_geometric_derivation(self):
    """Golden value: a policy written uniformly over 1/1-12/31 (aggregate=True),
    evaluated at the mid-year analysis date (7/1 or 7/2 depending on leap
    year), has a geometrically-derivable triangle-overlap earned fraction of
    exactly 0.5 by symmetry, under the uniform-writing assumption (Werner &
    Modlin, Basic Ratemaking, 5th ed., CAS -- parallelogram method chapter).
    """
    meta = ExposureMetaData(..., aggregate=True,
                             exposure_period_start=date(2023, 1, 1),
                             exposure_period_end=date(2023, 12, 31))
    exposure = Exposure(meta, ExposureValues(exposure_value=1_000_000, attachment_point=0, limit=1_000_000))
    pct = exposure._earned_pct(date(2023, 7, 1))
    self.assertAlmostEqual(pct, 0.5, places=2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_exposures.py -k aggregate_symmetric -v`
Expected: FAIL — `_earned_pct` currently returns `0.0` unconditionally for
`aggregate=True`.

- [ ] **Step 3: Implement the parallelogram method**

Replace `return 0.0` (line 182) with the geometric triangle/trapezoid-overlap
calculation for a uniform-writing assumption. Cite Werner & Modlin in the
method's docstring — confirm the exact chapter/section against the actual
text before finalizing the citation (don't guess a page number).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_exposures.py -k aggregate_symmetric -v`
Expected: PASS.

- [ ] **Step 5: Add boundary-case regression tests**

```python
def test_earned_pct_aggregate_before_period_start_is_zero(self): ...
def test_earned_pct_aggregate_after_period_end_plus_term_is_one(self): ...
```

- [ ] **Step 6: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`

- [ ] **Step 7: Commit**

```bash
git add src/pyre/exposures/exposures.py tests/test_exposures.py
git commit -m "feat: implement parallelogram method for aggregate exposure earned-pct (Werner & Modlin)"
```

---

### Task 18: Populate `Exposure/__init__.py` (+ `models/__init__.py`)

**Files:**
- Modify: `src/pyre/models/Exposure/__init__.py` (currently 0 bytes)
- Modify: `src/pyre/models/__init__.py`
- Test: `tests/test_exposure_module_init.py` (new, small)

**Interfaces:**
- Produces: eager exports `ExposureModel`, `ExposureCurveType`, `mbbefd_curve`,
  `mixed_exponential_curve`, `riebesell_curve`, `swissRe_c_values`,
  `pareto_ilf`, `power_ilf`; lazy `__getattr__` for `ExposureCurveFitter`/`ILFFitter`.

- [ ] **Step 1: Write failing tests**

```python
def test_exposure_module_imports_without_scipy_installed(self):
    # import pyre.models.Exposure must succeed and expose ExposureModel
    # regardless of scipy's presence
    from pyre.models.Exposure import ExposureModel
    self.assertTrue(callable(ExposureModel))

def test_exposure_curve_fitter_lazy_import_error_names_the_extra(self):
    # only meaningful when scipy is NOT installed -- skip if it is
    if _scipy_available():
        self.skipTest("scipy is installed; lazy-import error path not exercised")
    import pyre.models.Exposure as exposure_pkg
    with self.assertRaises(ImportError) as ctx:
        exposure_pkg.ExposureCurveFitter
    self.assertIn("curve-fitting", str(ctx.exception))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_exposure_module_init.py -v`
Expected: FAIL — `ImportError: cannot import name 'ExposureModel' from 'pyre.models.Exposure'`
(empty `__init__.py`).

- [ ] **Step 3: Implement `Exposure/__init__.py`**

```python
from .exposure_rating_cost import ExposureModel
from .exposure_curve_functions import (
    ExposureCurveType, mbbefd_curve, mixed_exponential_curve, riebesell_curve, swissRe_c_values,
)
from .exposure_ILF_functions import pareto_ilf, power_ilf

__all__ = [
    "ExposureModel", "ExposureCurveType", "mbbefd_curve", "mixed_exponential_curve",
    "riebesell_curve", "swissRe_c_values", "pareto_ilf", "power_ilf",
    "ExposureCurveFitter", "ILFFitter",
]

def __getattr__(name):
    if name == "ExposureCurveFitter":
        try:
            from .exposure_curve_fitting import ExposureCurveFitter
            return ExposureCurveFitter
        except ImportError as e:
            raise ImportError(
                f'{name} requires the "curve-fitting" optional extra: pip install -e ".[curve-fitting]"'
            ) from e
    if name == "ILFFitter":
        try:
            from .exposure_ILF_fitting import ILFFitter
            return ILFFitter
        except ImportError as e:
            raise ImportError(
                f'{name} requires the "curve-fitting" optional extra: pip install -e ".[curve-fitting]"'
            ) from e
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

- [ ] **Step 4: Add `from .Exposure import ExposureModel` to `models/__init__.py`**

(Don't propagate the lazy-import boundary further up — `models/__init__.py`
only re-exports `ExposureModel`, not the fitters.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_exposure_module_init.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`

- [ ] **Step 7: Commit**

```bash
git add src/pyre/models/Exposure/__init__.py src/pyre/models/__init__.py tests/test_exposure_module_init.py
git commit -m "feat: populate Exposure/__init__.py public API with lazy scipy-dependent exports"
```

---

### Task 19: `ModellingAssumptions` dataclass + `Simulation` core (sampling, loss_cost, required_capital)

**Files:**
- Modify: `src/pyre/models/AggregateFeatures/aggregate_features.py` (ModellingAssumptions)
- Modify: `src/pyre/models/AggregateFeatures/simulation_engine.py`
- Test: `tests/test_simulation.py` (new)

**Interfaces:**
- Consumes: `FrequencyFit`/`SeverityFit` (Tasks 9-10), `RILayer.loss_to_layer_fn`
  (works for all layer types post-Task 5), `RIContract.layers`.
- Produces: `ModellingAssumptions` dataclass (`cost_of_capital`,
  `required_rate_of_return`, `capital_confidence_level: float = 0.995`,
  `use_tvar: bool = True`, `investment_yield: float = 0.0`, `tax_rate: float = 0.0`,
  `acquisition_cost_ratio: float = 0.0`, `brokerage_cost_ratio: float = 0.0`);
  `Simulation.__init__(frequency_fit, severity_fit, ri_contract, assumptions,
  n_simulations=10_000, random_seed=None, retrocession_contract=None)`;
  `Simulation.run() -> None` (populates internal per-simulation ceded-loss
  arrays, keyed by layer_id); `Simulation.loss_cost() -> Dict[int, float]`;
  `Simulation.required_capital() -> Dict[int, float]`.

- [ ] **Step 1: Convert `ModellingAssumptions` to a dataclass**

Replace the `namedtuple` in `aggregate_features.py:6-9` with a `@dataclass`
carrying the 8 fields listed above. Document `capital_confidence_level=0.995`
explicitly as "a commonly used convention in practice (e.g. Solvency II's
1-in-200 standard)" — NOT attributed to Butsic or the DFA Handbook (neither
source mandates this specific number; this distinction is a Review Focus item).

- [ ] **Step 2: Write a failing determinism test**

```python
def test_run_is_deterministic_with_same_random_seed(self):
    freq_fit = FrequencyFit([FrequencyDistribution.POISSON], [2, 3, 2, 4]).fit()[0]
    sev_fit = ... # a fixed-severity FitResult stand-in, or a trivial SeverityFit
    sim = Simulation(freq_fit, sev_fit, ri_contract=xol_contract,
                      assumptions=ModellingAssumptions(cost_of_capital=0.1, required_rate_of_return=0.08),
                      n_simulations=1000, random_seed=42)
    sim.run()
    first = sim.loss_cost()
    sim2 = Simulation(freq_fit, sev_fit, ri_contract=xol_contract,
                       assumptions=sim2_assumptions, n_simulations=1000, random_seed=42)
    sim2.run()
    self.assertEqual(first, sim2.loss_cost())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_simulation.py -k deterministic -v`
Expected: FAIL — `Simulation.__init__` currently takes no arguments.

- [ ] **Step 3: Implement `__init__` and `run()`**

`run()`: for `n_simulations` draws, sample a claim count from the frequency
fit, then that many severities from the severity fit; run each simulated
gross loss through every layer's `loss_to_layer_fn` (this is why
`required_capital` must use the *ceded*, not gross, distribution — Review
Focus item); accumulate per-simulation aggregate ceded loss per layer_id.
Use `random.Random(random_seed)` for reproducibility.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_simulation.py -k deterministic -v`
Expected: PASS.

- [ ] **Step 5: Write and implement `loss_cost()`**

```python
def test_loss_cost_converges_to_analytical_expectation(self):
    """Poisson(lambda=2) x fixed severity $10,000 through an unlimited XOL
    layer -> analytically E[loss] = 20,000. Asserted within a documented
    Monte Carlo tolerance (n_simulations=20,000, tolerance=+/-5%) -- not a
    textbook golden value (inherently stochastic), but an analytically
    derivable sanity bound."""
```
Implement `loss_cost() -> Dict[int, float]` as the mean ceded loss per layer
across simulations.

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_simulation.py -k loss_cost -v`
Expected: PASS within the documented tolerance.

- [ ] **Step 7: Write and implement `required_capital()`**

```python
def test_required_capital_tvar_is_at_least_var_same_confidence(self):
    # TVaR >= VaR at the same confidence level is a definitional inequality
```
Implement VaR/TVaR (per `assumptions.use_tvar`) at
`assumptions.capital_confidence_level` of the simulated *ceded* aggregate-loss
distribution per layer.

- [ ] **Step 8: Run test, then full suite**

Run: `pytest tests/test_simulation.py -v` then
`pytest -q --ignore=tests/test_exposure_curve_fitting.py`

- [ ] **Step 9: Commit**

```bash
git add src/pyre/models/AggregateFeatures/aggregate_features.py src/pyre/models/AggregateFeatures/simulation_engine.py tests/test_simulation.py
git commit -m "feat: implement Simulation core (Monte Carlo sampling, loss_cost, required_capital)"
```

---

### Task 20: `Simulation` remaining methods (cashflows, investment, retrocession, required premium, output, save)

**Files:**
- Modify: `src/pyre/models/AggregateFeatures/simulation_engine.py`
- Test: `tests/test_simulation.py` (extend)

**Interfaces:**
- Consumes: `ClaimDevelopmentHistory.mean_payment_duration` (existing,
  `claims.py:92-100`); Task 19's `loss_cost()`/`required_capital()`.
- Produces: `SimulationResults` dataclass; `Simulation.output() ->
  SimulationResults`; `Simulation.save(path: str) -> None` (JSON via stdlib `json`).

- [ ] **Step 1: Write failing tests for the premium build-up**

```python
def test_required_premium_layer_exceeds_loss_cost_when_cost_of_capital_positive(self):
    sim.run()
    for layer_id in loss_costs:
        self.assertGreater(sim.required_premium_layer(layer_id), sim.loss_cost()[layer_id])

def test_required_premium_programme_sums_across_layers(self):
    total = sim.required_premium_programme()
    self.assertAlmostEqual(total, sum(sim.required_premium_layer(lid) for lid in layer_ids), places=2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_simulation.py -k required_premium -v`
Expected: FAIL — these methods are still `pass`-bodied stubs.

- [ ] **Step 3: Implement `cashflows()`/`investment_return()`**

Use `mean_payment_duration` per claim to discount/accrue investment income at
`assumptions.investment_yield`. Cite Clark (1996/2014) §B (investment income
treatment), reusing the citation from Task 5.

- [ ] **Step 4: Implement `profit_commission()`, `retrocession_cost()`/`retrocession_benefits()`**

`retrocession_cost()`/`retrocession_benefits()` apply `retrocession_contract`
(if provided) to the simulated ceded losses the same way `run()` applies the
primary `ri_contract`. `profit_commission()` applies a configurable rate to
the layer's underwriting profit (loss_cost vs. premium) — expose as a
constructor-level parameter rather than hardcoding a rate, since no source
pins one specific number.

- [ ] **Step 5: Implement `required_premium_layer()`/`required_premium_programme()`**

`required_premium_layer(layer_id) = loss_cost[layer_id] +
assumptions.cost_of_capital * required_capital[layer_id] -
investment_return[layer_id] + net_retrocession_cost[layer_id] +
acquisition_cost + brokerage_cost`. `required_premium_programme()` sums this
across all layer_ids.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_simulation.py -v`
Expected: PASS.

- [ ] **Step 7: Implement `output()` and `save()`**

`SimulationResults` dataclass carrying all per-layer figures (`loss_cost`,
`required_capital`, `required_premium_layer`, `required_premium_programme`,
etc.). `save(path)` writes it as JSON via stdlib `json` (no new dependency).

- [ ] **Step 8: Write a round-trip test**

```python
def test_save_and_reload_produces_equivalent_json(self):
    sim.run()
    sim.save(tmp_path)
    with open(tmp_path) as f:
        data = json.load(f)
    self.assertIn("required_premium_programme", data)
```

- [ ] **Step 9: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`

- [ ] **Step 10: Commit**

```bash
git add src/pyre/models/AggregateFeatures/simulation_engine.py tests/test_simulation.py
git commit -m "feat: complete Simulation DFA engine (cashflows, retrocession, required premium, output/save)"
```

---

### Task 21: `AggregateFeatures` orchestrator + `AggregateFeatures/__init__.py`

**Files:**
- Modify: `src/pyre/models/AggregateFeatures/aggregate_features.py`
- Modify: `src/pyre/models/AggregateFeatures/__init__.py` (currently 0 bytes)
- Test: `tests/test_aggregate_features.py` (check existing filename first; create if absent)

**Interfaces:**
- Consumes: `Simulation` (Tasks 19-20), `Selections` (Task 12), `ExperienceModelData`, `ExposureModel`.
- Produces: `AggregateFeatures(experience_data, exposure_data, selections,
  assumptions).run(n_simulations=10_000) -> SimulationResults`.

- [ ] **Step 1: Write a failing smoke test**

```python
def test_aggregate_features_run_returns_well_formed_results(self):
    af = AggregateFeatures(experience_data=fixture_experience_data,
                            exposure_data=fixture_exposure_model,
                            selections=fixture_selections,
                            assumptions=ModellingAssumptions(cost_of_capital=0.1, required_rate_of_return=0.08))
    results = af.run(n_simulations=500)
    self.assertGreaterEqual(results.required_premium_programme, 0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_aggregate_features.py -v`
Expected: FAIL — `create_simulation`'s `Simulation(...)` call passes `Ellipsis`,
mismatched against Task 19's real `__init__` signature.

- [ ] **Step 3: Implement the orchestrator**

Restructure `AggregateFeatures.__init__(experience_data, exposure_data,
selections, assumptions)`. `run(n_simulations=10_000)`: fit frequency/severity
from `experience_data` (via `FrequencyFit`/`SeverityFit`), build a `Simulation`
with the real constructor args, call `.run()` then `.output()`, return the
`SimulationResults`. Remove the `# TODO tidy up` comment.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_aggregate_features.py -v`
Expected: PASS.

- [ ] **Step 5: Populate `AggregateFeatures/__init__.py`**

```python
from .simulation_engine import Simulation, SimulationResults
from .selections import Selections, CredibilityWeight
from .aggregate_features import AggregateFeatures, ModellingAssumptions

__all__ = ["Simulation", "SimulationResults", "Selections", "CredibilityWeight",
           "AggregateFeatures", "ModellingAssumptions"]
```
(Pure stdlib — no lazy-import pattern needed here, unlike Task 18.)

- [ ] **Step 6: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`

- [ ] **Step 7: Commit**

```bash
git add src/pyre/models/AggregateFeatures/aggregate_features.py src/pyre/models/AggregateFeatures/__init__.py tests/test_aggregate_features.py
git commit -m "feat: implement AggregateFeatures orchestrator and populate its public API"
```

---

### Task 22: E2E — SURPLUS_SHARE through `run_pricing`

**Files:**
- Modify: `tests/test_app_service.py`

**Interfaces:**
- Consumes: Tasks 5-6 (SURPLUS_SHARE backend + `build_layer`'s `sum_insured` passthrough).

- [ ] **Step 1: Write the failing e2e test**

```python
def test_run_pricing_with_surplus_share_layer_matches_clark_cession(self):
    claims = parse_claims_csv(CLAIMS_CSV)  # existing fixture in this file
    exposures = parse_exposures_csv(EXPOSURES_CSV)
    layer = build_layer({
        "layer_id": 1, "layer_name": "Surplus 1", "layer_type": "SURPLUS_SHARE",
        "occurrence_attachment": 100_000, "occurrence_limit": 400_000,
        "sum_insured": 1_000_000, "full_subject_premium": 0.0,
    })
    contract = RIContract(contract_meta_data=build_contract_metadata({...}), layers=[layer])
    results = run_pricing(claims, exposures, contract)
    # hand-computed: 40% of whatever ceded_incurred the CLAIMS_CSV fixture
    # produces for this layer, using Clark's risk-5 cession percentage
    self.assertAlmostEqual(results.by_layer_year.loc[0, "ceded_incurred"], expected_value, places=2)
```

- [ ] **Step 2: Remove/replace the now-stale test**

Delete `test_run_pricing_with_surplus_share_layer_raises` (it asserted
`NotImplementedError`, which Task 5 removed).

- [ ] **Step 3: Run test to verify it fails, then passes**

Run: `pytest tests/test_app_service.py -k surplus_share -v`
Expected: FAIL first (compute `expected_value` by hand from the fixture CSVs
+ Clark's cession %), then PASS once the hand-computed value is confirmed correct.

- [ ] **Step 4: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`

- [ ] **Step 5: Commit**

```bash
git add tests/test_app_service.py
git commit -m "test: add SURPLUS_SHARE end-to-end pricing test, remove stale NotImplementedError test"
```

---

### Task 23: E2E — fitted exposure curve → `ExposureModel` → share-of-layer

**Files:**
- Modify: `tests/test_exposure_rating_cost.py` (extend — reuse rather than fragment into a new file)

**Interfaces:**
- Consumes: Task 16's `ExposureModel.from_fitted_curve`.

- [ ] **Step 1: Write the failing e2e test**

```python
@pytest.mark.skipif(not _scipy_available(), reason="requires curve-fitting extra")
def test_fitted_curve_through_calculate_all_shares_e2e():
    fitter = ExposureCurveFitter()
    fitter.fit_all_curves(synthetic_positions, synthetic_values)
    model = ExposureModel.from_fitted_curve(fitter, exposures=mock_exposures, ri_contract=mock_contract)
    shares = model.calculate_all_shares()
    for layer_shares in shares.values():
        values = list(layer_shares.values())
        assert all(0.0 <= v <= 1.0 for v in values)
```

- [ ] **Step 2: Run test to verify it fails (with extra installed)**

Run: `pip install -e ".[curve-fitting]" && pytest tests/test_exposure_rating_cost.py -k e2e -v`

- [ ] **Step 3: Fix anything Task 16 didn't already cover**

Most of this should already work from Task 16; this task is primarily about
proving the full pipeline, not new production code — if something doesn't
wire up, treat it as a Task 16 gap and fix it there, re-running Task 16's own tests too.

- [ ] **Step 4: Run test to verify it passes, then full suite both ways**

Run: `pytest tests/test_exposure_rating_cost.py -v` (with and without the extra)
Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py` (always)

- [ ] **Step 5: Commit**

```bash
git add tests/test_exposure_rating_cost.py
git commit -m "test: add fitted-curve-to-share-of-layer end-to-end test"
```

---

### Task 24: E2E — AggregateFeatures/Simulation pricing path

**Files:**
- Modify: `tests/test_app_service.py` or `tests/test_aggregate_features.py` (whichever Task 21 used)

**Interfaces:**
- Consumes: Tasks 19-21 (full Simulation/AggregateFeatures stack).

- [ ] **Step 1: Write the failing e2e test**

```python
def test_aggregate_features_pricing_path_structural_e2e(self):
    """Scoped to structural correctness and sane bounds, not an exact figure --
    Simulation output is inherently stochastic, so no independent textbook
    number exists to check against (same reasoning as Tasks 19-20's test gaps).
    """
    claims = parse_claims_csv(CLAIMS_CSV)
    exposures = parse_exposures_csv(EXPOSURES_CSV)
    experience_data = ExperienceModelData(claims=claims, exposures=exposures, ri_contract=contract)
    exposure_model = ExposureModel(exposures=exposures, ri_contract=contract,
                                    selected_curve=ExposureCurveType.MBBEFD, curve_parameters={...})
    selections = Selections(experience_data, exposure_model)
    assumptions = ModellingAssumptions(cost_of_capital=0.15, required_rate_of_return=0.1)
    af = AggregateFeatures(experience_data, exposure_model, selections, assumptions)
    results = af.run(n_simulations=1000)
    self.assertGreaterEqual(results.required_capital_total, 0.0)
    self.assertGreater(results.required_premium_programme, results.loss_cost_total)
    # seeded reproducibility
    af2 = AggregateFeatures(experience_data, exposure_model, selections, assumptions)
    results2 = af2.run(n_simulations=1000)
    self.assertAlmostEqual(results.required_premium_programme, results2.required_premium_programme, places=0)
```

(Adjust field names to whatever `SimulationResults` actually exposes from Task 20.)

- [ ] **Step 2: Run test to verify it fails, then passes**

Run: `pytest -k aggregate_features_pricing_path_structural_e2e -v`

- [ ] **Step 3: Run the full suite**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: add AggregateFeatures/Simulation structural end-to-end pricing test"
```

---

### Task 25: Final docs sweep

**Files:**
- Modify: `docs/models.md`, `docs/treaty.md`, `CLAUDE.md`

- [ ] **Step 1: Run the full suite and capture the real final count**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py` (record N passed)
Run: `pip install -e ".[curve-fitting]" && pytest tests/test_exposure_curve_fitting.py -v` (confirm passes with the extra)

- [ ] **Step 2: Update `docs/models.md`**

Remove the "early-stage"/"not yet functional" callouts for `SeverityFit` and
`AggregateFeatures`/`Simulation` (both now implemented). Confirm the Trending
warning was already corrected in Task 4. Add a short worked SURPLUS_SHARE
example mirroring the existing XOL example.

- [ ] **Step 3: Update `docs/treaty.md` and `CLAUDE.md`**

Confirm Task 5/6's SURPLUS_SHARE updates are complete and consistent. Update
`CLAUDE.md`'s Known Test State section with the real final test count from
Step 1 (never a guessed number) and the `curve-fitting` extra note from Task 15/16.

- [ ] **Step 4: Run the full suite one final time**

Run: `pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: 0 failed.

- [ ] **Step 5: Commit**

```bash
git add docs/models.md docs/treaty.md CLAUDE.md
git commit -m "docs: final sweep -- remove stale maturity warnings, update test counts"
```
