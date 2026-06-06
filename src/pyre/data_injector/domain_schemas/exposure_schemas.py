# src/pyre/data_injector/domain_schemas/exposure_schemas.py
"""Pre-built Schema objects and Loader factories for pyre Exposure domain classes."""

from __future__ import annotations

from datetime import date
from typing import Any

from pyre.enums import ExposureBasis
from pyre.exposures.exposures import Exposure, ExposureMetaData, ExposureValues

from ..descriptors import FieldDescriptor
from ..loader import Loader
from ..schema import Schema
from ..utils import parse_bool, underscore_to_dotted, unflatten


def _parse_exposure_basis(value: Any) -> ExposureBasis:
    if isinstance(value, str) and value.strip() == "":
        return ExposureBasis.EARNED
    if isinstance(value, ExposureBasis):
        return value
    return ExposureBasis[str(value).upper()]


exposure_meta_schema: Schema[ExposureMetaData] = Schema(
    target_class=ExposureMetaData,
    fields=[
        FieldDescriptor("exposure_id"),
        FieldDescriptor("exposure_name"),
        FieldDescriptor("exposure_period_start", type_coerce=date.fromisoformat),
        FieldDescriptor("exposure_period_end", type_coerce=date.fromisoformat),
        FieldDescriptor("currency"),
        FieldDescriptor(
            "aggregate",
            required=False,
            default=False,
            # SQLite returns 0/1 as int; parse_bool expects string "0"/"1" or "true"/"false"
            pre_process=lambda v: str(v) if isinstance(v, int) else v,
            type_coerce=parse_bool,
        ),
        FieldDescriptor("line_of_business", required=False, default=None),
        FieldDescriptor("stacking_id", required=False, default=None),
        FieldDescriptor(
            "exposure_type",
            required=False,
            default=ExposureBasis.EARNED,
            type_coerce=_parse_exposure_basis,
        ),
        FieldDescriptor("location", required=False, default=None),
        FieldDescriptor("peril", required=False, default=None),
        FieldDescriptor("occupancy", required=False, default=None),
    ],
)

exposure_values_schema: Schema[ExposureValues] = Schema(
    target_class=ExposureValues,
    fields=[
        FieldDescriptor("exposure_value", type_coerce=float),
        FieldDescriptor("attachment_point", type_coerce=float),
        FieldDescriptor("limit", type_coerce=float),
    ],
)

# For flat sources (CSV/Excel/JSON) with dot-notation columns like:
#   "exposure_meta.exposure_id", "exposure_values.exposure_value"
# unflatten pre_hook converts these to nested dicts for _inject_nested.
exposure_schema: Schema[Exposure] = Schema(
    target_class=Exposure,
    fields=[
        FieldDescriptor("exposure_meta"),
        FieldDescriptor("exposure_values"),
    ],
    nested={
        "exposure_meta": exposure_meta_schema,
        "exposure_values": exposure_values_schema,
    },
    pre_hooks=[unflatten],
)


def exposures_loader() -> Loader[Exposure]:
    """Return a Loader[Exposure] for flat sources with dot-notation column names."""
    return Loader(exposure_schema)


_EXPOSURE_DB_PREFIXES = ("exposure_meta_", "exposure_values_")


def _underscore_to_dotted_exposure(record: dict[str, Any]) -> dict[str, Any]:
    """Convert DB underscore-namespaced columns to dot-notation for unflatten."""
    return underscore_to_dotted(record, _EXPOSURE_DB_PREFIXES)


_exposure_db_schema: Schema[Exposure] = Schema(
    target_class=Exposure,
    fields=[
        FieldDescriptor("exposure_meta"),
        FieldDescriptor("exposure_values"),
    ],
    nested={
        "exposure_meta": exposure_meta_schema,
        "exposure_values": exposure_values_schema,
    },
    pre_hooks=[_underscore_to_dotted_exposure, unflatten],
)


def exposures_db_loader() -> Loader[Exposure]:
    """Return a Loader[Exposure] for DB sources with underscore-namespaced columns."""
    return Loader(_exposure_db_schema)
