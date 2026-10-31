# Excel File I/O

`pyre.io_excel` reads `Claims`/`Exposures` from `.xlsx` workbooks and writes
triangle, experience-rating, and exposure-rating results back out — no Excel
installation required (this is headless file I/O via
[openpyxl](https://openpyxl.readthedocs.io/), not a live Excel connection;
that's a separate, not-yet-built xlwings integration).

## Installation

```bash
pip install -e ".[excel]"
```

`pyre.io_excel` is never imported by a bare `import pyre` — only
`from pyre.io_excel import ...` requires `openpyxl` to be installed.

## Reading claims and exposures

```python
from pyre.io_excel import read_claims, read_exposures

claims = read_claims("claims.xlsx")       # expects a "Claims" sheet
exposures = read_exposures("exposures.xlsx")  # expects an "Exposures" sheet
```

Both use the same long-format column schema as the Panel workbench's CSV
upload (see [Treaty Pricing Workbench](workbench.md)): one row per
claim/development-point for claims, one row per exposure. `contract_limit`
must be set to a positive value, same requirement as elsewhere in `pyre` —
see [Claims](claims.md).

### Column schema

**Claims** — required: `claim_id`, `currency`, `contract_limit`,
`development_month`, `cumulative_paid`, `cumulative_incurred`. Optional
(default shown): `claim_year_basis` (`ACCIDENT_YEAR`), `contract_deductible`
(`0.0`), `claim_in_xs_of_deductible` (`False`), `loss_date`,
`policy_inception_date`, `report_date` (all `1900-01-01`),
`line_of_business` (`None`), `status` (`"Open"`).

**Exposures** — required: `exposure_id`, `exposure_name`,
`exposure_period_start`, `exposure_period_end`, `currency`,
`exposure_value`. Optional (default shown): `aggregate` (`False`),
`line_of_business`, `stacking_id`, `exposure_type` (`EARNED`), `location`,
`peril`, `occupancy` (all `None`), `attachment_point` (`0.0`), `limit`
(defaults to `exposure_value`).

A required cell left blank (not just an absent column) raises `ValueError`
naming the claim/exposure id and the empty field, rather than silently
becoming the string `"None"` or an opaque `TypeError`.

**Dates**: a native Excel date cell, or an ISO-format (`YYYY-MM-DD`) string.
**Booleans**: a native Excel boolean, or the strings `"true"`/`"1"`/`"yes"`
(case-insensitive) as `True` — anything else, including blank, is `False`.

## Writing results

```python
from pyre.io_excel import write_triangle, write_experience_rating_results, write_exposure_rating_results

write_triangle(triangle, "triangle.xlsx")
write_experience_rating_results(model_data, "experience_results.xlsx")  # model_data: ExperienceModelData
write_exposure_rating_results(exposure_model, "exposure_results.xlsx")  # exposure_model: ExposureModel
```

`write_experience_rating_results` writes two sheets ("ByLayerYear",
"ExposuresByYear") to one workbook. Re-running either write function against
the same path overwrites that sheet rather than duplicating it.

!!! warning "Point this at a dedicated output file"
    These functions load and re-save the whole workbook at `path` via
    `openpyxl`, which does not round-trip every part of an `.xlsx` file —
    **charts, images, and pivot tables already in that file will be lost**.
    Use a dedicated output path for generated reports; don't point these at
    a workbook you're also editing by hand with charts/pivots in it.

## API Reference

::: pyre.io_excel.claims_io

::: pyre.io_excel.exposures_io

::: pyre.io_excel.triangle_io

::: pyre.io_excel.results_io
