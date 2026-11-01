# Model Versioning & SQLite Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Panel treaty pricing workbench a local SQLite-backed persistence layer — save/load/copy/delete pricing models, mark versions final vs. optional, a catalog dashboard, and a version-comparison view.

**Architecture:** A new Panel-free `app/db.py` repository module (schema, pickled-input blobs, relational results/metadata) sits under everything; two existing pages (`contract_config.py`, `data_loading.py`) are retrofitted to seed from `WorkbenchState`; `results.py` gains Save/Recalculate actions; two new pages (`model_library.py`, `compare.py`) and `main.py`'s tab wiring complete the UI.

**Tech Stack:** Python stdlib `sqlite3` + `pickle` (no new dependencies), Panel, pandas (already-present `panel` extra).

**Spec:** `docs/superpowers/specs/2026-11-01-model-versioning-backend-design.md`

## Global Constraints

- `src/pyre` is untouched — this entire subsystem lives under `app/`.
- No new third-party dependencies.
- `WorkbenchState`'s existing non-persisted in-session behavior is unchanged; persistence is additive.
- `is_final` is a plain boolean column, never enforced-unique.
- Delete is a real delete — no trash/soft-delete.
- Copy duplicates the full pickled blob — no reference-sharing.
- Results are cached at save time; nothing recomputes on load except the explicit Recalculate action.
- DB file lives at `data/workbench.db` (repo root, gitignored).

## Review Focus

- Deleting a version that other versions point to as `parent_id` must not destroy those children or raise an unhandled `sqlite3.IntegrityError` — covered in Task 1 (schema) and Task 5 (delete test).
- Saving and reloading a fully-empty draft (no claims, no exposures, no contract, no layers) must round-trip cleanly, not raise — covered in Task 2.
- Loading a blob saved under an incompatible/corrupted pickle must raise a clear error naming the stored `pyre_version`, not a raw `pickle` traceback — covered in Task 2.
- `diff_versions` on two versions that share no common layer/year combination must return empty diff lists, not crash — covered in Task 6.
- Copying a draft version (no results saved yet) must succeed and produce another resultless draft — covered in Task 4.

---

### Task 1: Schema and connection helper

**Files:**
- Create: `app/db.py`
- Modify: `.gitignore` (add `data/`)
- Test: `tests/test_db.py` (new)

**Interfaces:**
- Produces: `DB_PATH: Path` (module constant, `<repo root>/data/workbench.db`), `init_db(path: Path) -> None`, `_connect(path: Path) -> sqlite3.Connection` (context-manager-compatible; enables `PRAGMA foreign_keys = ON`). All later tasks' functions take a `path: Path` parameter and call `_connect(path)` themselves — no shared global connection.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db.py
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.db import init_db


class TestInitDb(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "test.db"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_creates_expected_tables(self):
        init_db(self.path)

        conn = sqlite3.connect(self.path)
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()

        self.assertEqual(
            names,
            {"pricing_versions", "pricing_results_by_layer_year", "pricing_results_exposures_by_year"},
        )

    def test_foreign_keys_enabled_on_connection(self):
        from app.db import _connect

        init_db(self.path)
        with _connect(self.path) as conn:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_deleting_a_version_with_children_nulls_their_parent_id_not_errors(self):
        from app.db import _connect

        init_db(self.path)
        with _connect(self.path) as conn:
            conn.execute(
                "INSERT INTO pricing_versions (id, label, is_final, created_at, updated_at, pyre_version, inputs_blob) "
                "VALUES (1, 'parent', 0, '2026-01-01', '2026-01-01', '0.0.1', x'00')"
            )
            conn.execute(
                "INSERT INTO pricing_versions (id, label, parent_id, is_final, created_at, updated_at, pyre_version, inputs_blob) "
                "VALUES (2, 'child', 1, 0, '2026-01-01', '2026-01-01', '0.0.1', x'00')"
            )
            conn.execute("DELETE FROM pricing_versions WHERE id = 1")
            conn.commit()
            remaining = conn.execute("SELECT id, parent_id FROM pricing_versions").fetchall()

        self.assertEqual(remaining, [(2, None)])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 3: Implement `app/db.py`'s schema and connection helper**

```python
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "workbench.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pricing_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    parent_id INTEGER REFERENCES pricing_versions(id) ON DELETE SET NULL,
    is_final INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    pyre_version TEXT NOT NULL,
    contract_id TEXT,
    cedent_name TEXT,
    contract_description TEXT,
    inception_date TEXT,
    expiration_date TEXT,
    inputs_blob BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS pricing_results_by_layer_year (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    layer_id INTEGER NOT NULL,
    layer_name TEXT NOT NULL,
    modelling_year INTEGER NOT NULL,
    ceded_paid REAL NOT NULL,
    ceded_incurred REAL NOT NULL,
    claim_count INTEGER NOT NULL,
    earned_premium REAL NOT NULL,
    loss_ratio REAL
);

CREATE TABLE IF NOT EXISTS pricing_results_exposures_by_year (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    modelling_year INTEGER NOT NULL,
    written REAL NOT NULL,
    earned REAL NOT NULL
);
"""


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as conn:
        conn.executescript(_SCHEMA)


@contextlib.contextmanager
def _connect(path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()
```

Needs `import contextlib`, `import sqlite3`, `from pathlib import Path`, `from typing import Iterator` at the top of the file.

Also add `data/` to `.gitignore`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_db.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add app/db.py .gitignore tests/test_db.py
git commit -m "feat: add SQLite schema and connection helper for model versioning"
```

---

### Task 2: `ModelSnapshot` and version save/load round-trip

**Files:**
- Modify: `app/db.py`
- Modify: `tests/test_db.py`

**Interfaces:**
- Consumes: Task 1's `_connect`.
- Produces: `ModelSnapshot` dataclass (`claims: Claims | None`, `exposures: Exposures | None`, `contract_metadata: RIContractMetadata | None`, `layers: list[RILayer]`); `save_version(path: Path, snapshot: ModelSnapshot, label: str, parent_id: int | None = None, is_final: bool = False) -> int` (returns new version id); `save_results(path: Path, version_id: int, by_layer_year: list[dict], exposures_by_year: list[dict]) -> None` (row shapes exactly match `summarize_by_layer_year`/`summarize_exposures_by_year` in `src/pyre/models/Experience/experience_preparer.py`); `load_version(path: Path, version_id: int) -> tuple[ModelSnapshot, list[dict], list[dict]]` (the two lists are the stored results rows, empty if none saved); `IncompatibleSnapshotError(Exception)` (carries `stored_pyre_version`/`current_pyre_version` attributes).

- [ ] **Step 1: Write the failing tests**

```python
class TestSaveLoadVersion(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "test.db"
        init_db(self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_round_trips_a_full_snapshot(self):
        from datetime import date

        from pyre import (
            Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData,
            Exposure, ExposureMetaData, Exposures, ExposureValues,
            RIContractMetadata, RILayer,
        )
        from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType
        from app.db import ModelSnapshot, load_version, save_version

        claims = Claims([Claim(
            ClaimsMetaData(claim_id="C1", currency="USD", contract_limit=1_000_000.0, loss_date=date(2022, 1, 1)),
            ClaimDevelopmentHistory(development_months=[12], cumulative_dev_paid=[1000.0], cumulative_dev_incurred=[2000.0]),
        )])
        exposures = Exposures([Exposure(
            ExposureMetaData(exposure_id="E1", exposure_name="E1", exposure_period_start=date(2022, 1, 1), exposure_period_end=date(2022, 12, 31), currency="USD"),
            ExposureValues(exposure_value=500_000.0, attachment_point=0.0, limit=500_000.0),
        )])
        metadata = RIContractMetadata(
            contract_id="C-0001", contract_description="Test", cedent_name="Acme",
            trigger_basis=ClaimTriggerBasis.LOD, indexation_clause=IndexationClauseType.FULL_INDEXATION,
            indexation_margin=0.0, inception_date=date(2022, 1, 1), expiration_date=date(2022, 12, 31),
            fx_rates={"USD": 1.0},
        )
        layer = RILayer(
            layer_id=1, layer_name="L1", layer_type=ContractType.EXCESS_OF_LOSS,
            occurrence_attachment=100_000.0, occurrence_limit=200_000.0,
            aggregate_attachment=0.0, aggregate_limit=0.0, subject_lines_of_business=[],
            subject_lob_exposure_amounts=[], full_subject_premium=0.0, written_line=1.0,
            signed_line=1.0, number_of_reinstatements=0, reinstatement_cost={},
        )
        snapshot = ModelSnapshot(claims=claims, exposures=exposures, contract_metadata=metadata, layers=[layer])

        version_id = save_version(self.path, snapshot, label="v1")
        loaded_snapshot, by_layer_year, exposures_by_year = load_version(self.path, version_id)

        self.assertEqual(loaded_snapshot.contract_metadata.contract_id, "C-0001")
        self.assertEqual(loaded_snapshot.layers[0].occurrence_limit, 200_000.0)
        self.assertEqual(loaded_snapshot.claims.claims[0].claims_meta_data.claim_id, "C1")
        self.assertEqual(by_layer_year, [])
        self.assertEqual(exposures_by_year, [])

    def test_round_trips_an_empty_draft(self):
        from app.db import ModelSnapshot, load_version, save_version

        snapshot = ModelSnapshot(claims=None, exposures=None, contract_metadata=None, layers=[])
        version_id = save_version(self.path, snapshot, label="draft")
        loaded_snapshot, by_layer_year, exposures_by_year = load_version(self.path, version_id)

        self.assertIsNone(loaded_snapshot.claims)
        self.assertIsNone(loaded_snapshot.contract_metadata)
        self.assertEqual(loaded_snapshot.layers, [])
        self.assertEqual(by_layer_year, [])

    def test_save_results_then_load_returns_the_rows(self):
        from app.db import ModelSnapshot, load_version, save_results, save_version

        version_id = save_version(self.path, ModelSnapshot(None, None, None, []), label="v1")
        by_layer_year = [{
            "layer_id": 1, "layer_name": "L1", "modelling_year": 2022, "ceded_paid": 0.0,
            "ceded_incurred": 150000.0, "claim_count": 1, "earned_premium": 1_000_000.0, "loss_ratio": 0.15,
        }]
        exposures_by_year = [{"modelling_year": 2022, "written": 1_000_000.0, "earned": 1_000_000.0}]
        save_results(self.path, version_id, by_layer_year, exposures_by_year)

        _, loaded_by_layer_year, loaded_exposures_by_year = load_version(self.path, version_id)

        self.assertEqual(loaded_by_layer_year, by_layer_year)
        self.assertEqual(loaded_exposures_by_year, exposures_by_year)

    def test_load_raises_named_error_on_incompatible_blob(self):
        from app.db import IncompatibleSnapshotError, _connect, load_version

        with _connect(self.path) as conn:
            conn.execute(
                "INSERT INTO pricing_versions (id, label, is_final, created_at, updated_at, pyre_version, inputs_blob) "
                "VALUES (1, 'bad', 0, '2026-01-01', '2026-01-01', '0.0.0-does-not-exist', x'ffff')"
            )
            conn.commit()

        with self.assertRaises(IncompatibleSnapshotError) as ctx:
            load_version(self.path, 1)
        self.assertEqual(ctx.exception.stored_pyre_version, "0.0.0-does-not-exist")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_db.py::TestSaveLoadVersion -v`
Expected: FAIL — `ImportError: cannot import name 'ModelSnapshot' from 'app.db'`

- [ ] **Step 3: Implement `ModelSnapshot`, `save_version`, `save_results`, `load_version`, `IncompatibleSnapshotError`**

`save_version`: `pickle.dumps(snapshot)`; denormalized columns (`contract_id`, `cedent_name`, `contract_description`, `inception_date`/`expiration_date` as `.isoformat()`) read from `snapshot.contract_metadata` if not `None`, else `NULL`; `created_at`/`updated_at` both `datetime.now(timezone.utc).isoformat()`; `pyre_version` from `pyre.__about__.__version__`. Returns `cursor.lastrowid`.

`save_results`: `DELETE FROM` both results tables `WHERE version_id = ?` first (so re-running results for the same version replaces, not duplicates — mirrors `write_table`'s own re-run-overwrites convention), then `INSERT` one row per dict in each list, then update `pricing_versions.updated_at`.

`load_version`: `SELECT inputs_blob, pyre_version FROM pricing_versions WHERE id = ?`; wrap `pickle.loads(blob)` in `try/except Exception` and raise `IncompatibleSnapshotError` carrying both pyre versions on failure (do not let a raw `pickle` exception propagate); then `SELECT * FROM pricing_results_by_layer_year WHERE version_id = ? ORDER BY layer_id, modelling_year` and the exposures-by-year equivalent, each row converted to a `dict` with the SQL column names as keys (matching `summarize_by_layer_year`'s key set minus the SQLite `id`/`version_id` columns).

- [ ] **Step 4: Run tests to verify they pass**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_db.py -v`
Expected: `7 passed` (3 from Task 1 + 4 here)

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_db.py
git commit -m "feat: add ModelSnapshot pickling and version save/load round-trip"
```

---

### Task 3: `list_versions` and `set_final`

**Files:**
- Modify: `app/db.py`
- Modify: `tests/test_db.py`

**Interfaces:**
- Consumes: Task 2's `save_version`.
- Produces: `VersionSummary` dataclass (`id: int`, `label: str`, `parent_id: int | None`, `is_final: bool`, `created_at: str`, `updated_at: str`, `contract_id: str | None`, `cedent_name: str | None`, `contract_description: str | None`, `inception_date: str | None`, `expiration_date: str | None`, `has_results: bool`); `list_versions(path: Path, *, final_only: bool = False) -> list[VersionSummary]` (ordered by `created_at` descending); `set_final(path: Path, version_id: int, is_final: bool) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
class TestListVersionsAndSetFinal(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "test.db"
        init_db(self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_lists_versions_without_touching_the_blob(self):
        from app.db import ModelSnapshot, list_versions, save_version

        save_version(self.path, ModelSnapshot(None, None, None, []), label="a")
        save_version(self.path, ModelSnapshot(None, None, None, []), label="b")

        summaries = list_versions(self.path)

        self.assertEqual({s.label for s in summaries}, {"a", "b"})
        self.assertFalse(summaries[0].has_results)

    def test_final_only_filters_to_final_versions_and_coexist_is_allowed(self):
        from app.db import ModelSnapshot, list_versions, save_version, set_final

        id_a = save_version(self.path, ModelSnapshot(None, None, None, []), label="a")
        id_b = save_version(self.path, ModelSnapshot(None, None, None, []), label="b")
        set_final(self.path, id_a, True)
        set_final(self.path, id_b, True)

        self.assertEqual(len(list_versions(self.path, final_only=True)), 2)
        self.assertEqual(len(list_versions(self.path)), 2)

    def test_final_only_returns_empty_list_when_none_are_final(self):
        from app.db import ModelSnapshot, list_versions, save_version

        save_version(self.path, ModelSnapshot(None, None, None, []), label="a")

        self.assertEqual(list_versions(self.path, final_only=True), [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_db.py::TestListVersionsAndSetFinal -v`
Expected: FAIL — `ImportError: cannot import name 'list_versions' from 'app.db'`

- [ ] **Step 3: Implement `VersionSummary`, `list_versions`, `set_final`**

`list_versions`: `SELECT` all `pricing_versions` columns except `inputs_blob`, plus `EXISTS (SELECT 1 FROM pricing_results_by_layer_year WHERE version_id = pricing_versions.id)` aliased as `has_results`; `WHERE is_final = 1` appended when `final_only`; `ORDER BY created_at DESC`.

`set_final`: `UPDATE pricing_versions SET is_final = ?, updated_at = ? WHERE id = ?`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_db.py -v`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_db.py
git commit -m "feat: add list_versions and set_final"
```

---

### Task 4: `copy_version`

**Files:**
- Modify: `app/db.py`
- Modify: `tests/test_db.py`

**Interfaces:**
- Consumes: Task 2's `save_version`/`load_version`.
- Produces: `copy_version(path: Path, version_id: int, new_label: str) -> int` (returns the new version's id).

- [ ] **Step 1: Write the failing tests**

```python
class TestCopyVersion(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "test.db"
        init_db(self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_copy_produces_an_independent_version_pointing_at_its_parent(self):
        from pyre import Claims
        from app.db import ModelSnapshot, copy_version, list_versions, load_version, save_version

        original_id = save_version(self.path, ModelSnapshot(Claims([]), None, None, []), label="original")
        copy_id = copy_version(self.path, original_id, new_label="copy")

        self.assertNotEqual(copy_id, original_id)
        summaries = {s.id: s for s in list_versions(self.path)}
        self.assertEqual(summaries[copy_id].parent_id, original_id)
        self.assertEqual(summaries[copy_id].label, "copy")

    def test_copying_a_draft_with_no_results_succeeds(self):
        from app.db import ModelSnapshot, copy_version, load_version, save_version

        original_id = save_version(self.path, ModelSnapshot(None, None, None, []), label="draft")
        copy_id = copy_version(self.path, original_id, new_label="draft copy")

        _, by_layer_year, exposures_by_year = load_version(self.path, copy_id)
        self.assertEqual(by_layer_year, [])
        self.assertEqual(exposures_by_year, [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_db.py::TestCopyVersion -v`
Expected: FAIL — `ImportError: cannot import name 'copy_version' from 'app.db'`

- [ ] **Step 3: Implement `copy_version`**

`load_version(path, version_id)` to get the `ModelSnapshot`, then `save_version(path, snapshot, label=new_label, parent_id=version_id, is_final=False)`. If the original has saved results, also copy those via `save_results` using the same `load_version` call's results lists. No sharing of the original's row data — this is a second, independent `pickle.dumps` from the unpickled object.

- [ ] **Step 4: Run tests to verify they pass**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_db.py -v`
Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_db.py
git commit -m "feat: add copy_version"
```

---

### Task 5: `delete_version`

**Files:**
- Modify: `app/db.py`
- Modify: `tests/test_db.py`

**Interfaces:**
- Consumes: Task 2's `save_version`/`save_results`, Task 4's `copy_version`.
- Produces: `delete_version(path: Path, version_id: int) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
class TestDeleteVersion(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "test.db"
        init_db(self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_delete_removes_the_version_and_cascades_its_results(self):
        from app.db import ModelSnapshot, _connect, delete_version, save_results, save_version

        version_id = save_version(self.path, ModelSnapshot(None, None, None, []), label="v1")
        save_results(
            self.path, version_id,
            [{"layer_id": 1, "layer_name": "L", "modelling_year": 2022, "ceded_paid": 0.0,
              "ceded_incurred": 0.0, "claim_count": 0, "earned_premium": 0.0, "loss_ratio": None}],
            [],
        )

        delete_version(self.path, version_id)

        with _connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM pricing_versions").fetchone()[0], 0)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM pricing_results_by_layer_year").fetchone()[0], 0
            )

    def test_deleting_a_version_with_children_orphans_rather_than_blocks(self):
        from app.db import ModelSnapshot, copy_version, delete_version, list_versions, save_version

        parent_id = save_version(self.path, ModelSnapshot(None, None, None, []), label="parent")
        child_id = copy_version(self.path, parent_id, new_label="child")

        delete_version(self.path, parent_id)  # must not raise

        remaining = {s.id: s for s in list_versions(self.path)}
        self.assertEqual(remaining[child_id].parent_id, None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_db.py::TestDeleteVersion -v`
Expected: FAIL — `ImportError: cannot import name 'delete_version' from 'app.db'`

- [ ] **Step 3: Implement `delete_version`**

`DELETE FROM pricing_versions WHERE id = ?` — the schema's `ON DELETE CASCADE`/`ON DELETE SET NULL` foreign keys (Task 1) handle the results rows and any children's `parent_id` automatically; no manual cascading needed in this function's body.

- [ ] **Step 4: Run tests to verify they pass**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_db.py -v`
Expected: `14 passed`

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_db.py
git commit -m "feat: add delete_version"
```

---

### Task 6: `diff_versions`

**Files:**
- Modify: `app/db.py`
- Modify: `tests/test_db.py`

**Interfaces:**
- Consumes: Task 2's `load_version`.
- Produces: `LayerFieldChange` dataclass (`layer_id: int`, `field: str`, `old_value: Any`, `new_value: Any`); `ResultsRowDiff` dataclass (`layer_id: int`, `layer_name: str`, `modelling_year: int`, `ceded_paid_old: float`, `ceded_paid_new: float`, `ceded_incurred_old: float`, `ceded_incurred_new: float`, `loss_ratio_old: float | None`, `loss_ratio_new: float | None`); `VersionDiff` dataclass (`claims_count_old: int`, `claims_count_new: int`, `claims_total_incurred_old: float`, `claims_total_incurred_new: float`, `exposures_count_old: int`, `exposures_count_new: int`, `exposures_total_value_old: float`, `exposures_total_value_new: float`, `layer_changes: list[LayerFieldChange]`, `results_changes: list[ResultsRowDiff]`); `diff_versions(path: Path, version_id_old: int, version_id_new: int) -> VersionDiff`.

- [ ] **Step 1: Write the failing tests**

```python
class TestDiffVersions(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "test.db"
        init_db(self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _layer(self, layer_id, occurrence_limit):
        from pyre import RILayer
        from pyre.treaty import ContractType
        return RILayer(
            layer_id=layer_id, layer_name="L", layer_type=ContractType.EXCESS_OF_LOSS,
            occurrence_attachment=100_000.0, occurrence_limit=occurrence_limit,
            aggregate_attachment=0.0, aggregate_limit=0.0, subject_lines_of_business=[],
            subject_lob_exposure_amounts=[], full_subject_premium=0.0, written_line=1.0,
            signed_line=1.0, number_of_reinstatements=0, reinstatement_cost={},
        )

    def test_detects_a_changed_layer_field_and_a_changed_result(self):
        from app.db import ModelSnapshot, diff_versions, save_results, save_version

        id_old = save_version(self.path, ModelSnapshot(None, None, None, [self._layer(1, 200_000.0)]), label="old")
        id_new = save_version(self.path, ModelSnapshot(None, None, None, [self._layer(1, 300_000.0)]), label="new")
        save_results(self.path, id_old,
            [{"layer_id": 1, "layer_name": "L", "modelling_year": 2022, "ceded_paid": 0.0,
              "ceded_incurred": 100.0, "claim_count": 1, "earned_premium": 1000.0, "loss_ratio": 0.1}], [])
        save_results(self.path, id_new,
            [{"layer_id": 1, "layer_name": "L", "modelling_year": 2022, "ceded_paid": 0.0,
              "ceded_incurred": 150.0, "claim_count": 1, "earned_premium": 1000.0, "loss_ratio": 0.15}], [])

        diff = diff_versions(self.path, id_old, id_new)

        self.assertIn(
            ("occurrence_limit", 200_000.0, 300_000.0),
            [(c.field, c.old_value, c.new_value) for c in diff.layer_changes],
        )
        self.assertEqual(len(diff.results_changes), 1)
        self.assertEqual(diff.results_changes[0].ceded_incurred_old, 100.0)
        self.assertEqual(diff.results_changes[0].ceded_incurred_new, 150.0)

    def test_no_overlap_returns_empty_diff_lists_not_an_error(self):
        from app.db import ModelSnapshot, diff_versions, save_version

        id_old = save_version(self.path, ModelSnapshot(None, None, None, [self._layer(1, 200_000.0)]), label="old")
        id_new = save_version(self.path, ModelSnapshot(None, None, None, [self._layer(2, 300_000.0)]), label="new")

        diff = diff_versions(self.path, id_old, id_new)

        self.assertEqual(diff.layer_changes, [])
        self.assertEqual(diff.results_changes, [])
        self.assertEqual(diff.claims_count_old, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_db.py::TestDiffVersions -v`
Expected: FAIL — `ImportError: cannot import name 'diff_versions' from 'app.db'`

- [ ] **Step 3: Implement `diff_versions`**

Load both versions via `load_version`. For `layer_changes`: match layers by `layer_id` present in both snapshots' `layers`; for each matched pair, iterate `dataclasses.fields(RILayer)` and emit a `LayerFieldChange` for every field whose old/new values differ. For `claims_count_*`/`claims_total_incurred_*`: `len(snapshot.claims.claims)` and `sum(c.capped_claim_development_history.latest_incurred for c in snapshot.claims.claims)` (0 if `claims is None`); same pattern for exposures using `exposure_value`. For `results_changes`: inner-join the two versions' `by_layer_year` rows on `(layer_id, modelling_year)` (plain Python dict keyed by that tuple), emitting a `ResultsRowDiff` only for pairs present in both.

- [ ] **Step 4: Run tests to verify they pass**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_db.py -v`
Expected: `16 passed`

- [ ] **Step 5: Run the full suite**

Run: `"/c/Program Files/Python312/python.exe" -m pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: `0 failed`, passed count up by 16 from this plan so far (140 baseline + 16 = 156).

- [ ] **Step 6: Commit**

```bash
git add app/db.py tests/test_db.py
git commit -m "feat: add diff_versions"
```

---

### Task 7: Seed `contract_config.py`/`data_loading.py` widgets from `WorkbenchState`

**Files:**
- Modify: `app/pages/contract_config.py`
- Modify: `app/pages/data_loading.py`
- Test: `tests/test_pages_state_seeding.py` (new) — Panel widgets can be constructed and read without a running server (same way `app/service.py`-level tests avoid needing one), so this is a real pytest test, not Playwright-only.

**Interfaces:**
- Consumes: `WorkbenchState` (unchanged signature).
- Produces: no new functions — `build_contract_config_page`/`build_data_loading_page` keep their existing signatures; only their widgets' *initial values* change when `state` already has data.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pages_state_seeding.py
import unittest
from datetime import date

from app.pages.contract_config import LAYER_COLUMNS, build_contract_config_page
from app.pages.data_loading import build_data_loading_page
from app.state import WorkbenchState
from pyre import RIContractMetadata, RILayer
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType


class TestContractConfigSeeding(unittest.TestCase):
    def test_seeds_widgets_from_existing_contract_metadata_and_layers(self):
        metadata = RIContractMetadata(
            contract_id="C-9999", contract_description="Seeded", cedent_name="Acme Re",
            trigger_basis=ClaimTriggerBasis.LOD, indexation_clause=IndexationClauseType.FULL_INDEXATION,
            indexation_margin=0.0, inception_date=date(2024, 1, 1), expiration_date=date(2024, 12, 31),
            fx_rates={"USD": 1.0},
        )
        layer = RILayer(
            layer_id=1, layer_name="Seeded Layer", layer_type=ContractType.EXCESS_OF_LOSS,
            occurrence_attachment=100_000.0, occurrence_limit=200_000.0, aggregate_attachment=0.0,
            aggregate_limit=0.0, subject_lines_of_business=[], subject_lob_exposure_amounts=[],
            full_subject_premium=0.0, written_line=1.0, signed_line=1.0,
            number_of_reinstatements=0, reinstatement_cost={},
        )
        state = WorkbenchState(contract_metadata=metadata, layers=[layer])

        page = build_contract_config_page(state)
        widgets = {w.name: w for row in page if hasattr(row, "__iter__") for w in row if hasattr(w, "name")}

        self.assertEqual(widgets["Contract ID"].value, "C-9999")
        self.assertEqual(widgets["Cedent"].value, "Acme Re")
        layer_table = next(obj for obj in page if getattr(obj, "name", None) == "Layers")
        self.assertEqual(layer_table.value.iloc[0]["layer_name"], "Seeded Layer")

    def test_defaults_unchanged_when_state_is_empty(self):
        page = build_contract_config_page(WorkbenchState())
        widgets = {w.name: w for row in page if hasattr(row, "__iter__") for w in row if hasattr(w, "name")}
        self.assertEqual(widgets["Contract ID"].value, "C-0001")


class TestDataLoadingSeeding(unittest.TestCase):
    def test_status_reflects_preloaded_claims_and_exposures_on_build(self):
        from app.service import parse_claims_csv, parse_exposures_csv
        import io

        state = WorkbenchState(
            claims=parse_claims_csv(io.StringIO(
                "claim_id,currency,contract_limit,loss_date,development_month,cumulative_paid,cumulative_incurred\n"
                "C1,USD,1000000,2022-01-01,12,100,200\n"
            )),
            exposures=parse_exposures_csv(io.StringIO(
                "exposure_id,exposure_name,exposure_period_start,exposure_period_end,currency,exposure_value\n"
                "E1,E1,2022-01-01,2022-12-31,USD,1000000\n"
            )),
        )

        page = build_data_loading_page(state)
        status = next(obj for obj in page if hasattr(obj, "alert_type"))

        self.assertEqual(status.alert_type, "success")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_pages_state_seeding.py -v`
Expected: FAIL on `test_seeds_widgets_from_existing_contract_metadata_and_layers` (widget shows `"C-0001"`, not `"C-9999"`) and on `test_status_reflects_preloaded_claims_and_exposures_on_build` (status is still the hardcoded "No data loaded yet." warning).

- [ ] **Step 3: Seed widget defaults from `state` in `contract_config.py`**

Replace each hardcoded literal default with `state.contract_metadata.<field> if state.contract_metadata else <current literal>` (e.g. `value=state.contract_metadata.contract_id if state.contract_metadata else "C-0001"`), for `contract_id`, `contract_description`, `cedent_name`, `trigger_basis` (`.name`), `indexation_clause` (`.name`), `indexation_margin`, `inception_date`, `expiration_date`. Seed `layer_rows` from `state.layers`:

```python
layer_rows: list[dict] = [
    {col: getattr(layer, col) if col != "layer_type" else layer.layer_type.name for col in LAYER_COLUMNS}
    for layer in state.layers
]
layer_table = pn.widgets.Tabulator(
    pd.DataFrame(layer_rows, columns=LAYER_COLUMNS), ...  # unchanged kwargs
)
```

Also seed `layer_id.value`/`layer_name.value` to continue the sequence (`max(layer.layer_id for layer in state.layers) + 1` if `state.layers` else `1`) so "Add layer" doesn't collide with a loaded layer's id.

- [ ] **Step 4: Call `_refresh_status()` once at build time in `data_loading.py`**

Move the existing `_refresh_status` function definition above the `return pn.Column(...)` (already the case) and call `_refresh_status()` once, unconditionally, right before the `return`, so a pre-populated `state` shows its real status immediately instead of the hardcoded "No data loaded yet." — the function already handles the "nothing loaded" case correctly, so calling it on an empty `state` is a no-op change in behavior for the existing empty-session path.

- [ ] **Step 5: Run tests to verify they pass**

Run: `"/c/Program Files/Python312/python.exe" -m pytest tests/test_pages_state_seeding.py -v`
Expected: `3 passed`

- [ ] **Step 6: Run the full suite**

Run: `"/c/Program Files/Python312/python.exe" -m pytest -q --ignore=tests/test_exposure_curve_fitting.py`
Expected: `0 failed`, `159 passed` (156 after Task 6 + 3 here)

- [ ] **Step 7: Commit**

```bash
git add app/pages/contract_config.py app/pages/data_loading.py tests/test_pages_state_seeding.py
git commit -m "feat: seed contract config and data loading widgets from WorkbenchState"
```

---

### Task 8: Save Version / Recalculate on the results page

**Files:**
- Modify: `app/state.py`
- Modify: `app/pages/results.py`
- Test: manual Playwright (no pytest harness for `app/pages/*.py` — same convention as the report-export work)

**Interfaces:**
- Consumes: Task 2's `save_version`/`save_results`, Task 6's types (none needed here).
- Produces: `WorkbenchState.loaded_version_id: Optional[int] = None` (new field, default `None`).

- [ ] **Step 1: Add `loaded_version_id` to `WorkbenchState`**

```python
loaded_version_id: Optional[int] = None
```

Added alongside the existing fields in `app/state.py`; no other change to that file.

- [ ] **Step 2: Add "Save Version" to `results.py`**

A `pn.widgets.TextInput(name="Version label", value="")` plus a `pn.widgets.Button(name="Save Version", button_type="default")` whose click handler: builds a `ModelSnapshot(claims=state.claims, exposures=state.exposures, contract_metadata=state.contract_metadata, layers=state.layers)` (import `ModelSnapshot` from `app.db`), calls `save_version(DB_PATH, snapshot, label=<label input's value>, parent_id=state.loaded_version_id)`, then — if `state.results is not None` — calls `save_results` with `summarize_by_layer_year`/`summarize_exposures_by_year` applied to the last-run `ExperienceModelData` (reuse `last_run_model_data[0]` if present, else skip saving results for a draft-only save), then sets `state.loaded_version_id` to the new id and updates `status`.

- [ ] **Step 3: Add "Recalculate" to `results.py`**

Visible only when `state.loaded_version_id is not None`. Click handler: rebuilds `ExperienceModelData` from current `state.claims`/`state.exposures`/`state.build_contract()` (same construction `_on_run` already does), re-runs `run_pricing`, refreshes `results_table`/`exposures_table`, and calls `save_results(DB_PATH, state.loaded_version_id, ...)` to overwrite the loaded version's cached rows in place (does not create a new version — that's what Copy, in Task 9's page, is for).

- [ ] **Step 4: Change `_export_results` to branch on whether a cached version is loaded**

If `state.loaded_version_id is not None` and no fresh run has happened this session (`last_run_model_data` is empty), export directly from the cached rows: `load_version(DB_PATH, state.loaded_version_id)`'s two results lists, written via two `write_table` calls with the same headers/sheet names `write_experience_rating_results` uses (`BY_LAYER_YEAR_COLUMNS` from `pyre.io_excel.results_io`), bypassing `ExperienceModelData` entirely. Otherwise (a live run happened this session), keep the existing `write_experience_rating_results(last_run_model_data[0], buffer)` path unchanged.

- [ ] **Step 5: Manual Playwright verification**

Save a version mid-configuration (before any run) and confirm it appears in the database (query `pricing_versions` directly via `sqlite3` in the verification script); run pricing, Save Version again, confirm `pricing_results_by_layer_year` now has rows for that version; confirm Export to Excel on a freshly-loaded version (no live run this session) produces a valid `.xlsx` sourced from cached rows.

- [ ] **Step 6: Commit**

```bash
git add app/state.py app/pages/results.py
git commit -m "feat: add Save Version and Recalculate to the results page"
```

---

### Task 9: "Saved Models" tab — catalog, Load, Copy, Delete, Mark Final

**Files:**
- Create: `app/pages/model_library.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: Task 3's `list_versions`/`set_final`, Task 4's `copy_version`, Task 5's `delete_version`, Task 2's `load_version`.
- Produces: `build_model_library_page(state: WorkbenchState, on_load: Callable[[], None]) -> pn.Column` — `on_load` is called, with no arguments, after a Load action has finished mutating `state`, so the caller (`main.py`) can rebuild the other tabs.

- [ ] **Step 1: Build the catalog table**

A `pn.widgets.Tabulator` (read-only, `disabled=True`) bound to a DataFrame built from `list_versions(DB_PATH)` — columns: `label`, `is_final`, `contract_id`, `cedent_name`, `inception_date`, `expiration_date`, `created_at`. A `pn.pane.Markdown` above it showing the count: `f"{len(summaries)} saved version(s)"`. A `pn.widgets.Select` (options built from the same summaries, `f"{s.id}: {s.label}"`) to pick a version for the row actions below.

- [ ] **Step 2: Add Load / Copy / Delete / Mark Final buttons**

- **Load**: `load_version(DB_PATH, selected_id)`, assign the returned snapshot's fields onto `state` (`state.claims = snapshot.claims`, etc., `state.loaded_version_id = selected_id`), rebuild `results_table`/`exposures_table`-equivalent by setting `state.results = PricingResults(by_layer_year=pd.DataFrame(by_layer_year_rows), exposures_by_year=pd.DataFrame(exposures_by_year_rows))` when rows exist (else `None`), then call `on_load()`.
- **Copy**: `copy_version(DB_PATH, selected_id, new_label=<a text input's value>)`, refresh the catalog table.
- **Delete**: `delete_version(DB_PATH, selected_id)`, refresh the catalog table.
- **Mark Final** (a checkbox or toggle next to the Select): `set_final(DB_PATH, selected_id, <checkbox value>)`, refresh the catalog table.

Each action re-fetches `list_versions(DB_PATH)` and reassigns the Tabulator's `.value` afterward so the catalog stays current.

- [ ] **Step 3: Wire the new tab into `app/main.py`**

```python
def build_app() -> pn.template.BootstrapTemplate:
    state = WorkbenchState()
    init_db(DB_PATH)

    def _build_editable_tabs():
        return [
            ("1. Load data", build_data_loading_page(state)),
            ("2. Configure contract", build_contract_config_page(state)),
            ("3. Run pricing", build_results_page(state)),
        ]

    tabs = pn.Tabs(*_build_editable_tabs())

    def _on_load():
        new_tabs = _build_editable_tabs()
        for i, pair in enumerate(new_tabs):
            tabs[i] = pair

    tabs.append(("4. Saved Models", build_model_library_page(state, on_load=_on_load)))

    return branded_template(tabs)
```

(`init_db`/`DB_PATH` imported from `app.db`.)

- [ ] **Step 4: Manual Playwright verification**

Save a version from the results page (Task 8), switch to "4. Saved Models," confirm it's listed with the right contract details; Load it, confirm tabs 1-3 now show the saved contract/layers/claims-exposures-status; Copy it, confirm a second row appears with a different label; Delete the copy, confirm it disappears; Mark Final, confirm the flag shows in the table.

- [ ] **Step 5: Commit**

```bash
git add app/pages/model_library.py app/main.py
git commit -m "feat: add Saved Models tab (catalog, load, copy, delete, mark final)"
```

---

### Task 10: "Compare" tab

**Files:**
- Create: `app/pages/compare.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: Task 3's `list_versions`, Task 6's `diff_versions`.
- Produces: `build_compare_page(state: WorkbenchState) -> pn.Column`.

- [ ] **Step 1: Build the version picker and diff display**

A `pn.widgets.MultiChoice` (options from `list_versions(DB_PATH)`, same `"{id}: {label}"` labels as Task 9) constrained to exactly two selections for this view (validate in the click handler: if `len(selected) != 2`, show a warning status and return, rather than disabling the widget itself). A "Compare" button whose handler calls `diff_versions(DB_PATH, id_old, id_new)` (older `created_at` of the two selected is `id_old`) and renders:
- a `pn.widgets.Tabulator` of `layer_changes` (columns: `layer_id`, `field`, `old_value`, `new_value`),
- a `pn.widgets.Tabulator` of `results_changes` (columns as the dataclass fields, with an added computed `ceded_incurred_delta = ceded_incurred_new - ceded_incurred_old` column for the "what moved" view the design calls for),
- a `pn.pane.Markdown` summarizing the claims/exposures counts and totals (`f"Claims: {old} -> {new}, total incurred {old_total:,.0f} -> {new_total:,.0f}"`).

- [ ] **Step 2: Wire the new tab into `app/main.py`**

```python
tabs.append(("5. Compare", build_compare_page(state)))
```

Added after Task 9's "4. Saved Models" append, inside `build_app()`.

- [ ] **Step 3: Manual Playwright verification**

With at least two saved versions from earlier verification steps (one with a different layer limit or a different run), select both in "5. Compare," click Compare, confirm the layer-field change and the results delta both render with the expected values.

- [ ] **Step 4: Commit**

```bash
git add app/pages/compare.py app/main.py
git commit -m "feat: add Compare tab for version diffing"
```

---

## Final Verification (after all 10 tasks)

1. `"/c/Program Files/Python312/python.exe" -m pytest -q --ignore=tests/test_exposure_curve_fitting.py` → `0 failed`, `159 passed` (140 baseline + 16 in `test_db.py` + 3 in `test_pages_state_seeding.py`).
2. `ruff check app/` / `ruff format --check app/` clean on every file this plan touched.
3. `mypy app/db.py app/pages/contract_config.py app/pages/data_loading.py app/pages/results.py app/pages/model_library.py app/pages/compare.py app/main.py` clean (pre-existing unrelated repo debt excluded, per the report-export plan's precedent of confirming via `git stash` that any remaining error predates this work).
4. Full manual Playwright walkthrough: save a draft, resume it, copy it with a changed layer, compare the two, mark one final, delete the other, confirm the catalog counts match reality throughout.
5. Update `CLAUDE.md`: add `app/db.py`/`data/workbench.db` to the Panel workbench table, the two new tabs to the module map, and the new test count to Known Test State.
