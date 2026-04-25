# tests/test_data_injector/test_db_adapter.py
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from pyre.data_injector.adapters.base import SourceAdapter
from pyre.data_injector.adapters.db_adapter import DBAdapter
from pyre.data_injector.registry import AdapterRegistry


def _make_sqlite_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE claims (claim_id TEXT, currency TEXT, amount REAL)")
    cur.executemany(
        "INSERT INTO claims VALUES (?, ?, ?)",
        [("CLM-001", "GBP", 50000.0), ("CLM-002", "USD", 75000.0)],
    )
    conn.commit()
    conn.close()


class TestDBAdapterSQLite:
    def test_load_returns_list_of_dicts(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        _make_sqlite_db(db_path)
        adapter = DBAdapter(f"sqlite:///{db_path}")
        records = adapter.load("SELECT claim_id, currency, amount FROM claims")
        assert len(records) == 2
        assert records[0] == {"claim_id": "CLM-001", "currency": "GBP", "amount": 50000.0}
        assert records[1] == {"claim_id": "CLM-002", "currency": "USD", "amount": 75000.0}

    def test_empty_result_returns_empty_list(self, tmp_path: Path) -> None:
        db_path = tmp_path / "empty.db"
        _make_sqlite_db(db_path)
        adapter = DBAdapter(f"sqlite:///{db_path}")
        records = adapter.load("SELECT * FROM claims WHERE 1=0")
        assert records == []

    def test_column_names_from_cursor_description(self, tmp_path: Path) -> None:
        db_path = tmp_path / "cols.db"
        _make_sqlite_db(db_path)
        adapter = DBAdapter(f"sqlite:///{db_path}")
        records = adapter.load("SELECT amount FROM claims LIMIT 1")
        assert "amount" in records[0]

    def test_invalid_sql_raises_runtime_error(self, tmp_path: Path) -> None:
        db_path = tmp_path / "bad.db"
        _make_sqlite_db(db_path)
        adapter = DBAdapter(f"sqlite:///{db_path}")
        with pytest.raises(RuntimeError, match="Query execution failed"):
            adapter.load("SELECT * FROM nonexistent_table")

    def test_unsupported_scheme_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unsupported connection scheme"):
            DBAdapter("mysql://localhost/mydb")


class TestDBAdapterPostgresImportError:
    def test_missing_psycopg2_raises_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import builtins

        real_import = builtins.__import__

        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "psycopg2":
                raise ImportError("mocked absence")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        adapter = DBAdapter("postgresql://localhost/mydb")
        with pytest.raises(ImportError, match="psycopg2"):
            adapter.load("SELECT 1")


class TestDBAdapterProtocol:
    def test_satisfies_source_adapter_protocol(self, tmp_path: Path) -> None:
        db_path = tmp_path / "proto.db"
        _make_sqlite_db(db_path)
        adapter = DBAdapter(f"sqlite:///{db_path}")
        assert isinstance(adapter, SourceAdapter)


class TestDBAdapterRegistry:
    def setup_method(self) -> None:
        # Re-register in case another test cleared the registry
        AdapterRegistry._adapters["db"] = DBAdapter

    def test_registered_under_db_key(self) -> None:
        assert "db" in AdapterRegistry.available()
        assert AdapterRegistry.get("db") is DBAdapter
