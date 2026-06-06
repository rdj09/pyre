# Project State (Concise)

## Core Architecture

- **pyre** — actuarial reinsurance pricing library; zero external prod deps; mypy strict on `src/pyre/` only; uv package manager
- **data_injector pipeline**: `Loader → Injector → Schema → FieldDescriptor`; `SourceAdapter` protocol + `AdapterRegistry`
- **Nested injection**: `unflatten` pre_hook converts dot-notation CSV columns (`"exposure_meta.exposure_id"`) → nested dicts for `_inject_nested`
- **Domain classes**: `Exposure(exposure_meta, exposure_values)`, `Claim(claims_meta_data, claims_development_history)`, `Triangle(triangle, origin_years, dev_periods)`
- **app/** — Shiny for Python 7-tab actuarial pricing tool; `page_navbar` layout; modular feature pattern; outside `src/pyre/` so not covered by mypy strict

## Completed Work (feature/shiny-webapp-data-injection)

### app/ File Map

| File | Responsibility |
|------|---------------|
| `app/db/__init__.py` | Package marker |
| `app/db/database.py` | `init_db(db_path)` — `CREATE TABLE IF NOT EXISTS` for `exposures` + `claims` |
| `app/services/storage_service.py` | `StorageService` — serialize domain objects → SQLite rows; `list_stored` |
| `app/services/domain_service.py` | `DomainService` — stateless facade; file/DB → domain objects |
| `app/services/model_service.py` | `ModelService` — stateless facade over pyre model APIs |
| `app/features/data_loader_module.py` | `dl_` prefix; file/DB upload → domain objects; Save to DB; Database viewer tab; startup modal to load all DB data |
| `app/features/triangle_module.py` | `tri_` prefix; ATA factors + IBNER pattern |
| `app/features/contract_module.py` | `ctr_` prefix; form (1–5 layers) + JSON upload; writes `_contract` |
| `app/features/experience_module.py` | `exp_` prefix; burn cost via `BurnCostModel`; dynamic layer select from `_contract` |
| `app/features/exposure_module.py` | `expm_` prefix; MBBEFD/MIXED_EXPONENTIAL/RIEBESELL curves; matplotlib bar chart |
| `app/features/rate_module.py` | `rm_` prefix; 4-card adequacy + rate change calculators |
| `app/features/simulation_module.py` | `sim_` prefix; Monte Carlo DFA; loss distribution histogram |
| `app/server.py` | Shared `_claims/_exposures/_triangle/_contract` reactive values; delegates to all feature servers |
| `app/ui.py` | `page_navbar` with 7 `nav_panel` tabs |
| `run_app.py` | Repo-root launcher; `shiny.run_app("app.app:app")`; avoids `__main__` import breakage |

### src/pyre/ Notable Additions

- `src/pyre/data_injector/adapters/db_adapter.py` — `DBAdapter`; SQLite (stdlib) + PostgreSQL (psycopg2)
- `src/pyre/data_injector/domain_schemas/` — exposure, claim, triangle schemas + loader factories (`exposures_loader`, `claims_loader`, `exposures_db_loader`, `claims_db_loader`, `triangle_loader`)

### SQLite Backend (completed 2026-06-02)

**Design:** explicit Save button; user-specified DB path (`./pyre_data.db` default); upsert semantics (`INSERT OR REPLACE`); Triangle rebuilt from stored claims via `Triangle.from_claims()` — not stored directly.

**Column naming:** underscore-namespaced (`exposure_meta_exposure_id`) to match `_underscore_to_dotted_exposure`/`_underscore_to_dotted_claim` pre-hooks in `pyre` library — no library changes needed.

**Key behaviours:**
- `list_stored()` checks `Path(db_path).exists()` — returns `[]` for non-existent file; does NOT call `init_db` (navigating to Database tab won't create an empty file)
- `_claim_to_row` uses `uncapped_claim_development_history` so `contract_limit` doesn't corrupt stored values
- Dev history stored as pipe-separated strings (`"12|24|36"`); `_parse_int_list`/`_parse_float_list` in claim schemas handle round-trip
- `build_triangle(source_type="db")` receives plain file path, constructs `sqlite:///` internally, loads via `claims_db_loader().from_db()`
- **Startup modal (2026-06-02)**: `_check_db_on_startup` runs once at session init (all reads wrapped in `reactive.isolate()` → no reactive deps → fires once). If DB has records, shows modal: "Load All" (`dl_modal_load_btn`) → `_on_modal_load` populates `_exposures`, `_claims`, `_triangle`; "Skip" dismisses.
- **Wipe-bug fixed**: `_on_load()` no longer blanket-clears all three reactive values on each load. Each branch only sets its own value — loading Claims leaves Exposures intact and vice versa.

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
svc.build_triangle(source, source_type, value_type="incurred") -> Triangle  # csv | db
svc.exposure_summary(exposures) -> dict[str, Any]
svc.claim_summary(claims) -> dict[str, Any]
```
`source_type` for load_exposures/load_claims: `"csv"`, `"excel"`, `"json"`, `"yaml"`, `"dict"`, `"db"`
`source_type` for build_triangle: `"csv"` (file path) | `"db"` (SQLite file path, no `sqlite:///` prefix)

### StorageService (app/services/storage_service.py)
```python
svc = StorageService()
svc.save_exposures(exposures: list[Exposure], db_path: str) -> None   # noop if empty
svc.save_claims(claims: list[Claim], db_path: str) -> None             # noop if empty
svc.list_stored(db_path: str, table: Literal["exposures","claims"]) -> list[str]  # returns PKs; [] if file missing
```

### database module (app/db/database.py)
```python
init_db(db_path: str) -> None  # CREATE TABLE IF NOT EXISTS; idempotent
```
Tables: `exposures` (PK: `exposure_meta_exposure_id`) · `claims` (PK: `claims_meta_data_claim_id`)

### App startup

```powershell
uv sync --group webapp   # install deps (always use --group webapp, never plain uv sync)
uv run python run_app.py # launch; browser: http://127.0.0.1:8000
```

> **Do NOT use** `shiny run app/app.py` — file-path form sets `__main__` and breaks relative imports.

## Active Constraints / Assumptions

- mypy strict covers `src/pyre/` only; `app/` excluded
- **Relative imports in app/**: all intra-app imports must use relative form (`from ..services.model_service import ModelService`); absolute imports only for external packages
- `aggregate_limit=0` in layer form → `float("inf")` (unlimited); non-zero value taken as-is
- Triangle IBNER optional for simulation — falls back to `{}` (SeverityFit uses factor 1.0 for all years)
- `ClaimDevelopmentHistory.__post_init__` raises `ValueError` for mismatched list lengths — not caught by `Injector`
- SQLite returns integers `0`/`1` for booleans — `claims_db_loader` / `exposures_db_loader` handle via `pre_process=lambda v: str(v) if isinstance(v, int) else v` in field descriptors
- `build_triangle(source_type="db")` takes a plain file path (no `sqlite:///` prefix); the method constructs the connection string internally
- `pytest pythonpath = ["."]` required for `app` package importable from repo root
- **No new external deps** — SQLite backend uses stdlib `sqlite3` only

## Current Test Status

- 366/366 tests pass (340 prior + 26 new: 24 storage_service + 2 domain_service triangle tests)
- Coverage ≥84.88% (threshold: ≥80%)
- 0 ruff errors, 0 mypy errors

## Refactoring & Feature History

| Area | What changed |
|------|-------------|
| pyre lib T1–T11 | Typo fixes; `parse_bool` case-insensitive; `Loader` uses `AdapterRegistry`; `quota_share_calculation` dispatched; `r_squared` de-duped; tests into subdirs; `_VarianceEstimator` extracted; `Resampling` random_seed; `BurnCostModel` bare-except narrowed |
| Shiny webapp | 7-tab `page_navbar` app; `data_loader`, `triangle`, `contract`, `experience`, `exposure`, `rate`, `simulation` feature modules; `ModelService` + `DomainService` service layer |
| SQLite backend | `app/db/database.py` DDL; `StorageService` serialise/upsert/list; `DomainService.build_triangle` extended to `source_type="db"`; Data Loader Save button + Database viewer tab |
| DB-aware reactive state | `_on_load()` wipe bug fixed (no longer clears all reactive values); `_check_db_on_startup` session-once effect; startup modal (Load All / Skip) populates `_exposures`, `_claims`, `_triangle` from DB |
| Demo data | `examples/webapp_demo/exposures.csv` (6 rows) + `claims.csv` (12 claims) + walk-through README |

## Demo Data (completed 2026-06-02)

`examples/webapp_demo/` — end-to-end demo dataset for the Shiny app:

| File | Contents |
|------|----------|
| `exposures.csv` | 6 rows, 2019–2024, UK Property GWP (£45k–£55k), attachment 2,000 / limit 3,000 |
| `claims.csv` | 12 claims, accident years 2019–2024, dev periods 12–72 months, pipe-separated lists |
| `README.md` | Tab-by-tab walk-through with exact UI field values for all 7 tabs |

**Key facts:** values in £000s; `contract_limit=15000` on all claims; `claims.csv` doubles as Triangle source; matching contract: Layer 1 XL 3,000 xs 2,000 / Layer 2 XL 5,000 xs 5,000.

## CSV Column Format Reference (dot-notation)

**Exposures:** `exposure_meta.{exposure_id, exposure_name, exposure_period_start, exposure_period_end, currency, aggregate, line_of_business, exposure_type, location, peril}` + `exposure_values.{exposure_value, attachment_point, limit}`

**Claims:** `claims_meta_data.{claim_id, currency, loss_date, policy_inception_date, report_date, contract_limit, contract_deductible, claim_in_xs_of_deductible, claim_year_basis, line_of_business, status}` + `claims_development_history.{development_months, cumulative_dev_paid, cumulative_dev_incurred}` (pipe-separated integers/floats)

**Triangle:** Same CSV format as Claims — `DomainService.build_triangle` calls `triangle_loader` which aggregates claims by origin year and dev period. No separate triangle CSV format; `source_type` is `"csv"` (file path) or `"db"` (SQLite file path).

## Next Steps

- **Create PR**: `feature/shiny-webapp-data-injection` → `main` (all work complete; 366/366 tests pass; DB-aware reactive state done)
- Optional: add Excel/YAML/JSON round-trip tests for domain schemas
- Optional: extend `DomainService.build_triangle` to support `source_type="excel"`

**CRITICAL — webapp deps**: Always use `uv sync --group webapp` (not plain `uv sync`). Plain `uv sync` drops the webapp optional group (shiny, pandas, matplotlib, etc.).
