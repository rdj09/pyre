# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project Overview

**pyRE** — Python package for non-life reinsurance pricing and analysis. Pure Python 3.10+, no external runtime dependencies. Build system: Hatch. Docs: MkDocs/Material → GitHub Pages. License: MIT. Version: 0.0.1 (Beta).

## Commands

```bash
pytest                          # run all tests (src-layout: pythonpath=["src", "."] set in pyproject.toml)
pytest tests/test_claims.py -v  # module-specific
pytest -q --ignore=tests/test_exposure_curve_fitting.py  # skip scipy-dependent test

hatch run types:check           # mypy across src/pyre and tests
ruff check src/pyre/            # lint (E, F, I, N, W, B rules; N999 ignored for exposure_ILF_* filenames)
ruff format src/pyre/           # auto-format

hatch run docs:serve            # local docs at localhost:8000
hatch run docs:deploy           # publish to gh-pages

hatch run brand:build           # regenerate app/assets/ AND docs/assets/ (Freyja wordmark, favicon, Montserrat woff2)

pip install -e .                # editable install for development
pip install -e ".[panel]"       # install with the Panel treaty pricing workbench's deps
pip install -e ".[excel]"       # install with headless Excel (.xlsx) read/write support
pip install -e ".[curve-fitting]" # install with curve-fitting deps (numpy/scipy/pandas/matplotlib)
pip install -e ".[panel,excel]" # same, plus the workbench's "Export to Excel" button
hatch run panel:serve           # serve app/main.py at localhost (panel serve, --show --autoreload)
```

## Architecture

### Module map (`src/pyre/`)

| Path | Purpose |
|------|---------|
| `enums.py` | **Single home for all enums** — `ClaimYearType`, `ExposureBasis`, `ClaimTriggerBasis`, `IndexationClauseType`, `ContractType`, `SeverityDistribution`, `FrequencyDistribution` |
| `_container.py` | Generic `ItemContainer[T]` base — provides `append`, `__iter__`, `__len__`, `__getitem__` (slice returns typed subclass), `__repr__` |
| `claims/` | `Claim`, `ClaimDevelopmentHistory`, `ClaimsMetaData`, `Claims`, `Triangle`, `IBNERPatternExtractor` |
| `exposures/` | `Exposure`, `ExposureMetaData`, `ExposureValues`, `Exposures` |
| `treaty/` | `RILayer`, `RIContractMetadata`, `RIContract`, layer loss functions |
| `models/` | `Experience/`, `Exposure/`, `AggregateFeatures/` submodules + `trending.py` |
| `io_excel/` | Headless `.xlsx` read/write (`read_claims`, `read_exposures`, `write_triangle`, `write_experience_rating_results`, `write_exposure_rating_results`) — optional, requires `pip install -e ".[excel]"` |
| `rate_monitoring/` | Rate adequacy and rate change tracking |
| `exceptions/` | `GeneralException`, `ExposureException`, `ClaimsException`, `ContractException` |

### Panel treaty pricing workbench (`app/`, top-level — not under `src/pyre/`)

A Panel (HoloViz) dashboard, kept **outside** `src/pyre/` so the core package
stays dependency-free. Install/run via the `panel` optional extra (see
Commands above). Layout:

| Path | Purpose |
|------|---------|
| `app/service.py` | Pure-Python core (no `import panel`) — CSV parsing into `Claims`/`Exposures`, form-dict → `RIContractMetadata`/`RILayer`, `run_pricing()` → `PricingResults` (pandas DataFrames). Unit-tested in `tests/test_app_service.py` without a running server. |
| `app/state.py` | Panel-free shared state (`WorkbenchState`) holding the current contract/layers/claims/exposures/results, plus `loaded_version_id` (the saved version currently loaded, if any). |
| `app/db.py` | SQLite model-versioning repository (stdlib `sqlite3` + `pickle`, no new deps) — `save_version`/`load_version`/`list_versions`/`copy_version`/`delete_version`/`set_final`/`diff_versions`. Relational tables for version/lineage metadata and cached per-layer-year/exposure results; full input object graph (claims/exposures/contract+layers) pickled into `inputs_blob`. `IncompatibleSnapshotError` on a pyre-version mismatch when unpickling. DB file: `data/workbench.db` (gitignored, created on first run via `init_db`). Unit-tested in `tests/test_db.py`. |
| `app/pages/` | Panel UI pages: `contract_config.py`, `data_loading.py` (both seed their widgets from `WorkbenchState` if already populated, e.g. after loading a saved version), `results.py` (Run/Save Version/Recalculate + "Export to Excel" via `pyre.io_excel.write_experience_rating_results` into an in-memory buffer — needs the `excel` extra), `model_library.py` ("Saved Models" tab — catalog/Load/Copy/Delete/Mark Final), `compare.py` ("Compare" tab — pick two saved versions, view `diff_versions`). Only these and `app/main.py` import `panel`. |
| `app/main.py` | Entrypoint (`panel serve app/main.py`). **Not** `app.py` — Bokeh's script loader would register it as module `app`, shadowing the `app` package. |
| `app/theme.py` | Freyja branding (Panel-only — design, header/footer, favicon, dark-mode toggle). Colours/type only from `app/assets/freyja.css`. |
| `app/assets/` | Brand SVGs/woff2, `freyja.css` (light + dark palette via `:host-context(.freyja-dark)`), `freyja-page.css` (document-level CSS), `theme-init.js` (dark-mode toggle — loaded via `pn.config.js_files`, **not** inlined in an HTML pane: Panel renders panes via `innerHTML`, which never executes `<script>` tags). Regenerate via `hatch run brand:build`; only the SVGs are diffed (woff2 subsetting order isn't deterministic). |
| `run_app.py` | Top-level launcher (`python run_app.py`); serves `app/assets/` at `./assets`. |
| `scripts/build_brand_assets.py` | Regenerates `app/assets/` from the Freyja brand guide. Run via `hatch run brand:build`. |
| `examples/panel_demo/` | Bundled demo CSVs loaded by the "Load demo data" button. |

v1 scope is a single-contract pricing workbench (not a general data explorer or
rate-monitoring dashboard). `RILayer.loss_to_layer_fn` now supports
`SURPLUS_SHARE` (requires `RILayer.sum_insured` to be set; raises `ValueError`
otherwise) but the layer type is still excluded from the Panel layer-type
selector pending UI re-enablement.

### Key design patterns (post-refactor, develop branch)

**`@dataclass` for data-holding classes** (`ClaimDevelopmentHistory`, `ClaimsMetaData`, `ExposureMetaData`, `ExposureValues`, `RILayer`, `RIContractMetadata`). Required fields before optional; cross-field validation in `__post_init__`; mutation validation via `__setattr__` where needed (e.g. date ordering, non-negative checks); computed values stay `@property`. Exception: `ClaimDevelopmentHistory` validates list lengths lazily, only in `cumulative_reserved_amount` — no construction-time check.

**Centralized enums** — all in `src/pyre/enums.py`, never in domain modules: `from pyre.enums import X`.

**`ItemContainer[T]`** — base for `Claims`/`Exposures`; both take `list[T]`, expose a domain alias property with setter; domain-specific properties (`modelling_years`, etc.) live on the subclass.

**Public API** — `from pyre import Claims` works; names are re-exported from `src/pyre/__init__.py` via subpackage `__init__.py`. Add new public classes there.

### Data flow

```
Claims + Exposures + RIContract → ExperienceModelData (with Trending) → Model calculations
```

Triangles: `{origin_year: {dev_period: value}}` nested dicts. Claims organised by `ClaimYearType`.

## Project Structure

```
pyre/
├── src/pyre/
│   ├── __init__.py            # public API surface (from pyre import ...)
│   ├── __about__.py           # version = "0.0.1"
│   ├── enums.py               # ALL enums live here
│   ├── _container.py          # ItemContainer[T] generic base
│   ├── claims/
│   ├── exposures/
│   ├── treaty/
│   ├── models/
│   │   ├── Experience/
│   │   ├── Exposure/
│   │   └── AggregateFeatures/
│   ├── io_excel/               # optional, requires pip install -e ".[excel]"
│   ├── rate_monitoring/
│   └── exceptions/
├── tests/                     # unittest.TestCase style; 194 tests collected (193 pass, 1 skipped without the curve-fitting extra)
├── docs/                      # MkDocs source
├── pyproject.toml             # Hatch, ruff, mypy, pytest, coverage config
└── mkdocs.yml
```

## Known Test State (feature/complete-pyre-actuarial-todos)

**Expected: 0 failed, 193 passed** for
`pytest -q --ignore=tests/test_exposure_curve_fitting.py` (confirmed this
session; **with the `excel` extra installed** — `openpyxl` is present in
this environment). No known pre-existing failures remain — if `pytest` is
red on this branch, it's new.

(Note: this branch forked from `develop` before the model-versioning-backend
work that produced the "162 passed" / "140 tests collected" figures seen on
other branches/docs revisions — those numbers do not apply here.)

`test_exposure_curve_fitting.py` reports **1 skipped** (not a collection
error) without the `curve-fitting` extra (`numpy`/`scipy`/`pandas`/
`matplotlib` not installed in this environment) — confirmed this session
via `pytest tests/test_exposure_curve_fitting.py -v`. Install the
`curve-fitting` extra (see Commands above) to run it for real; always
`--ignore` or skip it otherwise.

**Double-import trap**: some tests import via `src.pyre.*` instead of
`pyre.*`. Under `pythonpath=["src", "."]` both resolve to distinct module
objects, so `assertRaises(SomeException)` can fail if the exception was
raised under the other import path. Write new code/tests against `pyre.*`.

## Tooling (configured in pyproject.toml)

- **ruff**: `line-length=100`, `target-version=py310`, rules E/F/I/N/W/B, `N999` ignored (needed for `exposure_ILF_fitting.py`/`exposure_ILF_functions.py` — uppercase "ILF" in the filename)
- **mypy**: non-strict, `python_version=3.10`, `ignore_missing_imports=true`
- **pytest**: `addopts="--tb=short"`, `pythonpath=["src", "."]` (the `.` lets tests import the top-level `app/` package)
- **pytest-cov**: `source_pkgs=["pyre","tests"]`, branch coverage

## Git Branches

- **main**: stable/production — fast-forward only from `develop`
- **develop**: active development
- **gh-pages**: docs hosting, deployed via `hatch run docs:deploy`

## Important Notes

- `models/Experience/frequency_severity.py`: class is `SeverityFit` (was `severity_fit`).
- Relative imports within `pyre` package — always use `from ..enums import X` style, not absolute `from pyre.enums import X`, inside `src/pyre/`.
- Full docs: https://rdj09.github.io/pyre/ — `hatch run docs:serve` locally. The MkDocs site is Freyja-branded too (custom palette via `docs/stylesheets/freyja-docs.css`, logo/favicon/fonts in `docs/assets/`, kept in sync with `app/assets/` by `scripts/build_brand_assets.py`).
