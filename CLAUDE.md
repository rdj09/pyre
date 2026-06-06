# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**pyRE** (Python Reinsurance) is a comprehensive Python package for non-life reinsurance pricing and analysis. It provides actuarial and statistical tools for analyzing claims data, managing exposures, pricing reinsurance contracts, and monitoring rates.

- **Language & Framework**: Pure Python (3.10+), no external dependencies in core package
- **Build System**: Hatch (with pyproject.toml configuration)
- **Documentation**: MkDocs with Material theme (deployed to GitHub Pages)
- **License**: MIT
- **Current Version**: 0.0.1 (Beta)

## Build & Test Commands

### Testing
```bash
# Run all tests using pytest
pytest

# Run tests for a specific module
pytest tests/test_claims.py
pytest tests/test_treaty.py

# Run a specific test class or function
pytest tests/test_claims.py::TestClaimDevelopmentHistory
pytest tests/test_claims.py::TestClaimDevelopmentHistory::test_latest_paid

# Run tests with verbose output
pytest -v
```

### Type Checking
```bash
# Check type hints across the codebase
hatch run types:check

# Check specific modules
mypy --install-types --non-interactive src/pyre tests
```

### Documentation
```bash
# Install docs dependencies and serve locally
pip install -e ".[docs]"
hatch run docs:serve

# Build documentation
hatch run docs:build

# Deploy documentation to GitHub Pages
hatch run docs:deploy
```

### Installation
```bash
# Install in editable mode (for development)
pip install -e .

# Install with documentation dependencies
pip install -e ".[docs]"
```

## High-Level Architecture

### Module Organization

The codebase is organized into six primary modules under `src/pyre/`:

#### 1. **Claims Module** (src/pyre/claims/)
Manages claim data and claims development analysis.
- `ClaimYearType` (Enum): Defines claim year bases (ACCIDENT_YEAR, UNDERWRITING_YEAR, REPORTED_YEAR)
- `ClaimDevelopmentHistory`: Tracks cumulative/incremental paid and incurred amounts over development months
- `ClaimsMetaData`: Metadata for individual claims (ID, dates, currency, limits, LOB)
- `Claim`: Combines metadata and development history
- `Claims`: Collection of claims with aggregation methods
- `Triangle`: Claims development triangles with curve fitting and age-to-age factor calculations
- `IBNERPatternExtractor`: Extracts IBNER (Incurred But Not Enough Reported) patterns

Key concept: Claims are structured hierarchically with metadata separate from development data, allowing flexible analysis by different year types and development periods.

#### 2. **Exposures Module** (src/pyre/exposures/)
Handles insurance exposure data management.
- `ExposureBasis` (Enum): EARNED or WRITTEN basis
- `ExposureMetaData`: Exposure identification, period, classification, location, peril, occupancy
- `ExposureValues`: Holds premium, limit, and exposure count values
- `Exposure`: Single exposure unit with metadata and values
- `Exposures`: Collection of exposures with aggregation and filtering capabilities

Key concept: Exposures are modeled with a base year derived from the policy inception or period dates, enabling exposure trending and classification.

#### 3. **Treaty Module** (src/pyre/treaty/)
Models reinsurance contracts and layers.
- `ContractType` (Enum): Contract types (QUOTA_SHARE, EXCESS_OF_LOSS, SURPLUS_SHARE, FRANCHISE, etc.)
- `ClaimTriggerBasis` (Enum): Defines how claims attach to contracts (LOD=Accident Year, RAD=Underwriting Year, CMB=Reported Year)
- `RILayer`: Individual reinsurance layer with attachment, limit, reinstatement terms, and participation percentages
- `RIContractMetadata`: Contract-level metadata (inception, effective dates, currency, counterparty)
- `RIContract`: Container holding metadata and multiple layers
- Layer loss functions: `xol_calculation`, `qs_calculation`, `surplus_share_calculation`, `franchise_calculation`, `layer_loss_calculation`

Key concept: Contracts are composed of layers, each with specific limits and attachments. Claims attach based on trigger basis, and losses are calculated through layer-specific loss functions.

#### 4. **Models Module** (src/pyre/Models/)
Contains pricing and rating models organized into submodules:

**Experience Submodule** (Models/Experience/):
- `burn_cost.py`: Burn cost analysis with chainladder, Bornhuetter-Ferguson, Cape Cod, and generalized Cape Cod methods
- `frequency_severity.py`: Frequency and severity distribution modeling
- `curve_fitting.py`: Regression and distribution fitting utilities
- `pareto_rating.py`: Pareto-based rating methods
- `resampling.py`: Simulation and resampling techniques
- `experience_preparer.py`: `ExperienceModelData` class that combines claims, exposures, and contracts with trending

**Exposure Submodule** (Models/Exposure/):
- `exposure_curve_fitting.py`: Curve fitting for exposure data
- `exposure_ILF_fitting.py`: Increased Limit Factor (ILF) fitting
- `exposure_rating_cost.py`: Premium calculations based on exposure characteristics
- `exposure_curve_functions.py` and `exposure_ILF_functions.py`: Supporting functions for curve and ILF models

**Aggregate Features Submodule** (Models/AggregateFeatures/):
- `aggregate_features.py`: Aggregate feature calculations
- `selections.py`: Feature selection and filtering
- `simulation_engine.py`: Simulation and aggregation engine

- `trending.py`: `Trending` class for applying trend factors to claims and exposures to a common base year

Key concept: Models work with `ExperienceModelData` which holds claims, exposures, and a reinsurance contract. Trending is applied consistently across all data before analysis.

#### 5. **Rate Monitoring Module** (src/pyre/rate_monitoring/)
Tools for tracking rate changes and adequacy.
- `rate_adequacy.py`: Assesses if current rates are adequate
- `rate_change.py`: Calculates and tracks rate changes over time

#### 6. **Exceptions Module** (src/pyre/exceptions/)
Custom exception hierarchy:
- `GeneralException`: Base exception with identifier support
- `ExposureException`: For exposure-related errors
- `ClaimsException`: For claims-related errors
- `ContractException`: For contract-related errors

### Data Flow Pattern

The typical workflow follows this pattern:
1. Create `Claim`/`Claims` objects from claims data
2. Create `Exposure`/`Exposures` objects from exposure data
3. Define a `RIContract` with `RILayer`s
4. Combine into `ExperienceModelData` with trending factors
5. Apply model calculations (burn cost, frequency-severity, etc.)
6. Extract results and insights

### Design Patterns

- **Enumerations**: Used extensively for type-safe constants (ClaimYearType, ContractType, ExposureBasis, etc.)
- **Properties**: Extensive use of Python properties for validation and computed values
- **Metadata Separation**: Metadata (metadata classes) is separate from operational data, enabling flexible analysis
- **Collection Classes**: Similar to "List" pattern but with domain-specific methods (Claims, Exposures)
- **Year-Based Organization**: Much of the codebase works with origin years and development periods as nested dictionary structures

## Project Structure

```
pyre/
├── src/pyre/              # Main source code
│   ├── __init__.py
│   ├── __about__.py       # Version info (0.0.1)
│   ├── claims/            # Claims analysis
│   ├── exposures/         # Exposure management
│   ├── Models/            # Pricing models (Experience, Exposure, AggregateFeatures)
│   ├── treaty/            # Reinsurance contracts
│   ├── rate_monitoring/   # Rate tracking and adequacy
│   └── exceptions/        # Custom exceptions
├── tests/                 # Test suite (~2,191 lines of code)
├── docs/                  # MkDocs documentation
│   ├── index.md
│   ├── about.md
│   ├── claims.md
│   ├── exposures.md
│   ├── models.md
│   ├── treaty.md
│   └── rate_monitoring.md
├── pyproject.toml         # Hatch configuration, dependencies, tool configs
├── mkdocs.yml             # MkDocs configuration
├── README.md              # Package overview
└── LICENSE.txt            # MIT License
```

## Key Implementation Details

### Trending and Year-Based Analysis

The `Trending` class is fundamental to the models. It applies year-to-year trend factors to convert data to a common base year. Trend factors are maintained separately for claims and exposures, allowing different inflation assumptions.

### Claims Development

Claims are organized by origin year (accident, underwriting, or reported depending on `ClaimYearType`) and development months. Triangles are stored as nested dictionaries: `{origin_year: {dev_period: value}}`. This structure supports easy extraction of rows (origin years) and columns (development periods) for triangle analysis.

### Contract Layer Application

`RILayer` objects define attachment and limit terms. The `layer_loss_calculation` function applies contract terms to loss amounts, respecting both occurrence and aggregate limits with reinstatement provisions.

### Type Safety

The codebase uses Python's `Enum` classes heavily for type-safe categorizations rather than strings or integers. This prevents errors from typos and provides IDE autocomplete support.

## Important Notes

- **No external dependencies** in the core package (as of v0.0.1)
- **Tests use pytest** (configured in `.vscode/settings.json`)
- **Docstring coverage is extensive** - most classes and methods have detailed docstrings explaining parameters and return values
- **GitHub Pages deployment** of docs is automated through `hatch run docs:deploy`
- **Relative imports within pyre package** ensure modules reference each other correctly
- **Python 3.10+ required** for all features (f-strings, type hints, etc.)

## Git Branches

- **main**: Production/stable branch
- **develop**: Development branch
- **gh-pages**: Documentation hosting
- **refactor/pyre-v1**: Active refactor branch (see below)

## Active Branch: refactor/pyre-v1

**Worktree location:** `C:\Users\rhysj\Documents\Actuarial\PricingToolDev\pyre\.worktrees\refactor`

**Status (as of 2026-04-20):** All implementation complete. 272 tests passing. Branch not yet merged or pushed — being kept as-is for the user to handle later.

**What this branch contains** (all ahead of `main`):
- Full refactor of existing modules (enums centralised, dataclasses, lowercase module names, public API surface via `__init__.py`, PEP 561 `py.typed`)
- Bug fixes across trending, exposures, claims, curve fitting, IBNER, triangle, burn cost, and contract calculations
- **New `pyre.data_injector` subpackage** — a complete, production-ready data injection library

### pyre.data_injector — What was built

Plan file: `docs/superpowers/plans/2026-04-18-data-injector.md` (all 9 tasks complete)

**Files created under `src/pyre/data_injector/`:**

| File | Purpose |
|---|---|
| `__init__.py` | Public API re-exports |
| `exceptions.py` | `InjectionError` |
| `descriptors.py` | `FieldDescriptor` — source key, coercion, defaults, validation, pre-processing |
| `schema.py` | `Schema` — collection of descriptors, auto-derives from dataclasses |
| `injector.py` | `Injector[T]` — flat/nested injection, pre/post hooks, `inject_many` with error aggregation |
| `loader.py` | `Loader[T]` facade — `from_json`, `from_csv`, `from_yaml`, `from_excel`, `from_dict`, `from_one`, `for_class` |
| `registry.py` | `AdapterRegistry` — plugin-style adapter registration/lookup |
| `utils.py` | `unflatten`, `parse_bool`, `parse_list` helpers |
| `adapters/base.py` | `SourceAdapter` `@runtime_checkable` Protocol |
| `adapters/dict_adapter.py` | Pass-through for `list[dict]` |
| `adapters/json_adapter.py` | JSON file/string loading |
| `adapters/csv_adapter.py` | CSV file loading |
| `adapters/yaml_adapter.py` | YAML file loading (optional dep) |
| `adapters/excel_adapter.py` | Excel `.xlsx` loading via openpyxl (optional dep) |

**Tests:** `tests/test_data_injector/` — test_descriptors.py, test_schema.py, test_injector.py, test_adapters.py, test_loader.py, test_registry.py, test_utils.py

**Public API (importable from `pyre.data_injector`):**
```python
from pyre.data_injector import (
    FieldDescriptor, InjectionError, Injector, Loader,
    AdapterRegistry, Schema, parse_bool, parse_list, unflatten
)
```

### Next steps for this branch

When ready to ship:
1. `git push -u origin refactor/pyre-v1`
2. `gh pr create` targeting `main`
3. After merge, remove worktree: `git worktree remove .worktrees/refactor`

## Documentation

Full documentation available at https://rdj09.github.io/pyre/ and locally via `hatch run docs:serve`. The docs include detailed API references, usage examples, and explanations of actuarial methodologies implemented in the package.

