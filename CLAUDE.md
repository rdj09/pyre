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
| `app/state.py` | Panel-free shared state (`WorkbenchState`) holding the current contract/layers/claims/exposures/results. |
| `app/pages/` | Panel UI pages: `contract_config.py`, `data_loading.py`, `results.py`. Only these and `app/main.py` import `panel`. |
| `app/main.py` | Entrypoint (`panel serve app/main.py`). Deliberately **not** named `app.py` — Bokeh's script loader would register the running script as a module named `app`, colliding with and shadowing the `app` package itself. |
| `app/theme.py` | Freyja Consulting branding (Panel-only — `FreyjaDesign`, header/footer, favicon, dark-mode toggle). Colours/type come only from `app/assets/freyja.css`. |
| `app/assets/` | Brand assets: `brand/*.svg` (wordmark, favicon — text pre-converted to outlines), `fonts/*.woff2` (self-hosted Montserrat subset + `OFL.txt`), `freyja.css` (per-component shadow-DOM stylesheet, light + derived dark palette via `:host-context(.freyja-dark)`), `freyja-page.css` (document-level `raw_css`, incl. `@font-face`), `theme-init.js` (dark-mode toggle logic — loaded via `pn.config.js_files`, **not** inlined in an HTML pane, since Panel renders pane content via `innerHTML` and browsers don't execute `<script>` tags inserted that way). Regenerate the brand assets via `hatch run brand:build` (see Commands) — SVG output is deterministic, woff2 is not (subsetting order), so only the SVGs are diffed to confirm a clean rebuild. |
| `run_app.py` | Top-level launcher (`python run_app.py`); serves `app/assets/` at `./assets`. |
| `scripts/build_brand_assets.py` | Regenerates `app/assets/` from the Freyja brand guide. Run via `hatch run brand:build`. |
| `examples/panel_demo/` | Bundled demo CSVs loaded by the "Load demo data" button. |

v1 scope is a single-contract pricing workbench (not a general data explorer or
rate-monitoring dashboard). `SURPLUS_SHARE` layers are intentionally excluded
from the layer-type selector — `RILayer.loss_to_layer_fn` raises
`NotImplementedError` for that type (no `sum_insured` concept modelled yet).

### Key design patterns (post-refactor, develop branch)

**`@dataclass` for data-holding classes.** `ClaimDevelopmentHistory`, `ClaimsMetaData`, `ExposureMetaData`, `ExposureValues`, `RILayer`, `RIContractMetadata` are `@dataclass`. Follow this pattern for new data classes.
- Required fields first (no default), optional fields after.
- Cross-field validation in `__post_init__`.
- Post-construction mutation validation via `__setattr__` override where needed (e.g., `ExposureMetaData` date ordering, `ExposureValues` non-negative check).
- Computed read-only values stay as `@property` (never removed by dataclass conversion).
- **Exception**: `ClaimDevelopmentHistory` validates list lengths lazily (only in `cumulative_reserved_amount`) — do not add construction-time validation.

**Centralized enums.** All enums live in `src/pyre/enums.py`. Never define enums in domain modules — always `from pyre.enums import X`.

**`ItemContainer[T]`.** `Claims` and `Exposures` inherit from `ItemContainer`. Both take a `list[T]` in `__init__` and expose a domain alias property (`claims`, `exposures`) with a setter. Domain-specific properties (`modelling_years`, `currencies`, `exposure_ids`, etc.) live on the subclass, not the base.

**Public API.** `from pyre import Claims` works. All public names are re-exported from `src/pyre/__init__.py` via subpackage `__init__.py` files. Add new public classes there when creating them.

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
├── tests/                     # unittest.TestCase style; 131 tests collected
├── docs/                      # MkDocs source
├── pyproject.toml             # Hatch, ruff, mypy, pytest, coverage config
└── mkdocs.yml
```

## Known Test State (develop)

**Expected: 0 failed, 131 passed** (when ignoring `test_exposure_curve_fitting.py`,
**with the `excel` extra installed** — `pip install -e ".[excel]"`, or via
`hatch run pytest`, since `openpyxl` is listed in `[tool.hatch.envs.default]`).
Without `openpyxl` installed, `tests/test_io_excel.py`'s 25 tests skip
cleanly instead of failing (106 passed, 25 skipped).

All previously-documented pre-existing bugs have now been fixed, each with
its own regression test — notably `Trending.calculate_trend_factor`'s
directionality (`tests/test_trending.py`), a full rewrite of
`IBNERPatternExtractor` to match its intended API
(`tests/test_ibner_pattern_extractor.py`), `_earned_pct`'s missing
lower-bound clamp and `earned_exposure_value`'s proration
(`tests/test_exposures.py`), and a day-count convention fix (actual/actual,
not 30/360). Fixing `earned_exposure_value` also surfaced and fixed a
previously-masked bug in `aggregate_exposures`
(`experience_preparer.py`) — it used the contract's inception date as a
shared `analysis_date` for every exposure regardless of modelling year;
each exposure now uses its own period end. No pre-existing failures remain.

`tests/test_exposure_curve_fitting.py` causes a **collection error** (requires `scipy`, not installed). Always `--ignore` it or skip it.

**Double-import trap**: `test_claims.py` imports from `src.pyre.claims.claims` (explicit src path) while also importing from `pyre.exceptions.exceptions`. With `pythonpath=["src"]`, both `src.pyre.*` and `pyre.*` are importable and produce distinct module objects. `assertRaises(ClaimsException)` will fail if the exception is raised by a module loaded under the other path.

## Tooling (configured in pyproject.toml)

- **ruff**: `line-length=100`, `target-version=py310`, rules E/F/I/N/W/B, `N999` ignored (needed for `exposure_ILF_fitting.py`/`exposure_ILF_functions.py` — uppercase "ILF" in the filename)
- **mypy**: non-strict, `python_version=3.10`, `ignore_missing_imports=true`
- **pytest**: `addopts="--tb=short"`, `pythonpath=["src", "."]` (the `.` lets tests import the top-level `app/` package)
- **pytest-cov**: `source_pkgs=["pyre","tests"]`, branch coverage

## Git Branches

- **main**: stable/production — kept in sync with `develop` (fast-forward only)
- **develop**: active development — both branches pushed and in sync with `origin`
- **gh-pages**: docs hosting, deployed via `hatch run docs:deploy` (see Commands)

No other local branches or worktrees exist — the former `.worktrees/refactor`
worktree and its `feature/shiny-webapp-data-injection`/`refactor/pyre-v1`
branches (both already fully-merged ancestors of `develop`) have been removed.

## Important Notes

- `models/Experience/frequency_severity.py`: class is `SeverityFit` (was `severity_fit`).
- Relative imports within `pyre` package — always use `from ..enums import X` style, not absolute `from pyre.enums import X`, inside `src/pyre/`.
- Full docs: https://rdj09.github.io/pyre/ — `hatch run docs:serve` locally. The MkDocs site is Freyja-branded too (custom palette via `docs/stylesheets/freyja-docs.css`, logo/favicon/fonts in `docs/assets/`, kept in sync with `app/assets/` by `scripts/build_brand_assets.py`).
