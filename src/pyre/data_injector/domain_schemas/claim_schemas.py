# src/pyre/data_injector/domain_schemas/claim_schemas.py
"""Pre-built Schema objects and Loader factories for pyre Claim domain classes."""
from __future__ import annotations

from datetime import date
from typing import Any

from pyre.claims.claims import Claim, ClaimDevelopmentHistory, ClaimsMetaData
from pyre.enums import ClaimYearType

from ..descriptors import FieldDescriptor
from ..loader import Loader
from ..schema import Schema
from ..utils import parse_bool, unflatten


def _parse_claim_year_type(value: Any) -> ClaimYearType:
    if isinstance(value, ClaimYearType):
        return value
    return ClaimYearType[str(value).upper()]


def _parse_date_with_default(value: Any) -> date:
    if not value or (isinstance(value, str) and value.strip() == ""):
        return date(1900, 1, 1)
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _parse_int_list(value: Any) -> list[int]:
    if isinstance(value, list):
        return [int(v) for v in value]
    if isinstance(value, str) and value.strip() == "":
        return []
    return [int(v.strip()) for v in str(value).split("|") if v.strip()]


def _parse_float_list(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(v) for v in value]
    if isinstance(value, str) and value.strip() == "":
        return []
    return [float(v.strip()) for v in str(value).split("|") if v.strip()]


claims_meta_schema: Schema[ClaimsMetaData] = Schema(
    target_class=ClaimsMetaData,
    fields=[
        FieldDescriptor("claim_id"),
        FieldDescriptor("currency"),
        FieldDescriptor("contract_limit", required=False, default=0.0, type_coerce=float),
        FieldDescriptor("contract_deductible", required=False, default=0.0, type_coerce=float),
        FieldDescriptor(
            "claim_in_xs_of_deductible",
            required=False,
            default=False,
            # SQLite returns 0/1 as int; parse_bool expects string "0"/"1" or "true"/"false"
            pre_process=lambda v: str(v) if isinstance(v, int) else v,
            type_coerce=parse_bool,
        ),
        FieldDescriptor(
            "claim_year_basis",
            required=False,
            default=ClaimYearType.ACCIDENT_YEAR,
            type_coerce=_parse_claim_year_type,
        ),
        FieldDescriptor(
            "loss_date",
            required=False,
            default_factory=lambda: date(1900, 1, 1),
            type_coerce=_parse_date_with_default,
        ),
        FieldDescriptor(
            "policy_inception_date",
            required=False,
            default_factory=lambda: date(1900, 1, 1),
            type_coerce=_parse_date_with_default,
        ),
        FieldDescriptor(
            "report_date",
            required=False,
            default_factory=lambda: date(1900, 1, 1),
            type_coerce=_parse_date_with_default,
        ),
        FieldDescriptor("line_of_business", required=False, default=None),
        FieldDescriptor("status", required=False, default="Open"),
    ],
)

claim_dev_history_schema: Schema[ClaimDevelopmentHistory] = Schema(
    target_class=ClaimDevelopmentHistory,
    fields=[
        FieldDescriptor(
            "development_months",
            required=False,
            default_factory=list,
            type_coerce=_parse_int_list,
        ),
        FieldDescriptor(
            "cumulative_dev_paid",
            required=False,
            default_factory=list,
            type_coerce=_parse_float_list,
        ),
        FieldDescriptor(
            "cumulative_dev_incurred",
            required=False,
            default_factory=list,
            type_coerce=_parse_float_list,
        ),
    ],
)

claim_schema: Schema[Claim] = Schema(
    target_class=Claim,
    fields=[
        FieldDescriptor("claims_meta_data"),
        FieldDescriptor("claims_development_history"),
    ],
    nested={
        "claims_meta_data": claims_meta_schema,
        "claims_development_history": claim_dev_history_schema,
    },
    pre_hooks=[unflatten],
)


def claims_loader() -> Loader[Claim]:
    """Return a Loader[Claim] for flat sources with dot-notation column names."""
    return Loader(claim_schema)


def _underscore_to_dotted_claim(record: dict[str, Any]) -> dict[str, Any]:
    """Convert DB underscore-namespaced columns to dot-notation for unflatten."""
    prefixes = ("claims_meta_data_", "claims_development_history_")
    result: dict[str, Any] = {}
    for key, value in record.items():
        converted = False
        for prefix in prefixes:
            if key.startswith(prefix):
                namespace = prefix.rstrip("_")
                field_name = key[len(prefix):]
                result[f"{namespace}.{field_name}"] = value
                converted = True
                break
        if not converted:
            result[key] = value
    return result


_claim_db_schema: Schema[Claim] = Schema(
    target_class=Claim,
    fields=[
        FieldDescriptor("claims_meta_data"),
        FieldDescriptor("claims_development_history"),
    ],
    nested={
        "claims_meta_data": claims_meta_schema,
        "claims_development_history": claim_dev_history_schema,
    },
    pre_hooks=[_underscore_to_dotted_claim, unflatten],
)


def claims_db_loader() -> Loader[Claim]:
    """Return a Loader[Claim] for DB sources with underscore-namespaced columns."""
    return Loader(_claim_db_schema)
