# Panel demo data

Bundled sample data for the treaty pricing workbench's "Load demo data" button.

Paired with a single Excess of Loss layer (100,000 xs 100,000 -> 200,000 xs
100,000, i.e. `occurrence_attachment=100000`, `occurrence_limit=200000`), these
claims and exposures produce:

| Modelling year | Ceded paid | Ceded incurred | Earned premium | Loss ratio |
|---|---|---|---|---|
| 2022 | 0 | 150,000 | 1,000,000 | 15.0% |
| 2023 | 50,000 | 200,000 | 1,200,000 | 16.7% |

- CLM001 (2022) illustrates a claim developing into the layer on an incurred
  basis but not yet paid there.
- CLM002 (2022) never reaches the layer (a "zero" case).
- CLM003 (2023) exhausts the 200,000 layer limit (demonstrates capping).
