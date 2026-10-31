from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from ..claims.claims import Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData
from ..enums import ClaimYearType

CLAIMS_REQUIRED_COLUMNS = [
    "claim_id",
    "currency",
    "contract_limit",
    "development_month",
    "cumulative_paid",
    "cumulative_incurred",
]


def _read_sheet(path: str | Path, sheet_name: str) -> tuple[list[str], list[tuple]]:
    workbook = load_workbook(path, data_only=True)
    if sheet_name not in workbook.sheetnames:
        raise ValueError(f"workbook '{path}' has no sheet named '{sheet_name}'")
    worksheet = workbook[sheet_name]
    rows_iter = worksheet.iter_rows(values_only=True)
    headers = [str(h) for h in next(rows_iter)]
    return headers, list(rows_iter)


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value).strip())


def _parse_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ("true", "1", "yes")


def read_claims(path: str | Path, sheet_name: str = "Claims") -> Claims:
    """Build a Claims collection from a long-format .xlsx sheet (one row per claim/dev-point).

    Raises:
        ValueError: if a required column is missing, or if any claim's
            contract_limit is missing/<= 0 (ClaimsMetaData.contract_limit
            defaults to 0.0, which silently caps every ceded amount to zero).
    """
    headers, rows = _read_sheet(path, sheet_name)

    missing = [c for c in CLAIMS_REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise ValueError(f"claims sheet '{sheet_name}' is missing required columns: {missing}")

    col = {name: idx for idx, name in enumerate(headers)}

    groups: dict[str, list[tuple]] = {}
    for row in rows:
        if row[col["claim_id"]] is None:
            continue
        groups.setdefault(str(row[col["claim_id"]]), []).append(row)

    claims: list[Claim] = []
    for claim_id, group_rows in groups.items():
        first = group_rows[0]

        contract_limit = first[col["contract_limit"]]
        if contract_limit is None or float(contract_limit) <= 0:
            raise ValueError(
                f"claim '{claim_id}': contract_limit must be set to a positive value "
                "-- ClaimsMetaData.contract_limit defaults to 0.0, which caps every "
                "ceded/gross amount to zero."
            )

        claim_year_basis_raw = first[col["claim_year_basis"]] if "claim_year_basis" in col else None
        claim_year_basis = (
            ClaimYearType[str(claim_year_basis_raw).strip()]
            if claim_year_basis_raw
            else ClaimYearType.ACCIDENT_YEAR
        )

        meta = ClaimsMetaData(
            claim_id=claim_id,
            currency=str(first[col["currency"]]),
            contract_limit=float(contract_limit),
            contract_deductible=(
                float(first[col["contract_deductible"]] or 0.0)
                if "contract_deductible" in col
                else 0.0
            ),
            claim_in_xs_of_deductible=(
                _parse_bool(first[col["claim_in_xs_of_deductible"]])
                if "claim_in_xs_of_deductible" in col
                else False
            ),
            claim_year_basis=claim_year_basis,
            loss_date=(
                _parse_date(first[col["loss_date"]])
                if "loss_date" in col and first[col["loss_date"]] is not None
                else date(1900, 1, 1)
            ),
            policy_inception_date=(
                _parse_date(first[col["policy_inception_date"]])
                if "policy_inception_date" in col
                and first[col["policy_inception_date"]] is not None
                else date(1900, 1, 1)
            ),
            report_date=(
                _parse_date(first[col["report_date"]])
                if "report_date" in col and first[col["report_date"]] is not None
                else date(1900, 1, 1)
            ),
            line_of_business=first[col["line_of_business"]] if "line_of_business" in col else None,
            status=(first[col["status"]] if "status" in col and first[col["status"]] else "Open"),
        )

        sorted_rows = sorted(group_rows, key=lambda r: r[col["development_month"]])
        dev_history = ClaimDevelopmentHistory(
            development_months=[int(r[col["development_month"]]) for r in sorted_rows],
            cumulative_dev_paid=[float(r[col["cumulative_paid"]]) for r in sorted_rows],
            cumulative_dev_incurred=[float(r[col["cumulative_incurred"]]) for r in sorted_rows],
        )

        claims.append(Claim(claims_meta_data=meta, claims_development_history=dev_history))

    return Claims(claims)
