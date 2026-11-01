# pyRE Standardized Report Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deduplicate the `by_layer_year`/`exposures_by_year` result aggregation (currently re-derived independently, and already drifted, in `app/service.py::run_pricing()` and `io_excel/results_io.py::write_experience_rating_results()`), give the Excel writer in-memory buffer support, and add a working "Export to Excel" button to the Panel app's results page.

**Architecture:** One new pair of pandas-free functions in `src/pyre/models/Experience/experience_preparer.py` becomes the single source of truth for result rows. Both `run_pricing()` (wraps rows as `pandas.DataFrame`s for the UI) and `write_experience_rating_results()` (wraps rows for `openpyxl`) call it. `write_table` gains the ability to write into an `io.BytesIO()` instead of only a disk path, so the Panel button never touches the filesystem.

**Tech Stack:** Python 3.10+, `openpyxl` (`excel` extra), `pandas`/`panel` (`panel` extra), `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-01-report-export-design.md`

## Global Constraints

- `src/pyre` stays dependency-free (`dependencies = []` in `pyproject.toml`) — the new `summarize_*` functions must not import `pandas` or `openpyxl`.
- Excel is the only export format this round — no CSV/PDF.
- `excel` and `panel` stay independently installable extras — neither becomes a hard dependency of the other.
- No new custom exception types; `write_experience_rating_results` and `summarize_*` raise nothing beyond what `ExperienceModelData` construction and `openpyxl` already can.
- `write_exposure_rating_results` and `write_triangle` keep their current behavior — only `write_table`'s signature widens (used by all of `io_excel`'s writers), and only `write_experience_rating_results` gains the `loss_ratio` column.

## Review Focus

- A layer/year combination with zero claims (an empty `Claims([])` or a layer that matches nothing) must still export a valid, openable workbook with header-only sheets, not raise — pinned in Task 3's new test.
- The Panel export button must hide again after a failed re-run that follows an earlier successful run — a stale result must never stay downloadable — pinned in Task 5's manual verification script.
- A buffer written by `write_table` must be read back from byte 0 by its consumer (not from wherever the write left the stream position) — pinned in Task 2's new test, which explicitly checks this rather than assuming it.
- A contract/year with exactly zero earned premium must produce `loss_ratio = None`, never `ZeroDivisionError` or a silently-wrong `0.0`/`inf` — pinned in Task 1's new test.
- `openpyxl` missing while `panel` is installed: the Panel app must fail clearly at startup (import time) rather than confusingly when the user clicks Export. Not independently pinned by an automated test (faking a missing installed module reliably inside this suite isn't practical) — instead documented as accepted, expected behavior in Task 5's README/CLAUDE.md note.

---

### Task 1: Shared result-aggregation functions in core

**Files:**
- Modify: `src/pyre/models/Experience/experience_preparer.py` (add two module-level functions after the `ExperienceModelData` class, which ends at line 293)
- Test: `tests/test_experience_preparer.py` (new file)

**Interfaces:**
- Consumes: `ExperienceModelData` (same file), specifically its `.aggregate_subject_contract_claims`, `.aggregate_exposures`, and `.ri_contract.layers` (all already defined, unchanged).
- Produces: `summarize_by_layer_year(model_data: ExperienceModelData) -> List[Dict[str, Any]]` and `summarize_exposures_by_year(model_data: ExperienceModelData) -> List[Dict[str, Any]]`, both in `src/pyre/models/Experience/experience_preparer.py`. Task 3 and Task 4 import both by name from this module.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_experience_preparer.py`:

```python
import unittest
from datetime import date

from pyre import (
    Claim,
    ClaimDevelopmentHistory,
    Claims,
    ClaimsMetaData,
    Exposure,
    ExposureMetaData,
    Exposures,
    ExposureValues,
    RIContract,
    RIContractMetadata,
    RILayer,
)
from pyre.models.Experience.experience_preparer import (
    ExperienceModelData,
    summarize_by_layer_year,
    summarize_exposures_by_year,
)
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType


def _build_model_data(claims, exposures, layers):
    metadata = RIContractMetadata(
        contract_id="C-0001",
        contract_description="Test",
        cedent_name="Acme Re",
        trigger_basis=ClaimTriggerBasis.LOD,
        indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0,
        inception_date=date(2022, 1, 1),
        expiration_date=date(2022, 12, 31),
        fx_rates={"USD": 1.0},
    )
    contract = RIContract(contract_meta_data=metadata, layers=layers)
    return ExperienceModelData(claims=claims, exposures=exposures, ri_contract=contract)


def _xol_layer():
    return RILayer(
        layer_id=1,
        layer_name="XOL Layer",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=100_000.0,
        occurrence_limit=200_000.0,
        aggregate_attachment=0.0,
        aggregate_limit=0.0,
        subject_lines_of_business=[],
        subject_lob_exposure_amounts=[],
        full_subject_premium=0.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=0,
        reinstatement_cost={},
    )


def _claim_2022():
    return Claim(
        ClaimsMetaData(
            claim_id="CLM001",
            currency="USD",
            contract_limit=2_000_000.0,
            loss_date=date(2022, 3, 1),
        ),
        ClaimDevelopmentHistory(
            development_months=[12, 24],
            cumulative_dev_paid=[50000.0, 90000.0],
            cumulative_dev_incurred=[120000.0, 250000.0],
        ),
    )


def _exposure_2022():
    return Exposure(
        ExposureMetaData(
            exposure_id="EXP2022",
            exposure_name="2022 Premium",
            exposure_period_start=date(2022, 1, 1),
            exposure_period_end=date(2022, 12, 31),
            currency="USD",
        ),
        ExposureValues(exposure_value=1_000_000.0, attachment_point=0.0, limit=1_000_000.0),
    )


class TestSummarizeByLayerYear(unittest.TestCase):
    def test_returns_one_row_per_layer_and_year_with_loss_ratio(self):
        model_data = _build_model_data(
            Claims([_claim_2022()]), Exposures([_exposure_2022()]), [_xol_layer()]
        )

        rows = summarize_by_layer_year(model_data)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["layer_id"], 1)
        self.assertEqual(row["layer_name"], "XOL Layer")
        self.assertEqual(row["modelling_year"], 2022)
        self.assertEqual(row["ceded_paid"], 0.0)
        self.assertEqual(row["ceded_incurred"], 150000.0)
        self.assertEqual(row["claim_count"], 1)
        self.assertEqual(row["earned_premium"], 1_000_000.0)
        self.assertAlmostEqual(row["loss_ratio"], 0.15)

    def test_loss_ratio_is_none_when_earned_premium_is_zero(self):
        model_data = _build_model_data(Claims([_claim_2022()]), Exposures([]), [_xol_layer()])

        rows = summarize_by_layer_year(model_data)

        self.assertEqual(rows[0]["earned_premium"], 0.0)
        self.assertIsNone(rows[0]["loss_ratio"])

    def test_no_claims_returns_empty_list_not_an_error(self):
        model_data = _build_model_data(Claims([]), Exposures([_exposure_2022()]), [_xol_layer()])

        rows = summarize_by_layer_year(model_data)

        self.assertEqual(rows, [])


class TestSummarizeExposuresByYear(unittest.TestCase):
    def test_returns_one_row_per_year(self):
        model_data = _build_model_data(Claims([]), Exposures([_exposure_2022()]), [_xol_layer()])

        rows = summarize_exposures_by_year(model_data)

        self.assertEqual(
            rows, [{"modelling_year": 2022, "written": 1_000_000.0, "earned": 1_000_000.0}]
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_experience_preparer.py -v`
Expected: `ImportError: cannot import name 'summarize_by_layer_year' from 'pyre.models.Experience.experience_preparer'` (or `ModuleNotFoundError` depending on how far collection gets) — the functions don't exist yet.

- [ ] **Step 3: Write minimal implementation**

Append to `src/pyre/models/Experience/experience_preparer.py` (after the `ExperienceModelData` class, i.e. after its final `aggregate_exposures` property at line 293):

```python
def summarize_by_layer_year(model_data: ExperienceModelData) -> List[Dict[str, Any]]:
    """One row per (layer_id, modelling_year) from model_data's aggregated claims/exposures.

    Keys: layer_id, layer_name, modelling_year, ceded_paid, ceded_incurred,
    claim_count, earned_premium, loss_ratio (None when earned_premium is 0,
    to avoid ZeroDivisionError and avoid a silently-wrong 0.0/inf value).
    """
    layer_names = {layer.layer_id: layer.layer_name for layer in model_data.ri_contract.layers}
    aggregate_claims = model_data.aggregate_subject_contract_claims
    aggregate_exposures = model_data.aggregate_exposures

    rows: List[Dict[str, Any]] = []
    for layer_id, year_agg in aggregate_claims.items():
        for modelling_year, values in year_agg.items():
            earned_premium = aggregate_exposures.get(modelling_year, {}).get("earned", 0.0)
            ceded_incurred = values["latest_incurred"]
            loss_ratio = (ceded_incurred / earned_premium) if earned_premium else None
            rows.append(
                {
                    "layer_id": layer_id,
                    "layer_name": layer_names.get(layer_id, str(layer_id)),
                    "modelling_year": modelling_year,
                    "ceded_paid": values["latest_paid"],
                    "ceded_incurred": ceded_incurred,
                    "claim_count": values["total_count"],
                    "earned_premium": earned_premium,
                    "loss_ratio": loss_ratio,
                }
            )
    return rows


def summarize_exposures_by_year(model_data: ExperienceModelData) -> List[Dict[str, Any]]:
    """One row per modelling_year. Keys: modelling_year, written, earned."""
    aggregate_exposures = model_data.aggregate_exposures
    return [
        {"modelling_year": year, "written": values["written"], "earned": values["earned"]}
        for year, values in sorted(aggregate_exposures.items())
    ]
```

The file's existing top import line `from typing import Dict, List, Any, Optional` already covers `Dict`/`List`/`Any` — no new imports needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_experience_preparer.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/models/Experience/experience_preparer.py tests/test_experience_preparer.py
git commit -m "feat: add shared by-layer-year/exposures-by-year result summarizers"
```

---

### Task 2: In-memory buffer support for `write_table`

**Files:**
- Modify: `src/pyre/io_excel/_workbook.py` (whole file, currently 44 lines)
- Test: `tests/test_io_excel.py` (add a method to the existing `TestWriteTable` class, around line 32-79)

**Interfaces:**
- Consumes: nothing new (pure `openpyxl` primitive).
- Produces: `write_table(headers: list[str], rows: Sequence[Sequence[Any]], path: str | Path | BinaryIO, sheet_name: str = "Sheet1") -> None` — same name, widened `path` type. Task 3 passes a `BinaryIO` through unchanged.

- [ ] **Step 1: Write the failing test**

Add to the `TestWriteTable` class in `tests/test_io_excel.py` (after `test_second_sheet_is_appended_not_replacing_the_first`, line 79):

```python
    def test_writes_to_an_in_memory_buffer(self):
        import io

        from pyre.io_excel._workbook import write_table

        buffer = io.BytesIO()
        write_table(headers=["a", "b"], rows=[[1, 2]], path=buffer, sheet_name="Sheet1")

        buffer.seek(0)
        wb = openpyxl.load_workbook(buffer)
        values = [list(row) for row in wb["Sheet1"].iter_rows(values_only=True)]
        self.assertEqual(values, [["a", "b"], [1, 2]])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_io_excel.py::TestWriteTable::test_writes_to_an_in_memory_buffer -v`
Expected: FAIL — `AttributeError: 'BytesIO' object has no attribute 'exists'` (current code unconditionally does `path = Path(path)` then `path.exists()`).

- [ ] **Step 3: Write minimal implementation**

Replace `src/pyre/io_excel/_workbook.py`'s `write_table` body:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO, Sequence

from openpyxl import Workbook, load_workbook


def write_table(
    headers: list[str],
    rows: Sequence[Sequence[Any]],
    path: str | Path | BinaryIO,
    sheet_name: str = "Sheet1",
) -> None:
    """Write one header row + data rows to a sheet in an .xlsx workbook.

    `path` may be a filesystem path (str/Path) or any writable binary stream
    (e.g. io.BytesIO) -- used by the Panel app to serve a download without
    touching disk. For a filesystem path that already exists, the named
    sheet is replaced (re-running a report overwrites cleanly) while any
    other existing sheets are preserved. A stream target has nothing to
    merge into, so it always gets a fresh workbook.

    Warning: the filesystem-path case loads and re-saves the whole workbook
    via openpyxl, which does not round-trip every part of an .xlsx file --
    charts, images, and pivot tables already at `path` will be lost. Point
    these functions at dedicated output files, not at a workbook that
    already has charts/pivots you want to keep.
    """
    is_filesystem_path = isinstance(path, (str, Path))
    target = Path(path) if is_filesystem_path else path

    if is_filesystem_path and target.exists():
        workbook = load_workbook(target)
        if sheet_name in workbook.sheetnames:
            del workbook[sheet_name]
    else:
        workbook = Workbook()
        workbook.remove(workbook.active)

    worksheet = workbook.create_sheet(sheet_name)
    worksheet.append(headers)
    for row in rows:
        worksheet.append(list(row))

    workbook.save(target)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_io_excel.py::TestWriteTable -v`
Expected: `5 passed` (the 4 existing `TestWriteTable` tests plus the new one).

- [ ] **Step 5: Commit**

```bash
git add src/pyre/io_excel/_workbook.py tests/test_io_excel.py
git commit -m "feat: support writing an in-memory buffer target in write_table"
```

---

### Task 3: `write_experience_rating_results` uses the shared summarizers, gains `loss_ratio`

**Files:**
- Modify: `src/pyre/io_excel/results_io.py` (whole file, currently 82 lines)
- Test: `tests/test_io_excel.py` (`TestWriteExperienceRatingResults` class, lines 351-452)

**Interfaces:**
- Consumes: Task 1's `summarize_by_layer_year`/`summarize_exposures_by_year`; Task 2's widened `write_table`.
- Produces: `write_experience_rating_results(model_data: ExperienceModelData, path: str | Path | BinaryIO) -> None` — same name, now includes `loss_ratio` in the `"ByLayerYear"` sheet and accepts a buffer. `write_exposure_rating_results` is untouched (not part of this task).

- [ ] **Step 1: Write the failing test**

In `tests/test_io_excel.py`, replace the body of `TestWriteExperienceRatingResults.test_writes_both_sheets` (lines 419-441):

```python
    def test_writes_both_sheets(self):
        from pyre.io_excel.results_io import write_experience_rating_results

        write_experience_rating_results(self.model_data, self.path)

        wb = openpyxl.load_workbook(self.path)
        self.assertEqual(set(wb.sheetnames), {"ByLayerYear", "ExposuresByYear"})

        by_layer_year = [list(row) for row in wb["ByLayerYear"].iter_rows(values_only=True)]
        self.assertEqual(
            by_layer_year[0],
            [
                "layer_id", "layer_name", "modelling_year", "ceded_paid",
                "ceded_incurred", "claim_count", "earned_premium", "loss_ratio",
            ],
        )
        self.assertEqual(by_layer_year[1][:7], [1, "XOL Layer", 2022, 0.0, 150000.0, 1, 1000000.0])
        self.assertAlmostEqual(by_layer_year[1][7], 0.15)

        exposures_by_year = [list(row) for row in wb["ExposuresByYear"].iter_rows(values_only=True)]
        self.assertEqual(exposures_by_year[0], ["modelling_year", "written", "earned"])
        self.assertEqual(exposures_by_year[1][0], 2022)

    def test_no_claims_still_writes_a_valid_header_only_sheet(self):
        from pyre.claims.claims import Claims
        from pyre.io_excel.results_io import write_experience_rating_results

        self.model_data.claims = Claims([])

        write_experience_rating_results(self.model_data, self.path)  # must not raise

        wb = openpyxl.load_workbook(self.path)
        by_layer_year = [list(row) for row in wb["ByLayerYear"].iter_rows(values_only=True)]
        self.assertEqual(
            by_layer_year,
            [[
                "layer_id", "layer_name", "modelling_year", "ceded_paid",
                "ceded_incurred", "claim_count", "earned_premium", "loss_ratio",
            ]],
        )
```

(`test_rerunning_overwrites_rather_than_duplicating_rows`, lines 443-452, is unchanged — it doesn't assert specific column contents.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_io_excel.py::TestWriteExperienceRatingResults -v`
Expected: `test_writes_both_sheets` FAILS on the header assertion (current code's header list has 7 entries, no `"loss_ratio"`); `test_no_claims_still_writes_a_valid_header_only_sheet` is new and also fails the same way.

- [ ] **Step 3: Write minimal implementation**

Replace `src/pyre/io_excel/results_io.py` in full:

```python
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from ..models.Experience.experience_preparer import (
    summarize_by_layer_year,
    summarize_exposures_by_year,
)
from ._workbook import write_table

if TYPE_CHECKING:
    from ..models.Experience.experience_preparer import ExperienceModelData
    from ..models.Exposure.exposure_rating_cost import ExposureModel

BY_LAYER_YEAR_COLUMNS = [
    "layer_id", "layer_name", "modelling_year", "ceded_paid",
    "ceded_incurred", "claim_count", "earned_premium", "loss_ratio",
]


def write_experience_rating_results(
    model_data: "ExperienceModelData", path: str | Path | BinaryIO
) -> None:
    """Write an ExperienceModelData's aggregated results to two sheets of one .xlsx workbook.

    "ByLayerYear": one row per (layer_id, modelling_year), including loss_ratio.
    "ExposuresByYear": one row per modelling_year.
    """
    by_layer_year_rows = summarize_by_layer_year(model_data)
    write_table(
        headers=BY_LAYER_YEAR_COLUMNS,
        rows=[[row[col] for col in BY_LAYER_YEAR_COLUMNS] for row in by_layer_year_rows],
        path=path,
        sheet_name="ByLayerYear",
    )

    exposures_rows = summarize_exposures_by_year(model_data)
    write_table(
        headers=["modelling_year", "written", "earned"],
        rows=[[row["modelling_year"], row["written"], row["earned"]] for row in exposures_rows],
        path=path,
        sheet_name="ExposuresByYear",
    )


def write_exposure_rating_results(exposure_model: "ExposureModel", path: str | Path | BinaryIO) -> None:
    """Write ExposureModel.calculate_all_shares() to one 'ExposureShares' sheet."""
    shares = exposure_model.calculate_all_shares()

    rows = [
        [exposure_id, layer_id, share]
        for exposure_id, layer_shares in shares.items()
        for layer_id, share in layer_shares.items()
    ]

    write_table(
        headers=["exposure_id", "layer_id", "share"],
        rows=rows,
        path=path,
        sheet_name="ExposureShares",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_io_excel.py -v`
Expected: all tests in the file pass (confirms `write_exposure_rating_results`, `write_triangle`, `read_claims`, `read_exposures` are all unaffected by this change).

- [ ] **Step 5: Commit**

```bash
git add src/pyre/io_excel/results_io.py tests/test_io_excel.py
git commit -m "fix: write_experience_rating_results now includes loss_ratio, matching the Panel app"
```

---

### Task 4: `run_pricing()` calls the shared summarizers (dedupe)

**Files:**
- Modify: `app/service.py:218-276` (the `run_pricing` function body)
- Test: `tests/test_app_service.py` (no new test — existing `TestRunPricing` tests are the regression safety net; this is a pure refactor, not a behavior change)

**Interfaces:**
- Consumes: Task 1's `summarize_by_layer_year`/`summarize_exposures_by_year`.
- Produces: `run_pricing(claims, exposures, ri_contract) -> PricingResults` — same signature, same output values/shape as before.

This task has no new test because it changes no observable behavior — `tests/test_app_service.py::TestRunPricing` (lines 97-154) already pins the exact output values (`ceded_paid`, `ceded_incurred`, `loss_ratio` per year). Per TDD's REFACTOR phase: "After green only... Keep tests green. Don't add behavior." The existing suite is the safety net; the steps below are refactor-and-reverify, not red-green.

- [ ] **Step 1: Run the existing tests to confirm they currently pass (pre-refactor baseline)**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_app_service.py::TestRunPricing -v`
Expected: `2 passed` (both `test_run_pricing_matches_expected_ceded_loss` and `test_run_pricing_with_surplus_share_layer_raises`).

- [ ] **Step 2: Replace `run_pricing`'s body**

In `app/service.py`, add to the import block from `pyre` (after line 21's `ExperienceModelData,`):

```python
from pyre.models.Experience.experience_preparer import (
    summarize_by_layer_year,
    summarize_exposures_by_year,
)
```

Replace the function body at lines 218-276:

```python
def run_pricing(claims: Claims, exposures: Exposures, ri_contract: RIContract) -> PricingResults:
    """Run pyre's experience-rating calculation and shape the output as DataFrames.

    Raises:
        NotImplementedError: if any layer on the contract is SURPLUS_SHARE
            (pyre does not yet support pricing that layer type). Callers
            (the UI) should prevent selecting that layer type rather than
            relying on catching this.
    """
    model_data = ExperienceModelData(claims=claims, exposures=exposures, ri_contract=ri_contract)

    by_layer_year = pd.DataFrame(
        summarize_by_layer_year(model_data),
        columns=[
            "layer_id",
            "layer_name",
            "modelling_year",
            "ceded_paid",
            "ceded_incurred",
            "claim_count",
            "earned_premium",
            "loss_ratio",
        ],
    ).sort_values(["layer_id", "modelling_year"], ignore_index=True)

    exposures_by_year = pd.DataFrame(
        summarize_exposures_by_year(model_data),
        columns=["modelling_year", "written", "earned"],
    )

    return PricingResults(by_layer_year=by_layer_year, exposures_by_year=exposures_by_year)
```

(Passing `columns=[...]` to `pd.DataFrame` on a possibly-empty list of dicts is what keeps the `SURPLUS_SHARE` error path's "no rows" case — exercised by `test_run_pricing_with_surplus_share_layer_raises`, which actually never reaches this code since it raises earlier via `loss_to_layer_fn` — and any other zero-row case producing a DataFrame with the right columns instead of a columnless empty one, matching the old code's behavior.)

- [ ] **Step 3: Run tests to verify they still pass**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_app_service.py -v`
Expected: all tests in the file pass, including both `TestRunPricing` tests with unchanged assertions (lines 125-131 and 153-154) — proves the refactor produced identical output.

- [ ] **Step 4: Run the full suite to confirm no wider regression**

Run: `"/c/Program Files/Python312/python.exe" -m pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: `0 failed` (same baseline as before this plan, plus Task 1/2/3's new tests now passing too).

- [ ] **Step 5: Commit**

```bash
git add app/service.py
git commit -m "refactor: run_pricing uses the shared result summarizers, removing duplicate aggregation"
```

---

### Task 5: "Export to Excel" button on the Panel app's results page

**Files:**
- Modify: `app/pages/results.py` (whole file, currently 81 lines)
- Modify: `README.md` (one sentence, near the install instructions)
- Modify: `CLAUDE.md` (one sentence, in the Panel workbench table's `app/pages/` row or Commands section)
- Test: manual Playwright script (no pytest — `app/pages/*.py` is UI code with no server-less unit test harness in this repo, per `CLAUDE.md`'s own module map: only `app/service.py` is unit-tested without a running server)

**Interfaces:**
- Consumes: Task 3's `write_experience_rating_results` (via `from pyre.io_excel import write_experience_rating_results`), `pyre.ExperienceModelData`, and `app.state.WorkbenchState`'s existing `claims`/`exposures`/`build_contract()`.
- Produces: no new importable symbols — this is the final, UI-facing task.

- [ ] **Step 1: Add the export button and its callback**

Replace `app/pages/results.py` in full:

```python
"""Pricing results page for the treaty pricing workbench."""

from __future__ import annotations

import io

import pandas as pd
import panel as pn
from bokeh.models.widgets.tables import NumberFormatter

from app.service import run_pricing
from app.state import WorkbenchState
from pyre import ExperienceModelData
from pyre.io_excel import write_experience_rating_results

AMOUNT = NumberFormatter(format="0,0", text_align="right")
TITLES = {
    "layer_id": "Layer ID",
    "layer_name": "Layer",
    "modelling_year": "Modelling year",
    "ceded_paid": "Ceded paid",
    "ceded_incurred": "Ceded incurred",
    "claim_count": "Claims",
    "earned_premium": "Earned premium",
    "loss_ratio": "Loss ratio",
    "written": "Written",
    "earned": "Earned",
}
FORMATTERS = {
    "modelling_year": NumberFormatter(format="0"),
    "ceded_paid": AMOUNT,
    "ceded_incurred": AMOUNT,
    "claim_count": NumberFormatter(format="0", text_align="right"),
    "earned_premium": AMOUNT,
    "loss_ratio": NumberFormatter(format="0.0%", text_align="right"),
    "written": AMOUNT,
    "earned": AMOUNT,
}


def build_results_page(state: WorkbenchState) -> pn.Column:
    status = pn.pane.Alert(
        "Load data and configure a contract, then run pricing.", alert_type="warning"
    )
    run_button = pn.widgets.Button(name="Run pricing", button_type="primary")
    results_table = pn.widgets.Tabulator(
        pd.DataFrame(), show_index=False, disabled=True, titles=TITLES, formatters=FORMATTERS
    )
    exposures_table = pn.widgets.Tabulator(
        pd.DataFrame(), show_index=False, disabled=True, titles=TITLES, formatters=FORMATTERS
    )

    def _export_results():
        model_data = ExperienceModelData(
            claims=state.claims, exposures=state.exposures, ri_contract=state.build_contract()
        )
        buffer = io.BytesIO()
        write_experience_rating_results(model_data, buffer)
        buffer.seek(0)
        return buffer

    export_button = pn.widgets.FileDownload(
        label="Export to Excel",
        filename="pricing_results.xlsx",
        callback=_export_results,
        button_type="default",
        visible=False,
    )

    def _on_run(_event):
        if not state.is_ready_to_price():
            status.object = (
                "Load claims + exposures and configure a contract with at least one layer first."
            )
            status.alert_type = "danger"
            export_button.visible = False
            return
        try:
            contract = state.build_contract()
            state.results = run_pricing(state.claims, state.exposures, contract)
            results_table.value = state.results.by_layer_year
            exposures_table.value = state.results.exposures_by_year
            status.object = "Pricing run complete. See the tables below."
            status.alert_type = "success"
            export_button.visible = True
        except NotImplementedError as exc:
            status.object = f"Unsupported layer configuration: {exc}"
            status.alert_type = "danger"
            export_button.visible = False
        except ValueError as exc:
            status.object = f"Could not run pricing: {exc}"
            status.alert_type = "danger"
            export_button.visible = False

    run_button.on_click(_on_run)

    return pn.Column(
        "## Pricing results",
        run_button,
        status,
        "### Ceded loss by layer and modelling year",
        results_table,
        "### Exposures by modelling year",
        exposures_table,
        export_button,
    )
```

- [ ] **Step 2: Add the extras-dependency note**

In `README.md`, find the install instructions (`pip install -e ".[panel]"` / `pip install -e ".[excel]"` lines) and add immediately after them:

```markdown
To use the "Export to Excel" button in the Panel workbench, install both extras: `pip install -e ".[panel,excel]"`.
```

In `CLAUDE.md`'s Commands section, update the line:

```
pip install -e ".[panel]"       # install with the Panel treaty pricing workbench's deps
```

to:

```
pip install -e ".[panel]"       # install with the Panel treaty pricing workbench's deps
pip install -e ".[panel,excel]" # same, plus the workbench's "Export to Excel" button
```

- [ ] **Step 3: Run the full test suite**

Run: `"/c/Program Files/Python312/python.exe" -m pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: `0 failed` — this task touches no pytest-covered code path (`app/pages/*.py` has no unit tests per the module map), so the count should match Task 4's final run plus no new failures.

- [ ] **Step 4: Manual Playwright verification**

Write a throwaway script (same pattern as prior sessions' Panel verification scripts, saved under the scratchpad directory, not committed) that:
1. Starts `panel serve app/main.py` (or reuses an already-running instance), navigates to it.
2. Confirms the "Export to Excel" button is **not visible** before any pricing run.
3. Clicks "Load demo data," configures a layer, saves the contract, runs pricing — confirms the button becomes **visible** and a click produces a non-empty `.xlsx` download (verify via Playwright's download event, then open it with `openpyxl.load_workbook` and assert the `"ByLayerYear"`/`"ExposuresByYear"` sheets exist with a `loss_ratio` column).
4. **Review Focus check:** forces a second, failing run (e.g. temporarily clear `state.claims` via the browser/devtools, or build a contract with a `SURPLUS_SHARE` layer and attempt to run pricing after the first successful run) and confirms the export button becomes **not visible** again — pins that a stale result can't be re-downloaded after a failure.
5. Confirms clicking Export twice in a row (two successful runs) both produce current, correct files — not a cached/stale first result.

Run it, read the output, and report pass/fail for each of the 5 checks above before marking this task complete — do not mark this task done on the basis of "the code looks right."

- [ ] **Step 5: Commit**

```bash
git add app/pages/results.py README.md CLAUDE.md
git commit -m "feat: add Export to Excel button to the Panel app's results page"
```

---

## Final Verification (after all 5 tasks)

1. `"/c/Program Files/Python312/python.exe" -m pytest -q --ignore=tests/test_exposure_curve_fitting.py` → expect `0 failed`, with the passed count up by 7 from this plan's new tests (4 in Task 1 + 1 in Task 2 + 1 in Task 3's new test + the rewritten `test_writes_both_sheets` still counting as 1 — net +6 new test functions, 1 existing test's assertions changed in place).
2. `ruff check src/pyre/ app/` and `ruff format --check src/pyre/ app/` clean.
3. `mypy src/pyre tests` clean (the new `summarize_*` functions' type hints must satisfy the existing non-strict config).
4. The Playwright script from Task 5 Step 4, all 5 checks passing.
5. Update `CLAUDE.md`'s "Known Test State" expected-count line to match the new total (currently `0 failed, 131 passed`; add this plan's net new test count).
