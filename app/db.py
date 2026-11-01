import contextlib
import sqlite3
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "workbench.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pricing_versions (
    id INTEGER PRIMARY KEY,
    label TEXT NOT NULL,
    parent_id INTEGER REFERENCES pricing_versions(id) ON DELETE SET NULL,
    is_final INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    pyre_version TEXT NOT NULL,
    contract_id TEXT,
    cedent_name TEXT,
    contract_description TEXT,
    inception_date TEXT,
    expiration_date TEXT,
    inputs_blob BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS pricing_results_by_layer_year (
    id INTEGER PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    layer_id INTEGER NOT NULL,
    layer_name TEXT NOT NULL,
    modelling_year INTEGER NOT NULL,
    ceded_paid REAL NOT NULL,
    ceded_incurred REAL NOT NULL,
    claim_count INTEGER NOT NULL,
    earned_premium REAL NOT NULL,
    loss_ratio REAL
);

CREATE TABLE IF NOT EXISTS pricing_results_exposures_by_year (
    id INTEGER PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    modelling_year INTEGER NOT NULL,
    written REAL NOT NULL,
    earned REAL NOT NULL
);
"""


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as conn:
        conn.executescript(_SCHEMA)


@contextlib.contextmanager
def _connect(path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()
