import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.db import init_db


class TestInitDb(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "test.db"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_creates_expected_tables(self):
        init_db(self.path)

        conn = sqlite3.connect(self.path)
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()

        self.assertEqual(
            names,
            {"pricing_versions", "pricing_results_by_layer_year", "pricing_results_exposures_by_year"},
        )

    def test_foreign_keys_enabled_on_connection(self):
        from app.db import _connect

        init_db(self.path)
        with _connect(self.path) as conn:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_deleting_a_version_with_children_nulls_their_parent_id_not_errors(self):
        from app.db import _connect

        init_db(self.path)
        with _connect(self.path) as conn:
            conn.execute(
                "INSERT INTO pricing_versions (id, label, is_final, created_at, updated_at, pyre_version, inputs_blob) "
                "VALUES (1, 'parent', 0, '2026-01-01', '2026-01-01', '0.0.1', x'00')"
            )
            conn.execute(
                "INSERT INTO pricing_versions (id, label, parent_id, is_final, created_at, updated_at, pyre_version, inputs_blob) "
                "VALUES (2, 'child', 1, 0, '2026-01-01', '2026-01-01', '0.0.1', x'00')"
            )
            conn.execute("DELETE FROM pricing_versions WHERE id = 1")
            conn.commit()
            remaining = conn.execute("SELECT id, parent_id FROM pricing_versions").fetchall()

        self.assertEqual(remaining, [(2, None)])


if __name__ == "__main__":
    unittest.main()
