# app/services/storage_service.py
"""StorageService — serialise domain objects to SQLite rows and read back IDs."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from pyre.claims.claims import Claim
from pyre.exposures.exposures import Exposure

from ..db.database import init_db


def _exposure_to_row(e: Exposure) -> dict[str, object]:
    m = e.exposure_meta
    v = e.exposure_values
    return {
        "exposure_meta_exposure_id": m.exposure_id,
        "exposure_meta_exposure_name": m.exposure_name,
        "exposure_meta_exposure_period_start": m.exposure_period_start.isoformat(),
        "exposure_meta_exposure_period_end": m.exposure_period_end.isoformat(),
        "exposure_meta_currency": m.currency,
        "exposure_meta_aggregate": int(m.aggregate),
        "exposure_meta_line_of_business": m.line_of_business,
        "exposure_meta_stacking_id": m.stacking_id,
        "exposure_meta_exposure_type": m.exposure_type.name,
        "exposure_meta_location": m.location,
        "exposure_meta_peril": m.peril,
        "exposure_meta_occupancy": m.occupancy,
        "exposure_values_exposure_value": v.exposure_value,
        "exposure_values_attachment_point": v.attachment_point,
        "exposure_values_limit": v.limit,
    }


def _claim_to_row(c: Claim) -> dict[str, object]:
    m = c.claims_meta_data
    h = c.uncapped_claim_development_history
    return {
        "claims_meta_data_claim_id": m.claim_id,
        "claims_meta_data_currency": m.currency,
        "claims_meta_data_contract_limit": m.contract_limit,
        "claims_meta_data_contract_deductible": m.contract_deductible,
        "claims_meta_data_claim_in_xs_of_deductible": int(m.claim_in_xs_of_deductible),
        "claims_meta_data_claim_year_basis": m.claim_year_basis.name,
        "claims_meta_data_loss_date": m.loss_date.isoformat(),
        "claims_meta_data_policy_inception_date": m.policy_inception_date.isoformat(),
        "claims_meta_data_report_date": m.report_date.isoformat(),
        "claims_meta_data_line_of_business": m.line_of_business,
        "claims_meta_data_status": m.status,
        "claims_development_history_development_months": "|".join(
            str(v) for v in h.development_months
        ),
        "claims_development_history_cumulative_dev_paid": "|".join(
            str(v) for v in h.cumulative_dev_paid
        ),
        "claims_development_history_cumulative_dev_incurred": "|".join(
            str(v) for v in h.cumulative_dev_incurred
        ),
    }


_ALLOWED_TABLES: frozenset[str] = frozenset({"exposures", "claims"})


def _upsert(rows: list[dict[str, object]], table: str, db_path: str) -> None:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table!r}")
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" * len(columns))
    sql = f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    conn = sqlite3.connect(db_path)
    try:
        conn.executemany(sql, [tuple(row[c] for c in columns) for row in rows])
        conn.commit()
    finally:
        conn.close()


class StorageService:
    def save_exposures(self, exposures: list[Exposure], db_path: str) -> None:
        if not exposures:
            return
        init_db(db_path)
        _upsert([_exposure_to_row(e) for e in exposures], "exposures", db_path)

    def save_claims(self, claims: list[Claim], db_path: str) -> None:
        if not claims:
            return
        init_db(db_path)
        _upsert([_claim_to_row(c) for c in claims], "claims", db_path)

    def list_stored(
        self, db_path: str, table: Literal["exposures", "claims"]
    ) -> list[str]:
        if table not in ("exposures", "claims"):
            raise ValueError(f"Invalid table '{table}'. Expected: 'exposures' or 'claims'.")
        if not Path(db_path).exists():
            return []
        pk = (
            "exposure_meta_exposure_id"
            if table == "exposures"
            else "claims_meta_data_claim_id"
        )
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.execute(f"SELECT {pk} FROM {table}")
            return [row[0] for row in cur.fetchall()]
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()
