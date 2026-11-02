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


class TestSaveLoadVersion(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "test.db"
        init_db(self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_round_trips_a_full_snapshot(self):
        from datetime import date

        from pyre import (
            Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData,
            Exposure, ExposureMetaData, Exposures, ExposureValues,
            RIContractMetadata, RILayer,
        )
        from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType
        from app.db import ModelSnapshot, load_version, save_version

        claims = Claims([Claim(
            ClaimsMetaData(claim_id="C1", currency="USD", contract_limit=1_000_000.0, loss_date=date(2022, 1, 1)),
            ClaimDevelopmentHistory(development_months=[12], cumulative_dev_paid=[1000.0], cumulative_dev_incurred=[2000.0]),
        )])
        exposures = Exposures([Exposure(
            ExposureMetaData(exposure_id="E1", exposure_name="E1", exposure_period_start=date(2022, 1, 1), exposure_period_end=date(2022, 12, 31), currency="USD"),
            ExposureValues(exposure_value=500_000.0, attachment_point=0.0, limit=500_000.0),
        )])
        metadata = RIContractMetadata(
            contract_id="C-0001", contract_description="Test", cedent_name="Acme",
            trigger_basis=ClaimTriggerBasis.LOD, indexation_clause=IndexationClauseType.FULL_INDEXATION,
            indexation_margin=0.0, inception_date=date(2022, 1, 1), expiration_date=date(2022, 12, 31),
            fx_rates={"USD": 1.0},
        )
        layer = RILayer(
            layer_id=1, layer_name="L1", layer_type=ContractType.EXCESS_OF_LOSS,
            occurrence_attachment=100_000.0, occurrence_limit=200_000.0,
            aggregate_attachment=0.0, aggregate_limit=0.0, subject_lines_of_business=[],
            subject_lob_exposure_amounts=[], full_subject_premium=0.0, written_line=1.0,
            signed_line=1.0, number_of_reinstatements=0, reinstatement_cost={},
        )
        snapshot = ModelSnapshot(claims=claims, exposures=exposures, contract_metadata=metadata, layers=[layer])

        version_id = save_version(self.path, snapshot, label="v1")
        loaded_snapshot, by_layer_year, exposures_by_year = load_version(self.path, version_id)

        self.assertEqual(loaded_snapshot.contract_metadata.contract_id, "C-0001")
        self.assertEqual(loaded_snapshot.layers[0].occurrence_limit, 200_000.0)
        self.assertEqual(loaded_snapshot.claims.claims[0].claims_meta_data.claim_id, "C1")
        self.assertEqual(by_layer_year, [])
        self.assertEqual(exposures_by_year, [])

    def test_round_trips_an_empty_draft(self):
        from app.db import ModelSnapshot, load_version, save_version

        snapshot = ModelSnapshot(claims=None, exposures=None, contract_metadata=None, layers=[])
        version_id = save_version(self.path, snapshot, label="draft")
        loaded_snapshot, by_layer_year, exposures_by_year = load_version(self.path, version_id)

        self.assertIsNone(loaded_snapshot.claims)
        self.assertIsNone(loaded_snapshot.contract_metadata)
        self.assertEqual(loaded_snapshot.layers, [])
        self.assertEqual(by_layer_year, [])

    def test_save_results_then_load_returns_the_rows(self):
        from app.db import ModelSnapshot, load_version, save_results, save_version

        version_id = save_version(self.path, ModelSnapshot(None, None, None, []), label="v1")
        by_layer_year = [{
            "layer_id": 1, "layer_name": "L1", "modelling_year": 2022, "ceded_paid": 0.0,
            "ceded_incurred": 150000.0, "claim_count": 1, "earned_premium": 1_000_000.0, "loss_ratio": 0.15,
        }]
        exposures_by_year = [{"modelling_year": 2022, "written": 1_000_000.0, "earned": 1_000_000.0}]
        save_results(self.path, version_id, by_layer_year, exposures_by_year)

        _, loaded_by_layer_year, loaded_exposures_by_year = load_version(self.path, version_id)

        self.assertEqual(loaded_by_layer_year, by_layer_year)
        self.assertEqual(loaded_exposures_by_year, exposures_by_year)

    def test_load_raises_named_error_on_incompatible_blob(self):
        from app.db import IncompatibleSnapshotError, _connect, load_version

        with _connect(self.path) as conn:
            conn.execute(
                "INSERT INTO pricing_versions (id, label, is_final, created_at, updated_at, pyre_version, inputs_blob) "
                "VALUES (1, 'bad', 0, '2026-01-01', '2026-01-01', '0.0.0-does-not-exist', x'ffff')"
            )
            conn.commit()

        with self.assertRaises(IncompatibleSnapshotError) as ctx:
            load_version(self.path, 1)
        self.assertEqual(ctx.exception.stored_pyre_version, "0.0.0-does-not-exist")


class TestListVersionsAndSetFinal(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "test.db"
        init_db(self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_lists_versions_without_touching_the_blob(self):
        from app.db import ModelSnapshot, list_versions, save_version

        save_version(self.path, ModelSnapshot(None, None, None, []), label="a")
        save_version(self.path, ModelSnapshot(None, None, None, []), label="b")

        summaries = list_versions(self.path)

        self.assertEqual({s.label for s in summaries}, {"a", "b"})
        self.assertFalse(summaries[0].has_results)

    def test_final_only_filters_to_final_versions_and_coexist_is_allowed(self):
        from app.db import ModelSnapshot, list_versions, save_version, set_final

        id_a = save_version(self.path, ModelSnapshot(None, None, None, []), label="a")
        id_b = save_version(self.path, ModelSnapshot(None, None, None, []), label="b")
        set_final(self.path, id_a, True)
        set_final(self.path, id_b, True)

        self.assertEqual(len(list_versions(self.path, final_only=True)), 2)
        self.assertEqual(len(list_versions(self.path)), 2)

    def test_final_only_returns_empty_list_when_none_are_final(self):
        from app.db import ModelSnapshot, list_versions, save_version

        save_version(self.path, ModelSnapshot(None, None, None, []), label="a")

        self.assertEqual(list_versions(self.path, final_only=True), [])


class TestCopyVersion(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "test.db"
        init_db(self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_copy_produces_an_independent_version_pointing_at_its_parent(self):
        from pyre import Claims
        from app.db import ModelSnapshot, copy_version, list_versions, load_version, save_version

        original_id = save_version(self.path, ModelSnapshot(Claims([]), None, None, []), label="original")
        copy_id = copy_version(self.path, original_id, new_label="copy")

        self.assertNotEqual(copy_id, original_id)
        summaries = {s.id: s for s in list_versions(self.path)}
        self.assertEqual(summaries[copy_id].parent_id, original_id)
        self.assertEqual(summaries[copy_id].label, "copy")

    def test_copying_a_draft_with_no_results_succeeds(self):
        from app.db import ModelSnapshot, copy_version, load_version, save_version

        original_id = save_version(self.path, ModelSnapshot(None, None, None, []), label="draft")
        copy_id = copy_version(self.path, original_id, new_label="draft copy")

        _, by_layer_year, exposures_by_year = load_version(self.path, copy_id)
        self.assertEqual(by_layer_year, [])
        self.assertEqual(exposures_by_year, [])


class TestDeleteVersion(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "test.db"
        init_db(self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_delete_removes_the_version_and_cascades_its_results(self):
        from app.db import ModelSnapshot, _connect, delete_version, save_results, save_version

        version_id = save_version(self.path, ModelSnapshot(None, None, None, []), label="v1")
        save_results(
            self.path, version_id,
            [{"layer_id": 1, "layer_name": "L", "modelling_year": 2022, "ceded_paid": 0.0,
              "ceded_incurred": 0.0, "claim_count": 0, "earned_premium": 0.0, "loss_ratio": None}],
            [],
        )

        delete_version(self.path, version_id)

        with _connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM pricing_versions").fetchone()[0], 0)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM pricing_results_by_layer_year").fetchone()[0], 0
            )

    def test_deleting_a_version_with_children_orphans_rather_than_blocks(self):
        from app.db import ModelSnapshot, copy_version, delete_version, list_versions, save_version

        parent_id = save_version(self.path, ModelSnapshot(None, None, None, []), label="parent")
        child_id = copy_version(self.path, parent_id, new_label="child")

        delete_version(self.path, parent_id)  # must not raise

        remaining = {s.id: s for s in list_versions(self.path)}
        self.assertEqual(remaining[child_id].parent_id, None)


class TestDiffVersions(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "test.db"
        init_db(self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _layer(self, layer_id, occurrence_limit):
        from pyre import RILayer
        from pyre.treaty import ContractType
        return RILayer(
            layer_id=layer_id, layer_name="L", layer_type=ContractType.EXCESS_OF_LOSS,
            occurrence_attachment=100_000.0, occurrence_limit=occurrence_limit,
            aggregate_attachment=0.0, aggregate_limit=0.0, subject_lines_of_business=[],
            subject_lob_exposure_amounts=[], full_subject_premium=0.0, written_line=1.0,
            signed_line=1.0, number_of_reinstatements=0, reinstatement_cost={},
        )

    def test_detects_a_changed_layer_field_and_a_changed_result(self):
        from app.db import ModelSnapshot, diff_versions, save_results, save_version

        id_old = save_version(self.path, ModelSnapshot(None, None, None, [self._layer(1, 200_000.0)]), label="old")
        id_new = save_version(self.path, ModelSnapshot(None, None, None, [self._layer(1, 300_000.0)]), label="new")
        save_results(self.path, id_old,
            [{"layer_id": 1, "layer_name": "L", "modelling_year": 2022, "ceded_paid": 0.0,
              "ceded_incurred": 100.0, "claim_count": 1, "earned_premium": 1000.0, "loss_ratio": 0.1}], [])
        save_results(self.path, id_new,
            [{"layer_id": 1, "layer_name": "L", "modelling_year": 2022, "ceded_paid": 0.0,
              "ceded_incurred": 150.0, "claim_count": 1, "earned_premium": 1000.0, "loss_ratio": 0.15}], [])

        diff = diff_versions(self.path, id_old, id_new)

        self.assertIn(
            ("occurrence_limit", 200_000.0, 300_000.0),
            [(c.field, c.old_value, c.new_value) for c in diff.layer_changes],
        )
        self.assertEqual(len(diff.results_changes), 1)
        self.assertEqual(diff.results_changes[0].ceded_incurred_old, 100.0)
        self.assertEqual(diff.results_changes[0].ceded_incurred_new, 150.0)

    def test_no_overlap_returns_empty_diff_lists_not_an_error(self):
        from app.db import ModelSnapshot, diff_versions, save_version

        id_old = save_version(self.path, ModelSnapshot(None, None, None, [self._layer(1, 200_000.0)]), label="old")
        id_new = save_version(self.path, ModelSnapshot(None, None, None, [self._layer(2, 300_000.0)]), label="new")

        diff = diff_versions(self.path, id_old, id_new)

        self.assertEqual(diff.layer_changes, [])
        self.assertEqual(diff.results_changes, [])
        self.assertEqual(diff.claims_count_old, 0)

    def test_added_and_removed_layers_are_reported_not_silently_dropped(self):
        # The renewal workflow the version tree exists for: copy a version and
        # add a whole new layer. layer_id-intersection diffing alone makes
        # this look like "nothing changed" -- layers_added/layers_removed
        # must surface it instead.
        from app.db import ModelSnapshot, diff_versions, save_version

        id_old = save_version(
            self.path, ModelSnapshot(None, None, None, [self._layer(1, 200_000.0)]), label="old"
        )
        id_new = save_version(
            self.path,
            ModelSnapshot(None, None, None, [self._layer(1, 200_000.0), self._layer(2, 300_000.0)]),
            label="new",
        )

        diff = diff_versions(self.path, id_old, id_new)

        self.assertEqual(diff.layers_added, [2])
        self.assertEqual(diff.layers_removed, [])
        self.assertEqual(diff.layer_changes, [])  # layer 1 itself is unchanged

    def test_removed_layer_is_reported(self):
        from app.db import ModelSnapshot, diff_versions, save_version

        id_old = save_version(
            self.path,
            ModelSnapshot(None, None, None, [self._layer(1, 200_000.0), self._layer(2, 300_000.0)]),
            label="old",
        )
        id_new = save_version(
            self.path, ModelSnapshot(None, None, None, [self._layer(1, 200_000.0)]), label="new"
        )

        diff = diff_versions(self.path, id_old, id_new)

        self.assertEqual(diff.layers_added, [])
        self.assertEqual(diff.layers_removed, [2])


if __name__ == "__main__":
    unittest.main()
