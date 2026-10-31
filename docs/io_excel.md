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

## API Reference

::: pyre.io_excel.claims_io

::: pyre.io_excel.exposures_io

::: pyre.io_excel.triangle_io

::: pyre.io_excel.results_io
