import contextlib
import pickle
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from pyre import Claims, Exposures, RIContractMetadata, RILayer, __about__

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


@dataclass
class ModelSnapshot:
    claims: Optional[Claims]
    exposures: Optional[Exposures]
    contract_metadata: Optional[RIContractMetadata]
    layers: list[RILayer]


@dataclass
class VersionSummary:
    id: int
    label: str
    parent_id: Optional[int]
    is_final: bool
    created_at: str
    updated_at: str
    contract_id: Optional[str]
    cedent_name: Optional[str]
    contract_description: Optional[str]
    inception_date: Optional[str]
    expiration_date: Optional[str]
    has_results: bool


class IncompatibleSnapshotError(Exception):
    """Raised when a stored snapshot blob can't be unpickled under the current pyre version."""

    def __init__(self, stored_pyre_version: str, current_pyre_version: str):
        self.stored_pyre_version = stored_pyre_version
        self.current_pyre_version = current_pyre_version
        super().__init__(
            f"Stored snapshot was saved with pyre {stored_pyre_version}, "
            f"which is incompatible with the currently installed pyre {current_pyre_version}."
        )


def save_version(
    path: Path,
    snapshot: ModelSnapshot,
    label: str,
    parent_id: Optional[int] = None,
    is_final: bool = False,
) -> int:
    blob = pickle.dumps(snapshot)
    now = datetime.now(timezone.utc).isoformat()
    metadata = snapshot.contract_metadata

    contract_id = metadata.contract_id if metadata is not None else None
    cedent_name = metadata.cedent_name if metadata is not None else None
    contract_description = metadata.contract_description if metadata is not None else None
    inception_date = metadata.inception_date.isoformat() if metadata is not None else None
    expiration_date = metadata.expiration_date.isoformat() if metadata is not None else None

    with _connect(path) as conn:
        cursor = conn.execute(
            "INSERT INTO pricing_versions ("
            "label, parent_id, is_final, created_at, updated_at, pyre_version, "
            "contract_id, cedent_name, contract_description, inception_date, expiration_date, "
            "inputs_blob"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                label,
                parent_id,
                int(is_final),
                now,
                now,
                __about__.__version__,
                contract_id,
                cedent_name,
                contract_description,
                inception_date,
                expiration_date,
                blob,
            ),
        )
        conn.commit()
        assert cursor.lastrowid is not None
        return cursor.lastrowid


def save_results(
    path: Path,
    version_id: int,
    by_layer_year: list[dict],
    exposures_by_year: list[dict],
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect(path) as conn:
        conn.execute(
            "DELETE FROM pricing_results_by_layer_year WHERE version_id = ?", (version_id,)
        )
        conn.execute(
            "DELETE FROM pricing_results_exposures_by_year WHERE version_id = ?", (version_id,)
        )
        for row in by_layer_year:
            conn.execute(
                "INSERT INTO pricing_results_by_layer_year ("
                "version_id, layer_id, layer_name, modelling_year, ceded_paid, ceded_incurred, "
                "claim_count, earned_premium, loss_ratio"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    version_id,
                    row["layer_id"],
                    row["layer_name"],
                    row["modelling_year"],
                    row["ceded_paid"],
                    row["ceded_incurred"],
                    row["claim_count"],
                    row["earned_premium"],
                    row["loss_ratio"],
                ),
            )
        for row in exposures_by_year:
            conn.execute(
                "INSERT INTO pricing_results_exposures_by_year ("
                "version_id, modelling_year, written, earned"
                ") VALUES (?, ?, ?, ?)",
                (
                    version_id,
                    row["modelling_year"],
                    row["written"],
                    row["earned"],
                ),
            )
        conn.execute(
            "UPDATE pricing_versions SET updated_at = ? WHERE id = ?", (now, version_id)
        )
        conn.commit()


def load_version(path: Path, version_id: int) -> tuple[ModelSnapshot, list[dict], list[dict]]:
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT inputs_blob, pyre_version FROM pricing_versions WHERE id = ?",
            (version_id,),
        ).fetchone()
        blob, stored_pyre_version = row

        try:
            snapshot: ModelSnapshot = pickle.loads(blob)
        except Exception:
            raise IncompatibleSnapshotError(
                stored_pyre_version=stored_pyre_version,
                current_pyre_version=__about__.__version__,
            ) from None

        conn.row_factory = sqlite3.Row
        by_layer_year_rows = conn.execute(
            "SELECT layer_id, layer_name, modelling_year, ceded_paid, ceded_incurred, "
            "claim_count, earned_premium, loss_ratio "
            "FROM pricing_results_by_layer_year WHERE version_id = ? "
            "ORDER BY layer_id, modelling_year",
            (version_id,),
        ).fetchall()
        exposures_by_year_rows = conn.execute(
            "SELECT modelling_year, written, earned "
            "FROM pricing_results_exposures_by_year WHERE version_id = ? "
            "ORDER BY modelling_year",
            (version_id,),
        ).fetchall()

        by_layer_year: list[dict[str, Any]] = [dict(r) for r in by_layer_year_rows]
        exposures_by_year: list[dict[str, Any]] = [dict(r) for r in exposures_by_year_rows]

    return snapshot, by_layer_year, exposures_by_year


def list_versions(path: Path, *, final_only: bool = False) -> list[VersionSummary]:
    with _connect(path) as conn:
        query = (
            "SELECT id, label, parent_id, is_final, created_at, updated_at, "
            "contract_id, cedent_name, contract_description, inception_date, expiration_date, "
            "EXISTS (SELECT 1 FROM pricing_results_by_layer_year WHERE version_id = pricing_versions.id) AS has_results "
            "FROM pricing_versions"
        )
        if final_only:
            query += " WHERE is_final = 1"
        query += " ORDER BY created_at DESC"

        rows = conn.execute(query).fetchall()

        summaries = []
        for row in rows:
            summary = VersionSummary(
                id=row[0],
                label=row[1],
                parent_id=row[2],
                is_final=bool(row[3]),
                created_at=row[4],
                updated_at=row[5],
                contract_id=row[6],
                cedent_name=row[7],
                contract_description=row[8],
                inception_date=row[9],
                expiration_date=row[10],
                has_results=bool(row[11]),
            )
            summaries.append(summary)

        return summaries


def set_final(path: Path, version_id: int, is_final: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect(path) as conn:
        conn.execute(
            "UPDATE pricing_versions SET is_final = ?, updated_at = ? WHERE id = ?",
            (int(is_final), now, version_id),
        )
        conn.commit()
