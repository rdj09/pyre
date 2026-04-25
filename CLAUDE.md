# Project State (Concise)

## Core Architecture

- **pyre** — actuarial reinsurance pricing library; zero external prod deps; mypy strict on `src/pyre/` only; uv package manager
- **data_injector pipeline**: `Loader → Injector → Schema → FieldDescriptor`; `SourceAdapter` protocol + `AdapterRegistry`
- **Nested injection**: `unflatten` pre_hook converts dot-notation CSV columns (`"exposure_meta.exposure_id"`) → nested dicts for `_inject_nested`
- **Domain classes**: `Exposure(exposure_meta, exposure_values)`, `Claim(claims_meta_data, claims_development_history)`, `Triangle(triangle, origin_years, dev_periods)`
- **app/** — Shiny for Python web app; outside `src/pyre/` so not covered by mypy strict

## Recent Changes (feature/shiny-webapp-data-injection)

### New Files
- `src/pyre/data_injector/adapters/db_adapter.py` — `DBAdapter`; SQLite (stdlib) + PostgreSQL (psycopg2); registered as `"db"` in `AdapterRegistry`
- `src/pyre/data_injector/domain_schemas/__init__.py` — re-exports all schema objects and loader factories
- `src/pyre/data_injector/domain_schemas/exposure_schemas.py` — `exposure_meta_schema`, `exposure_values_schema`, `exposure_schema`, `exposures_loader()`, `exposures_db_loader()`
- `src/pyre/data_injector/domain_schemas/claim_schemas.py` — `claims_meta_schema`, `claim_dev_history_schema`, `claim_schema`, `claims_loader()`, `claims_db_loader()`; pipe-separated list coercion (`"12|24|36"`)
- `src/pyre/data_injector/domain_schemas/triangle_schemas.py` — `triangle_loader(source, value_type)` (claims CSV → Triangle), `triangle_from_csv(source)` (wide-format)
- `app/__init__.py`, `app/app.py`, `app/ui.py`, `app/server.py` — Shiny app; **use relative imports**; start with `uv run python -m shiny run app.app`
- `app/services/__init__.py`, `app/services/domain_service.py` — stateless `DomainService` facade over domain schema loaders

### Modified Files
- `src/pyre/data_injector/__init__.py` — added `DBAdapter` export (populates registry on import)
- `src/pyre/data_injector/loader.py` — added `from_db(connection_string, query)` method; fixed `from_json` type args (`dict[str, Any] | list[Any]`)
- `src/pyre/data_injector/injector.py` — renamed loop vars: `pre_hook` (pre_hooks loop), `post_hook` (post_hooks loop) to fix mypy type collision
- `src/pyre/data_injector/schema.py` — removed 3 stale `# type: ignore` comments
- `src/pyre/data_injector/adapters/dict_adapter.py` — wrapped `vars(obj)` in `dict(...)` to satisfy mypy strict
- `pyproject.toml` — added `[dependency-groups]` and `[project.optional-dependencies]` for webapp/excel/db-postgres/yaml; added `pythonpath = ["."]` to `[tool.pytest.ini_options]`; extended `ignore_missing_imports` override to include `yaml.*`, `openpyxl.*`, `psycopg2.*`
- `.gitignore` — added `app/__pycache__/*`, `app/services/__pycache__/*`, `tests/test_app/__pycache__/*`

### New Tests
- `tests/test_data_injector/test_db_adapter.py` — 8 tests
- `tests/test_data_injector/test_domain_schemas/test_exposure_schemas.py`
- `tests/test_data_injector/test_domain_schemas/test_claim_schemas.py`
- `tests/test_data_injector/test_domain_schemas/test_triangle_schemas.py`
- `tests/test_app/test_domain_service.py` — 8 tests
- `tests/test_app/test_app_structure.py` — 5 smoke tests (use `pytest.importorskip` for shiny/pandas)

## Current Interfaces / APIs

### DBAdapter
```python
DBAdapter("sqlite:///path.db").load("SELECT * FROM t")  # → list[dict[str, Any]]
DBAdapter("postgresql://user:pass@host/db").load("SELECT * FROM t")
```

### DomainService
```python
svc = DomainService()
svc.load_exposures(source, source_type, *, query="", sheet_name=0) -> Exposures
svc.load_claims(source, source_type, *, query="", sheet_name=0) -> Claims
svc.build_triangle(source, source_type, value_type="incurred") -> Triangle  # csv only
svc.exposure_summary(exposures) -> dict[str, Any]  # count, total_exposure_value, currencies, modelling_years
svc.claim_summary(claims) -> dict[str, Any]  # count, total_latest_incurred, total_latest_paid, currencies, modelling_years
```
`source_type` values: `"csv"`, `"excel"`, `"json"`, `"yaml"`, `"dict"`, `"db"`

### DB column naming convention
- Flat CSV: dot-notation (`exposure_meta.exposure_id`) + `unflatten` pre_hook
- DB sources: underscore-namespaced (`exposure_meta_exposure_id`) + custom pre_hook → `unflatten`

### App startup
```bash
uv run python -m shiny run app.app          # correct — module-path form
# NOT: shiny run app/app.py                 # broken — relative imports fail as __main__
```

## Active Constraints / Assumptions

- mypy strict covers `src/pyre/` only; `app/` excluded
- `ClaimDevelopmentHistory.__post_init__` raises `ValueError` for mismatched list lengths — not caught by `Injector` (only catches `TypeError`); data quality must be validated upstream
- SQLite returns integers `0`/`1` for booleans — handled via `pre_process=lambda v: str(v) if isinstance(v, int) else v` on bool fields
- Triangle building only supports `source_type="csv"` (claims CSV format) in `DomainService.build_triangle`
- `pytest pythonpath = ["."]` required for `app` package to be importable from repo root in tests

## Current Test Status

- 321/321 tests pass
- 85% coverage (threshold: ≥80%)
- 0 ruff errors, 0 mypy errors (55 source files)

## Next Steps

- Create PR: `feature/shiny-webapp-data-injection` → `main`
- Optional: add Excel/YAML/JSON round-trip tests for domain schemas
- Optional: extend `DomainService.build_triangle` to support `source_type="excel"`
