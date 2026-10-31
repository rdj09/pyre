# Treaty Pricing Workbench

A [Panel](https://panel.holoviz.org/) (HoloViz) dashboard, bundled at the top
level of the repository in `app/` — kept **outside** `src/pyre/` so the core
package stays dependency-free. It lets you configure a reinsurance
contract/layer, load claims and exposures data, run `pyre`'s experience
rating calculation, and view ceded-loss results by layer and modelling year.

v1 scope is deliberately narrow: a single-contract pricing workbench, not a
general data explorer or rate-monitoring dashboard.

## Install and run

```bash
pip install -e ".[panel]"       # installs panel>=1.4, pandas>=2.0
hatch run panel:serve           # panel serve app/main.py --show --autoreload
# or, without Hatch:
python run_app.py
```

## Layout

| Path | Purpose |
|---|---|
| `app/service.py` | Pure-Python core (no `import panel`) — CSV parsing into `Claims`/`Exposures`, form-dict → `RIContractMetadata`/`RILayer`, `run_pricing()` → `PricingResults` (pandas DataFrames). Unit-tested in `tests/test_app_service.py` without a running server. |
| `app/state.py` | Panel-free shared state (`WorkbenchState`). |
| `app/pages/` | Panel UI: `contract_config.py`, `data_loading.py`, `results.py`. |
| `app/main.py` | Entrypoint (`panel serve app/main.py`). Not named `app.py` — Bokeh's script loader would otherwise register the running script as a module named `app`, shadowing the `app` package. |
| `examples/panel_demo/` | Bundled demo CSVs loaded by the "Load demo data" button. |

## Walkthrough

1. **Load data** — upload a claims CSV and an exposures CSV, or click
   "Load demo data" to use the bundled `examples/panel_demo/` files.
2. **Configure contract** — fill in contract metadata (cedent, trigger
   basis, indexation, dates) and add one or more layers. The layer-type
   selector intentionally **excludes `SURPLUS_SHARE`** — `loss_to_layer_fn`
   raises `NotImplementedError` for it (no `sum_insured` concept modelled
   yet; see [Treaty: layer loss-to-layer formulas](treaty.md#layer-loss-to-layer-formulas)).
3. **Run pricing** — runs `ExperienceModelData` under the hood and shows
   ceded paid/incurred, claim counts, earned premium, and loss ratio per
   layer and modelling year.

!!! note "What this calculation does (and doesn't) do"
    The workbench applies each layer's loss-to-layer function to trended
    claims and aggregates by modelling year — the same calculation
    documented in [Models: `ExperienceModelData`](models.md#experiencemodeldata-the-central-entry-point).
    It does **not** apply development factors, IBNER, or non-trivial trend
    factors in v1 — `run_pricing()` builds `ExperienceModelData` with its
    default trend factors (all `1.0`), so burn costs are undeveloped,
    un-trended ceded losses over earned exposure. This also sidesteps the
    known `Trending.calculate_trend_factor` direction bug (see
    [Models: Trending](models.md#trending)), which only affects non-default
    trend factors.

## CSV formats

Both CSVs are long/row-per-datapoint format, matching `app/service.py`'s
`CLAIMS_REQUIRED_COLUMNS` / `EXPOSURES_REQUIRED_COLUMNS`.

**Claims** — one row per claim per development valuation, grouped by `claim_id`:

| Column | Notes |
|---|---|
| `claim_id` | Groups rows into one `Claim`'s development history. |
| `currency` | |
| `contract_limit` | **Required and must be > 0** — `ClaimsMetaData.contract_limit` defaults to `0.0`, which silently caps every ceded amount to zero. `parse_claims_csv` raises `ValueError` if missing or `<= 0`. |
| `loss_date` | ISO date; determines the claim's modelling (accident) year. |
| `development_month` | |
| `cumulative_paid`, `cumulative_incurred` | |

**Exposures** — one row per exposure:

| Column | Notes |
|---|---|
| `exposure_id`, `exposure_name` | |
| `exposure_period_start`, `exposure_period_end` | ISO dates. |
| `currency` | |
| `exposure_value` | |

## Demo data

`examples/panel_demo/claims_demo.csv` and `exposures_demo.csv` contain three
claims across 2022/2023 and a 200k xs 100k XOL layer, chosen to show three
cases: a claim within the layer, one that never reaches it, and one that
exhausts the limit. Expected results (also asserted by
`tests/test_app_service.py::TestRunPricing::test_run_pricing_matches_expected_ceded_loss`):

| Modelling year | Ceded paid | Ceded incurred | Loss ratio |
|---|---|---|---|
| 2022 | 0 | 150,000 | 15.0% |
| 2023 | 50,000 | 200,000 | 16.7% |

See `examples/panel_demo/README.md` for the full per-claim breakdown.
