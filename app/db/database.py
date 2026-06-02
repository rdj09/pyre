# app/db/database.py
"""SQLite schema definitions and initialisation for the pyre webapp."""

from __future__ import annotations

import sqlite3

EXPOSURES_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS exposures (
    exposure_meta_exposure_id              TEXT PRIMARY KEY,
    exposure_meta_exposure_name            TEXT NOT NULL,
    exposure_meta_exposure_period_start    TEXT NOT NULL,
    exposure_meta_exposure_period_end      TEXT NOT NULL,
    exposure_meta_currency                 TEXT NOT NULL,
    exposure_meta_aggregate                INTEGER NOT NULL DEFAULT 0,
    exposure_meta_line_of_business         TEXT,
    exposure_meta_stacking_id              TEXT,
    exposure_meta_exposure_type            TEXT NOT NULL DEFAULT 'EARNED',
    exposure_meta_location                 TEXT,
    exposure_meta_peril                    TEXT,
    exposure_meta_occupancy                TEXT,
    exposure_values_exposure_value         REAL NOT NULL,
    exposure_values_attachment_point       REAL NOT NULL,
    exposure_values_limit                  REAL NOT NULL
)
"""

CLAIMS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS claims (
    claims_meta_data_claim_id                               TEXT PRIMARY KEY,
    claims_meta_data_currency                               TEXT NOT NULL,
    claims_meta_data_contract_limit                         REAL NOT NULL DEFAULT 0.0,
    claims_meta_data_contract_deductible                    REAL NOT NULL DEFAULT 0.0,
    claims_meta_data_claim_in_xs_of_deductible              INTEGER NOT NULL DEFAULT 0,
    claims_meta_data_claim_year_basis                       TEXT NOT NULL DEFAULT 'ACCIDENT_YEAR',
    claims_meta_data_loss_date                              TEXT NOT NULL DEFAULT '1900-01-01',
    claims_meta_data_policy_inception_date                  TEXT NOT NULL DEFAULT '1900-01-01',
    claims_meta_data_report_date                            TEXT NOT NULL DEFAULT '1900-01-01',
    claims_meta_data_line_of_business                       TEXT,
    claims_meta_data_status                                 TEXT NOT NULL DEFAULT 'Open',
    claims_development_history_development_months           TEXT NOT NULL DEFAULT '',
    claims_development_history_cumulative_dev_paid          TEXT NOT NULL DEFAULT '',
    claims_development_history_cumulative_dev_incurred      TEXT NOT NULL DEFAULT ''
)
"""


def init_db(db_path: str) -> None:
    """Create exposures and claims tables in the SQLite database at *db_path* if they don't exist."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(EXPOSURES_TABLE_DDL)
        conn.execute(CLAIMS_TABLE_DDL)
        conn.commit()
    finally:
        conn.close()
