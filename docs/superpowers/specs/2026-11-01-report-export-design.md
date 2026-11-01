# pyRE Standardized Report Export Design

**Date:** 2026-11-01
**Status:** Approved
**Scope:** Deduplicate experience-rating result aggregation into one core function; add in-memory (buffer) write support to the existing Excel writer; add a "Export to Excel" download button to the Panel app's results page.
**Backward compatibility:** Fully additive to public signatures except one bug fix (see below) and one new column in an existing Excel sheet.

---

## Overview

This is the second of four follow-up sub-projects identified after the
Freyja branding/test-fix work (report export, database backend, xlwings
integration — the other three are each separate, independent, and not
covered here). It closes out the "Panel app export button" and "write
`Claims`/`Exposures` results as standard package output" deferrals
explicitly called out in `docs/superpowers/specs/2026-10-31-excel-io-design.md`'s
Out of Scope section.

### Why this scope

- `app/service.py::run_pricing()` and
  `src/pyre/io_excel/results_io.py::write_experience_rating_results()`
  independently re-derive the same `by_layer_year`/`exposures_by_year`
  aggregation from `ExperienceModelData`. They have already **drifted**:
  `run_pricing()` computes a `loss_ratio` column that the Excel writer
  omits entirely. This is a real, currently-shipping gap between what the
  Panel UI shows and what a user can export — not just style duplication.
- The Panel app (`app/pages/results.py`) has no export/download affordance
  at all today — results can only be read off the screen.
- `src/pyre/io_excel/_workbook.py::write_table` only accepts a filesystem
  path, so nothing in `io_excel` can serve bytes to a browser download
  without writing a temp file first.

### Dependency approach

No new dependencies. `src/pyre` stays dependency-free (`dependencies = []`
in `pyproject.toml`); the new shared aggregation function lives in core and
returns plain `list[dict]` (no `pandas`), so it's usable by both the
pandas-free `excel` extra and the pandas-using `panel` extra without either
one depending on the other.

---

## Components

### 1. New core function: shared result aggregation

`src/pyre/models/Experience/experience_preparer.py` gains two module-level
functions (alongside the existing `ExperienceModelData` class):

```python
def summarize_by_layer_year(model_data: ExperienceModelData) -> list[dict]:
    """One dict per (layer_id, modelling_year).

    Keys: layer_id, layer_name, modelling_year, ceded_paid, ceded_incurred,
    claim_count, earned_premium, loss_ratio.
    loss_ratio = ceded_incurred / earned_premium, or None if earned_premium
    is 0 (avoids ZeroDivisionError -- matches run_pricing's existing
    behavior today).
    """

def summarize_exposures_by_year(model_data: ExperienceModelData) -> list[dict]:
    """One dict per modelling_year. Keys: modelling_year, written, earned."""
```

Both are extracted verbatim (same source data: `aggregate_subject_contract_claims`,
`aggregate_exposures`, `ri_contract.layers`) from `run_pricing()`'s current
body — no behavior change to the numbers it already produces, just a new
home plus reuse.

### 2. `app/service.py::run_pricing()` — rewritten to call the shared functions

```python
def run_pricing(claims: Claims, exposures: Exposures, ri_contract: RIContract) -> PricingResults:
    model_data = ExperienceModelData(claims=claims, exposures=exposures, ri_contract=ri_contract)
    by_layer_year = pd.DataFrame(summarize_by_layer_year(model_data)).sort_values(
        ["layer_id", "modelling_year"], ignore_index=True
    )
    exposures_by_year = pd.DataFrame(summarize_exposures_by_year(model_data))
    return PricingResults(by_layer_year=by_layer_year, exposures_by_year=exposures_by_year)
```

Deletes the ~25 lines of duplicate aggregation. Output shape (column names,
values, sort order) is unchanged from today — existing
`tests/test_app_service.py` assertions keep passing without modification.

### 3. `src/pyre/io_excel/_workbook.py::write_table` — accept a buffer target

```python
def write_table(
    headers: list[str],
    rows: Sequence[Sequence[Any]],
    path: str | Path | BinaryIO,
    sheet_name: str = "Sheet1",
) -> None:
```

Behavior change: if `path` is a `str`/`Path`, behavior is unchanged
(load-and-merge-if-exists, as today). If `path` is anything else (duck-typed
as a writable binary stream — `hasattr(path, "write")`), skip the
"does it exist / load existing workbook" branch entirely (a fresh in-memory
buffer has nothing to merge into) and always build a new `Workbook`, then
call `workbook.save(path)` — `openpyxl.Workbook.save()` already accepts a
file-like object natively, so no new serialization logic is needed.

### 4. `src/pyre/io_excel/results_io.py::write_experience_rating_results` — call the shared functions, widen `path` type

```python
BY_LAYER_YEAR_COLUMNS = [
    "layer_id", "layer_name", "modelling_year", "ceded_paid",
    "ceded_incurred", "claim_count", "earned_premium", "loss_ratio",
]

def write_experience_rating_results(model_data: "ExperienceModelData", path: str | Path | BinaryIO) -> None:
    by_layer_year_rows = summarize_by_layer_year(model_data)
    write_table(
        headers=BY_LAYER_YEAR_COLUMNS,
        rows=[[r[col] for col in BY_LAYER_YEAR_COLUMNS] for r in by_layer_year_rows],
        path=path,
        sheet_name="ByLayerYear",
    )
    exposures_rows = summarize_exposures_by_year(model_data)
    write_table(
        headers=["modelling_year", "written", "earned"],
        rows=[[r["modelling_year"], r["written"], r["earned"]] for r in exposures_rows],
        path=path,
        sheet_name="ExposuresByYear",
    )
```

Net effect: the `"ByLayerYear"` sheet gains a `loss_ratio` column it never
had before (the bug-fix half of this spec), and the two aggregation
implementations that used to be able to drift can no longer drift, because
there is only one.

`write_exposure_rating_results` and `write_triangle` are **not** changed —
neither currently has a Panel-app caller needing buffer support, and
widening `write_table`'s signature already covers them if a future caller
needs it (they all route through the same primitive).

### 5. `app/pages/results.py` — "Export to Excel" button

```python
export_button = pn.widgets.FileDownload(
    label="Export to Excel",
    filename="pricing_results.xlsx",
    callback=_export_results,
    button_type="default",
    visible=False,
)

def _export_results() -> io.BytesIO:
    model_data = ExperienceModelData(
        claims=state.claims, exposures=state.exposures, ri_contract=state.build_contract()
    )
    buffer = io.BytesIO()
    write_experience_rating_results(model_data, buffer)
    buffer.seek(0)
    return buffer
```

`export_button.visible` is set `True` at the end of `_on_run`'s success
path (mirroring how `status`/`results_table`/`exposures_table` already
update there), and reset to `False` if a later run fails — so the button is
only ever shown for a result that's actually current, matching the existing
`status` alert's own lifecycle. Rebuilding `ExperienceModelData` from
`state.claims`/`state.exposures`/`state.build_contract()` (already in scope
inside `_on_run`, and all three are plain `WorkbenchState` fields) costs one
cheap in-memory aggregation pass — no need to add a fourth field to
`WorkbenchState` to cache it.

`app/pages/results.py` moves from `import pandas as pd` + ad hoc dict
building to importing `write_experience_rating_results` from
`pyre.io_excel` — meaning the Panel app's `panel` extra now has a hard
dependency on the `excel` extra being installed too for this one button to
work. That's an existing-pattern question, addressed in Error Handling
below rather than by adding `excel` to the `panel` extra's dependency list
(keeping the two extras independently installable, per the existing-code
convention documented in `2026-10-31-excel-io-design.md`).

---

## Data Flow

```
claims + exposures + contract
  -> ExperienceModelData
    -> summarize_by_layer_year() / summarize_exposures_by_year()   (core, pandas-free)
      -> run_pricing(): wrap as pd.DataFrame for Tabulator display
      -> write_experience_rating_results(): wrap as rows for write_table (path or BytesIO)
```

---

## Error Handling

- If `openpyxl` is not installed and the user clicks "Export to Excel," the
  `from pyre.io_excel import write_experience_rating_results` import at the
  top of `app/pages/results.py` raises `ModuleNotFoundError` at app startup,
  not at click time — i.e. the whole Panel app fails to start rather than
  failing confusingly mid-session. This matches how a missing `panel`/
  `pandas` install already behaves for `app/` today (fails fast at import),
  so no new error-handling code is added; `README.md`'s install instructions
  already list `pip install -e ".[panel]"` and `pip install -e ".[excel]"` as
  separate steps, and this spec adds a sentence there (and to
  `CLAUDE.md`'s Commands section) noting both extras are needed to run the
  full Panel app including export.
- No new exception types. `write_experience_rating_results` raises nothing
  new; `ExperienceModelData` construction inside `_export_results` can raise
  whatever it already can (e.g. a `KeyError` from an out-of-range trend
  year, per the known risk documented in `CLAUDE.md`) — this is the exact
  same construction `_on_run` already performed successfully just before
  the button became visible, so in practice it cannot fail at export time
  without having already failed at run time first.

---

## Testing

1. `tests/test_experience_preparer.py` (existing file) — add tests for
   `summarize_by_layer_year`/`summarize_exposures_by_year` using the repo's
   existing `ExperienceModelData` test fixture pattern; assert exact dict
   contents including `loss_ratio`, and the `earned_premium == 0 ->
   loss_ratio is None` edge case.
2. `tests/test_app_service.py::TestRunPricing` — existing tests unchanged
   (same output values/shape); add one assertion that `by_layer_year` now
   also has a `loss_ratio` column (it already did, via the old inline code —
   this pins that the refactor didn't drop it).
3. `tests/test_io_excel.py` — extend
   `TestWriteExperienceRatingResults` (or equivalent) to assert the
   `"ByLayerYear"` sheet now has a `loss_ratio` column with correct values.
4. `tests/test_io_excel.py` — new test: `write_table` writes to an
   `io.BytesIO()`, the buffer is non-empty, and `openpyxl.load_workbook`
   can read it back with the expected header + rows (proves buffer mode
   produces a valid, readable workbook, not just "doesn't crash").
5. Manual Playwright check (same technique used for the dark-mode work):
   run the Panel app's demo-data walkthrough end to end, click "Export to
   Excel" after a successful pricing run, confirm a download fires with a
   non-empty `.xlsx` file, and confirm the button is not visible before any
   run and disappears again if a subsequent run fails (e.g. by temporarily
   breaking `state.claims` between runs in the test script).

---

## Out of Scope (explicitly deferred to later sub-projects)

- Database backend.
- xlwings live two-way Excel integration.
- CSV, PDF, or any other export format (Excel only, per this round's scope
  decision).
- Exporting anything beyond the two tables already shown on the results
  page (e.g. the input claims/exposures triangles, contract configuration) —
  nothing else is currently displayed in the Panel app for a user to expect
  an export of.
- Adding `excel` as a hard dependency of the `panel` extra, or vice versa —
  both extras stay independently installable; a user who installs only
  `panel` gets a Panel app that fails fast at import if they click into
  code requiring `io_excel` (documented, not silently handled).
