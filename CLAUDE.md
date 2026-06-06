# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project Overview

**pyRE** — Python package for non-life reinsurance pricing and analysis. Pure Python 3.10+, no external runtime dependencies. Build system: Hatch. Docs: MkDocs/Material → GitHub Pages. License: MIT. Version: 0.0.1 (Beta).

## Commands

```bash
pytest                          # run all tests (src-layout: pythonpath=["src"] set in pyproject.toml)
pytest tests/test_claims.py -v  # module-specific
pytest -q --ignore=tests/test_exposure_curve_fitting.py  # skip scipy-dependent test

hatch run types:check           # mypy across src/pyre and tests
ruff check src/pyre/            # lint (E, F, I, N, W, B rules; N999 ignored for Models/)
ruff format src/pyre/           # auto-format

hatch run docs:serve            # local docs at localhost:8000
hatch run docs:deploy           # publish to gh-pages

pip install -e .                # editable install for development
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
| `Models/` | `Experience/`, `Exposure/`, `AggregateFeatures/` submodules + `trending.py` |
| `rate_monitoring/` | Rate adequacy and rate change tracking |
| `exceptions/` | `GeneralException`, `ExposureException`, `ClaimsException`, `ContractException` |

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
│   ├── Models/                # uppercase — non-Pythonic, rename deferred
│   │   ├── Experience/
│   │   ├── Exposure/
│   │   └── AggregateFeatures/
│   ├── rate_monitoring/
│   └── exceptions/
├── tests/                     # unittest.TestCase style; ~84 tests collected
├── docs/                      # MkDocs source
├── pyproject.toml             # Hatch, ruff, mypy, pytest, coverage config
└── mkdocs.yml
```

## Known Test State (develop, as of Pythonic refactor)

**Expected: 22 failed, 62 passed** (when ignoring `test_exposure_curve_fitting.py`).

All 22 failures are **pre-existing** — not caused by the refactor. Do not attempt to fix them without understanding they pre-date the refactor:

| Failure group | Count | Root cause |
|---|---|---|
| `test_trending.py` | 9 | `trending.py` calls `exposure.modelling_year()` as method but it's a `@property`; also mismatched API expectations |
| `test_ibner_pattern_extractor.py` | 4 | `IBNERPatternExtractor` internal API diverged from test expectations |
| `test_claims.py` modelling year | 4 | Test expects years set by a *different* test method (broken test isolation — data in setUp doesn't match expected values) |
| `test_claims.py` + `test_exposures.py` append/len | 2 | Tests expect `append` not to mutate in place (tests written incorrectly) |
| `test_triangles.py` fit_curve | 1 | ZeroDivisionError in curve fitting |
| `test_exposures.py` earned_pct/earned_value | 2 | `exposure_type` defaults to `ExposureBasis.EARNED` so the method returns full value, not prorated |

`tests/test_exposure_curve_fitting.py` causes a **collection error** (requires `scipy`, not installed). Always `--ignore` it or skip it.

**Double-import trap**: `test_claims.py` imports from `src.pyre.claims.claims` (explicit src path) while also importing from `pyre.exceptions.exceptions`. With `pythonpath=["src"]`, both `src.pyre.*` and `pyre.*` are importable and produce distinct module objects. `assertRaises(ClaimsException)` will fail if the exception is raised by a module loaded under the other path.

## Tooling (configured in pyproject.toml)

- **ruff**: `line-length=100`, `target-version=py310`, rules E/F/I/N/W/B, `N999` ignored (for `Models/`)
- **mypy**: non-strict, `python_version=3.10`, `ignore_missing_imports=true`
- **pytest**: `addopts="--tb=short"`, `pythonpath=["src"]`
- **pytest-cov**: `source_pkgs=["pyre","tests"]`, branch coverage

## Git Branches

- **main**: stable/production
- **develop**: active development (12 commits ahead of origin — Pythonic refactor complete)
- **gh-pages**: docs hosting

Active development on `develop`. The `refactor/pyre-v1` branch is abandoned (superseded by refactor applied directly to `develop`). The worktree at `.worktrees/refactor` can be removed: `git worktree remove .worktrees/refactor`

## Important Notes

- `Models/` uses an uppercase directory name — rename to `models/` is a follow-up task (affects all imports and docs).
- `Models/Experience/frequency_severity.py`: class is `SeverityFit` (was `severity_fit`).
- Relative imports within `pyre` package — always use `from ..enums import X` style, not absolute `from pyre.enums import X`, inside `src/pyre/`.
- Full docs: https://rdj09.github.io/pyre/ — `hatch run docs:serve` locally.
