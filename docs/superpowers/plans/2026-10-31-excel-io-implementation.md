# pyRE Excel File I/O (Headless) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new optional `src/pyre/io_excel/` subpackage that reads `Claims`/`Exposures` from `.xlsx` workbooks and writes `Triangle`, experience-rating, and exposure-rating results to `.xlsx` — all via `openpyxl` directly, with zero impact on the dependency-free core `pyre` package.

**Architecture:** A new subpackage gated behind a new `excel` optional extra (`openpyxl>=3.1`, no pandas), never imported from `src/pyre/__init__.py`. All writers build on one low-level primitive (`write_table`) that appends/overwrites named sheets in a workbook. Reading is done with `openpyxl`'s cell API directly, re-implementing (not importing) the same long-format schema and validation already used by `app/service.py`'s CSV parsers. One pre-existing bug in `ExposureModel` (an indentation error that silently drops layers from exposure-rating results) must be fixed first, since the new `calculate_all_shares()` method depends on correct behavior from the method it wraps.

**Tech Stack:** Python 3.10+, `openpyxl>=3.1`, `unittest` (repo convention), `hatch`.

**Spec:** `docs/superpowers/specs/2026-10-31-excel-io-design.md`

## Global Constraints

- Python 3.10+ compatible. Every new module starts with `from __future__ import annotations` (matches `app/service.py`'s existing pattern) so `str | Path`-style annotations work without runtime evaluation on 3.10.
- `openpyxl` must never be imported transitively by a bare `import pyre` — only by `from pyre.io_excel import ...`. Do not add `io_excel` to `src/pyre/__init__.py`'s re-exports.
- `pyre.io_excel` must not import anything from `app/` (not an installable package) or `pandas`.
- ruff rules `E, F, I, N, W, B`, line-length 100, must pass on every new/modified file (`ruff check src/pyre/ tests/`).
- Relative imports inside `src/pyre/` (`from ..claims.claims import X`), per the project's existing convention (`CLAUDE.md`).
- Tests are `unittest.TestCase`-style, matching every existing test file in `tests/`.
- Error handling: plain `ValueError` with a descriptive message, matching `app/service.py`'s existing CSV-parser wording style — no new custom exception types.
- The one bug fix in this plan (`ExposureModel`'s indentation bug) is scoped to exactly the lines needed for `calculate_all_shares()` correctness — do not touch the file's other TODOs.

## Review Focus

- A workbook with an **optional column entirely absent** (not just an empty cell) — `claim_year_basis`, `contract_deductible`, `attachment_point`, etc. must default, never `KeyError`. (Tasks 2, 3)
- **`str` vs `pathlib.Path`** given as `path` — both must work identically for every `read_*`/`write_*` function. (Task 1, and re-exercised in Tasks 2–4, 6, 7)
- **Re-writing to the same path** (e.g. re-running a report) must overwrite that sheet cleanly, not duplicate it or raise. (Task 1, re-exercised in Task 6)
- **Trailing blank rows** in a sheet (common after manual edits in Excel) must not produce a bogus claim/exposure from an all-`None` row. (Tasks 2, 3)
- **Empty collections** — `calculate_all_shares()` on an `Exposures([])` or an `ExposureModel` whose contract has zero layers must return `{}`, not raise. (Task 5)

---

### Task 1: `excel` extra + `write_table` primitive

**Files:**
- Modify: `pyproject.toml`
- Create: `src/pyre/io_excel/__init__.py` (stub for now — re-exports added in Task 8)
- Create: `src/pyre/io_excel/_workbook.py`
- Create: `tests/test_io_excel.py`

**Interfaces:**
- Produces: `pyre.io_excel._workbook.write_table(headers: list[str], rows: list[Sequence[Any]], path: str | Path, sheet_name: str = "Sheet1") -> None` — every later writer task calls this.

- [ ] **Step 1: Add the `excel` optional dependency**

In `pyproject.toml`, add alongside the existing `[project.optional-dependencies]` block:

```toml
[project.optional-dependencies]
panel = [
  "panel>=1.4",
  "pandas>=2.0",
]
excel = [
  "openpyxl>=3.1",
]
```

And a matching hatch env, mirroring the existing `[tool.hatch.envs.panel]` block:

```toml
[tool.hatch.envs.excel]
dependencies = [
  "openpyxl>=3.1",
]
```

- [ ] **Step 2: Install the extra locally so you can run the new tests**

```bash
pip install -e ".[excel]"
```

- [ ] **Step 3: Write the failing test**

Create `tests/test_io_excel.py`:

```python
import tempfile
import unittest
from pathlib import Path

try:
    import openpyxl

    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestWriteTable(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "out.xlsx"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_writes_header_and_rows(self):
        from pyre.io_excel._workbook import write_table

        write_table(
            headers=["a", "b"],
            rows=[[1, 2], [3, 4]],
            path=self.path,
            sheet_name="Sheet1",
        )

        wb = openpyxl.load_workbook(self.path)
        ws = wb["Sheet1"]
        values = [list(row) for row in ws.iter_rows(values_only=True)]
        self.assertEqual(values, [["a", "b"], [1, 2], [3, 4]])

    def test_accepts_str_path_and_pathlib_path(self):
        from pyre.io_excel._workbook import write_table

        write_table(["a"], [[1]], str(self.path), sheet_name="S")
        write_table(["a"], [[1]], Path(self.path), sheet_name="S")  # must not raise

    def test_rewriting_same_sheet_overwrites_not_duplicates(self):
        from pyre.io_excel._workbook import write_table

        write_table(["a"], [[1], [2]], self.path, sheet_name="S")
        write_table(["a"], [[9]], self.path, sheet_name="S")  # re-run with different data

        wb = openpyxl.load_workbook(self.path)
        self.assertEqual(wb.sheetnames, ["S"])
        values = [list(row) for row in wb["S"].iter_rows(values_only=True)]
        self.assertEqual(values, [["a"], [9]])

    def test_second_sheet_is_appended_not_replacing_the_first(self):
        from pyre.io_excel._workbook import write_table

        write_table(["a"], [[1]], self.path, sheet_name="First")
        write_table(["b"], [[2]], self.path, sheet_name="Second")

        wb = openpyxl.load_workbook(self.path)
        self.assertEqual(set(wb.sheetnames), {"First", "Second"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run the test to verify it fails**

```bash
pytest tests/test_io_excel.py -v
```

Expected: `ModuleNotFoundError` / `ImportError` on `from pyre.io_excel._workbook import write_table` (module doesn't exist yet).

- [ ] **Step 5: Create the package and implement `write_table`**

Create `src/pyre/io_excel/__init__.py` (empty for now):

```python
"""Headless Excel file I/O for pyre -- requires the 'excel' optional extra (openpyxl).

Never imported by pyre/__init__.py: a bare `import pyre` must not require
openpyxl. Only `from pyre.io_excel import ...` does.
"""
```

Create `src/pyre/io_excel/_workbook.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from openpyxl import Workbook, load_workbook


def write_table(
    headers: list[str],
    rows: list[Sequence[Any]],
    path: str | Path,
    sheet_name: str = "Sheet1",
) -> None:
    """Write one header row + data rows to a sheet in an .xlsx workbook.

    If `path` already exists, the named sheet is replaced (re-running a
    report overwrites cleanly) while any other existing sheets in the
    workbook are preserved -- this is how write_experience_rating_results
    puts two sheets in one file via two calls to this function.
    """
    path = Path(path)

    if path.exists():
        workbook = load_workbook(path)
        if sheet_name in workbook.sheetnames:
            del workbook[sheet_name]
    else:
        workbook = Workbook()
        workbook.remove(workbook.active)

    worksheet = workbook.create_sheet(sheet_name)
    worksheet.append(headers)
    for row in rows:
        worksheet.append(list(row))

    workbook.save(path)
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
pytest tests/test_io_excel.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/pyre/io_excel/__init__.py src/pyre/io_excel/_workbook.py tests/test_io_excel.py
git commit -m "feat(io_excel): add excel optional extra and write_table primitive"
```

---

### Task 2: `read_claims`

**Files:**
- Create: `src/pyre/io_excel/claims_io.py`
- Modify: `tests/test_io_excel.py`

**Interfaces:**
- Consumes: nothing from Task 1 (standalone read path).
- Produces: `pyre.io_excel.claims_io.read_claims(path: str | Path, sheet_name: str = "Claims") -> Claims` — re-exported in Task 8.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_io_excel.py` (keep the `openpyxl`/`HAS_OPENPYXL` guard import at top; add these imports near the top of the file too):

```python
from datetime import date

from openpyxl import Workbook
```

```python
@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestReadClaims(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "claims.xlsx"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_claims_sheet(self, rows, headers=None, sheet_name="Claims", trailing_blank_row=False):
        headers = headers or [
            "claim_id", "currency", "contract_limit",
            "loss_date", "development_month", "cumulative_paid", "cumulative_incurred",
        ]
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name
        ws.append(headers)
        for row in rows:
            ws.append(row)
        if trailing_blank_row:
            ws.append([None] * len(headers))
        wb.save(self.path)

    def test_builds_claims_with_correct_dev_history(self):
        from pyre.io_excel.claims_io import read_claims

        self._write_claims_sheet(
            [
                ["CLM001", "USD", 2000000, date(2022, 3, 1), 12, 50000, 120000],
                ["CLM001", "USD", 2000000, date(2022, 3, 1), 24, 90000, 250000],
                ["CLM002", "USD", 2000000, date(2022, 7, 10), 12, 20000, 60000],
            ]
        )

        claims = read_claims(self.path)
        self.assertEqual(sorted(claims.modelling_years), [2022])

        by_id = {c.claims_meta_data.claim_id: c for c in claims.claims}
        self.assertEqual(
            by_id["CLM001"].capped_claim_development_history.cumulative_dev_paid,
            [50000.0, 90000.0],
        )
        self.assertEqual(
            by_id["CLM001"].capped_claim_development_history.development_months,
            [12, 24],
        )

    def test_accepts_iso_string_dates_as_well_as_native_excel_dates(self):
        from pyre.io_excel.claims_io import read_claims

        self._write_claims_sheet(
            [["CLM001", "USD", 2000000, "2022-03-01", 12, 50000, 120000]]
        )

        claims = read_claims(self.path)
        self.assertEqual(claims.claims[0].claims_meta_data.loss_date, date(2022, 3, 1))

    def test_rejects_missing_required_column(self):
        from pyre.io_excel.claims_io import read_claims

        self._write_claims_sheet(
            rows=[["CLM001", "USD", 12, 50000, 120000]],
            headers=["claim_id", "currency", "development_month", "cumulative_paid", "cumulative_incurred"],
        )

        with self.assertRaises(ValueError):
            read_claims(self.path)

    def test_rejects_missing_or_zero_contract_limit(self):
        from pyre.io_excel.claims_io import read_claims

        self._write_claims_sheet(
            [["CLM001", "USD", 0, date(2022, 3, 1), 12, 50000, 120000]]
        )

        with self.assertRaises(ValueError):
            read_claims(self.path)

    def test_ignores_trailing_blank_row(self):
        from pyre.io_excel.claims_io import read_claims

        self._write_claims_sheet(
            [["CLM001", "USD", 2000000, date(2022, 3, 1), 12, 50000, 120000]],
            trailing_blank_row=True,
        )

        claims = read_claims(self.path)
        self.assertEqual(len(claims), 1)

    def test_missing_optional_column_entirely_defaults_cleanly(self):
        from pyre.io_excel.claims_io import read_claims

        # No "claim_year_basis", "contract_deductible", "line_of_business" etc. columns at all
        self._write_claims_sheet(
            [["CLM001", "USD", 2000000, date(2022, 3, 1), 12, 50000, 120000]]
        )

        claims = read_claims(self.path)  # must not raise KeyError
        self.assertEqual(claims.claims[0].claims_meta_data.contract_deductible, 0.0)
        self.assertEqual(claims.claims[0].claims_meta_data.status, "Open")
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_io_excel.py::TestReadClaims -v
```

Expected: `ModuleNotFoundError` (module doesn't exist yet).

- [ ] **Step 3: Implement `read_claims`**

Create `src/pyre/io_excel/claims_io.py`:

```python
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from ..claims.claims import Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData
from ..enums import ClaimYearType

CLAIMS_REQUIRED_COLUMNS = [
    "claim_id",
    "currency",
    "contract_limit",
    "development_month",
    "cumulative_paid",
    "cumulative_incurred",
]


def _read_sheet(path: str | Path, sheet_name: str) -> tuple[list[str], list[tuple]]:
    workbook = load_workbook(path, data_only=True)
    if sheet_name not in workbook.sheetnames:
        raise ValueError(f"workbook '{path}' has no sheet named '{sheet_name}'")
    worksheet = workbook[sheet_name]
    rows_iter = worksheet.iter_rows(values_only=True)
    headers = [str(h) for h in next(rows_iter)]
    return headers, list(rows_iter)


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value).strip())


def _parse_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ("true", "1", "yes")


def read_claims(path: str | Path, sheet_name: str = "Claims") -> Claims:
    """Build a Claims collection from a long-format .xlsx sheet (one row per claim/dev-point).

    Raises:
        ValueError: if a required column is missing, or if any claim's
            contract_limit is missing/<= 0 (ClaimsMetaData.contract_limit
            defaults to 0.0, which silently caps every ceded amount to zero).
    """
    headers, rows = _read_sheet(path, sheet_name)

    missing = [c for c in CLAIMS_REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise ValueError(f"claims sheet '{sheet_name}' is missing required columns: {missing}")

    col = {name: idx for idx, name in enumerate(headers)}

    groups: dict[str, list[tuple]] = {}
    for row in rows:
        if row[col["claim_id"]] is None:
            continue
        groups.setdefault(str(row[col["claim_id"]]), []).append(row)

    claims: list[Claim] = []
    for claim_id, group_rows in groups.items():
        first = group_rows[0]

        contract_limit = first[col["contract_limit"]]
        if contract_limit is None or float(contract_limit) <= 0:
            raise ValueError(
                f"claim '{claim_id}': contract_limit must be set to a positive value "
                "-- ClaimsMetaData.contract_limit defaults to 0.0, which caps every "
                "ceded/gross amount to zero."
            )

        claim_year_basis_raw = first[col["claim_year_basis"]] if "claim_year_basis" in col else None
        claim_year_basis = (
            ClaimYearType[str(claim_year_basis_raw).strip()]
            if claim_year_basis_raw
            else ClaimYearType.ACCIDENT_YEAR
        )

        meta = ClaimsMetaData(
            claim_id=claim_id,
            currency=str(first[col["currency"]]),
            contract_limit=float(contract_limit),
            contract_deductible=(
                float(first[col["contract_deductible"]] or 0.0) if "contract_deductible" in col else 0.0
            ),
            claim_in_xs_of_deductible=(
                _parse_bool(first[col["claim_in_xs_of_deductible"]])
                if "claim_in_xs_of_deductible" in col
                else False
            ),
            claim_year_basis=claim_year_basis,
            loss_date=(
                _parse_date(first[col["loss_date"]])
                if "loss_date" in col and first[col["loss_date"]] is not None
                else date(1900, 1, 1)
            ),
            policy_inception_date=(
                _parse_date(first[col["policy_inception_date"]])
                if "policy_inception_date" in col and first[col["policy_inception_date"]] is not None
                else date(1900, 1, 1)
            ),
            report_date=(
                _parse_date(first[col["report_date"]])
                if "report_date" in col and first[col["report_date"]] is not None
                else date(1900, 1, 1)
            ),
            line_of_business=first[col["line_of_business"]] if "line_of_business" in col else None,
            status=(first[col["status"]] if "status" in col and first[col["status"]] else "Open"),
        )

        sorted_rows = sorted(group_rows, key=lambda r: r[col["development_month"]])
        dev_history = ClaimDevelopmentHistory(
            development_months=[int(r[col["development_month"]]) for r in sorted_rows],
            cumulative_dev_paid=[float(r[col["cumulative_paid"]]) for r in sorted_rows],
            cumulative_dev_incurred=[float(r[col["cumulative_incurred"]]) for r in sorted_rows],
        )

        claims.append(Claim(claims_meta_data=meta, claims_development_history=dev_history))

    return Claims(claims)
```

- [ ] **Step 4: Run to verify it passes**

```bash
pytest tests/test_io_excel.py::TestReadClaims -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyre/io_excel/claims_io.py tests/test_io_excel.py
git commit -m "feat(io_excel): add read_claims"
```

---

### Task 3: `read_exposures`

**Files:**
- Create: `src/pyre/io_excel/exposures_io.py`
- Modify: `tests/test_io_excel.py`

**Interfaces:**
- Produces: `pyre.io_excel.exposures_io.read_exposures(path: str | Path, sheet_name: str = "Exposures") -> Exposures`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_io_excel.py`:

```python
@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestReadExposures(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "exposures.xlsx"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_exposures_sheet(self, rows, headers=None, trailing_blank_row=False):
        headers = headers or [
            "exposure_id", "exposure_name", "exposure_period_start",
            "exposure_period_end", "currency", "exposure_value",
        ]
        wb = Workbook()
        ws = wb.active
        ws.title = "Exposures"
        ws.append(headers)
        for row in rows:
            ws.append(row)
        if trailing_blank_row:
            ws.append([None] * len(headers))
        wb.save(self.path)

    def test_builds_exposures(self):
        from pyre.io_excel.exposures_io import read_exposures

        self._write_exposures_sheet(
            [
                ["EXP2022", "2022 Premium", date(2022, 1, 1), date(2022, 12, 31), "USD", 1000000],
                ["EXP2023", "2023 Premium", date(2023, 1, 1), date(2023, 12, 31), "USD", 1200000],
            ]
        )

        exposures = read_exposures(self.path)
        self.assertEqual(sorted(exposures.modelling_years), [2022, 2023])

    def test_rejects_missing_required_column(self):
        from pyre.io_excel.exposures_io import read_exposures

        self._write_exposures_sheet(
            rows=[["EXP2022", date(2022, 1, 1), date(2022, 12, 31), "USD", 1000000]],
            headers=["exposure_id", "exposure_period_start", "exposure_period_end", "currency", "exposure_value"],
        )

        with self.assertRaises(ValueError):
            read_exposures(self.path)

    def test_ignores_trailing_blank_row(self):
        from pyre.io_excel.exposures_io import read_exposures

        self._write_exposures_sheet(
            [["EXP2022", "2022 Premium", date(2022, 1, 1), date(2022, 12, 31), "USD", 1000000]],
            trailing_blank_row=True,
        )

        exposures = read_exposures(self.path)
        self.assertEqual(len(exposures), 1)

    def test_missing_optional_column_entirely_defaults_cleanly(self):
        from pyre.io_excel.exposures_io import read_exposures

        self._write_exposures_sheet(
            [["EXP2022", "2022 Premium", date(2022, 1, 1), date(2022, 12, 31), "USD", 1000000]]
        )

        exposures = read_exposures(self.path)  # must not raise KeyError
        self.assertEqual(exposures.exposures[0].exposure_values.attachment_point, 0.0)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_io_excel.py::TestReadExposures -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `read_exposures`**

Create `src/pyre/io_excel/exposures_io.py`:

```python
from __future__ import annotations

from pathlib import Path

from ..enums import ExposureBasis
from ..exposures.exposures import Exposure, ExposureMetaData, Exposures, ExposureValues
from .claims_io import _parse_bool, _parse_date, _read_sheet

EXPOSURES_REQUIRED_COLUMNS = [
    "exposure_id",
    "exposure_name",
    "exposure_period_start",
    "exposure_period_end",
    "currency",
    "exposure_value",
]


def read_exposures(path: str | Path, sheet_name: str = "Exposures") -> Exposures:
    """Build an Exposures collection from a .xlsx sheet (one row per exposure)."""
    headers, rows = _read_sheet(path, sheet_name)

    missing = [c for c in EXPOSURES_REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise ValueError(f"exposures sheet '{sheet_name}' is missing required columns: {missing}")

    col = {name: idx for idx, name in enumerate(headers)}

    exposures: list[Exposure] = []
    for row in rows:
        if row[col["exposure_id"]] is None:
            continue

        exposure_type_raw = row[col["exposure_type"]] if "exposure_type" in col else None
        exposure_type = (
            ExposureBasis[str(exposure_type_raw).strip()]
            if exposure_type_raw
            else ExposureBasis.EARNED
        )

        meta = ExposureMetaData(
            exposure_id=str(row[col["exposure_id"]]),
            exposure_name=str(row[col["exposure_name"]]),
            exposure_period_start=_parse_date(row[col["exposure_period_start"]]),
            exposure_period_end=_parse_date(row[col["exposure_period_end"]]),
            currency=str(row[col["currency"]]),
            aggregate=(_parse_bool(row[col["aggregate"]]) if "aggregate" in col else False),
            line_of_business=row[col["line_of_business"]] if "line_of_business" in col else None,
            stacking_id=row[col["stacking_id"]] if "stacking_id" in col else None,
            exposure_type=exposure_type,
            location=row[col["location"]] if "location" in col else None,
            peril=row[col["peril"]] if "peril" in col else None,
            occupancy=row[col["occupancy"]] if "occupancy" in col else None,
        )

        exposure_value = float(row[col["exposure_value"]])
        values = ExposureValues(
            exposure_value=exposure_value,
            attachment_point=(
                float(row[col["attachment_point"]])
                if "attachment_point" in col and row[col["attachment_point"]] is not None
                else 0.0
            ),
            limit=(
                float(row[col["limit"]])
                if "limit" in col and row[col["limit"]] is not None
                else exposure_value
            ),
        )
        exposures.append(Exposure(exposure_meta=meta, exposure_values=values))

    return Exposures(exposures)
```

Note: `_parse_bool`, `_parse_date`, `_read_sheet` are imported from `claims_io`
rather than duplicated — both modules need identical date/bool parsing, and
`claims_io` has no dependency on `exposures_io`, so this one-directional
import is safe (no cycle).

- [ ] **Step 4: Run to verify it passes**

```bash
pytest tests/test_io_excel.py::TestReadExposures -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyre/io_excel/exposures_io.py tests/test_io_excel.py
git commit -m "feat(io_excel): add read_exposures"
```

---

### Task 4: `write_triangle`

**Files:**
- Create: `src/pyre/io_excel/triangle_io.py`
- Modify: `tests/test_io_excel.py`

**Interfaces:**
- Consumes: `write_table` from Task 1 (`pyre.io_excel._workbook.write_table`).
- Produces: `pyre.io_excel.triangle_io.write_triangle(triangle: Triangle, path: str | Path, sheet_name: str = "Triangle") -> None`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_io_excel.py`:

```python
@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestWriteTriangle(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "triangle.xlsx"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_writes_grid_with_blank_cells_for_missing_combinations(self):
        from pyre.claims.triangles import Triangle
        from pyre.io_excel.triangle_io import write_triangle

        triangle = Triangle(
            triangle={
                2020: {1: 100.0, 2: 150.0, 3: 175.0},
                2021: {1: 110.0, 2: 165.0},
                2022: {1: 120.0},
            },
            origin_years=[2020, 2021, 2022],
            dev_periods=[1, 2, 3],
        )

        write_triangle(triangle, self.path)

        wb = openpyxl.load_workbook(self.path)
        ws = wb["Triangle"]
        rows = [list(row) for row in ws.iter_rows(values_only=True)]

        self.assertEqual(rows[0], ["origin_year", "1", "2", "3"])
        self.assertEqual(rows[1], [2020, 100.0, 150.0, 175.0])
        self.assertEqual(rows[2], [2021, 110.0, 165.0, None])
        self.assertEqual(rows[3], [2022, 120.0, None, None])
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_io_excel.py::TestWriteTriangle -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `write_triangle`**

Create `src/pyre/io_excel/triangle_io.py`:

```python
from __future__ import annotations

from pathlib import Path

from ..claims.triangles import Triangle
from ._workbook import write_table


def write_triangle(triangle: Triangle, path: str | Path, sheet_name: str = "Triangle") -> None:
    """Write a Triangle's origin-year x dev-period grid to one sheet of an .xlsx workbook.

    Missing (origin_year, dev_period) combinations -- no claim data at that
    point -- are left as blank cells.
    """
    headers = ["origin_year"] + [str(period) for period in triangle.dev_periods]

    rows = []
    for year in triangle.origin_years:
        row: list = [year]
        for period in triangle.dev_periods:
            row.append(triangle.triangle.get(year, {}).get(period))
        rows.append(row)

    write_table(headers=headers, rows=rows, path=path, sheet_name=sheet_name)
```

- [ ] **Step 4: Run to verify it passes**

```bash
pytest tests/test_io_excel.py::TestWriteTriangle -v
```

Expected: 1 test PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyre/io_excel/triangle_io.py tests/test_io_excel.py
git commit -m "feat(io_excel): add write_triangle"
```

---

### Task 5: Fix `ExposureModel` share-calculation bug + add `calculate_all_shares()`

**Files:**
- Modify: `src/pyre/models/Exposure/exposure_rating_cost.py`
- Create: `tests/test_exposure_rating_cost.py`

**Interfaces:**
- Produces: `ExposureModel.calculate_all_shares(self) -> Dict[str, Dict[int, float]]` (exposure_id -> {layer_id: share}), consumed by Task 7.

**Context:** `_calculate_single_exposure_share` (private, existing) has an
indentation bug: the curve-position calculation and the
`shares_by_layer[layer.layer_id] = share` assignment are nested *only* inside
the `else` branch of `if treaty_layer_limit + treaty_layer_attachment <
policy_limit`. So whenever a layer's limit+attachment fits inside the policy
limit (the `if` branch — the common case), that layer never gets an entry in
the result. `calculate_all_shares()` needs this fixed to be correct.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_exposure_rating_cost.py`:

```python
import unittest
from datetime import date

from pyre import (
    Exposure,
    ExposureMetaData,
    Exposures,
    ExposureValues,
    RIContract,
    RIContractMetadata,
    RILayer,
)
from pyre.models.Exposure.exposure_curve_functions import ExposureCurveType, mbbefd_curve
from pyre.models.Exposure.exposure_rating_cost import ExposureModel
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType


def _build_contract(layers):
    metadata = RIContractMetadata(
        contract_id="C-0001",
        contract_description="Test",
        cedent_name="Acme Re",
        trigger_basis=ClaimTriggerBasis.LOD,
        indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0,
        inception_date=date(2023, 1, 1),
        expiration_date=date(2023, 12, 31),
        fx_rates={"USD": 1.0},
    )
    return RIContract(contract_meta_data=metadata, layers=layers)


def _build_layer(layer_id, occurrence_attachment, occurrence_limit):
    return RILayer(
        layer_id=layer_id,
        layer_name=f"Layer {layer_id}",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=occurrence_attachment,
        occurrence_limit=occurrence_limit,
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


def _build_exposure(exposure_id, attachment_point, limit):
    meta = ExposureMetaData(
        exposure_id=exposure_id,
        exposure_name=exposure_id,
        exposure_period_start=date(2023, 1, 1),
        exposure_period_end=date(2023, 12, 31),
        currency="USD",
    )
    values = ExposureValues(
        exposure_value=attachment_point + limit,
        attachment_point=attachment_point,
        limit=limit,
    )
    return Exposure(exposure_meta=meta, exposure_values=values)


class TestCalculateAllShares(unittest.TestCase):
    def setUp(self):
        # Policy: attachment 0, limit 1,000,000 -> total_insured_value 1,000,000.
        self.exposure = _build_exposure("EXP001", attachment_point=0.0, limit=1_000_000.0)
        self.exposures = Exposures([self.exposure])
        self.curve_param = 3.0

    def test_layer_fitting_inside_policy_limit_is_included(self):
        # 400,000 + 100,000 = 500,000 < 1,000,000 policy limit -> "if" branch,
        # previously never added to shares_by_layer at all.
        layer = _build_layer(layer_id=1, occurrence_attachment=100_000.0, occurrence_limit=400_000.0)
        contract = _build_contract([layer])
        model = ExposureModel(
            exposures=self.exposures,
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": self.curve_param},
        )

        shares = model.calculate_all_shares()

        self.assertIn("EXP001", shares)
        self.assertIn(1, shares["EXP001"])

        expected = (
            mbbefd_curve(self.curve_param, 500_000.0 / 1_000_000.0)
            - mbbefd_curve(self.curve_param, 100_000.0 / 1_000_000.0)
        ) / (
            mbbefd_curve(self.curve_param, 1.0) - mbbefd_curve(self.curve_param, 0.0)
        )
        self.assertAlmostEqual(shares["EXP001"][1], expected)

    def test_layer_exceeding_policy_limit_is_included(self):
        # 600,000 + 500,000 = 1,100,000 >= 1,000,000 policy limit -> "else" branch.
        layer = _build_layer(layer_id=2, occurrence_attachment=500_000.0, occurrence_limit=600_000.0)
        contract = _build_contract([layer])
        model = ExposureModel(
            exposures=self.exposures,
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": self.curve_param},
        )

        shares = model.calculate_all_shares()

        expected = (
            mbbefd_curve(self.curve_param, 1.0)
            - mbbefd_curve(self.curve_param, 500_000.0 / 1_000_000.0)
        ) / (
            mbbefd_curve(self.curve_param, 1.0) - mbbefd_curve(self.curve_param, 0.0)
        )
        self.assertAlmostEqual(shares["EXP001"][2], expected)

    def test_both_layer_types_present_simultaneously(self):
        layer_inside = _build_layer(layer_id=1, occurrence_attachment=100_000.0, occurrence_limit=400_000.0)
        layer_outside = _build_layer(layer_id=2, occurrence_attachment=500_000.0, occurrence_limit=600_000.0)
        contract = _build_contract([layer_inside, layer_outside])
        model = ExposureModel(
            exposures=self.exposures,
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": self.curve_param},
        )

        shares = model.calculate_all_shares()

        self.assertEqual(set(shares["EXP001"].keys()), {1, 2})

    def test_empty_exposures_returns_empty_dict(self):
        layer = _build_layer(layer_id=1, occurrence_attachment=100_000.0, occurrence_limit=400_000.0)
        contract = _build_contract([layer])
        model = ExposureModel(
            exposures=Exposures([]),
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": self.curve_param},
        )

        self.assertEqual(model.calculate_all_shares(), {})

    def test_zero_layers_gives_empty_share_dict_per_exposure(self):
        contract = _build_contract([])
        model = ExposureModel(
            exposures=self.exposures,
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": self.curve_param},
        )

        self.assertEqual(model.calculate_all_shares(), {"EXP001": {}})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_exposure_rating_cost.py -v
```

Expected: `AttributeError: 'ExposureModel' object has no attribute 'calculate_all_shares'`.

- [ ] **Step 3: Fix the indentation bug and add `calculate_all_shares`**

In `src/pyre/models/Exposure/exposure_rating_cost.py`, replace the body of
`_calculate_single_exposure_share` from the `if treaty_layer_limit...` line
through `return shares_by_layer` with:

```python
        for layer in self._ri_contract.layers:
            treaty_layer_attachment = layer.occurrence_attachment
            treaty_layer_limit = layer.occurrence_limit

            # Calculate treaty layer bottom and top
            treaty_bottom = min(policy_attachment + treaty_layer_attachment, total_insured_value)

            if treaty_layer_limit + treaty_layer_attachment < policy_limit:
                treaty_top = policy_attachment + treaty_layer_limit + treaty_layer_attachment
            else:
                treaty_top = total_insured_value

            # TODO: below is not general for all function very much mbbefd curve input expectations.
            curve_position_policy_lower = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                policy_attachment / total_insured_value,
            )
            curve_position_policy_higher = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                total_insured_value / total_insured_value,  # This equals 1.0
            )
            curve_position_treaty_lower = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                treaty_bottom / total_insured_value,
            )
            curve_position_treaty_higher = self.calculate_exposure_curve(
                self._selected_curve, self._curve_parameters, treaty_top / total_insured_value
            )

            share = (curve_position_treaty_higher - curve_position_treaty_lower) / (
                curve_position_policy_higher - curve_position_policy_lower
            )
            shares_by_layer[layer.layer_id] = share

        return shares_by_layer
```

(This is the same code that was there before, dedented one level so it runs
regardless of which `if`/`else` branch was taken — the two branches only
disagree on the value of `treaty_top`.)

Then add the new public method, directly after `calculate_exposure_curve`:

```python
    def calculate_all_shares(self) -> Dict[str, Dict[int, float]]:
        """Run _calculate_single_exposure_share for every exposure in self._exposures.

        Returns:
            Dict mapping exposure_id -> {layer_id: share}.
        """
        return {
            exposure.exposure_meta.exposure_id: self._calculate_single_exposure_share(exposure)
            for exposure in self._exposures
        }
```

- [ ] **Step 4: Run to verify it passes**

```bash
pytest tests/test_exposure_rating_cost.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Run the full suite to confirm no regression**

```bash
pytest -q --ignore=tests/test_exposure_curve_fitting.py
```

Expected: same 22 pre-existing failures as documented in `CLAUDE.md`'s Known
Test State, plus all newly-added tests (from this task and Tasks 1-4) passing.
No new failures among previously-passing tests.

- [ ] **Step 6: Commit**

```bash
git add src/pyre/models/Exposure/exposure_rating_cost.py tests/test_exposure_rating_cost.py
git commit -m "fix(models): correct ExposureModel share calculation for layers inside the policy limit; add calculate_all_shares"
```

---

### Task 6: `write_experience_rating_results`

**Files:**
- Create: `src/pyre/io_excel/results_io.py`
- Modify: `tests/test_io_excel.py`

**Interfaces:**
- Consumes: `write_table` (Task 1).
- Produces: `pyre.io_excel.results_io.write_experience_rating_results(model_data: ExperienceModelData, path: str | Path) -> None`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_io_excel.py` (add these imports near the top too):

```python
from pyre import (
    Claim,
    ClaimDevelopmentHistory,
    ClaimsMetaData,
    Claims as PyreClaims,
    Exposure as PyreExposure,
    ExposureMetaData as PyreExposureMetaData,
    Exposures as PyreExposures,
    ExposureValues as PyreExposureValues,
    ExperienceModelData,
    RIContract,
    RIContractMetadata,
    RILayer,
)
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType
```

```python
@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestWriteExperienceRatingResults(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "experience.xlsx"

        claim = Claim(
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
        claims = PyreClaims([claim])

        exposure = PyreExposure(
            PyreExposureMetaData(
                exposure_id="EXP2022",
                exposure_name="2022 Premium",
                exposure_period_start=date(2022, 1, 1),
                exposure_period_end=date(2022, 12, 31),
                currency="USD",
            ),
            PyreExposureValues(exposure_value=1_000_000.0, attachment_point=0.0, limit=1_000_000.0),
        )
        exposures = PyreExposures([exposure])

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
        layer = RILayer(
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
        contract = RIContract(contract_meta_data=metadata, layers=[layer])

        self.model_data = ExperienceModelData(claims=claims, exposures=exposures, ri_contract=contract)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_writes_both_sheets(self):
        from pyre.io_excel.results_io import write_experience_rating_results

        write_experience_rating_results(self.model_data, self.path)

        wb = openpyxl.load_workbook(self.path)
        self.assertEqual(set(wb.sheetnames), {"ByLayerYear", "ExposuresByYear"})

        by_layer_year = [list(row) for row in wb["ByLayerYear"].iter_rows(values_only=True)]
        self.assertEqual(
            by_layer_year[0],
            ["layer_id", "layer_name", "modelling_year", "ceded_paid", "ceded_incurred", "claim_count", "earned_premium"],
        )
        self.assertEqual(by_layer_year[1][0], 1)
        self.assertEqual(by_layer_year[1][1], "XOL Layer")
        self.assertEqual(by_layer_year[1][2], 2022)

        exposures_by_year = [list(row) for row in wb["ExposuresByYear"].iter_rows(values_only=True)]
        self.assertEqual(exposures_by_year[0], ["modelling_year", "written", "earned"])
        self.assertEqual(exposures_by_year[1][0], 2022)

    def test_rerunning_overwrites_rather_than_duplicating_rows(self):
        from pyre.io_excel.results_io import write_experience_rating_results

        write_experience_rating_results(self.model_data, self.path)
        write_experience_rating_results(self.model_data, self.path)  # re-run

        wb = openpyxl.load_workbook(self.path)
        self.assertEqual(wb.sheetnames.count("ByLayerYear"), 1)
        by_layer_year_rows = list(wb["ByLayerYear"].iter_rows(values_only=True))
        self.assertEqual(len(by_layer_year_rows), 2)  # header + 1 data row, not 1 + 2
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_io_excel.py::TestWriteExperienceRatingResults -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `write_experience_rating_results`**

Create `src/pyre/io_excel/results_io.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ._workbook import write_table

if TYPE_CHECKING:
    from ..models.Experience.experience_preparer import ExperienceModelData
    from ..models.Exposure.exposure_rating_cost import ExposureModel


def write_experience_rating_results(model_data: "ExperienceModelData", path: str | Path) -> None:
    """Write an ExperienceModelData's aggregated results to two sheets of one .xlsx workbook.

    "ByLayerYear": one row per (layer_id, modelling_year).
    "ExposuresByYear": one row per modelling_year.
    """
    layer_names = {layer.layer_id: layer.layer_name for layer in model_data.ri_contract.layers}
    aggregate_claims = model_data.aggregate_subject_contract_claims
    aggregate_exposures = model_data.aggregate_exposures

    by_layer_year_rows = []
    for layer_id, year_agg in aggregate_claims.items():
        for modelling_year, values in year_agg.items():
            earned_premium = aggregate_exposures.get(modelling_year, {}).get("earned", 0.0)
            by_layer_year_rows.append(
                [
                    layer_id,
                    layer_names.get(layer_id, str(layer_id)),
                    modelling_year,
                    values["latest_paid"],
                    values["latest_incurred"],
                    values["total_count"],
                    earned_premium,
                ]
            )

    write_table(
        headers=[
            "layer_id",
            "layer_name",
            "modelling_year",
            "ceded_paid",
            "ceded_incurred",
            "claim_count",
            "earned_premium",
        ],
        rows=by_layer_year_rows,
        path=path,
        sheet_name="ByLayerYear",
    )

    exposures_rows = [
        [year, values["written"], values["earned"]]
        for year, values in sorted(aggregate_exposures.items())
    ]
    write_table(
        headers=["modelling_year", "written", "earned"],
        rows=exposures_rows,
        path=path,
        sheet_name="ExposuresByYear",
    )
```

- [ ] **Step 4: Run to verify it passes**

```bash
pytest tests/test_io_excel.py::TestWriteExperienceRatingResults -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyre/io_excel/results_io.py tests/test_io_excel.py
git commit -m "feat(io_excel): add write_experience_rating_results"
```

---

### Task 7: `write_exposure_rating_results`

**Files:**
- Modify: `src/pyre/io_excel/results_io.py`
- Modify: `tests/test_io_excel.py`

**Interfaces:**
- Consumes: `write_table` (Task 1), `ExposureModel.calculate_all_shares()` (Task 5).
- Produces: `pyre.io_excel.results_io.write_exposure_rating_results(exposure_model: ExposureModel, path: str | Path) -> None`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_io_excel.py`:

```python
@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestWriteExposureRatingResults(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "exposure.xlsx"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_writes_one_row_per_exposure_layer_pair(self):
        from pyre.models.Exposure.exposure_curve_functions import ExposureCurveType
        from pyre.models.Exposure.exposure_rating_cost import ExposureModel
        from pyre.io_excel.results_io import write_exposure_rating_results

        exposure = PyreExposure(
            PyreExposureMetaData(
                exposure_id="EXP001",
                exposure_name="EXP001",
                exposure_period_start=date(2023, 1, 1),
                exposure_period_end=date(2023, 12, 31),
                currency="USD",
            ),
            PyreExposureValues(exposure_value=1_000_000.0, attachment_point=0.0, limit=1_000_000.0),
        )
        layer = RILayer(
            layer_id=1,
            layer_name="Layer 1",
            layer_type=ContractType.EXCESS_OF_LOSS,
            occurrence_attachment=100_000.0,
            occurrence_limit=400_000.0,
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
        metadata = RIContractMetadata(
            contract_id="C-0001",
            contract_description="Test",
            cedent_name="Acme Re",
            trigger_basis=ClaimTriggerBasis.LOD,
            indexation_clause=IndexationClauseType.FULL_INDEXATION,
            indexation_margin=0.0,
            inception_date=date(2023, 1, 1),
            expiration_date=date(2023, 12, 31),
            fx_rates={"USD": 1.0},
        )
        contract = RIContract(contract_meta_data=metadata, layers=[layer])
        model = ExposureModel(
            exposures=PyreExposures([exposure]),
            ri_contract=contract,
            selected_curve=ExposureCurveType.MBBEFD,
            curve_parameters={"curve": 3.0},
        )

        write_exposure_rating_results(model, self.path)

        wb = openpyxl.load_workbook(self.path)
        rows = [list(row) for row in wb["ExposureShares"].iter_rows(values_only=True)]
        self.assertEqual(rows[0], ["exposure_id", "layer_id", "share"])
        self.assertEqual(rows[1][0], "EXP001")
        self.assertEqual(rows[1][1], 1)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_io_excel.py::TestWriteExposureRatingResults -v
```

Expected: `ImportError: cannot import name 'write_exposure_rating_results'`.

- [ ] **Step 3: Implement `write_exposure_rating_results`**

Append to `src/pyre/io_excel/results_io.py`:

```python
def write_exposure_rating_results(exposure_model: "ExposureModel", path: str | Path) -> None:
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

- [ ] **Step 4: Run to verify it passes**

```bash
pytest tests/test_io_excel.py::TestWriteExposureRatingResults -v
```

Expected: 1 test PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyre/io_excel/results_io.py tests/test_io_excel.py
git commit -m "feat(io_excel): add write_exposure_rating_results"
```

---

### Task 8: Public exports, docs, and final verification

**Files:**
- Modify: `src/pyre/io_excel/__init__.py`
- Create: `docs/io_excel.md`
- Modify: `mkdocs.yml`
- Modify: `CLAUDE.md`
- Modify: `tests/test_io_excel.py` (one final integration test)

**Interfaces:**
- Consumes: every function from Tasks 1-7.
- Produces: the finished `pyre.io_excel` public surface (`read_claims`, `read_exposures`, `write_triangle`, `write_experience_rating_results`, `write_exposure_rating_results`).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_io_excel.py`:

```python
@unittest.skipUnless(HAS_OPENPYXL, "openpyxl not installed; pip install -e '.[excel]'")
class TestPublicApiSurface(unittest.TestCase):
    def test_all_five_functions_importable_from_io_excel_package(self):
        from pyre.io_excel import (
            read_claims,
            read_exposures,
            write_exposure_rating_results,
            write_experience_rating_results,
            write_triangle,
        )

        self.assertTrue(callable(read_claims))
        self.assertTrue(callable(read_exposures))
        self.assertTrue(callable(write_triangle))
        self.assertTrue(callable(write_experience_rating_results))
        self.assertTrue(callable(write_exposure_rating_results))

    def test_bare_import_pyre_does_not_require_openpyxl(self):
        # Confirms pyre/__init__.py never imports io_excel transitively.
        # (openpyxl IS installed in this test env, so this only checks that
        # `pyre.io_excel` is absent from sys.modules after a bare `import pyre`
        # -- it does not prove openpyxl is uninstallable-safe, just that the
        # import graph doesn't pull it in.)
        import sys

        for name in list(sys.modules):
            if name == "pyre" or name.startswith("pyre."):
                del sys.modules[name]

        import pyre  # noqa: F401

        self.assertNotIn("pyre.io_excel", sys.modules)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_io_excel.py::TestPublicApiSurface -v
```

Expected: `ImportError` (nothing re-exported from `pyre.io_excel.__init__` yet).

- [ ] **Step 3: Add the re-exports**

Replace the contents of `src/pyre/io_excel/__init__.py`:

```python
"""Headless Excel file I/O for pyre -- requires the 'excel' optional extra (openpyxl).

Never imported by pyre/__init__.py: a bare `import pyre` must not require
openpyxl. Only `from pyre.io_excel import ...` does.
"""

from .claims_io import read_claims
from .exposures_io import read_exposures
from .results_io import write_exposure_rating_results, write_experience_rating_results
from .triangle_io import write_triangle

__all__ = [
    "read_claims",
    "read_exposures",
    "write_exposure_rating_results",
    "write_experience_rating_results",
    "write_triangle",
]
```

- [ ] **Step 4: Run to verify it passes**

```bash
pytest tests/test_io_excel.py -v
```

Expected: every test in the file PASSES.

- [ ] **Step 5: Write the docs page**

Create `docs/io_excel.md`:

```markdown
# Excel File I/O

`pyre.io_excel` reads `Claims`/`Exposures` from `.xlsx` workbooks and writes
triangle, experience-rating, and exposure-rating results back out — no Excel
installation required (this is headless file I/O via
[openpyxl](https://openpyxl.readthedocs.io/), not a live Excel connection;
that's a separate, not-yet-built xlwings integration).

## Installation

```bash
pip install -e ".[excel]"
```

`pyre.io_excel` is never imported by a bare `import pyre` — only
`from pyre.io_excel import ...` requires `openpyxl` to be installed.

## Reading claims and exposures

```python
from pyre.io_excel import read_claims, read_exposures

claims = read_claims("claims.xlsx")       # expects a "Claims" sheet
exposures = read_exposures("exposures.xlsx")  # expects an "Exposures" sheet
```

Both use the same long-format column schema as the Panel workbench's CSV
upload (see [Treaty Pricing Workbench](workbench.md)): one row per
claim/development-point for claims, one row per exposure. `contract_limit`
must be set to a positive value, same requirement as elsewhere in `pyre` —
see [Claims](claims.md).

## Writing results

```python
from pyre.io_excel import write_triangle, write_experience_rating_results, write_exposure_rating_results

write_triangle(triangle, "triangle.xlsx")
write_experience_rating_results(model_data, "experience_results.xlsx")  # model_data: ExperienceModelData
write_exposure_rating_results(exposure_model, "exposure_results.xlsx")  # exposure_model: ExposureModel
```

`write_experience_rating_results` writes two sheets ("ByLayerYear",
"ExposuresByYear") to one workbook. Re-running either write function against
the same path overwrites that sheet rather than duplicating it.

## API Reference

::: pyre.io_excel.claims_io

::: pyre.io_excel.exposures_io

::: pyre.io_excel.triangle_io

::: pyre.io_excel.results_io
```

- [ ] **Step 6: Add the docs page to the nav**

In `mkdocs.yml`, add `- Excel File I/O: io_excel.md` to the `nav:` list,
alongside the existing entries (e.g. near `workbench.md`'s entry).

- [ ] **Step 7: Update `CLAUDE.md`**

In the "Module map (`src/pyre/`)" table, add a row:

```markdown
| `io_excel/` | Headless `.xlsx` read/write (`read_claims`, `read_exposures`, `write_triangle`, `write_experience_rating_results`, `write_exposure_rating_results`) — optional, requires `pip install -e ".[excel]"` |
```

In the "Commands" section, add alongside the existing `pip install -e ".[panel]"` line:

```bash
pip install -e ".[excel]"       # install with headless Excel (.xlsx) read/write support
```

Update the "Known Test State" baseline numbers (re-run
`pytest -q --ignore=tests/test_exposure_curve_fitting.py` after Step 8 below
and paste the exact new `X failed, Y passed` count — do not guess the number
in advance).

- [ ] **Step 8: Full verification pass**

```bash
ruff check src/pyre/ app/ tests/
hatch run types:check
pytest -q --ignore=tests/test_exposure_curve_fitting.py
hatch run docs:build
```

Expected: `ruff` reports no new issues; `mypy` reports no new errors beyond
the pre-existing non-strict baseline; `pytest` shows the same pre-existing 22
failures plus all new tests (Tasks 1-8) passing; `mkdocs build --strict`
succeeds with the new `io_excel.md` page resolving its `:::` directives
(requires the `excel` extra installed in the docs-build environment, same as
how `app/service.py`'s classes resolve today).

- [ ] **Step 9: Commit**

```bash
git add src/pyre/io_excel/__init__.py docs/io_excel.md mkdocs.yml CLAUDE.md tests/test_io_excel.py
git commit -m "feat(io_excel): finalize public API, add docs page, update CLAUDE.md"
```
