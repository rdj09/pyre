# src/pyre/data_injector/adapters/db_adapter.py
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from ..registry import AdapterRegistry


@AdapterRegistry.register("db")
class DBAdapter:
    """Load records from a SQL database via a raw query.

    Supported schemes:
      - sqlite:///path/to/file.db  (stdlib sqlite3, no extra deps)
      - postgresql://user:pass@host/dbname  (requires psycopg2)
    """

    def __init__(self, connection_string: str) -> None:
        parsed = urlparse(connection_string)
        scheme = parsed.scheme
        if scheme == "sqlite":
            self._scheme = "sqlite"
            self._db_path = parsed.netloc + parsed.path
        elif scheme in ("postgresql", "postgres"):
            self._scheme = "postgresql"
            self._connection_string = connection_string
        else:
            raise ValueError(
                f"Unsupported connection scheme '{scheme}'. Supported: 'sqlite', 'postgresql'."
            )

    def load(self, source: str) -> list[dict[str, Any]]:
        """Execute *source* as a SQL query and return rows as dicts."""
        if self._scheme == "sqlite":
            return self._load_sqlite(source)
        return self._load_postgresql(source)

    def _load_sqlite(self, query: str) -> list[dict[str, Any]]:
        import sqlite3

        try:
            conn = sqlite3.connect(self._db_path)
        except sqlite3.OperationalError as exc:
            raise RuntimeError(
                f"Database connection failed for path '{self._db_path}': {exc}"
            ) from exc
        try:
            cur = conn.cursor()
            try:
                cur.execute(query)
            except sqlite3.OperationalError as exc:
                raise RuntimeError(f"Query execution failed: {exc}") from exc
            if cur.description is None:
                return []
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row, strict=False)) for row in cur.fetchall()]
        finally:
            conn.close()

    def _load_postgresql(self, query: str) -> list[dict[str, Any]]:
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError as exc:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. "
                "Install it with: pip install psycopg2-binary"
            ) from exc
        try:
            conn = psycopg2.connect(self._connection_string)
        except psycopg2.OperationalError as exc:
            raise RuntimeError(f"Database connection failed: {exc}") from exc
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                cur.execute(query)
            except psycopg2.ProgrammingError as exc:
                raise RuntimeError(f"Query execution failed: {exc}") from exc
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
