# Project State (Concise)

## Core Architecture

- **pyre** — actuarial reinsurance pricing library; zero external prod deps; mypy strict on `src/pyre/` only; uv package manager
- **data_injector pipeline**: `Loader → Injector → Schema → FieldDescriptor`; `SourceAdapter` protocol + `AdapterRegistry`
- **Nested injection**: `unflatten` pre_hook converts dot-notation CSV columns (`"exposure_meta.exposure_id"`) → nested dicts for `_inject_nested`
- **Domain classes**: `Exposure(exposure_meta, exposure_values)`, `Claim(claims_meta_data, claims_development_history)`, `Triangle(triangle, origin_years, dev_periods)`
- **app/** — Shiny for Python 7-tab actuarial pricing tool; `page_navbar` layout; modular feature pattern; outside `src/pyre/` so not covered by mypy strict

## Recent Changes (feature/shiny-webapp-data-injection — library refactor, 11 tasks)

### New Files
- `src/pyre/data_injector/adapters/db_adapter.py` — `DBAdapter`; SQLite (stdlib) + PostgreSQL (psycopg2)
- `src/pyre/data_injector/domain_schemas/` — exposure, claim, triangle schemas + loader factories
- `app/features/__init__.py` — empty package marker
- `app/features/data_loader_module.py` — `data_loader_ui/server`; `dl_` prefix; writes shared `_claims/_exposures/_triangle`; clears siblings on each load
- `app/features/triangle_module.py` — `triangle_ui/server`; `tri_` prefix; ATA factors + IBNER pattern
- `app/features/contract_module.py` — `contract_ui/server`; `ctr_` prefix; form (1–5 layers) + JSON upload; writes `_contract`
- `app/features/experience_module.py` — `experience_ui/server`; `exp_` prefix; burn cost via `BurnCostModel`; dynamic layer select from `_contract`
- `app/features/exposure_module.py` — `exposure_ui/server`; `expm_` prefix; MBBEFD/MIXED_EXPONENTIAL/RIEBESELL curves; matplotlib bar chart
- `app/features/rate_module.py` — `rate_ui/server`; `rm_` prefix; 4-card adequacy + rate change calculators
- `app/features/simulation_module.py` — `simulation_ui/server`; `sim_` prefix; Monte Carlo DFA; loss distribution histogram
- `app/services/model_service.py` — `ModelService`; stateless facade over pyre model APIs (parsers, contract, experience, burn cost, exposure, IBNER, simulation, results→df)
- `tests/test_app/test_model_service.py` — 8 tests (parsers, contract form+JSON, IBNER extraction)

### Modified Files
- `app/server.py` — shared `_claims/_exposures/_triangle/_contract` reactive values; delegates to all 7 feature servers
- `app/ui.py` — `page_navbar` with 7 `nav_panel` tabs
- `app/services/domain_service.py` — unchanged (existing DomainService)
- `pyproject.toml` — added `matplotlib>=3.5` to webapp dep group; `pythonpath = ["."]` in pytest opts
- `.gitignore` — added `app/features/__pycache__/*`

## Current Interfaces / APIs

### ModelService (app/services/model_service.py)
```python
svc = ModelService()
svc.parse_year_factors("2020:1.0,2021:1.05") -> dict[int, float]
svc.parse_fx_rates("GBP:1.0,USD:1.25") -> dict[str, float]
svc.build_contract(contract_id, ..., layers_data) -> RIContract
svc.build_contract_from_json(json_bytes) -> RIContract
svc.build_experience_data(claims, exposures, contract, exposure_trends, claim_trends) -> ExperienceModelData
svc.run_burn_cost(model_data, layer_id, projection_method, dev_pattern, a_priori) -> dict[int, float]
svc.build_exposure_model(exposures, contract, curve_type_str, curve_params) -> ExposureModel
svc.run_exposure_rate(model, analysis_date) -> dict[int, float]
svc.extract_ibner(triangle) -> dict[int, float | None]
svc.run_simulation(experience_data, assumptions, n_simulations, random_seed, ibner_pattern) -> SimulationResults
svc.simulation_results_to_df(results, contract) -> pd.DataFrame
```

### DomainService (app/services/domain_service.py)
```python
svc.load_exposures(source, source_type, *, query="", sheet_name=0) -> Exposures
svc.load_claims(source, source_type, *, query="", sheet_name=0) -> Claims
svc.build_triangle(source, source_type, value_type="incurred") -> Triangle  # csv only
svc.exposure_summary(exposures) -> dict[str, Any]
svc.claim_summary(claims) -> dict[str, Any]
```
`source_type` values: `"csv"`, `"excel"`, `"json"`, `"yaml"`, `"dict"`, `"db"`

### App startup
```bash
uv run python -m shiny run app.app          # correct — module-path form
# NOT: shiny run app/app.py                 # broken — relative imports fail as __main__
```

## Active Constraints / Assumptions

- mypy strict covers `src/pyre/` only; `app/` excluded
- **Relative imports in app/**: all intra-app imports must use relative form (`from ..services.model_service import ModelService`); absolute imports only for external packages
- `aggregate_limit=0` in layer form → `float("inf")` (unlimited); non-zero value taken as-is
- Triangle IBNER optional for simulation — falls back to `{}` (SeverityFit uses factor 1.0 for all years)
- `ClaimDevelopmentHistory.__post_init__` raises `ValueError` for mismatched list lengths — not caught by `Injector`
- SQLite returns integers `0`/`1` for booleans — handle with `pre_process=lambda v: str(v) if isinstance(v, int) else v`
- Triangle building only supports `source_type="csv"` in `DomainService.build_triangle`
- `pytest pythonpath = ["."]` required for `app` package importable from repo root

## Current Test Status

- 340/340 tests pass (329 baseline + 11 new parametrized parse_bool tests)
- 84.88% coverage (threshold: ≥80%)
- 0 ruff errors, 0 mypy errors

## Refactoring Completed (Tasks 1–11)

| Task | What changed |
|------|-------------|
| T1 | Fixed `risk_premium_extropolate` typo (alias kept); removed unused `attachment`/`x_m` params; fixed `power_ilf` type hint; fixed `"paramaters_mus"` typo |
| T2 | `inverse_power_fit` already canonical in `curve_fitting.py` — no change needed |
| T3 | Replaced `assert` with `raise ValueError` in `Trending`; added `DeprecationWarning` to 4 module-level shims |
| T4 | Moved 4 exception classes into `exceptions/__init__.py`; `exceptions/exceptions.py` → thin re-export |
| T5 | `parse_bool` now case-insensitive (`.strip().lower()`); added parametrized tests |
| T6 | `Loader` now uses `AdapterRegistry.get(source_type)` via `from_source()`; removed 6 hard-coded adapter imports |
| T7 | `quota_share_calculation` added to dispatch dict; `loss_to_layer_fn` simplified; `surplus_share_calculation` kept public |
| T8 | `r_squared` imported from `curve_fitting` in both exposure fitters; 5 inline duplicates removed |
| T9 | Tests reorganized into subdirs mirroring `src/pyre/`; `tests/conftest.py` with 6 shared fixtures |
| T10 | `_VarianceEstimator` extracted from `CredibilityWeight`; `CredibilityConfig` replaces `**kwargs` |
| T11 | `Resampling` accepts `random_seed`; `BurnCostModel` bare `except` narrowed to specific types |

## Backward Compat Aliases Still Active (remove in next major version)

- `risk_premium_extropolate` → alias for `risk_premium_extrapolate`
- `pyre.exceptions.exceptions` → re-exports from `pyre.exceptions`
- Module-level `calculate_trend_factor`, `trend_exposures`, `trend_claims`, `get_trend_factors` → DeprecationWarning shims

## Next Steps

- Create PR: `feature/shiny-webapp-data-injection` → `main`
- Optional: add Excel/YAML/JSON round-trip tests for domain schemas
- Optional: extend `DomainService.build_triangle` to support `source_type="excel"`
