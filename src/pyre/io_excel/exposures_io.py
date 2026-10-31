from __future__ import annotations

from pathlib import Path

from ..enums import ExposureBasis
from ..exposures.exposures import Exposure, ExposureMetaData, Exposures, ExposureValues
from .claims_io import _parse_bool, _parse_date, _read_sheet

EXPOSURES_REQUIRED_COLUMNS = [
    "exposure_id",
    "exposure_name",
    "exposure_period_start",
    "exposure_period_end",
    "currency",
    "exposure_value",
]


def read_exposures(path: str | Path, sheet_name: str = "Exposures") -> Exposures:
    """Build an Exposures collection from a .xlsx sheet (one row per exposure)."""
    headers, rows = _read_sheet(path, sheet_name)

    missing = [c for c in EXPOSURES_REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise ValueError(f"exposures sheet '{sheet_name}' is missing required columns: {missing}")

    col = {name: idx for idx, name in enumerate(headers)}

    exposures: list[Exposure] = []
    for row in rows:
        if row[col["exposure_id"]] is None:
            continue

        exposure_type_raw = row[col["exposure_type"]] if "exposure_type" in col else None
        exposure_type = (
            ExposureBasis[str(exposure_type_raw).strip()]
            if exposure_type_raw
            else ExposureBasis.EARNED
        )

        meta = ExposureMetaData(
            exposure_id=str(row[col["exposure_id"]]),
            exposure_name=str(row[col["exposure_name"]]),
            exposure_period_start=_parse_date(row[col["exposure_period_start"]]),
            exposure_period_end=_parse_date(row[col["exposure_period_end"]]),
            currency=str(row[col["currency"]]),
            aggregate=(_parse_bool(row[col["aggregate"]]) if "aggregate" in col else False),
            line_of_business=row[col["line_of_business"]] if "line_of_business" in col else None,
            stacking_id=row[col["stacking_id"]] if "stacking_id" in col else None,
            exposure_type=exposure_type,
            location=row[col["location"]] if "location" in col else None,
            peril=row[col["peril"]] if "peril" in col else None,
            occupancy=row[col["occupancy"]] if "occupancy" in col else None,
        )

        exposure_value = float(row[col["exposure_value"]])
        values = ExposureValues(
            exposure_value=exposure_value,
            attachment_point=(
                float(row[col["attachment_point"]])
                if "attachment_point" in col and row[col["attachment_point"]] is not None
                else 0.0
            ),
            limit=(
                float(row[col["limit"]])
                if "limit" in col and row[col["limit"]] is not None
                else exposure_value
            ),
        )
        exposures.append(Exposure(exposure_meta=meta, exposure_values=values))

    return Exposures(exposures)
