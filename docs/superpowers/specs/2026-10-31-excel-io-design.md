# pyRE Excel File I/O (Headless) Design

**Date:** 2026-10-31
**Status:** Approved
**Scope:** New optional subpackage `src/pyre/io_excel/` — read claims/exposures from `.xlsx`, write experience-rating, exposure-rating, and triangle results to `.xlsx`
**Backward compatibility:** Fully additive. No changes to any existing public signature except one bug fix (see below).

---

## Overview

This is the first of several planned enhancements to pyRE (database backend, xlwings
live integration, and Panel-app report export are each separate, independent
follow-up sub-projects — not covered here). This spec covers **headless Excel file
I/O**: reading `.xlsx` workbooks into `Claims`/`Exposures`, and writing triangle,
experience-rating, and exposure-rating results out to `.xlsx` — all without
requiring Excel to be installed (no xlwings/COM).

### Why this scope, and why first

- No database, xlwings, or report-export code exists anywhere in the repo today
  (confirmed via `grep`) — this is greenfield.
- Reinsurance actuaries' source data and deliverables are overwhelmingly Excel-native.
  File I/O is the most immediately useful, least architecturally entangled piece of
  the five originally-requested items.
- It has no dependency on the Panel app (`app/`), the (not-yet-designed) database
  backend, or xlwings — it stands alone and is usable from plain `pyre` scripts.

### Dependency approach

A new optional extra, `excel = ["openpyxl>=3.1"]`, added to `pyproject.toml`
alongside the existing `panel` extra. `src/pyre/io_excel/` is **never imported by
`src/pyre/__init__.py`** — a bare `import pyre` never requires `openpyxl`. Only
`from pyre.io_excel import ...` does, exactly mirroring how `panel`/`pandas` are
gated behind the `panel` extra today.

`io_excel` does **not** depend on `pandas` or on `app/` (which isn't an installable
package at all — see `CLAUDE.md`'s note on `app/main.py`). All reading/writing is
done directly via `openpyxl`'s cell API. This keeps the `excel` extra minimal and
keeps `io_excel` usable by anyone with just `pip install -e ".[excel]"`, independent
of whether they've also installed `panel`.

---

## Module Layout

```
src/pyre/io_excel/
├── __init__.py       # re-exports: read_claims, read_exposures, write_triangle,
│                      #   write_experience_rating_results, write_exposure_rating_results
├── _workbook.py        # write_table(headers, rows, path, sheet_name) -- low-level
│                        #   openpyxl-only primitive shared by all write_* functions
├── claims_io.py         # read_claims(path, sheet_name="Claims") -> Claims
├── exposures_io.py      # read_exposures(path, sheet_name="Exposures") -> Exposures
├── triangle_io.py        # write_triangle(triangle, path, sheet_name="Triangle") -> None
└── results_io.py          # write_experience_rating_results(model_data, path) -> None
                            # write_exposure_rating_results(exposure_model, path) -> None
```

Each `write_*` function builds its sheet(s) from `_workbook.write_table`, so a
later sub-project (e.g. the Panel-app export button) can reuse the same primitive
without pulling in `io_excel`'s claims/exposures-specific read logic.

---

## Public API

### Reading

```python
def read_claims(path: str | Path, sheet_name: str = "Claims") -> Claims: ...
def read_exposures(path: str | Path, sheet_name: str = "Exposures") -> Exposures: ...
```

Mirrors the existing long-format CSV schema in `app/service.py`
(`CLAIMS_REQUIRED_COLUMNS` / `EXPOSURES_REQUIRED_COLUMNS`) — same required
columns, same grouping-by-`claim_id` behavior for claims (one row per
development point), same `ValueError` if `contract_limit` is missing or `<= 0`
(it defaults to `0.0` on `ClaimsMetaData`, which silently zeroes every value in
`capped_claim_development_history`). The column lists are **redefined locally**
in `io_excel` (not imported from `app/service.py`) since `app/` is not an
installable package and must not become a dependency of `io_excel`.

Date cells: accept native Excel dates (`openpyxl` gives back `datetime.datetime`/
`datetime.date` directly) or ISO-format (`YYYY-MM-DD`) strings; anything else
raises `ValueError`.

Boolean cells (e.g. `claim_in_xs_of_deductible`, `aggregate`): accept native
Excel booleans, or strings `"true"/"1"/"yes"` (case-insensitive) as `True`,
anything else (including empty/missing) as `False` — same semantics as
`app/service.py`'s `_parse_bool`, reimplemented locally.

### Writing

```python
def write_triangle(triangle: Triangle, path: str | Path, sheet_name: str = "Triangle") -> None: ...

def write_experience_rating_results(model_data: ExperienceModelData, path: str | Path) -> None: ...

def write_exposure_rating_results(exposure_model: ExposureModel, path: str | Path) -> None: ...
```

- `write_triangle`: one sheet, a grid with `origin_years` as rows and
  `dev_periods` as columns (header row = dev periods, first column = origin
  year), values from `triangle.triangle`. Missing cells (no claim data at that
  origin/dev combination) are left blank.
- `write_experience_rating_results`: two sheets.
  - `"ByLayerYear"`: one row per `(layer_id, modelling_year)`, columns
    `layer_id, layer_name, modelling_year, ceded_paid, ceded_incurred,
    claim_count, earned_premium`, sourced from
    `model_data.aggregate_subject_contract_claims` and
    `model_data.aggregate_exposures` (for `earned_premium`), with
    `layer_name` looked up from `model_data.ri_contract.layers`. (No
    `loss_ratio` column — that derived value is a Panel-app presentation
    choice in `app/service.py::run_pricing`, not part of the core results
    shape; a later report-export sub-project can add it if needed.)
  - `"ExposuresByYear"`: one row per `modelling_year`, columns
    `modelling_year, written, earned`, sourced from `model_data.aggregate_exposures`.
- `write_exposure_rating_results`: one sheet, `"ExposureShares"`, one row per
  `(exposure_id, layer_id)`, columns `exposure_id, layer_id, share`, sourced
  from the new `ExposureModel.calculate_all_shares()` method (see below).

### New method: `ExposureModel.calculate_all_shares()`

`src/pyre/models/Exposure/exposure_rating_cost.py` currently has no public
method that runs `_calculate_single_exposure_share` across an entire `Exposures`
collection and aggregates the result — `_calculate_single_exposure_share` is
private and per-exposure only. Add:

```python
def calculate_all_shares(self) -> Dict[str, Dict[int, float]]:
    """Run _calculate_single_exposure_share for every exposure in self._exposures.

    Returns:
        Dict mapping exposure_id -> {layer_id: share}.
    """
```

### Bug fix required for correctness: `_calculate_single_exposure_share` indentation

Lines 85–116 of `exposure_rating_cost.py` today:

```python
            if treaty_layer_limit + treaty_layer_attachment < policy_limit:
                treaty_top = policy_attachment + treaty_layer_limit + treaty_layer_attachment
            else:
                treaty_top = total_insured_value

                ##TODO: below is not general for all function very much mbbefd curve input expectations.

                # Use the general calculate_curve function for other curve types
                curve_position_policy_lower = self.calculate_exposure_curve(...)
                curve_position_policy_higher = self.calculate_exposure_curve(...)
                curve_position_treaty_lower = self.calculate_exposure_curve(...)
                curve_position_treaty_higher = self.calculate_exposure_curve(...)

                share = (curve_position_treaty_higher - curve_position_treaty_lower) / (
                    curve_position_policy_higher - curve_position_policy_lower
                )
                shares_by_layer[layer.layer_id] = share

        return shares_by_layer
```

The curve-position calculation and the `shares_by_layer[layer.layer_id] = share`
assignment are nested **only** inside the `else` branch — so whenever a layer's
limit+attachment fits inside the policy limit (the `if` branch, likely the
common case), that layer is silently missing from the result entirely. Fix: dedent
that block one level so it runs after the `if`/`else` regardless of which branch
was taken (both branches only need to agree on `treaty_top`; the curve-position
calculation is identical either way).

This is a required fix, not an optional cleanup — `calculate_all_shares()`
would otherwise silently produce incomplete results for the common case. Scope
is limited to this one indentation fix; the file's other TODOs (e.g. the
general-curve-type comment, the ILF option mentioned in a separate TODO) are
untouched.

---

## Error Handling

All `read_*`/`write_*` functions raise plain `ValueError` with a descriptive
message, matching the existing CSV-parser convention in `app/service.py` — no
new custom exception types. `openpyxl`'s own exceptions (e.g. `FileNotFoundError`
for a missing path, `KeyError`/`InvalidFileException` for a bad sheet name or
corrupt workbook) propagate unchanged; no need to wrap them.

If `openpyxl` is not installed and someone does `from pyre.io_excel import
read_claims`, Python's own `ModuleNotFoundError` surfaces naturally (same as
`panel`/`pandas` behave for the `app/` layer today) — no custom wrapping needed.

---

## Testing

New file: `tests/test_io_excel.py`, `unittest.TestCase` style (matches the rest
of the repo). Guard the whole file so a default `pytest` run — without the
`excel` extra installed — **skips cleanly** rather than erroring at collection
(improves on the pre-existing `test_exposure_curve_fitting.py`/`scipy` situation,
which does error at collection):

```python
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
```

...with every test class decorated `@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")`.

Coverage required:

1. `write_table` → read back raw cells via `openpyxl.load_workbook` → assert
   header row + values.
2. `read_claims` round-trip: write a workbook with the expected schema (via
   `openpyxl` directly, not via `write_table`, to simulate a real user's file),
   read it with `read_claims`, assert the resulting `Claims` collection's
   values. Include: missing required column → `ValueError`; `contract_limit`
   missing/`<= 0` → `ValueError`; a date given as an ISO string vs. a native
   Excel date cell, both parse correctly.
3. `read_exposures`: same pattern, one row per exposure (no grouping).
4. `write_triangle`: build a small `Triangle`, write it, read back raw cells,
   assert origin years are rows, dev periods are columns, values match
   (including blank cells where no data exists for that combination).
5. `write_experience_rating_results`: build a minimal `ExperienceModelData`
   using the same claims/exposures/contract construction pattern as
   `tests/test_app_service.py::TestRunPricing.setUp` (build `Claims`/
   `Exposures` directly via `Claim`/`ClaimDevelopmentHistory`/`ClaimsMetaData`/
   `Exposure`/`ExposureMetaData`/`ExposureValues`, and an `RIContract` via
   `RIContractMetadata` + `RILayer`), write, read back both sheets, assert row
   values.
6. `write_exposure_rating_results`: build a minimal `ExposureModel` with two
   layers, assert both sheets reflect `calculate_all_shares()`'s output.
7. **Regression test for the indentation bug**: construct one exposure/layer
   pair where `treaty_layer_limit + treaty_layer_attachment < policy_limit`
   (the previously-broken `if` branch) and one pair where it doesn't (the
   `else` branch), call `calculate_all_shares()`, and assert **both** layers
   appear in the result with correct share values — this is the test that
   would have caught the original bug.

---

## Out of Scope (explicitly deferred to later sub-projects)

- Database backend (persistence for contracts/claims/exposures/results).
- xlwings live two-way Excel integration (Windows/Mac desktop only, requires
  Excel installed — architecturally distinct from headless file I/O).
- Writing `Claims`/`Exposures` back out to `.xlsx` (round-trip write) —
  reading covers the "my source data is in Excel" workflow; writing a
  *result* (triangle/experience/exposure rating) is what "export" means in
  this spec. A template-generator or audit-export feature is a reasonable
  future ask but wasn't requested here.
- Panel app "export" button — will reuse `_workbook.write_table` once built,
  but wiring it into `app/pages/results.py` is its own follow-up sub-project.
- Fixing `exposure_rating_cost.py`'s other TODOs (general curve-type handling,
  the ILF-option comment) beyond the one indentation bug required for
  `calculate_all_shares()` correctness.
